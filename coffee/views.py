import uuid

import redis
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from coffee.serializers import IngredientSerializer, RecipeSerializer, RecipeIngredientSerializer, UserSerializer, \
    DraftRecipeSerializer, IngredientPicSerializer
from .minio import add_pic, delete_pic
from .models import Ingredient, Recipe, RecipeIngredient
from .permissions import IsAdmin, IsModerator, IsCreator, IsGuest
from .singletons import CreatorSingleton

session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)


def method_permission_classes(classes):
    def decorator(func):
        def decorated_func(self, *args, **kwargs):
            self.permission_classes = classes
            self.check_permissions(self.request)
            return func(self, *args, **kwargs)

        return decorated_func

    return decorator


class IngredientList(APIView):
    ingredient_serializer_class = IngredientSerializer
    recipe_serializer_class = DraftRecipeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Возвращает список ингредиентов и черновика рецепта
    @swagger_auto_schema(method='get')
    def get(self, request, format=None):
        name_filter = request.query_params.get('ingredient_name', None)
        ingredients = Ingredient.objects.filter(status="active")
        if name_filter:
            ingredients = ingredients.filter(
                ingredient_name__icontains=name_filter)
        ingredient_data = self.ingredient_serializer_class(ingredients, many=True)

        if not request.user.is_authenticated:
            draft_recipe = None
        else:
            draft_recipe = Recipe.objects.filter(recipe_status="draft", creator=request.user).first()
        draft_recipe_data = self.recipe_serializer_class(draft_recipe).data if draft_recipe else None
        if name_filter:
            return Response({
                'ingredients': ingredient_data.data,
            })
        else:

            return Response({
                'ingredients': ingredient_data.data,
                'draft_recipe': draft_recipe_data,
            })

    # Добавляет новый ингредиент
    @swagger_auto_schema(request_body=IngredientSerializer)
    @method_permission_classes((IsModerator,))
    def post(self, request, format=None):
        serializer = self.ingredient_serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngredientDetail(APIView):
    ingredient_serializer_class = IngredientSerializer
    ingredient_pic_serializer_class = IngredientPicSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Возвращает одну услугу
    @swagger_auto_schema(method='get')
    def get(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, status="active")
        serializer = self.ingredient_serializer_class(ingredient)
        return Response(serializer.data)

    # Изменение полей услуги
    @swagger_auto_schema(request_body=IngredientSerializer)
    @method_permission_classes((IsModerator,))
    def put(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, status="active")
        serializer = self.ingredient_serializer_class(ingredient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Удаление услуги
    @swagger_auto_schema(method='delete')
    @method_permission_classes((IsModerator,))
    def delete(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk)

        if not delete_pic(ingredient):
            return Response({"error": "Не удалось удалить изображение из MinIO."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        ingredient.status = 'deleted'
        ingredient.image_url = ""
        ingredient.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # Добавление изображения в услугу
    @swagger_auto_schema(request_body=IngredientPicSerializer, operation_summary="add pic")
    @method_permission_classes((IsModerator,))
    def post(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk)
        if 'pic' not in request.data:
            return Response({"error": "Нет файла изображения."}, status=status.HTTP_400_BAD_REQUEST)
        pic = request.data['pic']
        pic_result = add_pic(ingredient, pic)
        if 'error' in pic_result.data:
            return pic_result
        ingredient.save()
        serializer = self.ingredient_serializer_class(ingredient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class IngredientDraftRecipe(APIView):
    recipe_serializer_class = RecipeIngredientSerializer
    creator = CreatorSingleton.get_creator()
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Создание рецепта-черновика с выбранной услугой
    @swagger_auto_schema(request_body=RecipeIngredientSerializer)
    @method_permission_classes((IsCreator,))
    def post(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, status="active")
        draft_recipe = Recipe.objects.filter(creator=request.user, recipe_status='draft').first()

        if draft_recipe:
            RecipeIngredient.objects.create(
                recipe=draft_recipe,
                ingredient=ingredient,
                quantity=1,
                unit=ingredient.unit
            )
            message = "Ингредиент добавлен в существующий черновик"
        else:
            draft_recipe = Recipe.objects.create(
                creator=request.user,
                recipe_status='draft',
                recipe_name='Латте с карамельным сиропом',
            )
            RecipeIngredient.objects.create(
                recipe=draft_recipe,
                ingredient=ingredient,
                quantity=1,
                unit=ingredient.unit
            )
            message = "Ингредиент добавлен в новый черновик"

        return Response({"message": message},
                        status=status.HTTP_201_CREATED)

class RecipeList(APIView):
    serializer_class = RecipeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Получение заявок кроме черновик удалена
    @swagger_auto_schema(method='get')
    @method_permission_classes((IsCreator,))
    def get(self, request, format=None):
        if request.user.is_staff or request.user.is_superuser:
            recipes = Recipe.objects.all()
        else:
            recipes = Recipe.objects.exclude(recipe_status__in=['draft','deleted']).filter(creator=request.user)

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')

        if status_filter:
            recipes = recipes.filter(status=status_filter)

        if start_date and end_date:
            recipes = recipes.filter(created_at__range=[start_date, end_date])

        serializer = self.serializer_class(recipes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RecipeDetail(APIView):
    recipe_serializer_class = RecipeSerializer
    recipe_ingredient_serializer_class = RecipeIngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    # Получение заявки и ее ингредиентов
    @swagger_auto_schema(method='get')
    @method_permission_classes((IsCreator,))
    def get(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        ingredients = RecipeIngredient.objects.filter(recipe=recipe)
        ingredients_data = self.recipe_ingredient_serializer_class(ingredients, many=True).data
        serializer = self.recipe_serializer_class(recipe)
        data = serializer.data
        data['ingredients'] = ingredients_data
        return Response(data)

    # Удаление заявки
    @swagger_auto_schema(method='delete')
    @method_permission_classes((IsCreator,))
    def delete(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe.objects.filter(creator=request.user)
        recipe.recipe_status = 'deleted'
        recipe.save()
        serializer = self.recipe_serializer_class(recipe)
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)

    # Обновление доп полей заявки
    @swagger_auto_schema(request_body=RecipeSerializer)
    @method_permission_classes((IsCreator,))
    def put(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe.objects.filter(creator=request.user)
        serializer = self.recipe_serializer_class(recipe, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RecipeSubmit(APIView):
    serializer_class = RecipeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Формирование заявки
    @swagger_auto_schema(request_body=RecipeSerializer)
    @method_permission_classes((IsCreator,))
    def put(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe.objects.filter(creator=request.user)
        if not recipe.recipe_name:
            return Response({"error": "Название заявки обязательно."}, status=status.HTTP_400_BAD_REQUEST)

        recipe.recipe_status = 'submitted'
        recipe.submitted_at = timezone.now()
        recipe.save()
        serializer = self.serializer_class(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RecipeRejectOrComplete(APIView):
    serializer_class = RecipeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Завершить отклонить модератором
    @swagger_auto_schema(request_body=RecipeSerializer)
    @method_permission_classes((IsModerator,))
    def put(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        status_action = request.data.get('status_action')  # 'complete' или 'reject'
        if not recipe.submitted_at:
            return Response({"error": "Заявка не сформирована"}, status=status.HTTP_400_BAD_REQUEST)
        if status_action == 'complete':
            recipe.recipe_status = 'completed'
            recipe.completed_at = timezone.now()
            recipe.moderator = request.user
        elif status_action == 'reject':
            recipe.recipe_status = 'rejected'
            recipe.moderator = request.user
            recipe.completed_at = timezone.now()
        else:
            return Response({"error": "Некорректное действие."}, status=status.HTTP_400_BAD_REQUEST)

        recipe.save()
        serializer = self.serializer_class(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RecipeIngredientDetail(APIView):
    serializer_class = RecipeIngredientSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Удаление из заявки
    @swagger_auto_schema(method='delete')
    @method_permission_classes((IsCreator,))
    def delete(self, request, recipe_id, ingredient_id, format=None):
        recipe_ingredient = get_object_or_404(RecipeIngredient, recipe_id=recipe_id,
                                              ingredient_id=ingredient_id)
        recipe_ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Изменение количества
    @swagger_auto_schema(request_body=RecipeIngredientSerializer)
    @method_permission_classes((IsCreator,))
    def put(self, request, recipe_id, ingredient_id, format=None):
        recipe_ingredient = get_object_or_404(RecipeIngredient, recipe_id=recipe_id,
                                              ingredient_id=ingredient_id)
        serializer = self.serializer_class(recipe_ingredient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserRegistration(APIView):
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []

    # Регистрация пользователя
    @swagger_auto_schema(request_body=UserSerializer)
    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            password = serializer.validated_data['password']
            serializer.validated_data['password'] = make_password(password)

            user = User(**{key: value for key, value in serializer.validated_data.items() if
                           key not in ['groups', 'user_permissions']})
            user.save()

            groups = serializer.validated_data.get('groups', None)
            if groups:
                user.groups.set(groups)

            user_permissions = serializer.validated_data.get('user_permissions', None)
            if user_permissions:
                user.user_permissions.set(user_permissions)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserUpdate(APIView):
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Изменение данных пользователя
    @swagger_auto_schema(request_body=UserSerializer)
    @method_permission_classes((IsAdmin,))
    def put(self, request, id,format=None):
        user = get_object_or_404(User, id=id)
        serializer = self.serializer_class(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserWork(APIView):
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            permission_classes = [IsCreator | IsGuest]
        elif self.request.method == 'POST':
            permission_classes = [IsAdmin | IsModerator | IsCreator]
        elif self.request.method in ['PUT', 'DELETE']:
            permission_classes = [IsAdmin | IsModerator | IsCreator]
        else:
            permission_classes = [IsAdmin]

        return [permission() for permission in permission_classes]

class UserAuthentication(APIView):
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []

    # Аутентификация пользователя
    @swagger_auto_schema(request_body=UserSerializer)
    def post(self, request, format=None):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response({"username": "username и пароль обязательны."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Аутентификация пользователя
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Вход пользователя (создание сессии)
            login(request, user)
            random_key = str(uuid.uuid4())
            session_storage.set(random_key, username)

            response = HttpResponse({"{'status': 'ok'}"}, status=status.HTTP_200_OK)
            response.set_cookie("session_id", random_key)

            return response
        else:
            return Response({"status": "error", "error": "Неверные данные для входа"},
                            status=status.HTTP_401_UNAUTHORIZED)

class UserLogout(APIView):
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = []

    # Деавторизация пользователя
    @swagger_auto_schema(request_body=UserSerializer)
    def post(self, request, format=None):
        # Выход пользователя (завершение сессии)
        logout(request._request)
        return Response({'status': 'Success', 'message': 'Успешный выход'}, status=status.HTTP_200_OK)

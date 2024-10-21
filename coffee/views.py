
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from coffee.serializers import IngredientSerializer, RecipeSerializer, RecipeIngredientSerializer, UserSerializer
from .minio import add_pic, delete_pic
from .models import Ingredient, Recipe, RecipeIngredient
from .singletons import CreatorSingleton


class IngredientList(APIView):
    ingredient_serializer_class = IngredientSerializer
    recipe_serializer_class = RecipeSerializer
    creator = CreatorSingleton.get_creator()

    # Возвращает список ингредиентов и черновика рецепта
    def get(self, request, format=None):
        name_filter = request.query_params.get('ingredient_name', None)
        ingredients = Ingredient.objects.filter(status="active")
        if name_filter:
            ingredients = ingredients.filter(
                ingredient_name__icontains=name_filter)
        ingredient_data = self.ingredient_serializer_class(ingredients, many=True)
        draft_recipe = Recipe.objects.filter(recipe_status="draft", creator=self.creator).first()
        draft_recipe_data = self.recipe_serializer_class(draft_recipe).data if draft_recipe else None
        if name_filter:
            return Response({
                'ingredients': ingredient_data.data,
            })
        else:
            return Response({
                'ingredients': ingredient_data.data,
                'draft_recipe': draft_recipe_data
            })

    # Добавляет новый ингредиент
    def post(self, request, format=None):
        serializer = self.ingredient_serializer_class(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IngredientDetail(APIView):
    ingredient_serializer_class = IngredientSerializer

    # Возвращает одну услугу
    def get(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, status="active")
        serializer = self.ingredient_serializer_class(ingredient)
        return Response(serializer.data)

    # Изменение полей услуги
    def put(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, status="active")
        serializer = self.ingredient_serializer_class(ingredient, data=request.data, partial=True)
        if 'pic' in serializer.initial_data:
            pic_result = add_pic(ingredient, serializer.initial_data['pic'])
            if 'error' in pic_result.data:
                return pic_result
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Удаление услуги
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

    # Создание рецепта-черновика с выбранной услугой
    def post(self, request, pk, format=None):
        ingredient = get_object_or_404(Ingredient, pk=pk, status="active")
        draft_recipe = Recipe.objects.filter(creator=self.creator, recipe_status='draft').first()

        if draft_recipe:
            recipe_ingredient = RecipeIngredient.objects.create(
                recipe=draft_recipe,
                ingredient=ingredient,
                quantity=1,
                unit=ingredient.unit
            )
            message = "Ингредиент добавлен в существующий черновик"
        else:
            draft_recipe = Recipe.objects.create(
                creator=self.creator,
                recipe_status='draft',
                recipe_name='Латте с карамельным сиропом',
            )
            recipe_ingredient = RecipeIngredient.objects.create(
                recipe=draft_recipe,
                ingredient=ingredient,
                quantity=1,
                unit=ingredient.unit
            )
            message = "Ингредиент добавлен в новый черновик"

        serializer = self.recipe_serializer_class(recipe_ingredient)
        return Response({"message": message, "draft_recipe": serializer.data},
                        status=status.HTTP_201_CREATED)


class RecipeList(APIView):
    serializer_class = RecipeSerializer
    creator = CreatorSingleton.get_creator()

    # Получение заявок кроме черновик удалена
    def get(self, request, format=None):
        recipes = Recipe.objects.exclude(recipe_status__in=['deleted', 'draft']).filter(creator=self.creator)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        status_filter = request.query_params.get('status')

        if status_filter:
            recipes = recipes.filter(recipe_status=status_filter)

        if start_date and end_date:
            recipes = recipes.filter(created_at__range=[start_date, end_date])

        serializer = self.serializer_class(recipes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeDetail(APIView):
    recipe_serializer_class = RecipeSerializer
    recipe_ingredient_serializer_class = RecipeIngredientSerializer

    # Получение заявки и ее ингредиентов
    def get(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        ingredients = RecipeIngredient.objects.filter(recipe=recipe)
        ingredients_data = self.recipe_ingredient_serializer_class(ingredients, many=True).data
        serializer = self.recipe_serializer_class(recipe)
        data = serializer.data
        data['ingredients'] = ingredients_data
        return Response(data)

    # Удаление заявки
    def delete(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe.recipe_status = 'deleted'
        recipe.save()
        serializer = self.recipe_serializer_class(recipe)
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)

    # Обновление доп полей заявки
    def put(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = self.recipe_serializer_class(recipe, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RecipeSubmit(APIView):
    serializer_class = RecipeSerializer

    # Формирование заявки
    def put(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if not recipe.recipe_name:
            return Response({"error": "Название заявки обязательно."}, status=status.HTTP_400_BAD_REQUEST)

        recipe.recipe_status = 'submitted'
        recipe.submitted_at = timezone.now()
        recipe.save()
        serializer = self.serializer_class(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeRejectOrComplete(APIView):
    serializer_class = RecipeSerializer

    # Завершить отклонить модератором
    def put(self, request, pk, format=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        moderator = CreatorSingleton.get_moderator()

        status_action = request.data.get('status_action')  # 'complete' или 'reject'
        if not recipe.submitted_at:
            return Response({"error":"Заявка не сформирована"}, status=status.HTTP_400_BAD_REQUEST)
        if status_action == 'complete':
            recipe.recipe_status = 'completed'
            recipe.completed_at = timezone.now()
            recipe.moderator = moderator
        elif status_action == 'reject':
            recipe.recipe_status = 'rejected'
            recipe.moderator = moderator
            recipe.completed_at = timezone.now()
        else:
            return Response({"error": "Некорректное действие."}, status=status.HTTP_400_BAD_REQUEST)

        recipe.save()
        serializer = self.serializer_class(recipe)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RecipeIngredientDetail(APIView):
    serializer_class = RecipeIngredientSerializer

    # Удаление из заявки
    def delete(self, request, recipe_id, ingredient_id, format=None):
        recipe_ingredient = get_object_or_404(RecipeIngredient, recipe_id=recipe_id, ingredient_id=ingredient_id)
        recipe_ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Изменение количества
    def put(self, request, recipe_id, ingredient_id, format=None):
        recipe_ingredient = get_object_or_404(RecipeIngredient, recipe_id=recipe_id, ingredient_id=ingredient_id)
        serializer = self.serializer_class(recipe_ingredient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegistration(APIView):
    serializer_class = UserSerializer

    # Регистрация пользователя
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
    moderator = CreatorSingleton.get_moderator()

    # Изменение данных пользователя
    def put(self, request, format=None):
        user = self.moderator
        serializer = self.serializer_class(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAuthentication(APIView):
    serializer_class = UserSerializer

    # Аутентификация пользователя
    def post(self, request, format=None):
        return Response({"error": "Метод не определен"}, status=status.HTTP_501_NOT_IMPLEMENTED)


class UserLogout(APIView):
    serializer_class = UserSerializer
    # Деавторизация пользователя
    def post(self, request, format=None):
        return Response({"error": "Метод не определен"},status=status.HTTP_501_NOT_IMPLEMENTED)


from django.contrib.auth.models import User
from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .models import Ingredient, Recipe, RecipeIngredient
from coffee.serializers import IngredientSerializer, RecipeSerializer, RecipeIngredientSerializer,UserSerializer
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate



class IngredientList(APIView):

    ingredient_serializer_class = IngredientSerializer
    recipe_serializer_class = RecipeSerializer
    #Возвращает список услуг
    def get(self, request, format=None):
        ingredients = Ingredient.objects.filter(status = "active")
        ingredient = self.ingredient_serializer_class(ingredients, many=True)

        draft_recipe = Recipe.objects.filter(recipe_status = "draft").first()
        draft_recipe_data = self.recipe_serializer_class(draft_recipe).data if draft_recipe else None

        return Response({
            'ingredients': ingredient.data,
            'draft_recipe': draft_recipe_data
        })

    # Добавляет новую услугу
    def post(self, request, format=None):
        serializer = self.ingredient_serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class IngredientDetail(APIView):
    ingredient_serializer_class = IngredientSerializer
    recipe_serializer_class = RecipeSerializer

    def get(self,request,pk,format=None):
        try:
            ingredient = Ingredient.objects.get_object_or_404(pk=pk,status = "active")
            serializer = self.ingredient_serializer_class(ingredient)
            return Response(serializer.data)
        except Ingredient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request,pk,format=None):
        try:
            ingredient = Ingredient.objects.get_object_or_404(pk=pk, status = "active")
            serializer = self.ingredient_serializer_class(ingredient, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Ingredient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self,request,pk,format=None):
        try:
            ingredient = Ingredient.objects.get_object_or_404(pk=pk)
            ingredient.status = 'deleted'  # Логическое удаление
            ingredient.image_filename = ""  # Удаление изображения
            ingredient.save()
            return Response(self.ingredient_serializer_class(ingredient).data, status=status.HTTP_204_NO_CONTENT)
        except Ingredient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


    def post(self,request,pk,format=None):
        try:
            ingredient = Ingredient.objects.get_object_or_404(pk=pk)
            ingredient.image_filename = request.data.get('image_filename')
            ingredient.save()
            serializer = self.ingredient_serializer_class(ingredient)
            return Response(serializer, status=status.HTTP_201_CREATED)
        except Ingredient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class IngredientDraftRecipe(APIView):
    recipe_serializer_class = RecipeIngredientSerializer

    def post(self, request, pk, format=None):
        try:
            ingredient = Ingredient.objects.get_object_or_404(pk=pk, status="active")

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
            serializer = self.recipe_serializer_class(draft_recipe)
            return Response({"message": "Услуга добавлена в черновик", "draft_recipe": serializer.data},
                            status=status.HTTP_201_CREATED)
        except Ingredient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class RecipeList(APIView):
    serializer_class = RecipeSerializer

    def get(self, request, format=None):
        recipes = Recipe.objects.exclude(recipe_status__in=['deleted', 'draft']).filter(
            creator=request.user
        ) | Recipe.objects.exclude(recipe_status__in=['deleted', 'draft']).filter(
            moderator=request.user
        )
        serializer = self.serializer_class(recipes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RecipeDetail(APIView):
    recipe_serializer_class = RecipeSerializer
    recipe_ingredient_serializer_class = RecipeIngredientSerializer

    def get(self, request, pk, format=None):
        try:
            recipe = Recipe.objects.get_object_or_404(pk=pk)
            ingredients = RecipeIngredient.objects.filter(recipe=recipe)
            ingredients_data = self.recipe_ingredient_serializer_class(ingredients, many=True).data
            serializer = self.recipe_serializer_class(recipe)
            data = serializer.data
            data['ingredients'] = ingredients_data
            return Response(data)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, format=None):
        try:
            recipe = Recipe.objects.get(pk=pk)
            recipe.recipe_status = 'deleted'
            recipe.save()
            serializer = self.recipe_serializer_class(recipe)
            return Response(serializer.data,status=status.HTTP_204_NO_CONTENT)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class RecipeUpdate(APIView):
    serializer_class = RecipeSerializer
    #изменение доп. полей заявки
    def put(self, request, pk, format=None):
        try:
            recipe = Recipe.objects.get(pk=pk)
            serializer = self.serializer_class(recipe, data=request.data,
                                               partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class RecipeSubmit(APIView):
    serializer_class = RecipeSerializer
    # Формирование заявки создателем с проверкой обязательных полей
    def put(self, request, pk, format=None):
        try:
            recipe = Recipe.objects.get(pk=pk)
            # Проверка на обязательные поля
            if not recipe.recipe_name:
                return Response({"error": "Название заявки обязательно."}, status=status.HTTP_400_BAD_REQUEST)

            recipe.recipe_status = 'submitted'
            recipe.submitted_at = timezone.now()
            recipe.save()
            serializer = self.serializer_class(recipe)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class RecipeRejectOrComplete(APIView):
    serializer_class = RecipeSerializer
    #завершить/отклонить модератором.
    def put(self, request, pk, format=None):
        try:
            recipe = Recipe.objects.get(pk=pk)

            # Проверка, является ли пользователь модератором
            if not request.user.is_staff:  # Пример проверки на модератора
                return Response({"error": "У вас нет прав для выполнения этого действия."},
                                status=status.HTTP_403_FORBIDDEN)

            # Определение статуса заявки (завершена или отклонена)
            status_action = request.data.get('status_action')  # 'complete' или 'reject'

            if status_action == 'complete':
                recipe.recipe_status = 'completed'
                recipe.completed_at = timezone.now()
                recipe.moderator = request.user
                recipe.total_cost()

            elif status_action == 'reject':
                recipe.recipe_status = 'rejected'
                recipe.moderator = request.user  # Установка модератора
                recipe.completed_at = timezone.now()  # Установка даты завершения
            else:
                return Response({"error": "Некорректное действие."}, status=status.HTTP_400_BAD_REQUEST)

            recipe.save()
            serializer = self.serializer_class(recipe)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Recipe.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
class RecipeIngredientDetail(APIView):
    serializer_class = RecipeIngredientSerializer

    def delete(self, request, recipe_id, ingredient_id, format=None):
        try:
            recipe_ingredient = RecipeIngredient.objects.get_object_or_404(recipe_id=recipe_id, ingredient_id=ingredient_id)
            recipe_ingredient.delete()
            serializer = self.serializer_class(recipe_ingredient)
            return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)
        except RecipeIngredient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, recipe_id, ingredient_id, format=None):
        try:
            recipe_ingredient = RecipeIngredient.objects.get_object_or_404(recipe_id=recipe_id, ingredient_id=ingredient_id)
            serializer = self.serializer_class(recipe_ingredient, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except RecipeIngredient.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class UserAuthentication(APIView):
    serializer_class = UserSerializer

    def post(self, request, format=None):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            password = serializer.validated_data['password']
            serializer.validated_data['password'] = make_password(password)
            user = User(**serializer.validated_data)
            user.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserUpdate(APIView):
    serializer_class = UserSerializer

    def put(self, request, format=None):
        user = request.user
        serializer = UserSerializer(user, data=request.data,
                                    partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserAuthorization(APIView):
    serializer_class = UserSerializer

    def post(self, request, format=None):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key}, status=status.HTTP_200_OK)
        return Response({"message": "Неверные учетные данные."}, status=status.HTTP_401_UNAUTHORIZED)

class UserLogout(APIView):
    serializer_class = UserSerializer
    def post(self, request, format=None):
        request.user.auth_token.delete()  # Удаляем токен аутентификации
        return Response({"message": "Вы успешно вышли из системы."}, status=status.HTTP_200_OK)

from django.contrib.auth.models import User
from rest_framework import serializers

from coffee.models import Ingredient
from coffee.models import Recipe
from coffee.models import RecipeIngredient


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'

class DraftRecipeSerializer(serializers.ModelSerializer):
    ingredient_count = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ['id', 'ingredient_count']  # Указываем только нужные поля

    def get_ingredient_count(self, obj):
        return RecipeIngredient.objects.filter(recipe=obj).count()

class RecipeSerializer(serializers.ModelSerializer):
    creator = serializers.CharField(source='creator.username', read_only=True)

    class Meta:
        model = Recipe
        fields = '__all__'


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer()

    class Meta:
        model = RecipeIngredient
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

    def validate(self, attrs):
        return attrs

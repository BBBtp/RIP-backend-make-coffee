from itertools import count
from venv import logger

from django.db import connection
from django.shortcuts import render, get_object_or_404, redirect
from .models import Ingredient, Recipe, RecipeIngredient

def add_ingredient_to_current_recipe(request):
    if request.method == 'POST':
        ingredient_id = request.POST.get('ingredient_id')
        recipe_id = request.POST.get('recipe_id')
        next_url = request.POST.get('next')

        if not ingredient_id:
            print("Error: Ingredient ID not provided")
            return render(request, 'ingredients.html')

        ingredient = get_object_or_404(Ingredient, pk=ingredient_id)

        # Проверяем, есть ли уже черновик рецепта, если нет — создаем новый
        current_recipe, created = Recipe.objects.get_or_create(
            recipe_status='draft', creator=request.user,
            defaults={'recipe_name': 'Латте с карамельным сиропом'}
        )

        # Добавляем ингредиент в рецепт
        recipe_ingredient, created = RecipeIngredient.objects.get_or_create(
            recipe=current_recipe, ingredient=ingredient,
            defaults={'quantity': 1, 'unit': ingredient.unit}
        )

        if not created:
            # Если ингредиент уже в рецепте, увеличиваем количество
            recipe_ingredient.quantity += 1
            recipe_ingredient.save()

        return redirect(next_url)


def ingredients_list(request):
    query = request.GET.get('search_ingredient', '').strip()

    # Фильтруем ингредиенты по статусу (только активные)
    filtered_ingredients = Ingredient.objects.filter(
        status='active')  # Предполагается, что статус активных ингредиентов 'active'

    # Если есть поисковой запрос, дополнительно фильтруем по названию
    if query:
        filtered_ingredients = filtered_ingredients.filter(ingredient_name__icontains=query)

    # Получаем существующий черновик рецепта, но не создаем новый на этом этапе
    current_recipe = Recipe.objects.filter(recipe_status='draft', creator=request.user).first()
    count = RecipeIngredient.objects.filter(recipe_id=current_recipe.id).count() if current_recipe else 0

    return render(request, 'ingredients.html', {
        'ingredients': filtered_ingredients,
        'count': count,
        'current_recipe_id': current_recipe.id if current_recipe else None
    })

def delete_recipe(request):
    if request.method == 'POST':
        recipe_id = request.POST.get('recipe_id')
        user = request.user
        if recipe_id:
            with connection.cursor() as cursor:
                print(f"Delete recipe {recipe_id} and {request.user.id}")
                cursor.execute(
                    "UPDATE public.coffee_recipe SET recipe_status = 'deleted' WHERE id = %s AND creator_id=%s AND recipe_status = 'draft'",
                    [recipe_id, user.id]
                )
            return redirect('ingridients')
    return redirect('ingridients')

def ingridient_about(request, id):
    ingredient = Ingredient.objects.get(id=id)
    return render(request, 'about_ingridient.html', {'ingredient': ingredient})

def recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    # Получаем связанные ингредиенты через модель RecipeIngredient
    recipe_ingredients = RecipeIngredient.objects.filter(recipe=recipe)
    cart_items = []
    total_mass = 0

    for item in recipe_ingredients:
        ingredient = item.ingredient
        image_url = ingredient.image_url.url if ingredient.image_url else ''
        cart_items.append({
            'name': ingredient.ingredient_name,
            'quantity': item.quantity,
            'unit': item.unit,
            'price': ingredient.price,
            'image_url': image_url
        })
        total_mass += item.quantity

    return render(request, 'recipe.html', {'cart_items': cart_items, 'total_mass': total_mass, 'recipe_name': recipe.recipe_name, 'current_recipe_id': recipe.id})

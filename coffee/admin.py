from django.contrib import admin
from .models import Recipe
from .models import Ingredient
from .models import RecipeIngredient
from .models import UserProfile


admin.site.register(Recipe)
admin.site.register(Ingredient)
admin.site.register(RecipeIngredient)
admin.site.register(UserProfile)
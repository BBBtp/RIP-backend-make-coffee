"""
URL configuration for web_5sem_backennd project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from coffee.views import *
from rest_framework import routers
from django.urls import include, path

router = routers.DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # URL для работы с ингредиентами
    path('ingredients/', IngredientList.as_view(), name='ingredient_list'),  # GET, POST
    path('ingredients/<int:pk>/', IngredientDetail.as_view(), name='ingredient_detail'),  # GET, PUT, DELETE
    path('ingredients/<int:pk>/draft-recipe/', IngredientDraftRecipe.as_view(), name='ingredient_draft_recipe'),
    # POST для создания черновика

    # URL для работы с рецептами
    path('recipes/', RecipeList.as_view(), name='recipe_list'),  # GET
    path('recipes/<int:pk>/', RecipeDetail.as_view(), name='recipe_detail'),  # GET, DELETE
    path('recipes/<int:pk>/update/', RecipeUpdate.as_view(), name='recipe_update'),  # PUT
    path('recipes/<int:pk>/submit/', RecipeSubmit.as_view(), name='recipe_submit'),  # PUT для отправки заявки
    path('recipes/<int:pk>/reject-or-complete/', RecipeRejectOrComplete.as_view(), name='recipe_reject_or_complete'),
    # PUT для завершения/отклонения
    path('recipes/<int:recipe_id>/ingredients/<int:ingredient_id>/', RecipeIngredientDetail.as_view(),
         name='recipe_ingredient_detail'),  # PUT, DELETE

    # URL для работы с пользователями
    path('users/register/', UserAuthentication.as_view(), name='user_registration'),  # POST
    path('users/update/', UserUpdate.as_view(), name='user_update'),  # PUT
    path('users/login/', UserAuthorization.as_view(), name='user_login'),  # POST
    path('users/logout/', UserLogout.as_view(), name='user_logout'),  # POST
]
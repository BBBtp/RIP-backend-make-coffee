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
from django.urls import path
from coffee import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.ingredients_list, name='ingridients'),
    path('ingridient_about/<int:id>/', views.ingridient_about, name='ingridient_about'),
    path('recipe/<int:recipe_id>/', views.recipe, name='recipe'),
    path('add-ingredient/', views.add_ingredient_to_current_recipe, name='add_ingredient_to_current_recipe'),
    path('delete_recipe/', views.delete_recipe, name='delete_recipe'),
]
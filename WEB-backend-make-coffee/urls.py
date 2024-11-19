from django.contrib import admin
from coffee.views import *
from rest_framework import routers, permissions
from django.urls import include, path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = routers.DefaultRouter()

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    # URL для работы с ингредиентами
    path('ingredients/', IngredientList.as_view(), name='ingredient_list'),  # GET, POST
    path('ingredients/<int:pk>/', IngredientDetail.as_view(), name='ingredient_detail'),  # GET, PUT, DELETE
    path('ingredients/<int:pk>/draft-recipe/', IngredientDraftRecipe.as_view(), name='ingredient_draft_recipe'),
    # POST для создания черновика

    # URL для работы с рецептами
    path('recipes/', RecipeList.as_view(), name='recipe_list'),  # GET
    path('recipes/<int:pk>/', RecipeDetail.as_view(), name='recipe_detail'),  # GET, DELETE, PUT
    path('recipes/<int:pk>/submit/', RecipeSubmit.as_view(), name='recipe_submit'),  # PUT для отправки заявки
    path('recipes/<int:pk>/reject-or-complete/', RecipeRejectOrComplete.as_view(), name='recipe_reject_or_complete'),
    # PUT для завершения/отклонения
    path('recipes/<int:recipe_id>/ingredients/<int:ingredient_id>/', RecipeIngredientDetail.as_view(),
         name='recipe_ingredient_detail'),  # PUT, DELETE

    # URL для работы с пользователями
    path('users/register/', UserRegistration.as_view(), name='user_registration'),  # POST
    path('users/<int:pk>/update/', UserUpdate.as_view(), name='user_update'),  # PUT
    path('users/login/', UserAuthentication.as_view(), name='user_login'),  # POST
    path('users/logout/', UserLogout.as_view(), name='user_logout'),  # POST
]

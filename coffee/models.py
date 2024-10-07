from django.contrib.auth.models import User
from django.db import models


class Ingredient(models.Model):
    STATUS_CHOICES = [
        ('active', 'Действует'),
        ('deleted', 'Удален'),
    ]
    ingredient_name = models.CharField(max_length=255, verbose_name="Название")
    description = models.CharField(max_length=5000, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    unit = models.CharField(max_length=10, verbose_name="Единица измерения")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active', verbose_name="Статус")
    image_url = models.URLField(verbose_name="Ссылка на изображение", max_length=1000, blank=True)

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return f"{self.ingredient_name} Статус: {self.get_status_display()}"


class Recipe(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('submitted', 'Сформирован'),
        ('completed', 'Завершен'),
        ('rejected', 'Отклонен'),
        ('deleted', 'Удален')
    ]

    recipe_name = models.CharField(max_length=255, null=True, verbose_name="Название")
    recipe_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата формирования")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    creator = models.ForeignKey(User, related_name='created_recipes', on_delete=models.CASCADE,
                                verbose_name="Создатель")
    moderator = models.ForeignKey(User, related_name='moderated_recipes', on_delete=models.SET_NULL, null=True,
                                  blank=True, verbose_name="Модератор")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name="Общая стоимость")

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return f'Рецепт: {self.recipe_name}, статус: {self.get_recipe_status_display()}'

    @property
    def calculate_total_cost(self):
        total = sum(ingredient.quantity * ingredient.ingredient.price for ingredient in self.ingredients.all())
        return total

    def save(self, *args, **kwargs):
        if self.recipe_status == 'completed':
            self.total_cost = self.calculate_total_cost
        super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name='ingredients', on_delete=models.CASCADE, verbose_name="Рецепт")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, verbose_name="Ингредиент")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Количество")
    unit = models.CharField(max_length=10, verbose_name="Единица измерения")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['recipe', 'ingredient'], name='unique_recipe_ingredient')
        ]
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'

    def save(self, *args, **kwargs):
        if not self.unit and self.ingredient:
            self.unit = self.ingredient.unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} {self.unit} {self.ingredient.ingredient_name} для {self.recipe.recipe_name}"

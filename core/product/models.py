from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from decimal import Decimal
from django.db.models import PositiveIntegerField
from .choices import ProductStatusEnum, BannerPositionEnum


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата последнего обновления', auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField('Название', max_length=250)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Product(TimeStampedModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        verbose_name='Категория',
        related_name='products'
    )
    name = models.CharField('Название', max_length=250)
    description = models.TextField('Описание')
    main_cover = models.ImageField('Основное фото', upload_to='products/main_cover')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    discount_percent: PositiveIntegerField = models.PositiveIntegerField(
        'Скидка (%)',
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    is_active = models.BooleanField('Активно', default=True)
    status = models.CharField(
        choices=ProductStatusEnum.choices,
        default=ProductStatusEnum.ON_SALE,
        verbose_name='Статус',
        max_length=30
    )
    @property
    def final_price(self) -> Decimal:
        if self.discount_percent:
            discount = Decimal(self.discount_percent) / Decimal('100')
            return (self.price * (1 - discount)).quantize(Decimal('0.01'))
        return self.price

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']


class Image(TimeStampedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар'
    )
    file = models.ImageField('Изображение', upload_to='products/detail_image')

    def __str__(self):
        return self.file.name

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'


class Banner(TimeStampedModel):
    name = models.CharField('Название', max_length=250)
    description = models.TextField('Описание')
    image = models.ImageField('Изображение', upload_to='banner')
    position = models.CharField(
        choices=BannerPositionEnum.choices,
        max_length=50,
        verbose_name='Расположение'
    )
    is_active = models.BooleanField('Активно', default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Баннер'
        verbose_name_plural = 'Баннеры'
        ordering = ['name']


class Brand(TimeStampedModel):
    name = models.CharField('Название', max_length=100)
    logo = models.ImageField('Логотип', upload_to='brands/logo')
    is_active = models.BooleanField('Активно', default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ['name']

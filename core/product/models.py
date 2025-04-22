from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from decimal import Decimal
from .choices import ProductStatusEnum, BannerPositionEnum, OrderStatusEnum
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator


User = get_user_model()


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


class Size(models.Model):
    VALID_SIZES = {'S', 'M', 'L', 'XL'}

    name = models.CharField('Размер', max_length=10, unique=True)

    def save(self, *args, **kwargs):
        if self.name not in self.VALID_SIZES:
            raise ValueError(f"Размер должен быть одним из: {', '.join(self.VALID_SIZES)}")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Размер'
        verbose_name_plural = 'Размеры'
        ordering = ['name']


class Cart(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь'
    )
    def __str__(self):
        return f"Корзина {self.user.username}"

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    size = models.ForeignKey(
        'Size',
        on_delete=models.CASCADE,
        verbose_name='Размер'
    )
    quantity = models.PositiveIntegerField(
        'Количество',
        default=1,
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return f"{self.product.name} ({self.size.name}) x{self.quantity}"

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ('cart', 'product', 'size')


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
    discount_percent = models.PositiveIntegerField(
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

    def available_sizes(self):
        return self.inventory.filter(stock__gt=0).select_related('size')

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


class Favorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Товар'
    )
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ('user', 'product')


class ProductSizeInventory(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='inventory',
        verbose_name='Товар'
    )
    size = models.ForeignKey(
        Size,
        on_delete=models.CASCADE,
        verbose_name='Размер'
    )
    stock = models.PositiveIntegerField(
        'Количество в наличии',
        default=0,
        validators=[MinValueValidator(0)]
    )

    def __str__(self):
        return f"{self.product.name} - {self.size.name} ({self.stock} шт.)"

    class Meta:
        verbose_name = 'Запас товара'
        verbose_name_plural = 'Запасы товаров'
        unique_together = ('product', 'size')


class Order(TimeStampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='Пользователь'
    )
    total = models.DecimalField('Общая сумма', max_digits=10, decimal_places=2)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=OrderStatusEnum.choices,
        default=OrderStatusEnum.IN_PROGRESS
    )
    receipt = models.FileField('Чек', upload_to='orders/receipts', blank=True, null=True)

    def __str__(self):
        return f"Заказ {self.id} ({self.user.username})"

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    size = models.ForeignKey(
        'Size',
        on_delete=models.CASCADE,
        verbose_name='Размер'
    )
    quantity = models.PositiveIntegerField('Количество', validators=[MinValueValidator(1)])
    price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} ({self.size.name}) x{self.quantity}"

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'
        unique_together = ('order', 'product', 'size')


class PaymentQR(models.Model):
    name = models.CharField('Название', max_length=100, help_text='Например, "Сбербанк" или "ЮMoney"')
    image = models.ImageField('QR-код', upload_to='qr_codes')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'QR-код оплаты'
        verbose_name_plural = 'QR-коды оплаты'

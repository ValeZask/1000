from django.core.validators import FileExtensionValidator
from rest_framework import serializers
from decimal import Decimal
from .models import (
    Product, Banner, Brand, Category, Size,
    Image, Cart, CartItem, Favorite, ProductSizeInventory,
    Order, OrderItem, PaymentQR
)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class BannerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'name', 'description', 'image', 'get_position_display')


class BrandListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ('id', 'name', 'logo', 'is_active')


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'price', 'discount_percent', 'final_price', 'main_cover', 'get_status_display')

    def get_final_price(self, obj):
        return obj.final_price


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ('id', 'name')


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ('id', 'file')


class ProductSizeInventorySerializer(serializers.ModelSerializer):
    size = SizeSerializer(read_only=True)

    class Meta:
        model = ProductSizeInventory
        fields = ('size', 'stock')


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    final_price = serializers.SerializerMethodField()
    images = ImageSerializer(many=True, read_only=True)
    sizes = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'price', 'discount_percent', 'final_price',
                  'description', 'main_cover', 'images', 'sizes', 'get_status_display')

    def get_final_price(self, obj):
        return obj.final_price  # Вызываем @property

    def get_sizes(self, obj):
        inventory = obj.inventory.filter(stock__gt=0).select_related('size')
        return ProductSizeInventorySerializer(inventory, many=True).data


class RelatedProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category', 'price', 'final_price', 'main_cover')


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    size = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Size.objects.all(),
        allow_null=False
    )
    product_details = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'product_details', 'size', 'quantity', 'subtotal')

    def validate(self, data):
        product = data['product']
        size = data['size']
        quantity = data.get('quantity', 1)

        inventory = ProductSizeInventory.objects.filter(product=product, size=size).first()
        if not inventory:
            raise serializers.ValidationError({"size": "Выбранный размер недоступен для этого товара."})

        if quantity > inventory.stock:
            raise serializers.ValidationError({
                "quantity": f"Недостаточно товара. В наличии: {inventory.stock} шт."
            })

        return data

    def get_product_details(self, obj):
        return {
            'name': obj.product.name,
            'category': CategorySerializer(obj.product.category).data,
            'main_cover': obj.product.main_cover.url,
            'final_price': obj.product.final_price
        }

    def get_subtotal(self, obj):
        return (obj.product.final_price * obj.quantity).quantize(Decimal('0.01'))


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    shipping_cost = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'user', 'items', 'shipping_cost', 'total')

    def get_total(self, obj):
        total = sum(item.product.final_price * item.quantity for item in obj.items.all())
        shipping = self.get_shipping_cost(obj)
        return (total + shipping).quantize(Decimal('0.01'))

    def get_shipping_cost(self, obj):
        total = sum(item.product.final_price * item.quantity for item in obj.items.all())
        return Decimal('10.00') if total < Decimal('100.00') else Decimal('0.00')


class FavoriteSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ('id', 'product', 'created_at')

    def get_product(self, obj):
        return {
            'id': obj.product.id,
            'name': obj.product.name,
            'category': CategorySerializer(obj.product.category).data,
            'main_cover': obj.product.main_cover.url,
            'final_price': obj.product.final_price
        }


class PaymentQRSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentQR
        fields = ('id', 'name', 'image')


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    size = serializers.SlugRelatedField(slug_field='name', queryset=Size.objects.all())
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ('product', 'size', 'quantity', 'price')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    receipt = serializers.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])],
        allow_null=True,
        required=False
    )

    class Meta:
        model = Order
        fields = ('id', 'user', 'items', 'total', 'status', 'receipt', 'created_at')
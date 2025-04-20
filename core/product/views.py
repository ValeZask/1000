from rest_framework.views import APIView, Response
from django.db.models import F, Q
from rest_framework.permissions import IsAuthenticated
from .models import Product, Banner, Brand, Cart, CartItem, Size, Image, Favorite
from django.shortcuts import get_object_or_404
from .models import Product
from rest_framework import status

from .serializers import (
    BannerListSerializer,
    BrandListSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    RelatedProductSerializer,
    CartItemSerializer,
    CartSerializer, SizeSerializer, FavoriteSerializer,
)


class IndexView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banners = Banner.objects.filter(is_active=True)
        brands = Brand.objects.filter(is_active=True)

        # TODO: Фильтрация пол самым продаваемым
        best_sellers_products = Product.objects.filter(is_active=True).select_related('category')
        promo_products = Product.objects.filter(discount_percent__gt=0, is_active=True).select_related('category')

        banners_serializer = BannerListSerializer(banners, many=True)
        brands_serializer = BrandListSerializer(brands, many=True)
        best_sellers_products_serializer = ProductListSerializer(best_sellers_products, many=True)
        promo_products_serializer = ProductListSerializer(promo_products, many=True)

        data = {
            "banners": banners_serializer.data,
            "brands": brands_serializer.data,
            "best_sellers_products": best_sellers_products_serializer.data,
            "promo_products": promo_products_serializer.data
        }

        return Response(data)


class ProductDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related('images', 'sizes'),
            pk=pk, is_active=True
        )

        related_products = Product.objects.filter(
            category=product.category, is_active=True
        ).exclude(pk=pk).select_related('category')[:4]

        product_serializer = ProductDetailSerializer(product)
        related_products_serializer = RelatedProductSerializer(related_products, many=True)

        data = {
            'product': product_serializer.data,
            'related_products': related_products_serializer.data
        }

        return Response(data)


class SizeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sizes = Size.objects.all()
        serializer = SizeSerializer(sizes, many=True)
        return Response(serializer.data)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    def post(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.validated_data['product']
            size = serializer.validated_data['size']  # Теперь size — это объект Size
            quantity = serializer.validated_data['quantity']

            # Проверяем, есть ли товар с таким размером
            if size not in product.sizes.all():
                return Response({"error": "Выбранный размер недоступен для этого товара"},
                                status=status.HTTP_400_BAD_REQUEST)

            # Проверяем или обновляем существующий элемент
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()

            return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        # Проверяем входные данные
        quantity = request.data.get('quantity')
        size_name = request.data.get('size')  # Теперь size — строка, например "M"

        if quantity is not None:
            if not isinstance(quantity, int) or quantity < 1:
                return Response({"error": "Количество должно быть положительным числом"},
                                status=status.HTTP_400_BAD_REQUEST)
            cart_item.quantity = quantity

        if size_name is not None:
            size = get_object_or_404(Size, name=size_name)
            if size not in cart_item.product.sizes.all():
                return Response({"error": "Выбранный размер недоступен для этого товара"},
                                status=status.HTTP_400_BAD_REQUEST)
            # Проверяем, нет ли уже такого элемента с другим размером
            if CartItem.objects.filter(cart=cart, product=cart_item.product, size=size).exclude(
                    id=cart_item.id).exists():
                return Response({"error": "Товар с этим размером уже есть в корзине"},
                                status=status.HTTP_400_BAD_REQUEST)
            cart_item.size = size

        cart_item.save()
        return Response(CartSerializer(cart).data)

    def delete(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        return Response(CartSerializer(cart).data)


class FavoriteListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favorites = Favorite.objects.filter(
            user=request.user,
            product__is_active=True
        ).select_related('product__category')
        serializer = FavoriteSerializer(favorites, many=True)
        return Response(serializer.data)


class FavoriteToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id, is_active=True)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            product=product
        )
        if not created:
            favorite.delete()
            return Response({"status": "removed"}, status=status.HTTP_200_OK)

        return Response(FavoriteSerializer(favorite).data, status=status.HTTP_201_CREATED)
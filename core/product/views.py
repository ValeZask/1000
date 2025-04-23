from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView, Response
from django.db.models import F, Q, Count, ExpressionWrapper, DecimalField
from rest_framework.permissions import IsAuthenticated
from .choices import OrderStatusEnum
from django.shortcuts import get_object_or_404
from rest_framework import status
from .models import (
    Product, Banner, Brand, Cart,
    CartItem, Size, Image,
    Favorite, ProductSizeInventory,
    OrderItem, PaymentQR, Order)
from .serializers import (
    BannerListSerializer,
    BrandListSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    RelatedProductSerializer,
    CartItemSerializer,
    CartSerializer, SizeSerializer,
    FavoriteSerializer, PaymentQRSerializer,
    OrderSerializer,
)


class IndexView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        banners = Banner.objects.filter(is_active=True)
        brands = Brand.objects.filter(is_active=True)

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
            Product.objects.select_related('category').prefetch_related('images', 'inventory'),
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
            size = serializer.validated_data['size']
            quantity = serializer.validated_data['quantity']

            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )
            if not created:
                new_quantity = cart_item.quantity + quantity
                inventory = ProductSizeInventory.objects.filter(product=product, size=size).first()
                if new_quantity > inventory.stock:
                    return Response({
                        "error": f"Недостаточно товара. В наличии: {inventory.stock} шт."
                    }, status=status.HTTP_400_BAD_REQUEST)
                cart_item.quantity = new_quantity
                cart_item.save()

            return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        quantity = request.data.get('quantity')
        size_name = request.data.get('size')

        if quantity is not None:
            if not isinstance(quantity, int) or quantity < 1:
                return Response({"error": "Количество должно быть положительным числом"},
                                status=status.HTTP_400_BAD_REQUEST)
            # Проверяем запас
            inventory = ProductSizeInventory.objects.filter(
                product=cart_item.product, size=cart_item.size
            ).first()
            if quantity > inventory.stock:
                return Response({
                    "error": f"Недостаточно товара. В наличии: {inventory.stock} шт."
                }, status=status.HTTP_400_BAD_REQUEST)
            cart_item.quantity = quantity

        if size_name is not None:
            size = get_object_or_404(Size, name=size_name)
            inventory = ProductSizeInventory.objects.filter(product=cart_item.product, size=size).first()
            if not inventory:
                return Response({"error": "Выбранный размер недоступен для этого товара"},
                                status=status.HTTP_400_BAD_REQUEST)
            if inventory.stock < cart_item.quantity:
                return Response({
                    "error": f"Недостаточно товара для размера {size_name}. В наличии: {inventory.stock} шт."
                }, status=status.HTTP_400_BAD_REQUEST)
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


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        sort = request.query_params.get('sort', 'new')
        products = Product.objects.filter(is_active=True).select_related('category')

        products = products.annotate(
            computed_final_price=ExpressionWrapper(
                F('price') * (1 - F('discount_percent') / 100.0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )

        if sort == 'popular':
            products = products.annotate(
                popularity=Count('favorited_by')
            ).order_by('-popularity', 'name')
        elif sort == 'new':
            products = products.order_by('-created_at')
        elif sort == 'cheap':
            products = products.order_by('computed_final_price')
        elif sort == 'expensive':
            products = products.order_by('-computed_final_price')
        else:
            return Response(
                {"error": "Неверный параметр сортировки. Используйте: popular, new, cheap, expensive"},
                status=400
            )

        paginator = self.pagination_class()
        paginated_products = paginator.paginate_queryset(products, request)
        serializer = ProductListSerializer(paginated_products, many=True)

        return paginator.get_paginated_response(serializer.data)


class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        item_ids = request.data.get('item_ids', None)
        if item_ids:
            cart_items = CartItem.objects.filter(id__in=item_ids, cart=cart)
        else:
            cart_items = cart.items.all()

        if not cart_items:
            return Response({"error": "Корзина пуста или товары не найдены"}, status=status.HTTP_400_BAD_REQUEST)

        for item in cart_items:
            inventory = ProductSizeInventory.objects.filter(product=item.product, size=item.size).first()
            if not inventory or inventory.stock < item.quantity:
                return Response({
                    "error": f"Недостаточно товара: {item.product.name} ({item.size.name})"
                }, status=status.HTTP_400_BAD_REQUEST)

        total = sum(item.product.final_price * item.quantity for item in cart_items)
        order = Order.objects.create(
            user=request.user,
            total=total,
            status=OrderStatusEnum.IN_PROGRESS
        )

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                size=item.size,
                quantity=item.quantity,
                price=item.product.final_price
            )

        if item_ids:
            CartItem.objects.filter(id__in=item_ids, cart=cart).delete()
        else:
            cart.items.all().delete()

        payment_qrs = PaymentQR.objects.all()
        qr_serializer = PaymentQRSerializer(payment_qrs, many=True)

        response_data = OrderSerializer(order).data
        response_data['payment_qrs'] = qr_serializer.data

        return Response(response_data, status=status.HTTP_201_CREATED)


class OrderReceiptUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user, status=OrderStatusEnum.IN_PROGRESS)
        receipt = request.FILES.get('receipt')
        if not receipt:
            return Response({"error": "Чек обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        if receipt.size > 5 * 1024 * 1024:
            return Response({"error": "Файл чека слишком большой (максимум 5 МБ)"}, status=status.HTTP_400_BAD_REQUEST)

        order.receipt = receipt
        order.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)


class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id, user=request.user)
        return Response(OrderSerializer(order).data)

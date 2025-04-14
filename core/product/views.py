from rest_framework.views import APIView, Response
from django.db.models import F, Q
from rest_framework.permissions import IsAuthenticated

from .models import Product, Banner, Brand
from .serializers import BannerListSerializer, BrandListSerializer, ProductListSerializer


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

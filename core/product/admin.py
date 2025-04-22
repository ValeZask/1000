from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from .choices import OrderStatusEnum
from .models import (
    Product, Banner, Brand, Category, Size, Image,
    Cart, CartItem, Favorite, ProductSizeInventory,
    Order, OrderItem, PaymentQR
)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'size', 'quantity', 'price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total', 'status', 'receipt_preview', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id')
    readonly_fields = ('total', 'created_at', 'updated_at', 'receipt_preview')
    inlines = [OrderItemInline]
    actions = ['mark_accepted', 'mark_rejected']

    def receipt_preview(self, obj):
        if obj.receipt:
            return format_html('<a href="{}" target="_blank">Просмотреть чек</a>', obj.receipt.url)
        return "Нет чека"

    receipt_preview.short_description = 'Чек'

    def mark_accepted(self, request, queryset):
        success_count = 0
        error_count = 0

        for order in queryset:
            try:
                if order.status != OrderStatusEnum.ACCEPTED:
                    order.status = OrderStatusEnum.ACCEPTED
                    order.save()
                    success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request, f"Ошибка при обработке заказа {order.id}: {str(e)}",
                    level='ERROR'
                )

        if success_count:
            self.message_user(
                request, f"Успешно принято {success_count} заказов",
                level='SUCCESS'
            )
        if error_count:
            self.message_user(
                request, f"Не удалось обработать {error_count} заказов",
                level='ERROR'
            )


    def mark_rejected(self, request, queryset):
        queryset.update(status=OrderStatusEnum.REJECTED)
        self.message_user(request, f"Успешно отклонено {queryset.count()} заказов.", level='SUCCESS')

    mark_rejected.short_description = "Пометить как отклонено"


@admin.register(PaymentQR)
class PaymentQRAdmin(admin.ModelAdmin):
    list_display = ('name', 'image_preview', 'created_at')
    readonly_fields = ('image_preview', 'created_at')
    search_fields = ('name',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = 'QR-код'


class ImageInline(admin.TabularInline):
    model = Image
    extra = 1
    fields = ('file', 'image_preview')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.file:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.file.url)
        return "Нет изображения"
    image_preview.short_description = 'Предпросмотр'


class ProductSizeInventoryInline(admin.TabularInline):
    model = ProductSizeInventory
    extra = 1
    autocomplete_fields = ['size']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'final_price', 'discount_percent',
                    'status', 'is_active', 'main_image_preview', 'inventory_status')
    list_filter = ('category', 'status', 'is_active', 'discount_percent')
    search_fields = ('name', 'description')
    readonly_fields = ('final_price', 'main_image_preview', 'created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'description', 'main_cover', 'main_image_preview')
        }),
        ('Цены', {
            'fields': ('price', 'discount_percent', 'final_price'),
        }),
        ('Статус', {
            'fields': ('status', 'is_active'),
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [ImageInline, ProductSizeInventoryInline]
    list_per_page = 20
    save_on_top = True

    def main_image_preview(self, obj):
        if obj.main_cover:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.main_cover.url)
        return "Нет изображения"
    main_image_preview.short_description = 'Фото'

    def inventory_status(self, obj):
        total_stock = ProductSizeInventory.objects.filter(product=obj).aggregate(Sum('stock'))['stock__sum'] or 0
        if total_stock <= 0:
            return format_html('<span style="color: red;">Нет в наличии</span>')
        elif total_stock < 5:
            return format_html('<span style="color: orange;">Мало ({} шт.)</span>', total_stock)
        else:
            return format_html('<span style="color: green;">В наличии ({} шт.)</span>', total_stock)
    inventory_status.short_description = 'Наличие'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Количество товаров'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(product_count=Count('products'))
        return queryset


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('name', 'position', 'is_active', 'banner_preview')
    list_filter = ('position', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('banner_preview', 'created_at', 'updated_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'image', 'banner_preview')
        }),
        ('Настройки отображения', {
            'fields': ('position', 'is_active'),
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def banner_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;" />', obj.image.url)
        return "Нет изображения"
    banner_preview.short_description = 'Предпросмотр баннера'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'logo_preview')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('logo_preview', 'created_at', 'updated_at')

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.logo.url)
        return "Нет логотипа"
    logo_preview.short_description = 'Логотип'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'items_count', 'total_value', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Количество товаров'

    def total_value(self, obj):
        total = 0
        for item in obj.items.all():
            total += item.product.final_price * item.quantity
        return f"{total:.2f} ₽"
    total_value.short_description = 'Общая стоимость'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1
    autocomplete_fields = ['product', 'size']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'size', 'quantity')
    list_filter = ('cart', 'product', 'size')
    search_fields = ('product__name', 'cart__user__username')
    autocomplete_fields = ['product', 'size', 'cart']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'product__name')
    autocomplete_fields = ['user', 'product']


@admin.register(ProductSizeInventory)
class ProductSizeInventoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'size', 'stock', 'stock_status')
    list_filter = ('product', 'size', 'stock')
    search_fields = ('product__name', 'size__name')
    list_editable = ('stock',)
    autocomplete_fields = ['product', 'size']

    def stock_status(self, obj):
        if obj.stock <= 0:
            return format_html('<span style="color: red;">Нет в наличии</span>')
        elif obj.stock < 5:
            return format_html('<span style="color: orange;">Мало</span>')
        else:
            return format_html('<span style="color: green;">В наличии</span>')
    stock_status.short_description = 'Статус'


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'file_preview')
    list_filter = ('product',)
    search_fields = ('product__name',)
    autocomplete_fields = ['product']

    def file_preview(self, obj):
        if obj.file:
            return format_html('<img src="{}" style="max-height: 50px;" />', obj.file.url)
        return "Нет изображения"
    file_preview.short_description = 'Изображение'


admin.site.site_header = 'Администрирование магазина кепок'
admin.site.site_title = 'Панель управления магазином'
admin.site.index_title = 'Управление магазином кепок'


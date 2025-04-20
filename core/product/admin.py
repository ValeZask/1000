from django.contrib import admin
from .models import Product, Banner, Brand, Category, Size, Image, Cart, CartItem, Favorite


admin.site.register(Product)
admin.site.register(Banner)
admin.site.register(Brand)
admin.site.register(Category)
admin.site.register(Size)
admin.site.register(Image)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Favorite)
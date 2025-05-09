from django.urls import path
from . import views


urlpatterns = [
    path('index/', views.IndexView.as_view(), name='index'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/items/<int:item_id>/', views.CartItemUpdateView.as_view(), name='cart_item_update'),
    path('sizes/', views.SizeListView.as_view(), name='size_list'),
    path('favorites/', views.FavoriteListView.as_view(), name='favorite_list'),
    path('favorites/<int:product_id>/', views.FavoriteToggleView.as_view(), name='favorite_toggle'),
    path('orders/', views.OrderCreateView.as_view(), name='order_create'),
    path('orders/<int:order_id>/receipt/', views.OrderReceiptUploadView.as_view(), name='order_receipt_upload'),
    path('orders/<int:order_id>/', views.OrderStatusView.as_view(), name='order_status'),
]

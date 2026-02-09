from django.urls import path
from . import views

app_name = 'Market_App'

urlpatterns = [
    # ====================================
    # Authentication URLs
    # ====================================
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    # ====================================
    # Product URLs
    # ====================================
# 1. Change name='list' to name='product_list'
    path('products/', views.product_list, name='product_list'),
    
    # 2. Change name='detail' to name='product_detail'
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    
    # 3. Change name='add' to name='product_add'
    path('product/add/', views.product_add, name='product_add'),
    
    # 4. Change name='edit' to name='product_edit'
    path('product/<int:pk>/edit/', views.product_edit, name='product_edit'),
    
    # 5. Change name='delete' to name='product_delete'
    path('product/<int:pk>/delete/', views.product_delete, name='product_delete'),
    # ====================================
    # Shopping Cart URLs
    # ====================================
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:pk>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:pk>/', views.update_cart_item, name='update_cart_item'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    
    # ====================================
    # Checkout URL
    # ====================================
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    # ====================================
    # User Profile & Wishlist URLs
    # ====================================
    path('profile/', views.profile_view, name='profile'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    
    # ====================================
    # API URLs (Optional)
    # ====================================
    path('api/search/', views.product_search_api, name='product_search_api'),
    path('api/cart/quick-add/<int:pk>/', views.quick_add_to_cart, name='quick_add_to_cart'),
]
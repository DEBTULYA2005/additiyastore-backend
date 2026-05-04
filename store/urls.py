from django.urls import path
from .views import (
    RegisterView, LoginView, AdminLoginView,
    ProductListView, ProductDetailView, ProductAdminView,
    CartView, CartItemView,
    OrderView,LogoutView, AdminUserListView, CreateAdminView, HealthCheckView,
)

urlpatterns = [
    # Auth
    path('register/', RegisterView.as_view()),
    path('login/', LoginView.as_view()),
    path('admin-login/', AdminLoginView.as_view()),
    path('logout/', LogoutView.as_view()),

    path('create-admin/', CreateAdminView.as_view()),

    # Products
    path('products/', ProductListView.as_view()),
    path('products/<int:pk>/', ProductDetailView.as_view()),
    path('products/manage/', ProductAdminView.as_view()),
    path('products/manage/<int:pk>/', ProductAdminView.as_view()),

    # Cart
    path('cart/', CartView.as_view()),
    path('cart/items/', CartItemView.as_view()),
    path('cart/items/<int:pk>/', CartItemView.as_view()),

    # Orders
    path('orders/', OrderView.as_view()),

    path('users/', AdminUserListView.as_view()),

    # health check
    path('health/', HealthCheckView.as_view()),
]
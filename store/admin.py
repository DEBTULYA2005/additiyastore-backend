from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product, Cart, CartItem, Order, OrderItem

class UserAdmin(BaseUserAdmin):
    ordering          = ['email']
    list_display      = ['email', 'username', 'role', 'is_staff']
    fieldsets         = (
        (None,           {'fields': ('email', 'username', 'password')}),
        ('Role',         {'fields': ('role',)}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets     = (
        (None, {
            'fields': ('email', 'username', 'password1', 'password2', 'role')
        }),
    )
    search_fields     = ['email', 'username']
    filter_horizontal = ()

admin.site.register(User,      UserAdmin)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
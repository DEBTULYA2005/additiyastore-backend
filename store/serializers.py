from rest_framework import serializers
from .models import User, Product, Cart, CartItem, Order, OrderItem


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            email    = validated_data['email'],
            username = validated_data['username'],
            password = validated_data['password'],
            role     = 'customer',   # ✅ always customer on register
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'role']


class ProductSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, use_url=True)
    class Meta:
        model  = Product
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    product  = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model  = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal', 'added_at']

    def get_subtotal(self, obj):
        return obj.subtotal()


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model  = Cart
        fields = ['id', 'user', 'items', 'total', 'created_at']

    def get_total(self, obj):
        return obj.total()


class OrderItemSerializer(serializers.ModelSerializer):
    product  = ProductSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model  = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'subtotal']

    def get_subtotal(self, obj):
        return obj.subtotal()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = ['id', 'user', 'status', 'total_price', 'items', 'created_at', 'updated_at']
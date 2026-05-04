from rest_framework import status
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from django.http import JsonResponse
from django.views import View

from .models import User, Product, Cart, CartItem, Order, OrderItem
from .serializers import (
    RegisterSerializer, UserSerializer,
    ProductSerializer,
    CartSerializer, CartItemSerializer,
    OrderSerializer,
)

# for health check
class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({"status": "ok"})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user     = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            Cart.objects.create(user=user)
            return Response({
                'token': token.key,
                'user' : UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email') or request.data.get('username')
        password = request.data.get('password')

        # print(email,"\n",password)

        # authenticate with email since USERNAME_FIELD = 'email'
        user = authenticate(request, username=email, password=password)
        # print(request.data)

        try:

            if user and user.role == 'customer':  # only customers can login here
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'token': token.key,
                    'user' : UserSerializer(user).data
                })
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password')

        user_obj = User.objects.filter(email=email).first()

        print("User exists:", bool(user_obj))

        if not user_obj:
            return Response({'error': 'Invalid credentials'}, status=400)

        # DIRECT PASSWORD CHECK (FIX)
        if not user_obj.check_password(password):
            print("Password mismatch")
            return Response({'error': 'Invalid credentials'}, status=400)

        print("Password matched")

        # ✅ Admin check
        if user_obj.is_staff or getattr(user_obj, 'role', '').lower() == 'admin':
            token, _ = Token.objects.get_or_create(user=user_obj)
            return Response({
                'token': token.key,
                'user': UserSerializer(user_obj).data
            })

        return Response({'error': 'Not authorized as admin'}, status=403)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully'})


class ProductListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get('category', None)
        products = Product.objects.all()
        if category and category != 'all':
            products = products.filter(category=category)
        return Response(ProductSerializer(products, many=True).data)


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductSerializer(product).data)


class ProductAdminView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            Product.objects.get(pk=pk).delete()
        except Product.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(CartSerializer(cart).data)


class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart, _    = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get('product_id')
        quantity   = request.data.get('quantity', 1)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            item.quantity += int(quantity)
            item.save()

        return Response(CartSerializer(cart).data)

    def delete(self, request, pk):
        try:
            item = CartItem.objects.get(pk=pk, cart__user=request.user)
            item.delete()
            return Response(CartSerializer(Cart.objects.get(user=request.user)).data)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)


class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user)
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(user=request.user, total_price=cart.total())

        for item in cart.items.all():
            OrderItem.objects.create(
                order    = order,
                product  = item.product,
                quantity = item.quantity,
                price    = item.product.price
            )

        cart.items.all().delete()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.filter(role='customer')
        return Response(UserSerializer(users, many=True).data)


#========================
class CreateAdminView(APIView):

    def get(self, request):
        secret = request.GET.get('key')

        if secret != settings.ADMIN_SECRET_KEY:
            return Response({"error": "Unauthorized"}, status=403)

        email = request.GET.get('email')
        username = request.GET.get('username')
        password = request.GET.get('password')

        # Basic validation
        if not email or not username or not password:
            return Response({"error": "Missing fields"}, status=400)

        User.objects.create_superuser(
            email=email,
            username=username,
            password=password
        )

        return Response({"message": "Admin created"})
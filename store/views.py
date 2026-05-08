from rest_framework import status
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from django.http import JsonResponse
from django.views import View

from .models import User, Product, ProductImage, Cart, CartItem, Order, OrderItem
from .serializers import (
    RegisterSerializer, UserSerializer,
    ProductSerializer, ProductImageSerializer,
    CartSerializer, CartItemSerializer,
    OrderSerializer,
)


# ── HEALTH CHECK ──
class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({"status": "ok"})


# ── REGISTER ──
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


# ── LOGIN ──
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get('email') or request.data.get('username')
        password = request.data.get('password')
        user     = authenticate(request, username=email, password=password)

        try:
            if user and user.role == 'customer':
                token, _ = Token.objects.get_or_create(user=user)
                return Response({'token': token.key, 'user': UserSerializer(user).data})
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── ADMIN LOGIN ──
class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email    = request.data.get('email', '').strip().lower()
        password = request.data.get('password')
        user_obj = User.objects.filter(email=email).first()

        if not user_obj or not user_obj.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=400)

        if user_obj.is_staff or getattr(user_obj, 'role', '').lower() == 'admin':
            token, _ = Token.objects.get_or_create(user=user_obj)
            return Response({'token': token.key, 'user': UserSerializer(user_obj).data})

        return Response({'error': 'Not authorized as admin'}, status=403)


# ── LOGOUT ──
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully'})


# ── PRODUCT LIST (public) ──
class ProductListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get('category', None)
        products = Product.objects.all().prefetch_related('images')
        if category and category != 'all':
            products = products.filter(category=category)
        return Response(ProductSerializer(products, many=True).data)


# ── PRODUCT DETAIL (public) ──
class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            product = Product.objects.prefetch_related('images').get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductSerializer(product).data)


# ── PRODUCT ADMIN (create / update / delete) ──
class ProductAdminView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            # handle up to 3 extra images sent as 'extra_images'
            self._save_extra_images(request, product)
            return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            product = serializer.save()
            # if new extra images are uploaded, replace old ones
            new_extras = request.FILES.getlist('extra_images')
            if new_extras:
                product.images.all().delete()           # remove old extra images
                self._save_extra_images(request, product)
            return Response(ProductSerializer(product).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            Product.objects.get(pk=pk).delete()
        except Product.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # ── helper ──
    def _save_extra_images(self, request, product):
        files = request.FILES.getlist('extra_images')
        for f in files[:3]:                             # max 3 extra images
            ProductImage.objects.create(product=product, image=f)


# ── PRODUCT IMAGES (upload extra images separately if needed) ──
class ProductImageView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist('images')
        if not files:
            return Response({'error': 'No images provided'}, status=status.HTTP_400_BAD_REQUEST)

        # respect max 3 extra images total
        existing_count = product.images.count()
        allowed        = 3 - existing_count
        created        = []

        for f in files[:allowed]:
            img = ProductImage.objects.create(product=product, image=f)
            created.append(ProductImageSerializer(img).data)

        return Response(created, status=status.HTTP_201_CREATED)

    def delete(self, request, pk, image_id):
        try:
            img = ProductImage.objects.get(pk=image_id, product__id=pk)
            img.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProductImage.DoesNotExist:
            return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)


# ── CART ──
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


# ── ORDERS ──
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
                order=order, product=item.product,
                quantity=item.quantity, price=item.product.price
            )
        cart.items.all().delete()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


# ── ADMIN: LIST USERS ──
class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.filter(role='customer')
        return Response(UserSerializer(users, many=True).data)


# ── CREATE ADMIN (secret key protected) ──
class CreateAdminView(APIView):

    def get(self, request):
        if request.GET.get('key') != settings.ADMIN_SECRET_KEY:
            return Response({"error": "Unauthorized"}, status=403)

        email    = request.GET.get('email')
        username = request.GET.get('username')
        password = request.GET.get('password')

        if not email or not username or not password:
            return Response({"error": "Missing fields"}, status=400)

        User.objects.create_superuser(email=email, username=username, password=password)
        return Response({"message": "Admin created"})
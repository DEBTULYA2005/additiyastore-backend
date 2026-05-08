from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# ── CUSTOM USER MANAGER ──
class UserManager(BaseUserManager):

    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user  = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, username, password, **extra_fields)


# ── CUSTOM USER MODEL ──
class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin',    'Admin'),
    ]

    username   = models.CharField(max_length=150, unique=True)
    email      = models.EmailField(unique=True)
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')

    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects    = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.email} ({self.role})"


# ── PRODUCT ──
class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Sharee',       'Sharee'),
        ('Kurti',        'Kurti'),
        ('Dupatta Sets', 'Dupatta Sets'),
        ('Skirt Top',    'Skirt Top'),
        ('Plazzo Top',   'Plazzo Top'),
        ('Cord Set',     'Cord Set'),
        ('Biyer Kulo',   'Biyer Kulo'),
        ('Biyer Mukut',  'Biyer Mukut'),
        ('Gachkouto',    'Gachkouto'),
    ]

    name           = models.CharField(max_length=255)
    category       = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    old_price      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount       = models.FloatField(default=0)
    image          = models.ImageField(upload_to='products/', blank=True)
    rating         = models.FloatField(default=0)
    review_count   = models.IntegerField(default=0)
    created_at     = models.DateTimeField(auto_now_add=True)

    # ── NEW FIELDS ──
    description    = models.TextField(blank=True, default='')
    material       = models.CharField(max_length=255, blank=True, default='')
    length         = models.CharField(max_length=100, blank=True, default='')
    neck           = models.CharField(max_length=100, blank=True, default='')
    size_options   = models.CharField(max_length=255, blank=True, default='')
    colour_options = models.CharField(max_length=255, blank=True, default='')

    def save(self, *args, **kwargs):
    # auto-calculate old_price from discount
        if self.discount and self.discount > 0:
            # old_price = price before discount
            # price = old_price * (1 - discount/100)
            # so old_price = price / (1 - discount/100)
            self.old_price = round(float(self.price) / (1 - float(self.discount) / 100), 2)
        else:
            self.old_price = None
            self.discount  = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ── PRODUCT EXTRA IMAGES ──
class ProductImage(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='products/extra/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.name}"


# ── CART ──
class Cart(models.Model):
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart of {self.user.email}"

    def total(self):
        return sum(item.subtotal() for item in self.items.all())


# ── CART ITEM ──
class CartItem(models.Model):
    cart     = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def subtotal(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


# ── ORDER ──
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped',   'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.email}"


# ── ORDER ITEM ──
class OrderItem(models.Model):
    order    = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price    = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
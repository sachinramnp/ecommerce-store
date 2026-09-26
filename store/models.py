from decimal import Decimal
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    brand = models.CharField(max_length=120, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    discount_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True,
                                         validators=[MinValueValidator(Decimal('0.00'))])
    stock_quantity = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'),
                                 validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))])
    review_count = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    specifications = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['brand']),
            models.Index(fields=['price']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.name

    @property
    def current_price(self):
        return self.discount_price if self.discount_price is not None and self.discount_price < self.price else self.price

    @property
    def discount_percent(self):
        if self.price and self.discount_price is not None and self.discount_price < self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0

    @property
    def in_stock(self):
        return self.stock_quantity > 0

    def recalculate_rating(self):
        data = self.reviews.aggregate(avg=models.Avg('rating'), count=models.Count('id'))
        self.rating = Decimal(str(data['avg'] or 0)).quantize(Decimal('0.01'))
        self.review_count = data['count'] or 0
        self.save(update_fields=['rating', 'review_count'])


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')

    def __str__(self):
        return f'{self.product.name} image'


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.select_related('product'))

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.select_related('product')), Decimal('0.00'))

    def __str__(self):
        return f'Cart of {self.user.username}'


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cart', 'product'], name='unique_cart_product')]

    @property
    def line_total(self):
        return self.product.current_price * self.quantity

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'


class Wishlist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Wishlist of {self.user.username}'


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['wishlist', 'product'], name='unique_wishlist_product')]


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=80, default='India')

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.full_name} - {self.city}'


class Coupon(models.Model):
    DISCOUNT_CHOICES = [('percentage', 'Percentage'), ('flat', 'Flat amount')]
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    maximum_discount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    start_date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=0, help_text='0 means unlimited.')
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def status_error(self, subtotal):
        now = timezone.now()
        if not self.is_active:
            return 'This coupon is inactive.'
        if now < self.start_date:
            return 'This coupon is not active yet.'
        if now > self.expiry_date:
            return 'Expired coupon.'
        if self.usage_limit and self.used_count >= self.usage_limit:
            return 'Coupon usage limit exceeded.'
        if subtotal < self.minimum_order_amount:
            return f'Minimum order amount is ₹{self.minimum_order_amount}.'
        return ''

    def calculate_discount(self, subtotal):
        error = self.status_error(subtotal)
        if error:
            return Decimal('0.00'), error
        if self.discount_type == 'percentage':
            discount = subtotal * self.discount_value / Decimal('100')
        else:
            discount = self.discount_value
        if self.maximum_discount is not None:
            discount = min(discount, self.maximum_discount)
        discount = min(discount, subtotal)
        return discount.quantize(Decimal('0.01')), ''


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_METHODS = [
        ('cod', 'Cash on Delivery'),
        ('upi', 'UPI'),
        ('card', 'Credit/Debit Card'),
        ('netbanking', 'Net Banking'),
    ]
    PAYMENT_STATUSES = [('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    order_number = models.CharField(max_length=30, unique=True)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, related_name='orders')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    delivery_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, default='pending')
    order_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    estimated_delivery_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    @property
    def can_cancel(self):
        return self.order_status in {'pending', 'confirmed'}


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def line_total(self):
        return self.price * self.quantity


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='one_review_per_user_product')]

    def __str__(self):
        return f'{self.product.name} - {self.rating}/5 by {self.user.username}'


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

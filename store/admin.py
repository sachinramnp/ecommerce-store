from django.contrib import admin
from .models import Address, Cart, CartItem, Category, Coupon, Notification, Order, OrderItem, Product, ProductImage, Review, Wishlist, WishlistItem
from .utils import create_notification


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'price', 'discount_price', 'stock_quantity', 'rating', 'is_active')
    list_filter = ('category', 'is_active', 'brand')
    search_fields = ('name', 'brand', 'description')
    list_editable = ('price', 'discount_price', 'stock_quantity', 'is_active')
    inlines = [ProductImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'payment_method', 'payment_status', 'order_status', 'created_at')
    list_filter = ('order_status', 'payment_status', 'payment_method')
    search_fields = ('order_number', 'user__username', 'user__email')
    readonly_fields = ('order_number', 'user', 'address', 'subtotal', 'discount', 'coupon_discount', 'delivery_charge', 'total_amount', 'payment_method', 'payment_status', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

    def save_model(self, request, obj, form, change):
        old_status = None
        if change:
            old_status = Order.objects.get(pk=obj.pk).order_status
        if change and old_status != 'cancelled' and obj.order_status == 'cancelled':
            for item in obj.items.select_related('product'):
                product = item.product
                product.stock_quantity += item.quantity
                product.save(update_fields=['stock_quantity', 'updated_at'])
        super().save_model(request, obj, form, change)
        if old_status != obj.order_status:
            status_label = obj.get_order_status_display()
            create_notification(obj.user, f'Order {status_label}', f'Order {obj.order_number} is now {status_label}.')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'start_date', 'expiry_date', 'usage_limit', 'used_count', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('code',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('product__name', 'user__username', 'comment')


admin.site.register(Address)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Notification)
admin.site.register(ProductImage)
admin.site.register(Wishlist)
admin.site.register(WishlistItem)

admin.site.site_header = 'E-Commerce Store Administration'
admin.site.site_title = 'E-Commerce Admin'
admin.site.index_title = 'Store Management'

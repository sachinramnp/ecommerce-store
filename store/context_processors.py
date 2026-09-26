from .models import Category, Cart, Wishlist, Notification


def store_context(request):
    cart_count = 0
    wishlist_count = 0
    notification_count = 0
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = cart.total_items
        wishlist = Wishlist.objects.filter(user=request.user).first()
        wishlist_count = wishlist.items.count() if wishlist else 0
        notification_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return {
        'nav_categories': Category.objects.filter(is_active=True).order_by('name'),
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'notification_count': notification_count,
    }

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from django.db import transaction
from django.utils import timezone
from .models import Cart, Coupon, Notification, Order, OrderItem, Product

DELIVERY_CHARGE = Decimal('60.00')
FREE_DELIVERY_THRESHOLD = Decimal('1500.00')


def get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def cart_totals(user):
    cart = get_cart(user)
    subtotal = cart.subtotal
    discount = sum((max(item.product.price - item.product.current_price, Decimal('0.00')) * item.quantity
                    for item in cart.items.select_related('product')), Decimal('0.00'))
    coupon_discount = Decimal('0.00')
    coupon_message = ''
    code = user.session.get('coupon_code') if hasattr(user, 'session') else None
    return cart, subtotal, discount, coupon_discount, coupon_message


def coupon_from_request(request, subtotal):
    code = request.session.get('coupon_code')
    if not code:
        return None, Decimal('0.00'), ''
    coupon = Coupon.objects.filter(code=code.upper()).first()
    if not coupon:
        request.session.pop('coupon_code', None)
        return None, Decimal('0.00'), 'Invalid coupon.'
    discount, error = coupon.calculate_discount(subtotal)
    if error:
        request.session.pop('coupon_code', None)
        return None, Decimal('0.00'), error
    return coupon, discount, ''


def calculate_cart_summary(request):
    cart = get_cart(request.user)
    subtotal = cart.subtotal
    product_discount = sum((max(item.product.price - item.product.current_price, Decimal('0.00')) * item.quantity
                            for item in cart.items.select_related('product')), Decimal('0.00'))
    coupon, coupon_discount, coupon_error = coupon_from_request(request, subtotal)
    delivery_charge = Decimal('0.00') if subtotal >= FREE_DELIVERY_THRESHOLD or subtotal == 0 else DELIVERY_CHARGE
    total = max(subtotal - coupon_discount + delivery_charge, Decimal('0.00'))
    return {
        'cart': cart,
        'subtotal': subtotal,
        'discount': product_discount,
        'coupon': coupon,
        'coupon_discount': coupon_discount,
        'coupon_error': coupon_error,
        'delivery_charge': delivery_charge,
        'total': total,
    }


def create_notification(user, title, message):
    Notification.objects.create(user=user, title=title, message=message)


def generate_order_number():
    return f'ORD-{timezone.now():%Y%m%d}-{uuid4().hex[:8].upper()}'


def create_order_from_cart(request, address, payment_method, payment_status='pending'):
    summary = calculate_cart_summary(request)
    cart = summary['cart']
    if not cart.items.exists():
        raise ValueError('Your cart is empty.')

    with transaction.atomic():
        # Re-read product rows while placing the order to avoid overselling in concurrent checkouts.
        item_rows = list(cart.items.select_related('product').select_for_update())
        for item in item_rows:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if item.quantity <= 0:
                raise ValueError('Invalid quantity.')
            if item.quantity > product.stock_quantity or not product.is_active:
                raise ValueError(f'{product.name} is unavailable in the requested quantity.')

        order = Order.objects.create(
            user=request.user,
            order_number=generate_order_number(),
            address=address,
            subtotal=summary['subtotal'],
            discount=summary['discount'],
            coupon_discount=summary['coupon_discount'],
            delivery_charge=summary['delivery_charge'],
            total_amount=summary['total'],
            payment_method=payment_method,
            payment_status=payment_status,
            order_status='pending',
            estimated_delivery_date=timezone.localdate() + timedelta(days=5),
        )
        for item in item_rows:
            product = Product.objects.get(pk=item.product_id)
            OrderItem.objects.create(order=order, product=product, quantity=item.quantity, price=product.current_price)
            product.stock_quantity -= item.quantity
            product.save(update_fields=['stock_quantity', 'updated_at'])
        cart.items.all().delete()
        if summary['coupon']:
            coupon = Coupon.objects.select_for_update().get(pk=summary['coupon'].pk)
            if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
                raise ValueError('Coupon usage limit exceeded.')
            coupon.used_count += 1
            coupon.save(update_fields=['used_count'])
        request.session.pop('coupon_code', None)

    create_notification(request.user, 'Order placed', f'Your order {order.order_number} has been placed successfully.')
    if payment_status == 'paid':
        create_notification(request.user, 'Payment successful', f'Demo payment for {order.order_number} was successful.')
    return order

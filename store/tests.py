from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import Address, Category, Coupon, Order, Product, Review, Wishlist


class StoreBaseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='TestPass@123')
        self.category = Category.objects.create(name='Electronics', description='Test')
        self.product = Product.objects.create(
            category=self.category, name='Test Phone', description='A test product', brand='TestBrand',
            price=Decimal('1000.00'), discount_price=Decimal('800.00'), stock_quantity=10,
        )
        Address.objects.create(user=self.user, full_name='Alice', phone='9999999999', address='Main Street', city='Mysuru', state='Karnataka', postal_code='570001', country='India')
        Wishlist.objects.create(user=self.user)

    def login(self):
        self.client.login(username='alice', password='TestPass@123')


class ProductTests(StoreBaseTest):
    def test_product_listing(self):
        response = self.client.get(reverse('store:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Phone')

    def test_product_search(self):
        response = self.client.get(reverse('store:search'), {'q': 'Phone'})
        self.assertContains(response, 'Test Phone')

    def test_cart_add_and_update(self):
        self.login()
        add = self.client.post(reverse('store:cart_add', args=[self.product.pk]), {'quantity': 2})
        self.assertEqual(add.status_code, 302)
        update = self.client.post(reverse('store:cart_update', args=[self.product.cart_items.first().pk]), {'quantity': 3})
        self.assertEqual(update.status_code, 302)
        self.assertEqual(self.user.cart.items.first().quantity, 3)

    def test_wishlist_toggle(self):
        self.login()
        self.client.post(reverse('store:wishlist_toggle', args=[self.product.pk]))
        self.assertTrue(self.user.wishlist.items.filter(product=self.product).exists())


class CheckoutTests(StoreBaseTest):
    def setUp(self):
        super().setUp()
        self.login()
        self.client.post(reverse('store:cart_add', args=[self.product.pk]), {'quantity': 2})
        self.coupon = Coupon.objects.create(code='TEST10', discount_type='percentage', discount_value=Decimal('10'), minimum_order_amount=Decimal('500'), start_date=timezone.now()-timedelta(days=1), expiry_date=timezone.now()+timedelta(days=2), usage_limit=10, is_active=True)

    def test_coupon_validation(self):
        response = self.client.post(reverse('store:apply_coupon'), {'code': 'TEST10'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('coupon_code'), 'TEST10')

    def test_checkout_creates_order_and_reduces_stock(self):
        address = self.user.addresses.first()
        self.client.post(reverse('store:checkout'), {'address_id': address.pk})
        response = self.client.post(reverse('store:payment'), {'payment_method': 'cod'})
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.subtotal, Decimal('1600.00'))
        self.assertEqual(order.total_amount, Decimal('1660.00'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_cancel_order_restores_stock(self):
        address = self.user.addresses.first()
        self.client.post(reverse('store:checkout'), {'address_id': address.pk})
        self.client.post(reverse('store:payment'), {'payment_method': 'cod'})
        order = Order.objects.get(user=self.user)
        self.client.post(reverse('store:cancel_order', args=[order.order_number]))
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.order_status, 'cancelled')
        self.assertEqual(self.product.stock_quantity, 10)


class ReviewTests(StoreBaseTest):
    def test_unpurchased_user_cannot_review(self):
        self.login()
        response = self.client.post(reverse('store:review_product', args=[self.product.pk]), {'rating': 5, 'comment': 'Nice'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(user=self.user, product=self.product).exists())

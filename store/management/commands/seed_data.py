from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from store.models import Category, Coupon, Product, Review, Address, Cart, Wishlist, Order, OrderItem

PRODUCT_IMAGES = {
    'Wireless Headphones': 'wireless-headphones.png',
    'Bluetooth Speaker': 'bluetooth-speaker.png',
    'USB-C Fast Charger': 'usb-c-fast-charger.png',
    'Smart LED Bulb': 'smart-led-bulb.png',
    'Cotton Hoodie': 'cotton-hoodie.png',
    'Classic Denim Jacket': 'classic-denim-jacket.png',
    'Programming in Python': 'programming-in-python.png',
    'Database Systems Guide': 'database-systems-guide.png',
    'Algorithm Practice Book': 'algorithm-practice-book.png',
    'Laptop Sleeve 15-inch': 'laptop-sleeve-15-inch.png',
    'Backpack Pro': 'backpack-pro.png',
    'Metal Water Bottle': 'metal-water-bottle.png',
    'Desk Lamp': 'desk-lamp.png',
    'Non-stick Pan': 'non-stick-pan.png',
    'Storage Organizer Set': 'storage-organizer-set.png',
}


class Command(BaseCommand):
    help = 'Create demo users, categories, products, reviews, coupons and address data.'

    def handle(self, *args, **options):
        categories = {
            'Electronics': 'Gadgets and useful electronic accessories.',
            'Clothing': 'Everyday fashion and campus wear.',
            'Books': 'Books for study and leisure.',
            'Accessories': 'Useful accessories for students and professionals.',
            'Home & Kitchen': 'Practical items for home and kitchen.',
        }
        category_objs = {}
        for name, desc in categories.items():
            category_objs[name], _ = Category.objects.get_or_create(name=name, defaults={'description': desc})

        products = [
            ('Wireless Headphones', 'Electronics', 'SoundMax', 2499, 1999, 24),
            ('Bluetooth Speaker', 'Electronics', 'BeatBox', 1799, 1399, 18),
            ('USB-C Fast Charger', 'Electronics', 'VoltPro', 999, 749, 35),
            ('Smart LED Bulb', 'Electronics', 'GlowHome', 799, 599, 40),
            ('Cotton Hoodie', 'Clothing', 'CampusWear', 1499, 1099, 20),
            ('Classic Denim Jacket', 'Clothing', 'BlueStreet', 2299, 1699, 15),
            ('Programming in Python', 'Books', 'TechPress', 899, 749, 30),
            ('Database Systems Guide', 'Books', 'StudyHub', 1099, 899, 25),
            ('Algorithm Practice Book', 'Books', 'StudyHub', 699, 549, 28),
            ('Laptop Sleeve 15-inch', 'Accessories', 'CarrySafe', 899, 649, 32),
            ('Backpack Pro', 'Accessories', 'TravelLite', 1899, 1499, 21),
            ('Metal Water Bottle', 'Accessories', 'HydroGo', 749, 599, 50),
            ('Desk Lamp', 'Home & Kitchen', 'BrightNest', 1299, 999, 19),
            ('Non-stick Pan', 'Home & Kitchen', 'CookWell', 1599, 1199, 14),
            ('Storage Organizer Set', 'Home & Kitchen', 'NeatHome', 899, 699, 27),
        ]
        product_objs = []
        for name, category, brand, price, discount, stock in products:
            obj, _ = Product.objects.get_or_create(
                name=name,
                defaults={
                    'category': category_objs[category],
                    'description': f'High-quality {name.lower()} suitable for a simple e-commerce demo project.',
                    'brand': brand,
                    'price': Decimal(str(price)),
                    'discount_price': Decimal(str(discount)),
                    'stock_quantity': stock,
                    'specifications': {'Brand': brand, 'Use': 'Everyday', 'Warranty': 'Demo warranty'},
                }
            )
            image_name = PRODUCT_IMAGES.get(name)
            if image_name and obj.image.name != f'products/{image_name}':
                obj.image.name = f'products/{image_name}'
                obj.save(update_fields=['image'])
            product_objs.append(obj)

        demo, created = User.objects.get_or_create(username='demo', defaults={'email': 'demo@example.com', 'first_name': 'Demo'})
        if created:
            demo.set_password('Demo@12345')
            demo.save()
        User.objects.filter(username='demo').update(is_active=True)
        Cart.objects.get_or_create(user=demo)
        Wishlist.objects.get_or_create(user=demo)
        for username, first in [('student1', 'Student One'), ('student2', 'Student Two')]:
            extra, was_created = User.objects.get_or_create(username=username, defaults={'email': f'{username}@example.com', 'first_name': first})
            if was_created:
                extra.set_password('Demo@12345')
                extra.save()
            Cart.objects.get_or_create(user=extra)
            Wishlist.objects.get_or_create(user=extra)
        Address.objects.get_or_create(user=demo, full_name='Demo User', defaults={
            'phone': '9876543210', 'address': 'College Road, Demo Area', 'city': 'Mysuru', 'state': 'Karnataka', 'postal_code': '570001', 'country': 'India'
        })

        now = timezone.now()
        coupons = [
            ('WELCOME10', 'percentage', Decimal('10'), Decimal('500'), Decimal('500')),
            ('SAVE200', 'flat', Decimal('200'), Decimal('1000'), None),
            ('CAMPUS15', 'percentage', Decimal('15'), Decimal('750'), Decimal('600')),
        ]
        for code, dtype, value, minimum, maximum in coupons:
            Coupon.objects.update_or_create(code=code, defaults={
                'discount_type': dtype, 'discount_value': value, 'minimum_order_amount': minimum,
                'maximum_discount': maximum, 'start_date': now - timedelta(days=1), 'expiry_date': now + timedelta(days=90),
                'usage_limit': 100, 'is_active': True,
            })

        # Give the demo customer a delivered sample order so seeded reviews also satisfy the purchase rule.
        if not Order.objects.filter(user=demo, order_number='DEMO-SEED-001').exists():
            sample_products = product_objs[:6]
            demo_address = Address.objects.get(user=demo)
            demo_order = Order.objects.create(user=demo, order_number='DEMO-SEED-001', address=demo_address, subtotal=Decimal('1.00'), discount=Decimal('0.00'), coupon_discount=Decimal('0.00'), delivery_charge=Decimal('0.00'), total_amount=Decimal('1.00'), payment_method='cod', payment_status='paid', order_status='delivered', estimated_delivery_date=timezone.localdate())
            for product in sample_products:
                OrderItem.objects.create(order=demo_order, product=product, quantity=1, price=product.current_price)

        review_texts = ['Good quality and works as expected.', 'Useful product for students.', 'Value for money.']
        for i, product in enumerate(product_objs[:6]):
            Review.objects.get_or_create(user=demo, product=product, defaults={'rating': 4 + (i % 2), 'comment': review_texts[i % len(review_texts)]})
            product.recalculate_rating()

        self.stdout.write(self.style.SUCCESS('Sample data loaded successfully.'))
        self.stdout.write('Demo customer: username=demo password=Demo@12345')

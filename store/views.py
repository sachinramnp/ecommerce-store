from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlencode
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from .forms import AddressForm, CategoryForm, CouponForm, LoginForm, ProductForm, ProfileForm, RegisterForm, ReviewForm
from .models import Address, Cart, Category, Coupon, Notification, Order, Product, Review, Wishlist
from .utils import calculate_cart_summary, create_order_from_cart, create_notification, get_cart


def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'You do not have permission to access that page.')
            return redirect('store:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def home(request):
    context = {
        'featured_products': Product.objects.filter(is_active=True).select_related('category').order_by('-rating')[:8],
        'latest_products': Product.objects.filter(is_active=True).select_related('category').order_by('-created_at')[:8],
        'categories': Category.objects.filter(is_active=True),
    }
    return render(request, 'store/home.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        Cart.objects.create(user=user)
        Wishlist.objects.create(user=user)
        create_notification(user, 'Welcome', 'Your account has been created successfully.')
        login(request, user)
        messages.success(request, 'Registration successful. Welcome to the store!')
        return redirect('store:home')
    return render(request, 'store/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('store:home')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(request, username=form.cleaned_data['username'], password=form.cleaned_data['password'])
        if user is not None and user.is_active:
            login(request, user)
            messages.success(request, 'Logged in successfully.')
            next_url = request.GET.get('next') or request.POST.get('next')
            return redirect(next_url or 'store:home')
        messages.error(request, 'Invalid login details.')
    return render(request, 'store/login.html', {'form': form, 'next': request.GET.get('next', '')})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('store:home')

@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('store:profile')
    return render(request, 'store/profile.html', {'form': form})

@login_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully.')
        return redirect('store:profile')
    return render(request, 'store/change_password.html', {'form': form})


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('category')
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    brand = request.GET.get('brand', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    rating = request.GET.get('rating', '').strip()
    availability = request.GET.get('availability', '').strip()
    sort = request.GET.get('sort', 'newest')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(category__name__icontains=query) | Q(brand__icontains=query) | Q(description__icontains=query))
    if category:
        products = products.filter(category_id=category)
    if brand:
        products = products.filter(brand__iexact=brand)
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except InvalidOperation:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except InvalidOperation:
            pass
    if rating:
        try:
            products = products.filter(rating__gte=Decimal(rating))
        except InvalidOperation:
            pass
    if availability == 'in_stock':
        products = products.filter(stock_quantity__gt=0)
    elif availability == 'out_of_stock':
        products = products.filter(stock_quantity=0)

    sort_map = {
        'price_low': 'discount_price',
        'price_high': '-discount_price',
        'newest': '-created_at',
        'popularity': '-review_count',
        'rating': '-rating',
    }
    ordering = sort_map.get(sort, '-created_at')
    if ordering in {'discount_price', '-discount_price'}:
        # Discounted products with no discount are kept in results using original price fallback in Python.
        products = products.order_by(ordering, 'price')
    else:
        products = products.order_by(ordering)

    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    brands = Product.objects.filter(is_active=True).exclude(brand='').values_list('brand', flat=True).distinct().order_by('brand')
    params = request.GET.copy()
    params.pop('page', None)
    context = {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True),
        'brands': brands,
        'query': query,
        'selected_category': category,
        'selected_brand': brand,
        'selected_rating': rating,
        'selected_availability': availability,
        'selected_sort': sort,
        'query_string': urlencode(params),
    }
    return render(request, 'store/product_list.html', context)


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk, is_active=True)
    related = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:4]
    reviews = product.reviews.select_related('user')[:10]
    can_review = request.user.is_authenticated and OrderItemPurchasedHelper.has_purchased(request.user, product)
    user_review = Review.objects.filter(user=request.user, product=product).first() if request.user.is_authenticated else None
    return render(request, 'store/product_detail.html', {'product': product, 'related_products': related, 'reviews': reviews, 'can_review': can_review, 'user_review': user_review})


class OrderItemPurchasedHelper:
    @staticmethod
    def has_purchased(user, product):
        return Order.objects.filter(user=user, order_status='delivered', items__product=product).exists()

@login_required
@require_POST
def review_product(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if not OrderItemPurchasedHelper.has_purchased(request.user, product):
        messages.error(request, 'You can review a product only after purchasing and receiving it.')
        return redirect('store:product_detail', pk=pk)
    review = Review.objects.filter(user=request.user, product=product).first()
    form = ReviewForm(request.POST, instance=review)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.product = product
        obj.save()
        product.recalculate_rating()
        messages.success(request, 'Your review has been saved.')
    else:
        messages.error(request, 'Please enter a valid rating and review.')
    return redirect('store:product_detail', pk=pk)

@login_required
@require_POST
def delete_review(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    review = get_object_or_404(Review, user=request.user, product=product)
    review.delete()
    product.recalculate_rating()
    messages.success(request, 'Your review has been deleted.')
    return redirect('store:product_detail', pk=pk)

@login_required
def cart_view(request):
    summary = calculate_cart_summary(request)
    return render(request, 'store/cart.html', summary)

@login_required
@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    if quantity < 1:
        messages.error(request, 'Invalid quantity.')
        return redirect('store:product_detail', pk=pk)
    cart = get_cart(request.user)
    item, created = cart.items.get_or_create(product=product, defaults={'quantity': 0})
    new_quantity = item.quantity + quantity
    if new_quantity > product.stock_quantity:
        messages.error(request, 'You cannot add more than the available stock.')
        return redirect(request.POST.get('next') or 'store:product_detail', pk=pk)
    item.quantity = new_quantity
    item.save(update_fields=['quantity'])
    messages.success(request, f'{product.name} added to cart.')
    return redirect(request.POST.get('next') or 'store:cart')

@login_required
@require_POST
def cart_update(request, pk):
    item = get_object_or_404(get_cart(request.user).items.select_related('product'), pk=pk)
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1
    if quantity < 1:
        item.delete()
        messages.info(request, 'Item removed from cart.')
    elif quantity > item.product.stock_quantity:
        messages.error(request, 'Requested quantity exceeds stock.')
    else:
        item.quantity = quantity
        item.save(update_fields=['quantity'])
        messages.success(request, 'Cart updated.')
    return redirect('store:cart')

@login_required
@require_POST
def cart_remove(request, pk):
    item = get_object_or_404(get_cart(request.user).items, pk=pk)
    item.delete()
    messages.info(request, 'Item removed from cart.')
    return redirect('store:cart')

@login_required
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist': wishlist, 'items': wishlist.items.select_related('product')})

@login_required
@require_POST
def wishlist_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    item = wishlist.items.filter(product=product).first()
    if item:
        item.delete()
        messages.info(request, 'Removed from wishlist.')
    else:
        wishlist.items.create(product=product)
        messages.success(request, 'Added to wishlist.')
    return redirect(request.POST.get('next') or 'store:wishlist')

@login_required
@require_POST
def wishlist_move_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if product.stock_quantity <= 0:
        messages.error(request, 'Product is out of stock.')
        return redirect('store:wishlist')
    cart = get_cart(request.user)
    item, _ = cart.items.get_or_create(product=product, defaults={'quantity': 0})
    if item.quantity >= product.stock_quantity:
        messages.error(request, 'Requested quantity exceeds stock.')
    else:
        item.quantity += 1
        item.save(update_fields=['quantity'])
        Wishlist.objects.get_or_create(user=request.user)[0].items.filter(product=product).delete()
        messages.success(request, 'Moved to cart.')
    return redirect('store:wishlist')

@login_required
@require_POST
def apply_coupon(request):
    code = request.POST.get('code', '').strip().upper()
    subtotal = get_cart(request.user).subtotal
    coupon = Coupon.objects.filter(code=code).first()
    if not coupon:
        messages.error(request, 'Invalid coupon.')
    else:
        discount, error = coupon.calculate_discount(subtotal)
        if error:
            messages.error(request, error)
        else:
            request.session['coupon_code'] = coupon.code
            messages.success(request, f'Coupon applied. You saved ₹{discount}.')
    return redirect(request.POST.get('next') or 'store:cart')

@login_required
@require_POST
def remove_coupon(request):
    request.session.pop('coupon_code', None)
    messages.info(request, 'Coupon removed.')
    return redirect('store:cart')

@login_required
def checkout(request):
    summary = calculate_cart_summary(request)
    if not summary['cart'].items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('store:cart')
    addresses = request.user.addresses.all()
    address_form = AddressForm()
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        if not address_id:
            messages.error(request, 'Select a delivery address.')
            return render(request, 'store/checkout.html', {**summary, 'addresses': addresses, 'address_form': address_form})
        address = get_object_or_404(Address, pk=address_id, user=request.user)
        request.session['checkout_address_id'] = address.pk
        return redirect('store:payment')
    return render(request, 'store/checkout.html', {**summary, 'addresses': addresses, 'address_form': address_form})

@login_required
def payment(request):
    summary = calculate_cart_summary(request)
    address_id = request.session.get('checkout_address_id')
    if not summary['cart'].items.exists() or not address_id:
        return redirect('store:checkout')
    address = get_object_or_404(Address, pk=address_id, user=request.user)
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        allowed = {'cod', 'upi', 'card', 'netbanking'}
        if payment_method not in allowed:
            messages.error(request, 'Invalid payment method.')
            return render(request, 'store/payment.html', {**summary, 'address': address})
        payment_status = 'pending' if payment_method == 'cod' else 'paid'
        try:
            order = create_order_from_cart(request, address, payment_method, payment_status=payment_status)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('store:cart')
        request.session.pop('checkout_address_id', None)
        return redirect('store:order_confirmation', order_number=order.order_number)
    return render(request, 'store/payment.html', {**summary, 'address': address})

@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number, user=request.user)
    return render(request, 'store/order_confirmation.html', {'order': order})

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    return render(request, 'store/my_orders.html', {'orders': orders})

@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), order_number=order_number, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})

@login_required
def order_tracking(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    statuses = ['pending', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered']
    current_index = statuses.index(order.order_status) if order.order_status in statuses else -1
    return render(request, 'store/order_tracking.html', {'order': order, 'statuses': statuses, 'current_index': current_index})

@login_required
@require_POST
def cancel_order(request, order_number):
    order = get_object_or_404(Order.objects.select_related('address'), order_number=order_number, user=request.user)
    if not order.can_cancel:
        messages.error(request, 'This order can no longer be cancelled.')
        return redirect('store:order_detail', order_number=order.order_number)
    for item in order.items.select_related('product'):
        product = item.product
        product.stock_quantity += item.quantity
        product.save(update_fields=['stock_quantity', 'updated_at'])
    order.order_status = 'cancelled'
    order.save(update_fields=['order_status', 'updated_at'])
    create_notification(request.user, 'Order cancelled', f'Your order {order.order_number} was cancelled.')
    messages.success(request, 'Order cancelled and stock restored.')
    return redirect('store:order_detail', order_number=order.order_number)

@login_required
def address_management(request):
    edit_id = request.GET.get('edit')
    instance = get_object_or_404(Address, pk=edit_id, user=request.user) if edit_id else None
    form = AddressForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        messages.success(request, 'Address saved.')
        return redirect('store:addresses')
    return render(request, 'store/addresses.html', {'form': form, 'addresses': request.user.addresses.all(), 'editing': instance})

@login_required
@require_POST
def delete_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if address.orders.exists():
        messages.error(request, 'This address cannot be deleted because it belongs to an order.')
    else:
        address.delete()
        messages.success(request, 'Address deleted.')
    return redirect('store:addresses')

@login_required
def notifications(request):
    notes = request.user.notifications.all()
    if request.method == 'POST':
        notes.filter(is_read=False).update(is_read=True)
        return redirect('store:notifications')
    return render(request, 'store/notifications.html', {'notifications': notes})

@login_required
@require_POST
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'Notifications marked as read.')
    return redirect('store:notifications')

@staff_required
def admin_dashboard(request):
    context = {
        'product_count': Product.objects.count(),
        'category_count': Category.objects.count(),
        'user_count': User.objects.count(),
        'order_count': Order.objects.count(),
        'pending_orders': Order.objects.filter(order_status='pending').count(),
        'coupon_count': Coupon.objects.count(),
        'review_count': Review.objects.count(),
        'recent_orders': Order.objects.select_related('user').order_by('-created_at')[:8],
    }
    return render(request, 'store/admin_dashboard.html', context)

@staff_required
def admin_products(request):
    products = Product.objects.select_related('category').order_by('-created_at')
    return render(request, 'store/admin_products.html', {'products': products})

@staff_required
def admin_categories(request):
    categories = Category.objects.all()
    return render(request, 'store/admin_categories.html', {'categories': categories})

@staff_required
def admin_orders(request):
    orders = Order.objects.select_related('user', 'address').order_by('-created_at')
    return render(request, 'store/admin_orders.html', {'orders': orders})

@staff_required
def admin_users(request):
    users = User.objects.order_by('-date_joined')
    return render(request, 'store/admin_users.html', {'users': users})

@staff_required
def admin_coupons(request):
    coupons = Coupon.objects.order_by('-expiry_date')
    return render(request, 'store/admin_coupons.html', {'coupons': coupons})


def custom_404(request, exception):
    return render(request, 'store/404.html', status=404)

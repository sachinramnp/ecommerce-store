from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Address, Category, Coupon, Product, Review


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ('full_name', 'phone', 'address', 'city', 'state', 'postal_code', 'country')
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.Select(choices=[(i, f'{i} Star') for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your experience'}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('category', 'name', 'description', 'brand', 'price', 'discount_price', 'stock_quantity', 'image', 'specifications', 'is_active')
        widgets = {'description': forms.Textarea(attrs={'rows': 5})}

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get('price')
        discount_price = cleaned.get('discount_price')
        if discount_price is not None and price is not None and discount_price > price:
            raise ValidationError('Discount price cannot be greater than original price.')
        return cleaned


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'description', 'is_active')
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class CouponForm(forms.ModelForm):
    start_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    expiry_date = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))

    class Meta:
        model = Coupon
        fields = ('code', 'discount_type', 'discount_value', 'minimum_order_amount', 'maximum_discount', 'start_date', 'expiry_date', 'usage_limit', 'is_active')

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('start_date') and cleaned.get('expiry_date') and cleaned['expiry_date'] <= cleaned['start_date']:
            raise ValidationError('Expiry date must be after start date.')
        return cleaned


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

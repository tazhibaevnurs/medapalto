from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm

from .models import User, Product


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Имя и фамилия", max_length=150)
    role = forms.ChoiceField(
        label="Роль", choices=User.ROLE_CHOICES, widget=forms.RadioSelect, initial=User.ROLE_SELLER
    )
    admin_code = forms.CharField(label="Код администратора", required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "password1", "password2", "role", "admin_code"]

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        code = cleaned.get("admin_code")
        if role == User.ROLE_ADMIN and code != settings.ADMIN_REGISTRATION_CODE:
            self.add_error("admin_code", "Неверный код администратора")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.first_name = self.cleaned_data["first_name"]
        if commit:
            user.save()
        return user


class ProductForm(forms.ModelForm):
    qty = forms.IntegerField(label="Количество, шт", min_value=1)

    class Meta:
        model = Product
        fields = ["name", "base_price"]
        labels = {"name": "Название товара", "base_price": "Базовая цена, сом"}


class ProductEditForm(forms.Form):
    name = forms.CharField(label="Название")
    base_price = forms.DecimalField(label="Базовая цена, сом", min_value=Decimal("0"))
    add_qty = forms.IntegerField(label="Дополнительный приход, шт", required=False, min_value=0, initial=0)


class IssuanceForm(forms.Form):
    product = forms.ModelChoiceField(label="Товар", queryset=Product.objects.none())
    seller = forms.ModelChoiceField(label="Продажник", queryset=User.objects.none())
    qty = forms.IntegerField(label="Количество, шт", min_value=1)
    markup = forms.DecimalField(label="Надбавка продажника, сом", min_value=Decimal("0"), initial=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(stock_qty__gt=0)
        self.fields["seller"].queryset = User.objects.filter(role=User.ROLE_SELLER)


class SaleForm(forms.Form):
    qty = forms.IntegerField(label="Продано, шт", min_value=1)
    pay_now = forms.DecimalField(label="Оплата сразу, сом (опционально)", min_value=Decimal("0"), required=False, initial=0)


class ReturnForm(forms.Form):
    qty = forms.IntegerField(label="Возврат, шт", min_value=1)


class PaymentForm(forms.Form):
    amount = forms.DecimalField(label="Сумма, сом", min_value=Decimal("0.01"))


class MarkupForm(forms.Form):
    markup = forms.DecimalField(label="Надбавка продажника, сом", min_value=Decimal("0"))

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, F
from django.shortcuts import render, redirect, get_object_or_404

from .models import User, Product, Issuance, LogEntry
from .forms import (
    RegisterForm, ProductForm, ProductEditForm, IssuanceForm,
    SaleForm, ReturnForm, PaymentForm, MarkupForm,
)


def is_admin(user):
    return user.is_authenticated and user.is_admin_role


admin_required = user_passes_test(is_admin, login_url="login")


def log_action(request, action, details):
    user = request.user if request.user.is_authenticated else None
    LogEntry.objects.create(
        actor=user,
        actor_name=user.display_name if user else "Система",
        role=user.role if user else "",
        action=action,
        details=details,
    )


# ---------------------------------------------------------------- АУТЕНТИФИКАЦИЯ

def home(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_admin_role:
        return redirect("dashboard")
    return redirect("seller_home")


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            log_action(
                request, "Регистрация",
                f"{user.display_name} зарегистрирован как "
                f"{'администратор' if user.is_admin_role else 'продажник'}",
            )
            messages.success(request, "Регистрация прошла успешно")
            return redirect("home")
    else:
        form = RegisterForm()
    return render(request, "consignment/auth.html", {"form": form, "mode": "register"})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return redirect("home")
    else:
        form = AuthenticationForm()
    return render(request, "consignment/auth.html", {"form": form, "mode": "login"})


def logout_view(request):
    auth_logout(request)
    return redirect("login")


# ---------------------------------------------------------------- ДАШБОРД (АДМИН)

@login_required
@admin_required
def dashboard(request):
    products = Product.objects.all()
    issuances = Issuance.objects.all()
    sellers = User.objects.filter(role=User.ROLE_SELLER)

    stock_value = sum((p.stock_value for p in products), Decimal("0"))
    total_issued_qty = sum(i.issued_qty for i in issuances)
    total_sold_qty = sum(i.sold_qty for i in issuances)
    total_returned_qty = sum(i.returned_qty for i in issuances)
    total_remaining = total_issued_qty - total_sold_qty - total_returned_qty
    total_due = sum((i.due_amount for i in issuances), Decimal("0"))
    total_paid = sum((i.paid_amount for i in issuances), Decimal("0"))
    total_debt = total_due - total_paid
    total_earned = sum((i.earned for i in issuances), Decimal("0"))

    per_seller = []
    for s in sellers:
        mine = [i for i in issuances if i.seller_id == s.id]
        issued_qty = sum(i.issued_qty for i in mine)
        sold_qty = sum(i.sold_qty for i in mine)
        returned_qty = sum(i.returned_qty for i in mine)
        debt = sum((i.debt for i in mine), Decimal("0"))
        earned = sum((i.earned for i in mine), Decimal("0"))
        per_seller.append({
            "seller": s, "issued_qty": issued_qty, "sold_qty": sold_qty,
            "remaining": issued_qty - sold_qty - returned_qty, "debt": debt, "earned": earned,
        })
    per_seller.sort(key=lambda r: r["earned"], reverse=True)
    max_earned = max([r["earned"] for r in per_seller], default=Decimal("0")) or Decimal("1")

    context = {
        "products_count": products.count(),
        "sellers_count": sellers.count(),
        "stock_value": stock_value,
        "total_remaining": total_remaining,
        "total_paid": total_paid,
        "total_debt": total_debt,
        "total_earned": total_earned,
        "total_returned_qty": total_returned_qty,
        "per_seller": per_seller,
        "max_earned": max_earned,
        "recent_logs": LogEntry.objects.all()[:6],
    }
    return render(request, "consignment/dashboard.html", context)


# ---------------------------------------------------------------- ТОВАРЫ

@login_required
@admin_required
def products_view(request):
    if request.method == "POST" and request.POST.get("form_id") == "new_product":
        form = ProductForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data["qty"]
            product = form.save(commit=False)
            product.total_qty = qty
            product.stock_qty = qty
            product.save()
            log_action(request, "Новый товар", f"{product.name} — {product.base_price} сом, приход {qty} шт")
            messages.success(request, "Товар добавлен в каталог")
            return redirect("products")
    else:
        form = ProductForm()

    products = Product.objects.all()
    return render(request, "consignment/products.html", {"products": products, "form": form})


@login_required
@admin_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductEditForm(request.POST)
        if form.is_valid():
            add_qty = form.cleaned_data["add_qty"] or 0
            product.name = form.cleaned_data["name"]
            product.base_price = form.cleaned_data["base_price"]
            product.stock_qty += add_qty
            product.total_qty += add_qty
            product.save()
            log_action(
                request, "Изменён товар",
                f"{product.name}" + (f", доп. приход +{add_qty} шт" if add_qty else ""),
            )
            messages.success(request, "Изменения сохранены")
    return redirect("products")


@login_required
@admin_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        if product.is_locked_for_delete():
            messages.error(request, "Нельзя удалить — этот товар сейчас у продажника")
        else:
            name = product.name
            product.delete()
            log_action(request, "Товар удалён", name)
            messages.success(request, "Товар удалён из каталога")
    return redirect("products")


# ---------------------------------------------------------------- ВЫДАЧИ

@login_required
@admin_required
def issuances_view(request):
    if request.method == "POST" and request.POST.get("form_id") == "new_issuance":
        form = IssuanceForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data["product"]
            seller = form.cleaned_data["seller"]
            qty = form.cleaned_data["qty"]
            markup = form.cleaned_data["markup"]
            if qty > product.stock_qty:
                messages.error(request, f"На складе только {product.stock_qty} шт")
            else:
                Issuance.objects.create(
                    product=product, product_name=product.name, base_price=product.base_price,
                    markup=markup, seller=seller, issued_qty=qty,
                )
                product.stock_qty -= qty
                product.save()
                log_action(
                    request, "Выдача товара",
                    f"{product.name} × {qty} шт → {seller.display_name}, "
                    f"цена {product.base_price + markup} сом (база {product.base_price} + надбавка {markup})",
                )
                messages.success(request, "Товар выдан продажнику")
                return redirect("issuances")
    else:
        form = IssuanceForm()

    issuances = Issuance.objects.all()
    seller_id = request.GET.get("seller")
    if seller_id:
        issuances = issuances.filter(seller_id=seller_id)

    return render(request, "consignment/issuances.html", {
        "issuances": issuances, "form": form,
        "sellers": User.objects.filter(role=User.ROLE_SELLER),
        "selected_seller": seller_id or "",
    })


@login_required
@admin_required
def issuance_sale(request, pk):
    iss = get_object_or_404(Issuance, pk=pk)
    if request.method == "POST":
        form = SaleForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data["qty"]
            pay_now = form.cleaned_data["pay_now"] or Decimal("0")
            if qty > iss.remaining_qty:
                messages.error(request, f"Можно продать максимум {iss.remaining_qty} шт")
            else:
                pay_now = min(pay_now, iss.base_price * qty)
                iss.sold_qty += qty
                iss.paid_amount += pay_now
                iss.save()
                log_action(
                    request, "Продажа отмечена",
                    f"{iss.product_name} × {qty} шт у {iss.seller.display_name}"
                    + (f", сразу оплачено {pay_now} сом" if pay_now else ""),
                )
                messages.success(request, "Продажа зафиксирована")
    return redirect("issuances")


@login_required
@admin_required
def issuance_return(request, pk):
    iss = get_object_or_404(Issuance, pk=pk)
    if request.method == "POST":
        form = ReturnForm(request.POST)
        if form.is_valid():
            qty = form.cleaned_data["qty"]
            if qty > iss.remaining_qty:
                messages.error(request, f"Можно вернуть максимум {iss.remaining_qty} шт")
            else:
                iss.returned_qty += qty
                iss.save()
                if iss.product:
                    iss.product.stock_qty += qty
                    iss.product.save()
                log_action(
                    request, "Возврат товара",
                    f"{iss.product_name} × {qty} шт от {iss.seller.display_name} — "
                    f"возвращён на склад, перерасчёт остатков выполнен",
                )
                messages.success(request, "Возврат оформлен")
    return redirect("issuances")


@login_required
@admin_required
def issuance_payment(request, pk):
    iss = get_object_or_404(Issuance, pk=pk)
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            debt = iss.debt
            if amount > debt:
                messages.error(request, f"Долг сейчас {debt} сом — нельзя принять больше")
            else:
                iss.paid_amount += amount
                iss.save()
                log_action(request, "Оплата получена", f"{amount} сом от {iss.seller.display_name} за «{iss.product_name}»")
                messages.success(request, "Оплата принята")
    return redirect("issuances")


@login_required
@admin_required
def issuance_markup(request, pk):
    iss = get_object_or_404(Issuance, pk=pk)
    if request.method == "POST":
        if iss.sold_qty > 0:
            messages.error(request, "Уже есть продажи — надбавку менять нельзя")
        else:
            form = MarkupForm(request.POST)
            if form.is_valid():
                iss.markup = form.cleaned_data["markup"]
                iss.save()
                log_action(request, "Изменена выдача", f"{iss.product_name} у {iss.seller.display_name}: новая надбавка {iss.markup} сом")
                messages.success(request, "Сохранено")
    return redirect("issuances")


@login_required
@admin_required
def issuance_delete(request, pk):
    iss = get_object_or_404(Issuance, pk=pk)
    if request.method == "POST":
        if iss.is_locked_for_delete():
            messages.error(request, "Нельзя удалить — по выдаче уже было движение")
        else:
            if iss.product:
                iss.product.stock_qty += iss.issued_qty
                iss.product.save()
            name, seller_name = iss.product_name, iss.seller.display_name
            iss.delete()
            log_action(request, "Выдача удалена", f"{name} у {seller_name} — товар возвращён на склад")
            messages.success(request, "Выдача удалена")
    return redirect("issuances")


# ---------------------------------------------------------------- ПРОДАЖНИКИ / ЖУРНАЛ

@login_required
@admin_required
def sellers_view(request):
    sellers = User.objects.filter(role=User.ROLE_SELLER)
    rows = []
    for s in sellers:
        mine = s.issuances.all()
        sold_qty = sum(i.sold_qty for i in mine)
        debt = sum((i.debt for i in mine), Decimal("0"))
        earned = sum((i.earned for i in mine), Decimal("0"))
        rows.append({"seller": s, "sold_qty": sold_qty, "debt": debt, "earned": earned})
    admins = User.objects.filter(role=User.ROLE_ADMIN)
    return render(request, "consignment/sellers.html", {"rows": rows, "admins": admins})


@login_required
@admin_required
def logs_view(request):
    logs = LogEntry.objects.all()[:300]
    return render(request, "consignment/logs.html", {"logs": logs})


# ---------------------------------------------------------------- КАБИНЕТ ПРОДАЖНИКА

@login_required
def seller_home(request):
    if request.user.is_admin_role:
        return redirect("dashboard")
    mine = Issuance.objects.filter(seller=request.user)
    issued_qty = sum(i.issued_qty for i in mine)
    sold_qty = sum(i.sold_qty for i in mine)
    returned_qty = sum(i.returned_qty for i in mine)
    context = {
        "issuances": mine,
        "remaining": issued_qty - sold_qty - returned_qty,
        "sold_qty": sold_qty,
        "returned_qty": returned_qty,
        "debt": sum((i.seller_amount_due for i in mine), Decimal("0")),
    }
    return render(request, "consignment/seller_home.html", context)

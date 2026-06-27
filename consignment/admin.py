from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Product, Issuance, LogEntry


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Роль", {"fields": ("role",)}),)
    list_display = ("username", "first_name", "role", "is_staff")
    list_filter = ("role", "is_staff")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "base_price", "total_qty", "stock_qty", "created_at")
    search_fields = ("name",)


@admin.register(Issuance)
class IssuanceAdmin(admin.ModelAdmin):
    list_display = ("product_name", "seller", "issued_qty", "sold_qty", "returned_qty", "paid_amount", "created_at")
    list_filter = ("seller",)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_name", "role", "action")
    list_filter = ("role",)
    search_fields = ("action", "details", "actor_name")

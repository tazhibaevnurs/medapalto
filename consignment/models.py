from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    """Пользователь системы: администратор или продажник."""

    ROLE_ADMIN = "admin"
    ROLE_SELLER = "seller"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Администратор"),
        (ROLE_SELLER, "Продажник"),
    ]

    role = models.CharField("Роль", max_length=10, choices=ROLE_CHOICES, default=ROLE_SELLER)

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_seller_role(self):
        return self.role == self.ROLE_SELLER

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def __str__(self):
        return self.display_name


class Product(models.Model):
    """Товар, который заводит администратор. Может выдаваться продажникам под реализацию."""

    name = models.CharField("Название", max_length=200)
    base_price = models.DecimalField("Базовая цена, сом", max_digits=12, decimal_places=2)
    total_qty = models.PositiveIntegerField("Всего поступило, шт", default=0)
    stock_qty = models.PositiveIntegerField("На складе, шт", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return self.name

    @property
    def stock_value(self):
        return self.stock_qty * self.base_price

    @property
    def with_sellers_qty(self):
        total = 0
        for iss in self.issuances.all():
            total += iss.remaining_qty
        return total

    def is_locked_for_delete(self):
        """Нельзя удалить товар, если он сейчас числится у какого-то продажника."""
        return any(iss.remaining_qty > 0 for iss in self.issuances.all())


class Issuance(models.Model):
    """Талон выдачи товара продажнику под реализацию."""

    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name="issuances"
    )
    product_name = models.CharField("Товар (на момент выдачи)", max_length=200)
    base_price = models.DecimalField("База на момент выдачи, сом", max_digits=12, decimal_places=2)
    markup = models.DecimalField("Надбавка продажника, сом", max_digits=12, decimal_places=2, default=0)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="issuances", verbose_name="Продажник"
    )
    issued_qty = models.PositiveIntegerField("Выдано, шт")
    sold_qty = models.PositiveIntegerField("Продано, шт", default=0)
    returned_qty = models.PositiveIntegerField("Возврат, шт", default=0)
    paid_amount = models.DecimalField("Оплачено, сом", max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Выдача"
        verbose_name_plural = "Выдачи"

    def __str__(self):
        return f"{self.product_name} → {self.seller}"

    @property
    def sell_price(self):
        return self.base_price + self.markup

    @property
    def remaining_qty(self):
        return self.issued_qty - self.sold_qty - self.returned_qty

    @property
    def due_amount(self):
        return self.base_price * self.sold_qty

    @property
    def debt(self):
        return self.due_amount - self.paid_amount

    @property
    def seller_amount_due(self):
        """Сколько продажник должен компании: неоплаченные продажи + остаток на руках."""
        return self.debt + self.base_price * self.remaining_qty

    @property
    def earned(self):
        return self.markup * self.sold_qty

    @property
    def status(self):
        if self.debt > 0:
            return ("ДОЛГ", "red")
        if self.remaining_qty == 0 and self.sold_qty > 0:
            return ("ОПЛАЧЕНО", "green")
        if self.remaining_qty == 0 and self.returned_qty == self.issued_qty:
            return ("ВОЗВРАТ", "blue")
        return ("В РАБОТЕ", "neutral")

    def is_locked_for_delete(self):
        return self.sold_qty > 0 or self.paid_amount > 0 or self.returned_qty > 0


class LogEntry(models.Model):
    """Журнал всех операций — кто, что и когда сделал."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="log_entries"
    )
    actor_name = models.CharField("Кто", max_length=200, default="Система")
    role = models.CharField("Роль", max_length=10, blank=True)
    action = models.CharField("Действие", max_length=200)
    details = models.TextField("Подробности", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Запись журнала"
        verbose_name_plural = "Журнал операций"

    def __str__(self):
        return f"{self.action} — {self.actor_name}"

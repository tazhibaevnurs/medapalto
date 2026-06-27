from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .models import User, Product, Issuance, LogEntry


class RegistrationTests(TestCase):
    def test_wrong_admin_code_is_rejected(self):
        resp = self.client.post(reverse("register"), {
            "username": "fakeadmin", "first_name": "Фейк",
            "password1": "TestPass123", "password2": "TestPass123",
            "role": "admin", "admin_code": "WRONG",
        })
        self.assertContains(resp, "Неверный код администратора")
        self.assertFalse(User.objects.filter(username="fakeadmin").exists())

    def test_correct_admin_code_creates_admin(self):
        from django.conf import settings
        resp = self.client.post(reverse("register"), {
            "username": "admin1", "first_name": "Админ",
            "password1": "TestPass123", "password2": "TestPass123",
            "role": "admin", "admin_code": settings.ADMIN_REGISTRATION_CODE,
        }, follow=True)
        self.assertTrue(User.objects.filter(username="admin1", role="admin").exists())
        self.assertContains(resp, "Сводка")

    def test_seller_registers_without_code(self):
        resp = self.client.post(reverse("register"), {
            "username": "seller1", "first_name": "Продажник",
            "password1": "TestPass123", "password2": "TestPass123",
            "role": "seller", "admin_code": "",
        }, follow=True)
        self.assertTrue(User.objects.filter(username="seller1", role="seller").exists())
        self.assertContains(resp, "Мои товары")


class ConsignmentFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="TestPass123", role=User.ROLE_ADMIN)
        self.seller = User.objects.create_user(username="seller1", password="TestPass123", role=User.ROLE_SELLER)
        self.client.login(username="admin1", password="TestPass123")
        self.product = Product.objects.create(name="Шуба", base_price=Decimal("1000"), total_qty=5, stock_qty=5)

    def test_seller_cannot_access_admin_pages(self):
        self.client.logout()
        self.client.login(username="seller1", password="TestPass123")
        resp = self.client.get(reverse("products"))
        self.assertNotEqual(resp.status_code, 200)

    def test_seller_sees_amount_due_for_items_in_work(self):
        Issuance.objects.create(
            product=self.product, product_name=self.product.name,
            base_price=self.product.base_price, markup=Decimal("100"),
            seller=self.seller, issued_qty=5,
        )
        self.client.logout()
        self.client.login(username="seller1", password="TestPass123")
        resp = self.client.get(reverse("seller_home"))
        self.assertContains(resp, "5 000")  # 5 шт × 1000 сом
        self.assertNotContains(resp, "база")
        self.assertNotContains(resp, "надб")

    def test_issuance_creation_reduces_stock_and_sets_price(self):
        self.client.post(reverse("issuances"), {
            "form_id": "new_issuance", "product": self.product.id,
            "seller": self.seller.id, "qty": "3", "markup": "100",
        })
        iss = Issuance.objects.get(product=self.product, seller=self.seller)
        self.assertEqual(iss.sell_price, Decimal("1100"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, 2)

    def test_sale_payment_return_full_cycle(self):
        self.client.post(reverse("issuances"), {
            "form_id": "new_issuance", "product": self.product.id,
            "seller": self.seller.id, "qty": "3", "markup": "100",
        })
        iss = Issuance.objects.get(product=self.product, seller=self.seller)

        # продаём 2 шт, оплачиваем сразу только 1500 из 2000
        self.client.post(reverse("issuance_sale", args=[iss.id]), {"qty": "2", "pay_now": "1500"})
        iss.refresh_from_db()
        self.assertEqual(iss.sold_qty, 2)
        self.assertEqual(iss.debt, Decimal("500.00"))
        self.assertEqual(iss.earned, Decimal("200.00"))  # 100 надбавки * 2 шт

        # нельзя продать больше остатка
        self.client.post(reverse("issuance_sale", args=[iss.id]), {"qty": "999", "pay_now": "0"})
        iss.refresh_from_db()
        self.assertEqual(iss.sold_qty, 2)

        # закрываем долг
        self.client.post(reverse("issuance_payment", args=[iss.id]), {"amount": "500"})
        iss.refresh_from_db()
        self.assertEqual(iss.debt, Decimal("0.00"))

        # возвращаем оставшуюся 1 шт — склад должен пересчитаться
        self.client.post(reverse("issuance_return", args=[iss.id]), {"qty": "1"})
        iss.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(iss.returned_qty, 1)
        self.assertEqual(self.product.stock_qty, 3)

        # выдачу с историей операций удалить нельзя
        resp = self.client.post(reverse("issuance_delete", args=[iss.id]), follow=True)
        self.assertTrue(Issuance.objects.filter(id=iss.id).exists())
        self.assertContains(resp, "Нельзя удалить")

    def test_product_with_seller_cannot_be_deleted(self):
        self.client.post(reverse("issuances"), {
            "form_id": "new_issuance", "product": self.product.id,
            "seller": self.seller.id, "qty": "1", "markup": "50",
        })
        resp = self.client.post(reverse("product_delete", args=[self.product.id]), follow=True)
        self.assertTrue(Product.objects.filter(id=self.product.id).exists())
        self.assertContains(resp, "Нельзя удалить")

    def test_actions_are_logged(self):
        self.client.post(reverse("products"), {
            "form_id": "new_product", "name": "Дублёнка", "base_price": "2000", "qty": "1",
        })
        self.assertTrue(LogEntry.objects.filter(action="Новый товар").exists())

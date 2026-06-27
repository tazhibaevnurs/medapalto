from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),

    path("products/", views.products_view, name="products"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),

    path("issuances/", views.issuances_view, name="issuances"),
    path("issuances/<int:pk>/sale/", views.issuance_sale, name="issuance_sale"),
    path("issuances/<int:pk>/return/", views.issuance_return, name="issuance_return"),
    path("issuances/<int:pk>/payment/", views.issuance_payment, name="issuance_payment"),
    path("issuances/<int:pk>/markup/", views.issuance_markup, name="issuance_markup"),
    path("issuances/<int:pk>/delete/", views.issuance_delete, name="issuance_delete"),

    path("sellers/", views.sellers_view, name="sellers"),
    path("logs/", views.logs_view, name="logs"),

    path("mine/", views.seller_home, name="seller_home"),
]

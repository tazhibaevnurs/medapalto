"""
Настройки проекта «Реализация» — учёт товаров под комиссию.
Сгенерировано на основе django-admin startproject, адаптировано для локального запуска.
"""

import os
from pathlib import Path

from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# --- БЕЗОПАСНОСТЬ -----------------------------------------------------------
# Для локальной разработки можно оставить как есть.
# Перед реальным боевым использованием — обязательно вынесите в переменные
# окружения и смените значения по умолчанию!
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-dev-key-change-me-before-production",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

_allowed_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = (
    ["*"]
    if DEBUG
    else [host.strip() for host in _allowed_hosts.split(",") if host.strip()]
)

_csrf_origins = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "")


def _parse_csrf_origins(raw: str) -> list[str]:
    """Django требует полные origin с http(s)://; добавляем схему и порт при необходимости."""
    app_port = os.environ.get("APP_PORT", "80")
    origins = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "://" not in item:
            item = f"http://{item}"
        parsed = urlparse(item)
        if parsed.port is None and parsed.hostname:
            if parsed.scheme == "http" and app_port not in ("", "80"):
                netloc = f"{parsed.hostname}:{app_port}"
            else:
                netloc = parsed.hostname
            item = urlunparse((parsed.scheme, netloc, "", "", "", ""))
        origins.append(item)
    return origins


CSRF_TRUSTED_ORIGINS = _parse_csrf_origins(_csrf_origins)

# Код, который нужно ввести при регистрации, чтобы получить роль "Администратор".
# Поменяйте на свой и сообщите только доверенным людям.
ADMIN_REGISTRATION_CODE = os.environ.get("ADMIN_REGISTRATION_CODE", "RP-2026-BOSS")

# --- ПРИЛОЖЕНИЯ --------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "consignment",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- БАЗА ДАННЫХ ---------------------------------------------------------------
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 4}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Своя модель пользователя — с ролью "администратор"/"продажник"
AUTH_USER_MODEL = "consignment.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# --- ЛОКАЛИЗАЦИЯ ---------------------------------------------------------------
LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True

# --- СТАТИКА -------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

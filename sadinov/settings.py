"""Django settings for Sadinov Store project."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-sadinov-dev-key-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "sadinov.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "sadinov.wsgi.application"

# SQLite — mavjud FastAPI store.db'ga ulanish
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Docker/prod: STORE_DB_PATH muhit o'zgaruvchisi orqali volume'ga ishora.
        # Dev: bir pog'ona yuqoridagi store.db (FastAPI bilan birga).
        "NAME": os.getenv("STORE_DB_PATH") or str(BASE_DIR.parent / "store.db"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# File-based cache — gunicorn workerlar orasida bo'lishish uchun
# (in-memory cache har worker uchun alohida bo'ladi).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": os.getenv("DJANGO_CACHE_DIR") or str(BASE_DIR / "cache"),
        "TIMEOUT": None,
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = False
USE_TZ = False

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Foydalanuvchi yuklagan rasm/fayl uchun
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "api.auth_backends.BearerAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "UNAUTHENTICATED_USER": None,
}

CORS_ALLOW_ALL_ORIGINS = True

ESKIZ_EMAIL = os.getenv("ESKIZ_EMAIL", "mustafoyevalibek90@gmall.com")
ESKIZ_PASSWORD = os.getenv("ESKIZ_PASSWORD", "S6Jpo5EKWY72AnIe7OU9z1mP79ahZmNMTPpBibHo")
ESKIZ_FROM = os.getenv("ESKIZ_FROM", "4546")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

FERNET_KEY = os.getenv("FERNET_KEY", "")

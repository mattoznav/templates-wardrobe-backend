from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise environ.ImproperlyConfigured("Set SECRET_KEY: it is required when DEBUG is off.")
    SECRET_KEY = "insecure-development-key-do-not-use-in-production"
# 10.0.2.2 is how the Android emulator reaches this machine
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "10.0.2.2"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.orders",
    "apps.payments",
    "apps.returns",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
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

# The demo has no database server: data/*.csv is the source of truth and is
# loaded into a throwaway SQLite file. Set DATABASE_URL to use a real database.
VAR_DIR = BASE_DIR / "var"
VAR_DIR.mkdir(exist_ok=True)
DATABASES = {
    "default": env.db_url_config(env("DATABASE_URL", default="") or f"sqlite:///{VAR_DIR / 'wardrobe.sqlite3'}"),
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Europe/Rome")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = VAR_DIR / "static"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:4322", "http://localhost:4201"])

# Shop rules
STORE_DATA_DIR = BASE_DIR / "data"
# Stock is set aside while the customer pays, then released if they do not
ORDER_HOLD_MINUTES = env.int("ORDER_HOLD_MINUTES", default=15)
ORDER_MAX_QUANTITY = env.int("ORDER_MAX_QUANTITY", default=10)
LOW_STOCK_THRESHOLD = env.int("LOW_STOCK_THRESHOLD", default=3)

DEMO_ADMIN_EMAIL = env("DEMO_ADMIN_EMAIL", default="admin@example.com")
DEMO_ADMIN_PASSWORD = env("DEMO_ADMIN_PASSWORD", default="")

# Payments: "fake" simulates the full flow offline, "stripe" talks to Stripe
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", default="stripe" if STRIPE_SECRET_KEY else "fake")

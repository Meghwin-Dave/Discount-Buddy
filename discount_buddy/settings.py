import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file at project root (if present)
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "change-me-in-production")

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

# ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOmake documentatSTS", "*").split(",")
ALLOWED_HOSTS = ["192.168.29.221","16.171.196.144","127.0.0.1", "localhost", "ec2-16-171-196-144.eu-north-1.compute.amazonaws.com"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_yasg",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    # Local apps
    "core",
    "users",
    "vouchers",
    "wallet",
    "restaurants",
    "notifications",
    # "orders",
    # "marketplace",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "discount_buddy.urls"

# Automatically append trailing slashes to URLs
APPEND_SLASH = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "discount_buddy.wsgi.application"

if os.environ.get("DB_ENGINE", "sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("discountbuddy", "discountbuddy"),
            "USER": os.environ.get("admin", "admin"),
            "PASSWORD": os.environ.get("1234", "1234"),
            # For Docker use POSTGRES_HOST=db; for local Postgres override to localhost explicitly
            "HOST": os.environ.get("localhost", "localhost"),
            "PORT": os.environ.get("5432", "5432"),
        }
    }
else:
    # Default to SQLite for local development (no external DB needed)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

# Google OAuth – set in .env (never commit real values)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_ANDROID_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_ANDROID_CLIENT_ID", "")
GOOGLE_OAUTH_IOS_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_IOS_CLIENT_ID", "")

# List of all allowed client IDs for token verification (e.g. from mobile apps)
GOOGLE_OAUTH_ALLOWED_CLIENT_IDS = [
    cid for cid in [
        GOOGLE_OAUTH_CLIENT_ID,
        GOOGLE_OAUTH_ANDROID_CLIENT_ID,
        GOOGLE_OAUTH_IOS_CLIENT_ID
    ] if cid
]

# Email configuration (for OTP and notifications)
# Use Gmail App Password: https://myaccount.google.com/apppasswords
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "priyanshuchavda999@gmail.com")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "evxd tzoy ulbf rdap")  # Gmail App Password
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Discount Buddy <priyanshuchavda999@gmail.com>"
)

# django-allauth
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = "optional"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_REQUIRED = True

# Google provider for allauth (web OAuth flow)
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "secret": GOOGLE_OAUTH_CLIENT_SECRET,
        },
        "SCOPE": [
            "profile",
            "email",
        ],
    }
}

# dj-rest-auth: use JWT
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,
    "JWT_AUTH_COOKIE": None,
    "JWT_AUTH_REFRESH_COOKIE": None,
}
REST_AUTH_REGISTER_SERIALIZERS = {}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Cache configuration
# Use Redis in production, local memory cache in development
if DEBUG or not os.environ.get("REDIS_URL"):
    # Use local memory cache for development
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
    # Use database sessions in development (no Redis needed)
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
else:
    # Use Redis in production
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/1"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# Security settings for production, overridable by env
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# In development (DEBUG=True), cookies don't need to be secure (HTTP is fine)
# In production (DEBUG=False), cookies should be secure (HTTPS only)
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False" if DEBUG else "True").lower() == "true"
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False" if DEBUG else "True").lower() == "true"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Swagger/OpenAPI settings
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\"",
        }
    },
    "USE_SESSION_AUTH": False,
}

# ============================================================================
# NOTIFICATIONS & PUSH NOTIFICATIONS
# ============================================================================

# Firebase Cloud Messaging (FCM) for push notifications
# Firebase service account credentials
FIREBASE_CREDENTIALS_PATH = BASE_DIR / "firebase-credentials.json"

# ============================================================================
# CELERY CONFIGURATION (for async push notifications)
# ============================================================================
# Celery is REQUIRED for production to handle push notifications asynchronously
# For development without Celery, push notifications will be skipped gracefully

# Celery broker URL (Redis recommended)
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# If no Redis is available, force eager mode (run synchronously)
# This prevents crashes when Redis is missing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Celery settings
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Celery task retry settings
CELERY_TASK_AUTORETRY_FOR = (Exception,)
CELERY_TASK_RETRY_KWARGS = {"max_retries": 3, "countdown": 5}

# Note: To run Celery worker in development:
# celery -A discount_buddy worker --loglevel=info
# To run Celery beat (for scheduled tasks):
# celery -A discount_buddy beat --loglevel=info

# Periodic schedules
CELERY_BEAT_SCHEDULE = {
    "assign-monthly-mystery-visits": {
        "task": "restaurants.tasks.assign_monthly_mystery_visits",
        # Run daily at 03:00 UTC; logic in the task respects required_visit_gap
        "schedule": crontab(hour=3, minute=0),
    },
}


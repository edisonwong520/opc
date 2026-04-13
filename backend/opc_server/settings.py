import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Load .env from project root (parent of backend directory)
load_dotenv(BASE_DIR.parent / ".env", override=True)


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-opc-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "daphne",
    "channels",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "apps.desk",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "opc_server.urls"

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

WSGI_APPLICATION = "opc_server.wsgi.application"
ASGI_APPLICATION = "opc_server.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

DB_ENGINE = os.getenv("DB_ENGINE", "django.db.backends.sqlite3")
if DB_ENGINE == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.getenv("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    default_port = "5432" if "postgresql" in DB_ENGINE else "3306"
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.getenv("DB_NAME", "opc"),
            "USER": os.getenv("DB_USER", "opc"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", default_port),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = False

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS configuration (must be before CSRF_TRUSTED_ORIGINS)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Session cookie security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production

# CSRF cookie security
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Production security headers
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"

OPENCLAW_GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:7788")
OPENCLAW_GATEWAY_AUTH_MODE = os.getenv("OPENCLAW_GATEWAY_AUTH_MODE", "token")
OPENCLAW_GATEWAY_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN", "")
OPENCLAW_GATEWAY_PASSWORD = os.getenv("OPENCLAW_GATEWAY_PASSWORD", "")
AI_BASE_URL = os.getenv("AI_BASE_URL", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
OPC_COST_INPUT_PER_1K_USD = os.getenv("OPC_COST_INPUT_PER_1K_USD", "0")
OPC_COST_OUTPUT_PER_1K_USD = os.getenv("OPC_COST_OUTPUT_PER_1K_USD", "0")
OPC_REQUIRE_AUTH = env_bool("OPC_REQUIRE_AUTH")

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "users",
    "courses",
    "assignments",
    "submissions",
    "dashboard",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
ASGI_APPLICATION = "config.asgi.application"

# SQLite keeps local setup self-contained. Set DATABASE_URL to use PostgreSQL locally or
# in production, for example: postgresql://user:password@localhost:5432/assignment_tracker
database_url = os.getenv("DATABASE_URL")
if not database_url:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    parsed_database_url = urlsplit(database_url)
    if parsed_database_url.scheme not in ("postgres", "postgresql"):
        raise ImproperlyConfigured("DATABASE_URL must use the postgres:// or postgresql:// scheme.")
    database_name = unquote(parsed_database_url.path.lstrip("/"))
    if not database_name:
        raise ImproperlyConfigured("DATABASE_URL must include a PostgreSQL database name.")

    database_options = {
        key: values[-1]
        for key, values in parse_qs(parsed_database_url.query).items()
    }
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": database_name,
            "USER": unquote(parsed_database_url.username or ""),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname or "localhost",
            "PORT": str(parsed_database_url.port or 5432),
            "OPTIONS": database_options,
            "CONN_MAX_AGE": int(os.getenv("DATABASE_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
        }
    }

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.TokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
AUTHENTICATION_BACKENDS = ["users.backends.EmailOrUsernameBackend"]

# Local development prints reminder emails in the Celery worker terminal.
EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "assignment-tracker@localhost")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULE = {
    "schedule-assignment-reminders-every-minute": {
        "task": "notifications.tasks.schedule_assignment_reminders",
        "schedule": 60.0,
    },
}

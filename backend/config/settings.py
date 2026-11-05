"""Django settings for By the Book."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from decouple import AutoConfig

BASE_DIR = Path(__file__).resolve().parent.parent

_env_search_path = os.environ.get('ABRENTAL_ENV_DIR', str(BASE_DIR.parent))
_config = AutoConfig(search_path=_env_search_path)


def env(name, default=''):
    return _config(name, default=os.environ.get(name, default))


DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development').strip().lower()
IS_PRODUCTION = DJANGO_ENV in ('prod', 'production')

SECRET_KEY = os.environ.get('SECRET_KEY', '').strip() or str(env('SECRET_KEY', '')).strip()

_debug_env = os.environ.get('DEBUG')
if _debug_env is None or str(_debug_env).strip() == '':
    _debug_env = env('DEBUG', '')
if _debug_env is None or str(_debug_env).strip() == '':
    DEBUG = not IS_PRODUCTION
else:
    DEBUG = str(_debug_env).strip().lower() in ('1', 'true', 'yes', 'on')

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-me'
    else:
        raise ImproperlyConfigured('SECRET_KEY is required when DEBUG is off.')

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

_hosts = os.environ.get('ALLOWED_HOSTS') or str(env('ALLOWED_HOSTS', ''))
ALLOWED_HOSTS = [host.strip() for host in _hosts.split(',') if host.strip()]
if DEBUG:
    for host in ('localhost', '127.0.0.1', 'backend', '*'):
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
elif not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS is required when DEBUG is off.')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'drf_spectacular',
    'corsheaders',
    'accounts',
    'properties',
    'tenancies',
    'inspections',
    'deposits',
    'records',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-ca'
TIME_ZONE = 'America/Edmonton'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
if not DEBUG:
    STORAGES['staticfiles'] = {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'}

_azure_account = str(env('AZURE_ACCOUNT_NAME', '')).strip()
if _azure_account:
    try:
        import storages  # noqa: F401
    except ImportError as exc:
        raise ImproperlyConfigured(
            'AZURE_ACCOUNT_NAME is set. Install django-storages[azure] in this environment.'
        ) from exc
    STORAGES['default'] = {'BACKEND': 'storages.backends.azure_storage.AzureStorage'}
    AZURE_ACCOUNT_NAME = _azure_account
    AZURE_ACCOUNT_KEY = str(env('AZURE_ACCOUNT_KEY', '')).strip()
    AZURE_CONTAINER = str(env('AZURE_CONTAINER', 'suite-files')).strip() or 'suite-files'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

_db_host = str(os.environ.get('DB_HOST') or env('DB_HOST', '')).strip()
if _db_host:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME') or env('DB_NAME', 'abrental'),
            'USER': os.environ.get('DB_USER') or env('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD') or env('DB_PASSWORD', 'postgres'),
            'HOST': _db_host,
            'PORT': os.environ.get('DB_PORT') or env('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.ScopedRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {
        'auth': '20/min',
        'waitlist': '30/min',
        'invite': '60/min',
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'By the Book API',
    'DESCRIPTION': 'Alberta rental inspection, deposit, rent, notice, and maintenance records.',
    'VERSION': '0.1.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

_origins = os.environ.get('CORS_ALLOWED_ORIGINS') or str(env('CORS_ALLOWED_ORIGINS', 'http://localhost:3000'))
CORS_ALLOWED_ORIGINS = [origin.strip().rstrip('/') for origin in _origins.split(',') if origin.strip()]
CORS_ALLOW_CREDENTIALS = True
if DEBUG:
    for _origin in ('http://localhost:8081', 'http://127.0.0.1:8081', 'http://localhost:19006'):
        if _origin not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(_origin)

_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS') or str(env('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000'))
CSRF_TRUSTED_ORIGINS = [origin.strip().rstrip('/') for origin in _csrf.split(',') if origin.strip()]
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = str(env('SECURE_SSL_REDIRECT', 'false')).lower() in ('1', 'true', 'yes', 'on')

EMAIL_HOST_USER = str(env('EMAIL_HOST_USER', '')).strip()
if not EMAIL_HOST_USER:
    if DEBUG:
        EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    else:
        EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
        EMAIL_FILE_PATH = BASE_DIR / 'logs' / 'sent_emails'
        EMAIL_FILE_PATH.mkdir(parents=True, exist_ok=True)
        EMAIL_FILE_PATH = str(EMAIL_FILE_PATH)
else:
    EMAIL_BACKEND = str(env('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'))

EMAIL_HOST = str(env('EMAIL_HOST', 'smtp.gmail.com'))
EMAIL_USE_TLS = str(env('EMAIL_USE_TLS', 'True')) == 'True'
EMAIL_USE_SSL = str(env('EMAIL_USE_SSL', 'False')) == 'True'
EMAIL_PORT = int(env('EMAIL_PORT', '587'))
EMAIL_HOST_PASSWORD = str(env('EMAIL_HOST_PASSWORD', ''))
DEFAULT_FROM_EMAIL = str(env('DEFAULT_FROM_EMAIL', '')).strip() or EMAIL_HOST_USER or 'notices@localhost'
SERVER_EMAIL = str(env('SERVER_EMAIL', '')).strip() or DEFAULT_FROM_EMAIL
EMAIL_TIMEOUT = int(env('EMAIL_TIMEOUT', '10'))

FRONTEND_ORIGIN = str(env('FRONTEND_ORIGIN', 'http://localhost:3000')).rstrip('/')

# Service Alberta publishes the yearly rate. The app reminds; it does not invent the rate.
DEPOSIT_INTEREST_CALCULATOR_URL = 'https://www.servicealberta.ca/interest-chart.cfm'
ALBERTA_INSPECTION_GUIDE_URL = 'https://www.alberta.ca/system/files/custom_downloaded_images/sa-inspection-reports.pdf'

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

NOT_LEGAL_ADVICE = (
    "This tool follows publicly described Alberta inspection and deposit rules. "
    "It is not legal advice. Check the current Residential Tenancies Act and regulations, "
    "and have an Alberta landlord-tenant lawyer review your template before you rely on it."
)

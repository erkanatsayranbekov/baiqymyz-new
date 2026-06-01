from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
import os

BASE_DIR = Path(__file__).resolve().parent.parent

def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    return int(value)


def env_float(name, default):
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    return float(value)


def env_list(name, default=""):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "local-dev-secret-key-change-me"
    else:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is false.")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',  
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',  
            'propagate': False,
        },
    },
}


ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "baiqymyz.kz,www.baiqymyz.kz,127.0.0.1,localhost")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "https://baiqymyz.kz,https://www.baiqymyz.kz")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "https://baiqymyz.kz,https://www.baiqymyz.kz")


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'authentication',
    'corsheaders',  
    'rest_framework',
    'rest_framework.authtoken',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': env_int('DRF_PAGE_SIZE', 50),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.environ.get('DRF_ANON_THROTTLE_RATE', '200/hour'),
        'user': os.environ.get('DRF_USER_THROTTLE_RATE', '1000/hour'),
        'login': os.environ.get('DRF_LOGIN_THROTTLE_RATE', '20/hour'),
        'register': os.environ.get('DRF_REGISTER_THROTTLE_RATE', '20/hour'),
        'vote_create': os.environ.get('DRF_VOTE_CREATE_THROTTLE_RATE', '120/hour'),
        'vote_lookup': os.environ.get('DRF_VOTE_LOOKUP_THROTTLE_RATE', '240/hour'),
        'otp_request': os.environ.get('DRF_OTP_REQUEST_THROTTLE_RATE', '10/hour'),
        'otp_verify': os.environ.get('DRF_OTP_VERIFY_THROTTLE_RATE', '30/hour'),
        'manager_otp_generate': os.environ.get('DRF_MANAGER_OTP_THROTTLE_RATE', '20/hour'),
        'manager_login_request': os.environ.get('DRF_MANAGER_LOGIN_REQUEST_THROTTLE_RATE', '10/hour'),
        'manager_login_verify': os.environ.get('DRF_MANAGER_LOGIN_VERIFY_THROTTLE_RATE', '30/hour'),
    },
}

CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'


AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]


MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'baiqymyz_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'baiqymyz_api.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'baiqymyz'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

CACHES = {
    'default': {
        'BACKEND': os.environ.get('DJANGO_CACHE_BACKEND', 'django.core.cache.backends.locmem.LocMemCache'),
        'LOCATION': os.environ.get('DJANGO_CACHE_LOCATION', 'baiqymyz-default-cache'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Asia/Qyzylorda'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SERVE_MEDIA_IN_DJANGO = env_bool("SERVE_MEDIA_IN_DJANGO", DEBUG)
PARTICIPANTS_LEGACY_UNPAGINATED = env_bool("PARTICIPANTS_LEGACY_UNPAGINATED", True)

MOBIZON_API_BASE_URL = os.environ.get("MOBIZON_API_BASE_URL", "https://api.mobizon.kz/service/")
MOBIZON_API_KEY = os.environ.get("MOBIZON_API_KEY", "")
MOBIZON_SENDER = os.environ.get("MOBIZON_SENDER", "")
MOBIZON_API_OUTPUT = os.environ.get("MOBIZON_API_OUTPUT", "json")
MOBIZON_API_VERSION = os.environ.get("MOBIZON_API_VERSION", "v1")
MOBIZON_TIMEOUT_SECONDS = env_int("MOBIZON_TIMEOUT_SECONDS", 5)

OTP_AUTH_ENABLED = env_bool("OTP_AUTH_ENABLED", False)
LEGACY_PASSWORD_AUTH_ENABLED = env_bool("LEGACY_PASSWORD_AUTH_ENABLED", True)
OTP_SECRET = os.environ.get("OTP_SECRET", "")
if OTP_AUTH_ENABLED and not OTP_SECRET:
    raise ImproperlyConfigured("OTP_SECRET must be set when OTP_AUTH_ENABLED is true.")

OTP_CODE_LENGTH = env_int("OTP_CODE_LENGTH", 6)
OTP_TTL_SECONDS = env_int("OTP_TTL_SECONDS", 300)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
OTP_LOCKOUT_SECONDS = env_int("OTP_LOCKOUT_SECONDS", 900)
OTP_RESEND_COOLDOWN_SECONDS = env_int("OTP_RESEND_COOLDOWN_SECONDS", 60)
OTP_PHONE_DAILY_LIMIT = env_int("OTP_PHONE_DAILY_LIMIT", 10)
OTP_IP_DAILY_LIMIT = env_int("OTP_IP_DAILY_LIMIT", 30)
OTP_PURPOSE_LOGIN = os.environ.get("OTP_PURPOSE_LOGIN", "login")
OTP_PURPOSE_MANAGER_LOGIN = os.environ.get("OTP_PURPOSE_MANAGER_LOGIN", "manager_login")
OTP_CHALLENGE_RETENTION_DAYS = env_int("OTP_CHALLENGE_RETENTION_DAYS", 7)
MANAGER_OTP_ENABLED = env_bool("MANAGER_OTP_ENABLED", True)
MANAGER_AUTH_ENABLED = env_bool("MANAGER_AUTH_ENABLED", True)
MANAGER_SESSION_TTL_SECONDS = env_int("MANAGER_SESSION_TTL_SECONDS", 28800)

EVENT_LATITUDE = env_float("EVENT_LATITUDE", 51.160006)
EVENT_LONGITUDE = env_float("EVENT_LONGITUDE", 71.426149)
EVENT_VOTE_RADIUS_METERS = env_int("EVENT_VOTE_RADIUS_METERS", 15000)

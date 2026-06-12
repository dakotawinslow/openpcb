import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

TESTING = 'test' in sys.argv

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env.bool('DJANGO_DEBUG', default=False)
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS')

# Behind an HTTPS-terminating reverse proxy, Django's CSRF check compares the
# request Origin against this list — without the deployed origin here, every
# POST (login, signup, uploads) is rejected with 403. Comma-separated, each
# entry includes the scheme, e.g. https://alpha.openpcb.com.
CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])

# Production hardening — off by default so local HTTP dev keeps working.
# Set DJANGO_SSL=True once the site is served over HTTPS (e.g. behind a
# reverse proxy that terminates TLS).
DJANGO_SSL = env.bool('DJANGO_SSL', default=False)
SECURE_SSL_REDIRECT = DJANGO_SSL
SESSION_COOKIE_SECURE = DJANGO_SSL
CSRF_COOKIE_SECURE = DJANGO_SSL
if DJANGO_SSL:
    # TLS is terminated at the reverse proxy, so requests reach Django over
    # plain HTTP. Trust the proxy's forwarded scheme — without this,
    # request.is_secure() is always False and SECURE_SSL_REDIRECT loops forever.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7  # 1 week; raise once HTTPS is confirmed stable
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Preload requires max-age >= 1 year, so leave it off until the line above
    # is raised — sending `preload` now is ignored at best, a premature
    # HTTPS-only commitment at worst.
    SECURE_HSTS_PRELOAD = False

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'whitenoise.runserver_nostatic',
    'allauth',
    'allauth.account',
    'core',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'openpcb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'openpcb.wsgi.application'

DATABASES = {'default': env.db('DATABASE_URL')}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'assets']

if TESTING:
    # Tests create real ProjectFile/ProjectPhoto instances (thumbnail signals
    # write to `default` storage) — keep them in memory instead of hitting R2
    # or requiring R2 credentials to be configured for the test run. The
    # manifest static storage requires `collectstatic` to have run first, so
    # fall back to the plain (unhashed) storage for tests too.
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'access_key': env('R2_ACCESS_KEY_ID'),
                'secret_key': env('R2_SECRET_ACCESS_KEY'),
                'bucket_name': env('R2_BUCKET_NAME'),
                'endpoint_url': env('R2_ENDPOINT_URL'),
                'default_acl': None,
                'file_overwrite': False,
                'signature_version': 's3v4',
                # Private-project confidentiality depends on this: every generated
                # URL is signed and short-lived, so objects are never reachable by
                # guessing the (predictable) projects/<id>/<name> path. Keep the R2
                # bucket itself private — do not attach a public r2.dev / custom
                # domain to it.
                'querystring_auth': True,
                'querystring_expire': 3600,
            },
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Structured logging to stdout — captured by `docker compose logs` / the
# host's container log driver. Django's own request/error logs (e.g. 500s)
# flow through the 'django' logger below.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# GlitchTip (Sentry-API-compatible) error tracking. Unset/empty in dev — no
# DSN means sentry_sdk.init is skipped entirely, so local runs never report.
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN and not TESTING:
    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, send_default_pii=False)

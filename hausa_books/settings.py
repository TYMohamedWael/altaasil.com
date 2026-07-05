import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

print(f"DEBUG={os.environ.get('DEBUG', 'True')}")
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production-abc123xyz')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
    'https://altaasil.com',
    'https://www.altaasil.com',
    'http://127.0.0.1:8000'
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'rest_framework.authtoken',
    'rosetta',
    'books',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hausa_books.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',  # <<< مهم
                'books.context_processors.languages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hausa_books.wsgi.application'

# Database: MySQL if configured, otherwise SQLite
DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite3')

if DB_ENGINE == 'mysql':
    import pymysql
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'littattafan_hausa'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            'OPTIONS': {'charset': 'utf8'},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'ha'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
USE_I18N = True
USE_L10N = True

from django.utils.translation import gettext_lazy as _

class DynamicLanguagesList(list):
    def __init__(self, fallback_list):
        self.fallback_list = fallback_list
        super().__init__(fallback_list)

    def _get_languages(self):
        try:
            from django.apps import apps
            if not apps.ready:
                return self.fallback_list
            from django.db import connection
            import django.conf.locale

            langs = []
            seen = set()

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT code, name_native, name_english, direction FROM books_language "
                    "WHERE is_active = 1 ORDER BY `order`"
                )
                rows = cursor.fetchall()

            for code, name_native, name_english, direction in rows:
                if not code:
                    continue
                code = code.strip().lower()
                name = name_native or name_english or code
                if code not in seen:
                    langs.append((code, name))
                    seen.add(code)
                    if code not in django.conf.locale.LANG_INFO:
                        django.conf.locale.LANG_INFO[code] = {
                            'bidi': direction == 'rtl',
                            'code': code,
                            'name': name_english or name,
                            'name_local': name,
                        }

            # Merge fallback entries not already in DB
            for fb_code, fb_name in self.fallback_list:
                fb_code = str(fb_code)
                if fb_code not in seen:
                    langs.append((fb_code, fb_name))
                    seen.add(fb_code)

            return langs if langs else self.fallback_list
        except Exception:
            return self.fallback_list

    def __iter__(self):
        return iter(self._get_languages())

    def __len__(self):
        return len(self._get_languages())

    def __getitem__(self, index):
        return self._get_languages()[index]

    def __repr__(self):
        return repr(self._get_languages())

    def __str__(self):
        return str(self._get_languages())

    def __contains__(self, item):
        return item in self._get_languages()

    def __eq__(self, other):
        return self._get_languages() == other

    def copy(self):
        return list(self._get_languages())

    def append(self, item):
        if item not in self.fallback_list:
            self.fallback_list.append(item)

    def extend(self, items):
        for item in items:
            self.append(item)

LANGUAGES = DynamicLanguagesList([
    ('ha', _('Hausa')),
    ('ar', _('العربية')),
    ('en', _('English')),
    ('am', _('Amharic')),
    ('sw', _('Swahili')),
    ('bn', _('Bengali'))
])

EXTRA_LANG_INFO = {
    'ha': {
        'bidi': False,
        'code': 'ha',
        'name': 'Hausa',
        'name_local': 'Hausa',
    },
    'am': {
        'bidi': False,
        'code': 'am',
        'name': 'Amharic',
        'name_local': 'Amharic',
    },
}

import django.conf.locale
django.conf.locale.LANG_INFO.update(EXTRA_LANG_INFO)
LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = DEBUG

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / '.cache',
    }
}

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}

# ==============================================================================
# MONKEY PATCH: Bypass MariaDB version check for XAMPP (MariaDB 10.4)
# ==============================================================================
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.mysql.features import DatabaseFeatures

# 1. Disable the database version check
BaseDatabaseWrapper.check_database_version_supported = lambda self: None

# 2. Disable `INSERT ... RETURNING` syntax 
# (Django 5.1+ expects this syntax, but MariaDB 10.4 doesn't support it)
DatabaseFeatures.can_return_columns_from_insert = False
DatabaseFeatures.can_return_rows_from_bulk_insert = False
# ==============================================================================

# EthAfri/core/settings.py

import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _
import dj_database_url

# 1. Environment Variable Setup (Termux Fix)
try:
    from environ import Env
    env = Env()
    Env.read_env()
except ImportError:
    class Env:
        def __call__(self, key, default=None): return os.environ.get(key, default)
        def bool(self, key, default=False): return os.environ.get(key, str(default)).lower() == 'true'
    env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env('SECRET_KEY', default='django-insecure-ethafri-key-2026')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com', 'https://*.pythonanywhere.com']

# 2. Application Definition
INSTALLED_APPS = [
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'marketplace',
    'cloudinary',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'marketplace.views.theme_context', 
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# 3. Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# 4. Internationalization
LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', _('English')),
    ('am', _('Amharic')),
    ('om', _('Oromo')),
    ('ar', _('Arabic')),
    ('so', _('Somali')),
    ('ti', _('Tigrinya')),
    ('fr', _('French')),
]
TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# 5. Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

# ⚠️ 6. የ AI እና የሰርቨር ቁልፎችን በቀጥታ ከሬንደር ሰርቨር ላይ ማንበቢያ (ስህተቱን በቋሚነት ይፈታል!)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')

RENDER_SERVICE_ID = os.environ.get('RENDER_SERVICE_ID', '')
RENDER_API_KEY = os.environ.get('RENDER_API_KEY', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
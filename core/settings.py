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
    # ፓኬጁ ተርሙክስ ላይ ባይኖር እንኳን ኮዱ እንዳይሰበር (ከ os.environ ያነባል)
    class Env:
        def __call__(self, key, default=None): return os.environ.get(key, default)
        def bool(self, key, default=False): return os.environ.get(key, str(default)).lower() == 'true'
    env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Security
SECRET_KEY = env('SECRET_KEY', default='django-insecure-ethafri-key-2026')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com', 'https://*.pythonanywhere.com']

# 3. Application Definition
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
                # የ AI ዲዛይን ለውጥን (Theme) በሁሉም ገጾች ላይ እንዲገኝ የሚያደርግ
                'marketplace.views.theme_context', 
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# 4. Database
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# 5. Internationalization (7 Languages)
LANGUAGE_CODE = 'am'
LANGUAGES = [
    ('am', _('Amharic')),
    ('en', _('English')),
    ('om', _('Oromo')),
    ('ar', _('Arabic')),
    ('so', _('Somali')),
    ('ti', _('Tigrinya')),
    ('fr', _('French')),
]
TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
USE_TZ = True

# 6. Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# 7. AI Keys
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GROQ_API_KEY = env('GROQ_API_KEY', default='')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
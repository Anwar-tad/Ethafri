# EthAfri/core/settings.py

import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _
import dj_database_url

# =====================================================================
# 1. Environment Variable & Base Directory Setup
# =====================================================================
try:
    from environ import Env
    env = Env()
    Env.read_env()
except ImportError:
    # django-environ በሌለበት አካባቢ (እንደ Termux) እንዳይቋረጥ መከላከያ
    class Env:
        def __call__(self, key, default=None): return os.environ.get(key, default)
        def bool(self, key, default=False): return os.environ.get(key, str(default)).lower() == 'true'
    env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================================================
# 2. Core Security & Environment Settings
# =====================================================================
SECRET_KEY = env('SECRET_KEY', default='django-insecure-ethafri-key-2026')
DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = ['*']

# በ Render ላይ የሚፈጠረውን የ CSRF Verification ስህተት በቋሚነት ለመከላከል የተደረገ ቅንብር
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com', 'https://*.pythonanywhere.com']

# =====================================================================
# 3. Application Definition
# =====================================================================
INSTALLED_APPS = [
    'cloudinary_storage',  # Cloudinary ስታቲክ ፋይሎችን እንዲያስተዳድር ከላይ መሆን አለበት
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
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ለስታቲክ ፋይሎች ማስተናገጃ
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # ⚠️ የቋንቋ መቀያየሪያ (Locale) ሚድልዌር
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',  # ⚠️ ወደ ትክክለኛው ሚድልዌር ተስተካክሏል
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
                'marketplace.views.theme_context',  # የ AI ዩአይ ከለር መቆጣጠሪያ ኮንቴክስት
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# =====================================================================
# 4. Database (Hybrid: PostgreSQL in Production, SQLite in Local)
# =====================================================================
database_url = env('DATABASE_URL', default='')

if database_url:
    # ሰርቨር ላይ በሚሆንበት ጊዜ PostgreSQL ይጠቀማል (ከ SSL ደህንነት ጋር)
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            ssl_require=True
        )
    }
else:
    # በኮምፒውተርህ ላይ (Locally) በሚሆንበት ጊዜ በራስ-ሰር SQLite3 ይጠቀማል
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =====================================================================
# 5. Internationalization (Multilingual Settings)
# =====================================================================
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

# =====================================================================
# 6. Static & Media Files (Whitenoise & Cloudinary Storage)
# =====================================================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# የስታቲክ ፋይሎችን በሰርቨር ላይ ለማሳነስና ለማመቅ (WhiteNoise)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# የሚሰቀሉ የሚዲያ ምስሎችን በ Cloudinary ላይ ለማስቀመጥ
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}

# =====================================================================
# 7. AI API & Server Keys (Environment Variables)
# =====================================================================
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GROQ_API_KEY = env('GROQ_API_KEY', default='')
MISTRAL_API_KEY = env('MISTRAL_API_KEY', default='')
OPENROUTER_API_KEY = env('OPENROUTER_API_KEY', default='')

RENDER_SERVICE_ID = env('RENDER_SERVICE_ID', default='')
RENDER_API_KEY = env('RENDER_API_KEY', default='')
GITHUB_TOKEN = env('GITHUB_TOKEN', default='')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
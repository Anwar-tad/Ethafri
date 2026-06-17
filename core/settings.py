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
    'cloudinary_storage', # ከ 'django.contrib.staticfiles' በፊት መሆን አለበት
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
    # ⚠️ 1. የቋንቋ መቀያየሪያ ሚድልዌር (LocaleMiddleware) ተጨምሯል (ለ i18n ወሳኝ ነው)
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
                # የ AI ዲዛይን ለውጥን (Theme) በሁሉም ገጾች ላይ እንዲገኝ የሚያደርግ
                (marketplace.views.theme_context)
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

# 5. Internationalization (ነባሪ ቋንቋው ወደ እንግሊዝኛ ተቀይሯል)
LANGUAGE_CODE = 'en' # ነባሪ ቋንቋ እንግሊዝኛ እንዲሆን

LANGUAGES = [
    ('en', _('English')), # እንግሊዝኛ ቀዳሚ ምርጫ ሆኗል
    ('am', _('Amharic')),
    ('om', _('Oromo')),
    ('ar', _('Arabic')),
    ('so', _('Somali')),
    ('ti', _('Tigrinya')),
    ('fr', _('French')),
]
TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
# ⚠️ 2. USE_L10N ተወግዷል (በአዲሱ Django 6.0.6 ስሪት ውስጥ ስለማይደገፍ ስህተት ይፈጥራል)
USE_TZ = True

# 3. የትርጉም ፋይሎች የሚቀመጡበት ፎልደር (Locale Path) ተጨምሯል
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# 6. Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ⚠️ 4. የCloudinary ማከማቻ ቅንብር ተጨምሯል (ምስሎች እንዳይጠፉ በ os.environ ያነባል)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

# 7. AI & Render Keys (በቀጥታ ከሲስተሙ ያነባል)
# 7. AI & Render Keys (ባለ 4ቱ የጀሚኒ ኪዮች ለትርጉም እና ለኮዲንግ)
# እነዚህ ኪዮች በ Render/PythonAnywhere Environment Variables ውስጥ መግባት አለባቸው
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')     # Translation Pool 1
GEMINI_API_KEY_2 = os.environ.get('GEMINI_API_KEY_2', '') # Translation Pool 2
GEMINI_API_KEY_3 = os.environ.get('GEMINI_API_KEY_3', '') # Coding Pool 1
GEMINI_API_KEY_4 = os.environ.get('GEMINI_API_KEY_4', '') # Coding Pool 2

GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY', '')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')

RENDER_SERVICE_ID = os.environ.get('RENDER_SERVICE_ID', '')
RENDER_API_KEY = os.environ.get('RENDER_API_KEY', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
import os
from pathlib import Path
from environ import Env
from django.utils.translation import gettext_lazy as _

env = Env()
Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env('SECRET_KEY', default='django-insecure-your-secret-key')

DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'cloudinary_storage', # ከ 'django.contrib.staticfiles' በፊት መሆን አለበት
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # የEthAfri ሞጁሎች
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

# (ስህተት 1 መፍትሄ) TEMPLATES ብሎኩ ሙሉ በሙሉ እንዲህ መሆን አለበት
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True, # ይህ ለአድሚን ገጽ በጣም አስፈላጊ ነው
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

WSGI_APPLICATION = 'core.wsgi.application'

# ዳታቤዝ
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=0, # ለ Pooler 0 መሆኑ ይመረጣል
        ssl_require=True
    )
}

# (ስህተት 2 መፍትሄ) ቋንቋ እና ትርጉም
LANGUAGE_CODE = 'am'
LANGUAGES = [
    ('am', _('Amharic')),
    ('en', _('English')),
]

TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ስታቲክ ፋይሎች
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ሚዲያ ፋይሎች (Cloudinary)
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}

# AI Keys (ሁለቱንም አማራጮች እዚህ እናስቀምጥ)
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GROQ_API_KEY = env('GROQ_API_KEY', default='') # ለFallback የተጨመረ

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
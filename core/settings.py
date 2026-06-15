import os
from pathlib import Path
from environ import Env
from django.utils.translation import gettext_lazy as _
import dj_database_url

# 1. Environment Variables Setup
env = Env()
Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Security Settings
SECRET_KEY = env('SECRET_KEY', default='django-insecure-your-secret-key-change-this')

DEBUG = env.bool('DEBUG', default=True)

# ሬንደር ላይ እና በሁሉም ቦታ እንዲሰራ
ALLOWED_HOSTS = ['*']
# POST ሪኩዌስት (እቃ መለጠፍ) እንዳይከለከል
CSRF_TRUSTED_ORIGINS = ['https://*.onrender.com', 'https://*.pythonanywhere.com']

# 3. Application Definition
INSTALLED_APPS = [
    'cloudinary_storage', # የግድ ከstaticfiles በፊት መሆን አለበት
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # የEthAfri ዋና መተግበሪያ
    'marketplace', 
    'cloudinary',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # ለስታቲክ ፋይሎች
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

# 4. Templates Setup (Admin ስህተትን የሚፈታ)
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
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# 5. Database Configuration (ለSupabase Pooler 6543 የተመቻቸ)
DATABASES = {
    'default': dj_database_url.config(
        default=env('DATABASE_URL'),
        conn_max_age=0,
        ssl_require=True
    )
}

# 6. Internationalization (ቋንቋና ሰዓት)
LANGUAGE_CODE = 'am'
LANGUAGES = [
    ('am', _('Amharic')),
    ('en', _('English')),
]

TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# 7. Static and Media Files (WhiteNoise + Cloudinary)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': env('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': env('CLOUDINARY_API_SECRET', default=''),
}

# 8. AI API Keys (ለራስ-ገዝ ዕድገት)
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GROQ_API_KEY = env('GROQ_API_KEY', default='')

# 9. Authentication URLs
LOGIN_URL = '/admin/login/' # ለጊዜው የአድሚን መግቢያን እንጠቀማለን
LOGIN_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
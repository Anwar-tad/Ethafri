# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/core/settings.py
# 📝 ስሪት፦ v10.18 (Production Grade - Central System Settings - Hardened)
# ✅ የተፈቱ ችግሮች፦ Added Gemini Key 4 config, central emergency schema reset switch, secure lazy-load logging warning, and Django 4.2+ STORAGES.
# 📅 ቀን፦ Saturday, July 04, 2026
# ============================================================

import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _
import dj_database_url
import logging

# =====================================================================
# 1. Environment Variable & Base Directory Setup
# =====================================================================
try:
    from environ import Env
    env = Env()
    Env.read_env()
except ImportError:
    class Env:
        def __call__(self, key, default=None): 
            return os.environ.get(key, default)
        def bool(self, key, default=False): 
            return os.environ.get(key, str(default)).lower() == 'true'
    env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================================================
# 2. Core Security & Environment Settings
# =====================================================================
SECRET_KEY = env('SECRET_KEY', default='django-insecure-ethafri-key-2026')
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = ['*']

CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com', 
    'https://*.pythonanywhere.com',
    'http://localhost:8000',
]

# =====================================================================
# 3. Application Definition (Daphne at top for ASGI support)
# =====================================================================
INSTALLED_APPS = [
    # Daphne for Django Channels ASGI (Daphne must be at the top)
    'daphne',
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'marketplace',
    'cloudinary',
    'channels',
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

# ASGI Application for WebSocket
ASGI_APPLICATION = 'core.asgi.application'

# =====================================================================
# 4. Database (Hybrid: PostgreSQL in Production, SQLite in Local)
# =====================================================================
database_url = env('DATABASE_URL', default='')

if database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# =====================================================================
# 5. Internationalization & Localization
# =====================================================================
LANGUAGE_CODE = 'am' # ዲፎልት ቋንቋ አማርኛ

TIME_ZONE = 'Africa/Addis_Ababa'

USE_I18N = True

USE_TZ = True

# =====================================================================
# 6. Cloudinary & Static Files Settings
# =====================================================================
CLOUDINARY_CLOUD_NAME = env('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = env('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = env('CLOUDINARY_API_SECRET', default='')

# Django 4.2/5.0 Storages መዝገብ [1]
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage" if CLOUDINARY_CLOUD_NAME else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage" if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
WHITENOISE_MAX_AGE = 31536000
WHITENOISE_ALLOW_ALL_ORIGINS = True
WHITENOISE_MANIFEST_STRICT = False

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
else:
    print("⚠️ Cloudinary not configured. Using local file storage.")

# =====================================================================
# 7. AI API & Server Keys
# =====================================================================
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_API_KEY_2 = env('GEMINI_API_KEY_2', default='')
GEMINI_API_KEY_3 = env('GEMINI_API_KEY_3', default='')
GEMINI_API_KEY_4 = env('GEMINI_API_KEY_4', default='') # ✅ FIXED: የ 4ኛው ጌሚኒ ቁልፍ እዚህ ተጨምሯል
GROQ_API_KEY = env('GROQ_API_KEY', default='')
MISTRAL_API_KEY = env('MISTRAL_API_KEY', default='')
OPENROUTER_API_KEY = env('OPENROUTER_API_KEY', default='')
HUGGINGFACE_API_KEY = env('HUGGINGFACE_API_KEY', default='')

# 🔴 AI KEY ROTATION: ኤጀንቱ አንዱ ኤፒአይ ሲያልቅበት ወደ ሌላው እንዲያልፍ ዝርዝር ማደራጀት [1]
AI_FALLBACK_API_KEYS = [
    GEMINI_API_KEY_2,
    GEMINI_API_KEY_3,
    GEMINI_API_KEY_4, # ✅ 4ኛው ጌሚኒ ቁልፍ እዚህ ማሽከርከሪያ ውስጥ ገብቷል
    GROQ_API_KEY,
    MISTRAL_API_KEY,
    OPENROUTER_API_KEY,
    HUGGINGFACE_API_KEY
]
# ባዶ የሆኑ ቁልፎችን ዝርዝር ውስጥ ማስወገድ
AI_FALLBACK_API_KEYS = [k for k in AI_FALLBACK_API_KEYS if k]

RENDER_SERVICE_ID = env('RENDER_SERVICE_ID', default='')
RENDER_API_KEY = env('RENDER_API_KEY', default='')
GITHUB_TOKEN = env('GITHUB_TOKEN', default='')

# 🛡️ FIXED: ድንገተኛ የዳታቤዝ መደመሰስን ለመከላከል የደህንነት ስዊች መቆጣጠሪያ እዚህ ተጭኗል
ALLOW_EMERGENCY_SCHEMA_RESET = env.bool('ALLOW_EMERGENCY_SCHEMA_RESET', default=False)

# Twilio for SMS Marketing
TWILIO_SID = env('TWILIO_SID', default='')
TWILIO_TOKEN = env('TWILIO_TOKEN', default='')
TWILIO_PHONE = env('TWILIO_PHONE', default='')

# Email Settings
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@ethafri.com')
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================================================
# 8. WebSocket & Channels Configuration
# =====================================================================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# ============================================================
# 9. የትውስታ መሸጎጫ አስተዳደር (Caching)
# ============================================================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# ============================================================
# 🎡 10. MASTER ENGINE COOLDOWNS & PACING
# ============================================================
AI_ENABLED_FEATURES = [
    'self_evolution', 'self_healing', 'competitor_intelligence', 
    'predictive_seo', 'auto_marketing', 'dynamic_pricing'
]
AI_MODEL_VERSION = '2026.07.04'


# ============================================================
# 🛡️ 11. SAFE SELF-HEALING DATABASE LOGGER INTEGRATION
# ============================================================
# ⚠️ ማሳሰቢያ፦ 'SelfHealingDBHandler' ሰርቨሩ በሚነሳበት ጊዜ 'AppRegistryNotReady' ስህተት
# እንዳይፈጥር፣ በውስጡ የሚገኙት ሞዴሎችና የዳታቤዝ ጥሪዎች በሙሉ Dynamically (lazy loaded) መሆን አለባቸው [1]።

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        # 🔴 የዳታቤዝ ግንኙነት ሲበላሽ ራሱን በራሱ የሚጠግነው የደህንነት ጋሻ [1]
        'self_healing_db': {
            'class': 'marketplace.log_handlers.SelfHealingDBHandler',
        },
    },
    'root': {
        'handlers': ['console', 'self_healing_db'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'INFO',
            'propagate': False,
        },
        'marketplace': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Autonomous Agent Settings
AUTONOMOUS_AGENT_ENABLED = env.bool('AUTONOMOUS_AGENT_ENABLED', default=True)
AGENT_INTERVAL = env('AGENT_INTERVAL', default=60)
AGENT_MAX_ERRORS = env('AGENT_MAX_ERRORS', default=10)
SKIP_SHELL = env.bool('SKIP_SHELL', default=True)
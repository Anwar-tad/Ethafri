# ============================================================
# 📁 ፋይል፦ EthAfri/core/settings.py
# 📝 ለውጥ፦ Advanced Agent Features — pgvector, WebSocket, Cache
# 📅 ቀን፦ 2026-06-21
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
# 3. Application Definition
# =====================================================================
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
    # 🆕 Channels for WebSocket
    'channels',
    # 🆕 pgvector for RAG (ከተጫነ በኋላ)
    # 'pgvector',
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

# 🆕 ASGI Application for WebSocket
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
            ssl_require=True
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

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
WHITENOISE_MAX_AGE = 31536000
WHITENOISE_ALLOW_ALL_ORIGINS = True
WHITENOISE_MANIFEST_STRICT = False

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME = env('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = env('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = env('CLOUDINARY_API_SECRET', default='')

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_STORAGE = {
        'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
        'API_KEY': CLOUDINARY_API_KEY,
        'API_SECRET': CLOUDINARY_API_SECRET,
    }
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    print("⚠️ Cloudinary not configured. Using local file storage.")

# =====================================================================
# 7. AI API & Server Keys
# =====================================================================
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
GEMINI_API_KEY_2 = env('GEMINI_API_KEY_2', default='')
GEMINI_API_KEY_3 = env('GEMINI_API_KEY_3', default='')
GROQ_API_KEY = env('GROQ_API_KEY', default='')
MISTRAL_API_KEY = env('MISTRAL_API_KEY', default='')
OPENROUTER_API_KEY = env('OPENROUTER_API_KEY', default='')
HUGGINGFACE_API_KEY = env('HUGGINGFACE_API_KEY', default='')

RENDER_SERVICE_ID = env('RENDER_SERVICE_ID', default='')
RENDER_API_KEY = env('RENDER_API_KEY', default='')
GITHUB_TOKEN = env('GITHUB_TOKEN', default='')

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
# core/settings.py ውስጥ
ASGI_APPLICATION = 'core.asgi.application'
# =====================================================================
# 8. 🆕 WebSocket & Channels Configuration
# =====================================================================

# Channels Layer (In-memory for development)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# ለምርት (Production) Redis መጠቀም ከፈለግክ
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             "hosts": [('127.0.0.1', 6379)],
#         },
#     },
# }

# =====================================================================
# 9. 🆕 Cache Configuration
# =====================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ethafri-cache',
    }
}

# Redis ለምርት ከፈለግክ
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#     }
# }

# Cache Timeouts
CACHE_TTL = {
    'short': 60,       # 1 ደቂቃ
    'medium': 300,     # 5 ደቂቃ
    'long': 3600,      # 1 ሰዓት
    'very_long': 86400, # 1 ቀን
}

# =====================================================================
# 10. 🆕 pgvector Configuration (RAG Memory)
# =====================================================================

# pgvector extension ን ለመጠቀም
# ማይግሬሽን ከሄደ በኋላ ይህንን አንቃ
# INSTALLED_APPS ላይ 'pgvector' ን ተጨምር

# Vector dimension for embeddings
VECTOR_DIMENSION = 1536  # OpenAI embedding size

# =====================================================================
# 11. Multi-Site Configuration
# =====================================================================

DEFAULT_SITE_CONFIG = {
    'name': 'primary',
    'display_name': 'EthAfri Primary',
    'niche': 'general',
    'target_market': 'Global',
    'content_style': 'professional',
    'is_active': True,
    'auto_update_enabled': True,
    'auto_marketing_enabled': True,
}

GROWTH_THRESHOLDS = {
    'LOCAL': 100,
    'CITY': 1000,
    'COUNTRY': 10000,
    'CONTINENT': 100000,
    'GLOBAL': 1000000,
}

AUTO_MARKETING_CONFIG = {
    'enabled': True,
    'max_campaigns_per_day': 3,
    'max_notifications_per_day': 50,
    'social_media_posting': True,
    'email_marketing': True,
    'sms_marketing': False,
}

# =====================================================================
# 12. Logging Configuration
# =====================================================================

try:
    from marketplace.log_handlers import SelfHealingDBHandler
except ImportError:
    class SelfHealingDBHandler(logging.Handler):
        def emit(self, record):
            pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '{levelname} {asctime} {name} {filename}:{lineno} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'self_healing_db': {
            'level': 'WARNING',
            'class': 'marketplace.log_handlers.SelfHealingDBHandler',
            'formatter': 'simple',
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
        'django.request': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'WARNING',
            'propagate': False,
        },
        'marketplace': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'INFO',
            'propagate': False,
        },
        'marketplace.growth_agent': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'marketplace.self_coder': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'marketplace.self_doctor': {
            'handlers': ['console', 'self_healing_db'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # 🆕 Channels logging
        'channels': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'daphne': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# core/settings.py ውስጥ ጨምር

# Autonomous Agent Settings
AUTONOMOUS_AGENT_ENABLED = env.bool('AUTONOMOUS_AGENT_ENABLED', default=True)
AGENT_INTERVAL = env('AGENT_INTERVAL', default=60)  # seconds
AGENT_MAX_ERRORS = env('AGENT_MAX_ERRORS', default=10)
SKIP_SHELL = env.bool('SKIP_SHELL', default=True)
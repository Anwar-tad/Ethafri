import os
from pathlib import Path
# ለደህንነት ሲባል API Keyዎችን ከ environment ለማንበብ
from environ import Env 

env = Env()
Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

# የደህንነት ማስጠንቀቂያ፡ ይህንን ቁልፍ ለወደፊት በ Environment Variable መደበቅ አለብህ
SECRET_KEY = env('SECRET_KEY', default='django-insecure-your-secret-key')

DEBUG = True # ወደ ፕሮዳክሽን ሲገባ False ይደረጋል

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # የEthAfri ሞጁሎች
    'marketplace', 
    'cloudinary_storage', # ለፎቶዎች (በRender ላይ ፎቶ እንዳይጠፋ)
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

# ... TEMPLATES እና WSGI እንዳሉ ይቀጥላሉ ...

# ዳታቤዝ፡ ለጊዜው በSQLite ይቆይና Render ላይ PostgreSQL ስንፈጥር እንቀይረዋለን
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

# ቋንቋ፡ ኢቲአፍሪን ለኢትዮጵያ ዝግጁ ማድረግ
LANGUAGE_CODE = 'am' # ዋናው ቋንቋ አማርኛ እንዲሆን
TIME_ZONE = 'Africa/Addis_Ababa'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ስታቲክ ፋይሎች
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ሚዲያ ፋይሎች (ፎቶዎች እዚህ ይገባሉ)
MEDIA_URL = '/media/'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage' # ፎቶዎች በCloudinary እንዲቀመጡ
MEDIA_ROOT = BASE_DIR / 'media'

# የGemini AI ቁልፍን በሲስተሙ ውስጥ ማገናኛ
GEMINI_API_KEY = env('GEMINI_API_KEY', default='YOUR_API_KEY_HERE')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/core/wsgi.py
# 📝 ዓላማ፦ WSGI Configuration for traditional HTTP Server (v1.2 - Complete)
# ✅ የተፈቱ ችግሮች፦ Standard production WSGI boot integration
# 📅 ቀን፦ Wednesday, July 01, 2026
# ============================================================
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = get_wsgi_application()
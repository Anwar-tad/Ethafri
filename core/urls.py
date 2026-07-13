# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/core/urls.py
# 📝 ዓላማ፦ Main URL Routing for the Core Project (v10.17)
# ✅ የተፈቱ ችግሮች፦ Dynamic i18n switching routing, admin and app inclusion, and secure debug static asset serving.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ዋና የፕሮጀክቱ ዩአርኤል መዋቅር
urlpatterns = [
    # የአድሚን ገጽ መግቢያ
    path('admin/', admin.site.urls),
    
    # የቋንቋ መቀያየሪያ የዲጃንጎ ኦፊሴላዊ ዩአርኤል (i18n Support)
    path('i18n/', include('django.conf.urls.i18n')), 
    
    # ዋና የማርኬት ፕሌስ መተግበሪያ ዩአርኤሎች
    path('', include('marketplace.urls')),
]

# በሙከራ (Testing) ወቅት የሚዲያ ፋይሎችን በደህንነት ማገልገያ
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
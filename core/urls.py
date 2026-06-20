# ============================================================
# 📁 ፋይል፦ EthAfri/core/urls.py
# 📝 ለውጥ፦ ምንም ለውጥ አያስፈልግም (አስቀድሞ በትክክል ተዘጋጅቷል)
# 📅 ቀን፦ 2026-06-20
# ============================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ⚠️ የቋንቋ መቀያየሪያ የዲጃንጎ ኦፊሴላዊ ዩአርኤል
    path('i18n/', include('django.conf.urls.i18n')), 
    
    path('', include('marketplace.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
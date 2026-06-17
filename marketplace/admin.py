# EthAfri/marketplace/admin.py

from django.contrib import admin
from .models import Product, Category, UserSearch, ProductTranslation, SiteConfig, MarketTrend, AISystemTask, OwnerDirective, SelfHealingLog

# የድሮዎቹ ምዝገባዎች
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(UserSearch)

# ⚠️ አዳዲሶቹ የ AI እና የአስተዳደር ሞዴሎች እዚህ ተመዝግበዋል (ስህተቱን ለመከላከልና ቁጥጥርን ለማጠናከር)
admin.site.register(ProductTranslation)
admin.site.register(SiteConfig)
admin.site.register(MarketTrend)
admin.site.register(AISystemTask)
admin.site.register(OwnerDirective)
admin.site.register(SelfHealingLog)
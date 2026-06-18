# EthAfri/marketplace/admin.py

from django.contrib import admin
from .models import (
    Product, Category, UserSearch, ProductTranslation, 
    SiteConfig, MarketTrend, AISystemTask, OwnerDirective, SelfHealingLog,
    AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction  # ⚠️ አዳዲሶቹ ሞዴሎች ተጨምረዋል
)

# 1. መሰረታዊ ሞዴሎች
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'category', 'created_at')
    search_fields = ('title', 'description')

admin.site.register(Category)
admin.site.register(UserSearch)

# 2. የ AI እና የራስ-ገዝ ሲስተም ሞዴሎች (Advanced Admin Views)
@admin.register(ProductTranslation)
class ProductTranslationAdmin(admin.ModelAdmin):
    list_display = ('product', 'am', 'en')
    search_fields = ('product__title',)

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')

@admin.register(MarketTrend)
class MarketTrendAdmin(admin.ModelAdmin):
    list_display = ('niche_name', 'demand_level', 'last_updated')

@admin.register(AISystemTask)
class AISystemTaskAdmin(admin.ModelAdmin):
    # ⚠️ 'priority' ወደ ትክክለኛው 'priority_reason' ተስተካክሏል
    list_display = ('task_name', 'priority_reason', 'status', 'created_at')
    list_filter = ('status',)

@admin.register(OwnerDirective)
class OwnerDirectiveAdmin(admin.ModelAdmin):
    # ⚠️ 'is_processed' ወደ ትክክለኛው 'is_active' ተስተካክሏል
    list_display = ('instruction', 'created_at', 'is_active')

@admin.register(SelfHealingLog)
class SelfHealingLogAdmin(admin.ModelAdmin):
    list_display = ('error_message', 'resolved', 'created_at')
    list_filter = ('resolved',)
    search_fields = ('error_message',)


# =====================================================================
# 🛠️ ፖርትፎሊዮ 1፦ የአዲሶቹ የዕዝ ማዕከል እና የባክሎግ ሞዴሎች ምዝገባ (NEW REGISTRATIONS)
# =====================================================================

@admin.register(AIProjectBacklog)
class AIProjectBacklogAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'target_file', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'target_file')
    search_fields = ('task_name', 'description')

@admin.register(AIEvolutionLog)
class AIEvolutionLogAdmin(admin.ModelAdmin):
    list_display = ('target_file', 'reason_for_change', 'created_at')
    search_fields = ('target_file', 'reason_for_change')

@admin.register(AdminOverrideInstruction)
class AdminOverrideInstructionAdmin(admin.ModelAdmin):
    list_display = ('instruction', 'priority_override', 'is_processed', 'created_at')
    list_filter = ('is_processed', 'priority_override')
    search_fields = ('instruction',)
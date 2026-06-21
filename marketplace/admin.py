# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/admin.py
# 📝 ለውጥ፦ Advanced Agent Features — Active (ኮሜንት ተወግዷል)
# 📅 ቀን፦ 2026-06-21
# ============================================================

from django.contrib import admin
from .models import (
    Product,
    Category,
    UserSearch,
    ProductTranslation,
    SiteConfig,
    MarketTrend,
    SelfHealingLog,
    AIProjectBacklog,
    AIEvolutionLog,
    AdminOverrideInstruction,
    AgentErrorLog,
    SiteRegistry,
    CustomerAcquisitionLog,
    MarketingCampaign,
    SellerProfile,
    NotificationQueue,
    # 🆕 አዲሶቹን ሞዴሎች እዚህ ተጨምረዋል
    VectorMemory,
    AgentTask,
    ABTest,
    SecurityLog,
    PredictionLog,
    ExternalAPI
)

# ============================================================
# 1. መሰረታዊ ሞዴሎች
# ============================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'category', 'seo_score', 'view_count', 'created_at')
    list_filter = ('category', 'is_active', 'market_value_status')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('view_count', 'inquiry_count', 'created_at', 'updated_at')

admin.site.register(Category)
admin.site.register(UserSearch)


# ============================================================
# 2. የ AI እና የራስ-ገዝ ሲስተም ሞዴሎች
# ============================================================

@admin.register(ProductTranslation)
class ProductTranslationAdmin(admin.ModelAdmin):
    list_display = ('product', 'am', 'en')
    search_fields = ('product__title',)

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'updated_at')
    search_fields = ('key',)

@admin.register(MarketTrend)
class MarketTrendAdmin(admin.ModelAdmin):
    list_display = ('niche_name', 'demand_level', 'last_updated')
    search_fields = ('niche_name', 'ai_suggestion')

@admin.register(SelfHealingLog)
class SelfHealingLogAdmin(admin.ModelAdmin):
    list_display = ('error_message', 'resolved', 'created_at')
    list_filter = ('resolved',)
    search_fields = ('error_message',)


# ============================================================
# 3. የኤጀንት ማህደረ-ትውስታ ሞዴሎች
# ============================================================

@admin.register(AIProjectBacklog)
class AIProjectBacklogAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'task_type', 'target_file', 'priority', 'status', 'site', 'created_at')
    list_filter = ('status', 'priority', 'task_type', 'site')
    search_fields = ('task_name', 'description', 'target_file')
    readonly_fields = ('task_hash', 'created_at', 'updated_at')
    raw_id_fields = ('site', 'dependency')


@admin.register(AIEvolutionLog)
class AIEvolutionLogAdmin(admin.ModelAdmin):
    list_display = ('target_file', 'site', 'created_at')
    list_filter = ('site',)
    search_fields = ('target_file', 'reason_for_change')
    raw_id_fields = ('backlog_task', 'site')


@admin.register(AdminOverrideInstruction)
class AdminOverrideInstructionAdmin(admin.ModelAdmin):
    list_display = ('instruction', 'priority_override', 'is_processed', 'site', 'created_at')
    list_filter = ('is_processed', 'priority_override', 'site')
    search_fields = ('instruction',)
    raw_id_fields = ('backlog_task', 'site')


@admin.register(AgentErrorLog)
class AgentErrorLogAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'error_type', 'resolved', 'site', 'created_at')
    list_filter = ('error_type', 'resolved', 'site')
    search_fields = ('task_name', 'error_message')
    readonly_fields = ('created_at',)


# ============================================================
# 4. 🌐 Multi-Site Orchestration — SiteRegistry
# ============================================================

@admin.register(SiteRegistry)
class SiteRegistryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'display_name', 'niche', 'target_market',
        'growth_level', 'monthly_visitors', 'is_active', 'created_at'
    )
    list_filter = (
        'is_active', 'niche', 'target_market', 'growth_level',
        'auto_update_enabled', 'auto_marketing_enabled'
    )
    search_fields = ('name', 'display_name', 'niche', 'target_market')
    readonly_fields = ('created_at', 'updated_at')


# ============================================================
# 5. 📊 የንግድ እድገት ሞዴሎች
# ============================================================

@admin.register(CustomerAcquisitionLog)
class CustomerAcquisitionLogAdmin(admin.ModelAdmin):
    list_display = ('contact_info', 'channel', 'name', 'converted_to_seller', 'site', 'created_at')
    list_filter = ('channel', 'converted_to_seller', 'site', 'response_received')
    search_fields = ('contact_info', 'name', 'message_sent')
    readonly_fields = ('created_at',)
    raw_id_fields = ('site',)


@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign_type', 'status', 'total_sent', 'total_opened', 'total_converted', 'site', 'created_at')
    list_filter = ('campaign_type', 'status', 'site')
    search_fields = ('name', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at', 'sent_at')
    raw_id_fields = ('site',)


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'total_products', 'total_sales', 'total_revenue', 'rating', 'site')
    list_filter = ('site',)
    search_fields = ('business_name', 'user__username', 'user__email', 'phone_number')
    readonly_fields = ('joined_at', 'last_active')
    raw_id_fields = ('user', 'site')


@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'is_sent', 'site', 'created_at')
    list_filter = ('notification_type', 'is_sent', 'site')
    search_fields = ('recipient', 'subject', 'message')
    readonly_fields = ('created_at', 'sent_at')
    raw_id_fields = ('site',)
    actions = ['mark_as_sent']

    def mark_as_sent(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_sent=True, sent_at=timezone.now())
        self.message_user(request, f"{queryset.count()} notifications marked as sent.")
    mark_as_sent.short_description = "Mark selected notifications as sent"


# ============================================================
# 6. 🆕 የላቁ የኤጀንት ባህሪያት (Advanced Agent Features)
# ✅ ኮሜንት ተወግዷል — ሙሉ በሙሉ ንቁ
# ============================================================

@admin.register(VectorMemory)
class VectorMemoryAdmin(admin.ModelAdmin):
    list_display = ('memory_type', 'content_preview', 'site', 'usage_count', 'success_rate', 'created_at')
    list_filter = ('memory_type', 'site')
    search_fields = ('content', 'metadata')
    readonly_fields = ('created_at', 'updated_at', 'usage_count', 'success_rate')
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'agent_type', 'status', 'priority', 'site', 'created_at')
    list_filter = ('agent_type', 'status', 'site')
    search_fields = ('task_name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')


@admin.register(ABTest)
class ABTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'site', 'winner', 'created_at')
    list_filter = ('status', 'site')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('category', 'severity', 'description_preview', 'is_fixed', 'site', 'created_at')
    list_filter = ('category', 'severity', 'is_fixed', 'site')
    search_fields = ('description', 'file_path')
    readonly_fields = ('created_at', 'updated_at')
    
    def description_preview(self, obj):
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
    description_preview.short_description = "Description"


@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ('prediction_type', 'predicted_value', 'confidence_score', 'site', 'predicted_at')
    list_filter = ('prediction_type', 'site')
    search_fields = ('input_data',)
    readonly_fields = ('predicted_at', 'verified_at')


@admin.register(ExternalAPI)
class ExternalAPIAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_type', 'status', 'site', 'calls_made', 'rate_limit')
    list_filter = ('api_type', 'status', 'site')
    search_fields = ('name', 'api_key')
    readonly_fields = ('created_at', 'updated_at', 'last_reset')
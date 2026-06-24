from django.contrib import admin
from django.utils.html import format_html
from .models import (
    # 1. መሰረታዊ የማርኬት ፕሌስ ሞዴሎች
    Product, Category, UserSearch, ProductTranslation, TranslationQueue,
    
    # 2. የኤጀንት ስትራቴጂ እና ኦፕሬሽን
    SiteRegistry, AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction,
    
    # 3. ጥገና እና ጤና (Health & Healing)
    AgentErrorLog, SelfHealingLog, SiteConfig, MarketTrend,
    
    # 4. የንግድ እድገት እና ማርኬቲንግ
    SellerProfile, CustomerAcquisitionLog, MarketingCampaign, NotificationQueue,
    
    # 5. የላቁ የኤአይ ባህሪያት (Advanced AI)
    VectorMemory, AgentTask, ABTest, SecurityLog, PredictionLog, ExternalAPI
)

# ============================================================
# 📦 1. ምርት እና ትርጉም አስተዳደር
# ============================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_site', 'price', 'category', 'market_status', 'view_count', 'created_at')
    list_filter = ('site', 'category', 'is_active', 'market_value_status')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('view_count', 'inquiry_count', 'created_at', 'updated_at')
    
    def get_site(self, obj):
        return obj.site.display_name if obj.site else "Primary"
    get_site.short_description = 'Site'

    def market_status(self, obj):
        color = 'green' if obj.market_value_status == 'Verified' else 'orange'
        return format_html('<b style="color: {};">{}</b>', color, obj.market_value_status)

admin.site.register(Category)
admin.site.register(TranslationQueue)
admin.site.register(ProductTranslation)

# ============================================================
# 🌐 2. Multi-Site እና የኤጀንት ሰሌዳ (Backlog)
# ============================================================

@admin.register(SiteRegistry)
class SiteRegistryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'niche', 'growth_level', 'build_phase', 'is_active')
    list_filter = ('is_active', 'growth_level', 'build_phase')
    fieldsets = (
        ('መሠረታዊ መረጃ', {'fields': ('name', 'display_name', 'niche', 'target_market')}),
        ('ቴክኒክ (Repo/URL)', {'fields': ('repo_path', 'deployment_url')}),
        ('የእድገት ሁኔታ', {'fields': ('growth_level', 'build_phase', 'real_product_count', 'monthly_visitors')}),
    )

@admin.register(AIProjectBacklog)
class AIProjectBacklogAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'priority_tag', 'status_tag', 'target_file', 'site', 'created_at')
    list_filter = ('status', 'priority', 'site', 'task_type')
    search_fields = ('task_name', 'description')
    readonly_fields = ('task_hash', 'created_at', 'updated_at')

    def priority_tag(self, obj):
        colors = {'Critical': 'red', 'High': 'orange', 'Medium': 'blue', 'Low': 'gray'}
        return format_html('<span style="color: white; background: {}; padding: 3px 7px; border-radius: 5px;">{}</span>', 
                           colors.get(obj.priority, 'gray'), obj.priority)
    
    def status_tag(self, obj):
        colors = {'Completed': 'green', 'Running': 'orange', 'Pending': 'gray', 'Blocked': 'red'}
        return format_html('<b style="color: {};">{}</b>', colors.get(obj.status, 'black'), obj.status)

# ============================================================
# 🩺 3. የኤጀንቱ ጤና እና ጥገና (Diagnostic Center)
# ============================================================

@admin.register(AgentErrorLog)
class AgentErrorLogAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'error_type', 'is_resolved', 'site', 'created_at')
    list_filter = ('resolved', 'error_type', 'site')
    readonly_fields = ('created_at',)

    def is_resolved(self, obj):
        return format_html('✅' if obj.resolved else '❌')

@admin.register(SelfHealingLog)
class SelfHealingLogAdmin(admin.ModelAdmin):
    list_display = ('error_message_short', 'resolved', 'created_at')
    
    def error_message_short(self, obj):
        return obj.error_message[:100] + "..."

admin.site.register(SiteConfig)
admin.site.register(AIEvolutionLog)

# ============================================================
# 👑 4. የአድሚን የበላይነት (Executive Control)
# ============================================================

@admin.register(AdminOverrideInstruction)
class AdminOverrideInstructionAdmin(admin.ModelAdmin):
    list_display = ('instruction_preview', 'priority_override', 'is_processed', 'site', 'created_at')
    list_filter = ('is_processed', 'priority_override')
    
    def instruction_preview(self, obj):
        return obj.instruction[:70] + "..."

# ============================================================
# 💰 5. የንግድ እድገት እና ማርኬቲንግ
# ============================================================

@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_name', 'site', 'rating', 'total_products')
    search_fields = ('business_name', 'user__username')

@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign_type', 'status', 'total_sent', 'total_converted')

admin.site.register(CustomerAcquisitionLog)
admin.site.register(NotificationQueue)

# ============================================================
# 🧠 6. የላቁ የኤአይ ባህሪያት (RAG & Security)
# ============================================================

@admin.register(VectorMemory)
class VectorMemoryAdmin(admin.ModelAdmin):
    list_display = ('memory_type', 'content_preview', 'success_rate', 'usage_count')
    
    def content_preview(self, obj):
        return obj.content[:100] + "..."

@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('severity_tag', 'category', 'description', 'is_fixed', 'file_path')
    list_filter = ('severity', 'is_fixed', 'category')

    def severity_tag(self, obj):
        color = 'red' if obj.severity == 'high' else 'orange'
        return format_html('<b style="color: {};">{}</b>', color, obj.severity.upper())

@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ('prediction_type', 'predicted_value', 'confidence_score', 'predicted_at')

admin.site.register(AgentTask)
admin.site.register(ABTest)
admin.site.register(ExternalAPI)
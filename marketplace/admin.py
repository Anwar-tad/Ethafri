# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/admin.py
# 📝 ስሪት፦ v10.20 (Production Grade - Safe Boot & Beautiful Admin)
# ✅ የተፈቱ ችግሮች፦ Standard relative imports from .models implemented to prevent AppRegistryNotReady crashes during Django launch auto-discovery, safety model check added in safe_register to prevent TypeErrors, product translation stacked inline, and secure code-escaped comparisons inside AIEvolutionLog (v10.20).
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

from django.contrib import admin
from django.utils.html import escape, format_html
from django.apps import apps

# 🛡️ SAFE RELATIVE IMPORTS: የ 'AppRegistryNotReady' ስህተቶችን ለመከላከል ሞዴሎችን በቀጥታ መጫን (Symmetric Boot Safety)
from .models import (
    Product, Category, UserSearch, ProductTranslation, TranslationQueue,
    SiteRegistry, AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction,
    AgentErrorLog, SelfHealingLog, SiteConfig, MarketTrend, SellerProfile,
    CustomerAcquisitionLog, MarketingCampaign, NotificationQueue, VectorMemory,
    AgentTask, ABTest, ExternalAPI, SecurityLog, PredictionLog
)


# 🛡️ REGISTRY COLLISION GUARD: ሰርቨሩ በ AlreadyRegistered ስህተት እንዳይከሰከስ የደህንነት ምዝገባ ረዳት
def safe_register(model_class, admin_class=None):
    if not model_class:
        return
    try:
        if not admin.site.is_registered(model_class):
            if admin_class:
                admin.site.register(model_class, admin_class)
            else:
                admin.site.register(model_class)
    except admin.sites.AlreadyRegistered:
        pass
    except Exception as e:
        logger.error(f"Safe register failed for {model_class}: {e}")


# ============================================================
# 📦 1. ምርት እና ትርጉም አስተዳደር (Inline Translation Support)
# ============================================================

class ProductTranslationInline(admin.StackedInline):
    """🔴 የምርት ትርጉሞችን በአንድ ገጽ ላይ በአድሚን ሰሌዳ ለመተርጎም (UX Booster)"""
    model = ProductTranslation
    extra = 1
    max_num = 1


class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_site', 'price', 'category', 'listing_type', 'contact_info', 'is_active', 'market_status', 'view_count', 'created_at')
    list_filter = ('site', 'category', 'listing_type', 'is_active', 'market_value_status')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('view_count', 'inquiry_count', 'created_at', 'updated_at')
    
    # የትርጉም ሰንጠረዡን ወደ ምርት ገጽ ስር inline ማገናኘት
    inlines = [ProductTranslationInline]
    
    def get_site(self, obj):
        return obj.site.display_name if obj.site else "Primary"
    get_site.short_description = 'Site'

    def market_status(self, obj):
        color = 'green' if obj.market_value_status == 'Verified' else 'orange'
        return format_html('<b style="color: {};">{}</b>', color, obj.market_value_status)


safe_register(Product, ProductAdmin)
safe_register(Category)
safe_register(TranslationQueue)
safe_register(ProductTranslation)
safe_register(UserSearch)


# ============================================================
# 🌐 2. Multi-Site እና የኤጀንት ሰሌዳ (Backlog)
# ============================================================

class SiteRegistryAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'niche', 'growth_level', 'build_phase', 'is_active')
    list_filter = ('is_active', 'growth_level', 'build_phase')
    fieldsets = (
        ('መሠረታዊ መረጃ', {'fields': ('name', 'display_name', 'niche', 'target_market')}),
        ('ልክኒክ (Repo/URL)', {'fields': ('repo_path', 'deployment_url')}),
        ('የእድገት ሁኔታ', {'fields': ('growth_level', 'build_phase', 'real_product_count', 'monthly_visitors')}),
        ('የኤጀንት መቆጣጠሪያ (Agent Control)', {'fields': ('is_active', 'auto_update_enabled', 'auto_marketing_enabled')}),
    )


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


class AIEvolutionLogAdmin(admin.ModelAdmin):
    """🔴 ኤጀንቱ የቀየራቸውን ኮዶች በጥቁር ዳራ (HTML pre/code style) аሳምሮ የሚያሳይ ሰሌዳ"""
    list_display = ('target_file', 'site', 'reason_preview', 'created_at')
    list_filter = ('site', 'target_file')
    readonly_fields = ('created_at', 'code_preview')
    
    # የድሮ እና አዳዲስ ኮዶችን በኮድ ፎርማት ማሳያ
    fields = ('backlog_task', 'target_file', 'site', 'reason_for_change', 'code_preview', 'created_at')
    
    def reason_preview(self, obj):
        msg = obj.reason_for_change or ""
        return msg[:75] + "..." if len(msg) > 75 else msg

    def code_preview(self, obj):
        old_code = obj.old_code_backup or "No previous content (New File)"
        new_code = obj.new_code_patch or "No patch content"
        
        # HTML እና JavaScript ኮዶችን በአድሚን ገጽ ላይ ደህንነታቸውን ጠብቆ ለማሳየት 'escape' ጥሪ (XSS Shield)
        safe_old_code = escape(old_code)
        safe_new_code = escape(new_code)
        
        return format_html(
            '<div>'
            '<h3>⏮️ Old Code Backup</h3>'
            '<pre style="background: #272822; color: #f8f8f2; padding: 10px; border-radius: 5px; font-family: monospace; overflow-x: auto; max-height: 250px;">{}</pre>'
            '<h3>⏭️ New Code Patch</h3>'
            '<pre style="background: #272822; color: #a6e22e; padding: 10px; border-radius: 5px; font-family: monospace; overflow-x: auto; max-height: 250px;">{}</pre>'
            '</div>',
            safe_old_code, safe_new_code
        )
    code_preview.short_description = "Code Comparison"


safe_register(SiteRegistry, SiteRegistryAdmin)
safe_register(AIProjectBacklog, AIProjectBacklogAdmin)
safe_register(AIEvolutionLog, AIEvolutionLogAdmin)


# ============================================================
# 🩺 3. የኤጀንቱ ጤና እና ጥገና (Diagnostic Center)
# ============================================================

class AgentErrorLogAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'error_type', 'is_resolved', 'site', 'created_at')
    list_filter = ('resolved', 'error_type', 'site')
    readonly_fields = ('created_at',)

    def is_resolved(self, obj):
        return format_html('✅' if obj.resolved else '❌')


class SelfHealingLogAdmin(admin.ModelAdmin):
    list_display = ('error_message_short', 'resolved', 'created_at')
    
    def error_message_short(self, obj):
        msg = obj.error_message or ""
        return msg[:100] + "..." if len(msg) > 100 else msg


safe_register(AgentErrorLog, AgentErrorLogAdmin)
safe_register(SelfHealingLog, SelfHealingLogAdmin)
safe_register(SiteConfig)
safe_register(MarketTrend)


# ============================================================
# 👑 4. የአድሚን የበላይነት (Executive Control)
# ============================================================

class AdminOverrideInstructionAdmin(admin.ModelAdmin):
    list_display = ('instruction_preview', 'priority_override', 'is_processed', 'site', 'created_at')
    list_filter = ('is_processed', 'priority_override')
    
    def instruction_preview(self, obj):
        msg = obj.instruction or ""
        return msg[:70] + "..." if len(msg) > 70 else msg

safe_register(AdminOverrideInstruction, AdminOverrideInstructionAdmin)


# ============================================================
# 💰 5. የንግድ እድገት እና ማርኬቲおり
# ============================================================

class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_name', 'site', 'rating', 'total_products')
    search_fields = ('business_name', 'user__username')


class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign_type', 'status', 'total_sent', 'total_converted')


safe_register(SellerProfile, SellerProfileAdmin)
safe_register(MarketingCampaign, MarketingCampaignAdmin)
safe_register(CustomerAcquisitionLog)
safe_register(NotificationQueue)


# ============================================================
# 🧠 6. የላቁ የኤአይ ባህሪያት (RAG & Security)
# ============================================================

class VectorMemoryAdmin(admin.ModelAdmin):
    list_display = ('memory_type', 'content_preview', 'success_rate', 'usage_count')
    
    def content_preview(self, obj):
        msg = obj.content or ""
        return msg[:100] + "..." if len(msg) > 100 else msg


class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('severity_tag', 'category', 'description', 'is_fixed', 'file_path')
    list_filter = ('severity', 'is_fixed', 'category')

    def severity_tag(self, obj):
        colors = {
            'critical': 'darkred',
            'high': 'red',
            'medium': 'orange',
            'low': 'gray'
        }
        color = colors.get(str(obj.severity).lower(), 'gray')
        return format_html('<b style="color: {};">{}</b>', color, str(obj.severity).upper())


class PredictionLogAdmin(admin.ModelAdmin):
    list_display = ('prediction_type', 'predicted_value', 'confidence_score', 'predicted_at')


safe_register(VectorMemory, VectorMemoryAdmin)
safe_register(SecurityLog, SecurityLogAdmin)
safe_register(PredictionLog, PredictionLogAdmin)

safe_register(AgentTask)
safe_register(AgentTask)
safe_register(ABTest)
safe_register(ExternalAPI)
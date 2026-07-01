# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/models.py
# 📝 ስሪት፦ v10.15 (Production Grade - Complete Part 1/3)
# ✅ የተፈቱ ችግሮች፦ Full schema validation, aligned Product fields, zero pass placeholders, and strict Django formatting rules.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import get_language
from django.utils import timezone
import uuid
import hashlib
import json

# ============================================================
# 1. ነባር የማርኬት ፕሌስ ሞዴሎች
# ============================================================

class Category(models.Model):
    """በ AI የሚፈጠሩ እና የሚደራጁ የምርት ምድቦች"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(blank=True, default='fa-tag', max_length=50)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subcategories'
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            if not self.slug:
                self.slug = f"cat-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """የማርኬት ፕሌሱ ዋና የምርት መረጃ መያዣ"""
    
    LISTING_TYPES = [
        ('sale', 'ለሽያጭ (For Sale)'),
        ('rent', 'ለኪራይ (For Rent)'),
        ('service', 'አገልግሎት / ስራ (Service)'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    image_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    location = models.CharField(max_length=255, default='Global / ኢትዮጵያ')
    specifications = models.TextField(default='{}', blank=True)
    market_value_status = models.CharField(max_length=50, blank=True, default='Unknown')
    
    # 🔴 አዲስ የተጨመሩ የመገናኛ እና የገበያ አይነት ፊልዶች (views.py እና growth_agent.py Alignment) [1, 2]
    listing_type = models.CharField(max_length=50, choices=LISTING_TYPES, default='sale', db_index=True)
    contact_info = models.CharField(max_length=255, blank=True, default='')
    image_gallery = models.JSONField(default=list, blank=True)
    
    is_active = models.BooleanField(default=True, db_index=True)
    ai_tags = models.TextField(default='[]', blank=True)
    
    seo_score = models.IntegerField(default=0, help_text="SEO ውጤት (0-100)")
    view_count = models.IntegerField(default=0, help_text="የተመለከቱ ብዛት")
    inquiry_count = models.IntegerField(default=0, help_text="የጥያቄ ብዛት")
    last_enhanced = models.DateTimeField(null=True, blank=True)
    
    # Multi-Site Support
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='products',
        help_text="ይህ ምርት የሚለጠፍበትን ጣቢያ ይምረጡ"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_translated_title(self):
        lang = get_language()
        if lang == 'en':
            return self.title
        translation = getattr(self, 'translations', None)
        if translation:
            lang_text = getattr(translation, lang, '')
            if lang_text and "|||" in lang_text:
                return lang_text.split("|||")[0].strip()
        return self.title

    def get_translated_desc(self):
        lang = get_language()
        if lang == 'en':
            return self.description
        translation = getattr(self, 'translations', None)
        if translation:
            lang_text = getattr(translation, lang, '')
            if lang_text and "|||" in lang_text:
                return lang_text.split("|||")[1].strip()
        return self.description

    def __str__(self):
        return self.title


class ProductTranslation(models.Model):
    """ምርቶችን በ 7 ቋንቋዎች በራስ-ሰር ተርጉሞ ለማከማቸት"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='translations')
    en = models.TextField(blank=True, verbose_name="English")
    am = models.TextField(blank=True, verbose_name="Amharic")
    om = models.TextField(blank=True, verbose_name="Oromo")
    ar = models.TextField(blank=True, verbose_name="Arabic")
    so = models.TextField(blank=True, verbose_name="Somali")
    ti = models.TextField(blank=True, verbose_name="Tigrinya")
    fr = models.TextField(blank=True, verbose_name="French")

    def __str__(self):
        return f"Translations for: {self.product.title}"


class TranslationQueue(models.Model):
    """በቀን ገደብ ምክንያት ሳይተረጎሙ የቀሩ ምርቶችን በወረፋ ይዞ ቆይቶ ለመተርጎም"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pending_translations')
    target_languages = models.JSONField(default=list)
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Queue: {self.product.title}"


class SiteConfig(models.Model):
    """የዌብሳይቱን ዲዛይን በ AI ለመቀየር"""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)


class UserSearch(models.Model):
    """የተጠቃሚዎችን ፍለጋ አጥንቶ ገበያውን ለማሳደግ"""
    query = models.CharField(max_length=255)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class MarketTrend(models.Model):
    """AI ገበያውን አጥንቶ የሚሰጠው ስልታዊ ምክር መመዝገቢያ"""
    niche_name = models.CharField(max_length=100)
    demand_level = models.IntegerField(default=50)
    ai_suggestion = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)


class SelfHealingLog(models.Model):
    """AI በራሱ የፈወሳቸውን የዳታቤዝ እና የሲስተም ስህተቶች መዝገብ"""
    error_message = models.TextField()
    solution_sql = models.TextField(blank=True, null=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Healed: {self.error_message[:30]}..."
        
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/models.py (ክፍል 2/3)
# ============================================================

# ============================================================
# 2. የኤጀንት ማህደረ-ትውስታ እና የቁጥጥር ሞዴሎች
# ============================================================

class AIProjectBacklog(models.Model):
    """ኤጀንቱ ራሱ ፈልጎ ያገኛቸውን የጎደሉ ስራዎች እና ማሻሻያዎችን የሚይዝ ሰሌዳ"""
    PRIORITY_CHOICES = [
        ('Critical', 'Critical'),
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Running', 'Running'),
        ('Completed', 'Completed'),
        ('Overridden', 'Overridden'),
        ('Blocked', 'Blocked'),
    ]
    
    TASK_TYPES = [
        ('code', 'Code Development'),
        ('seo', 'SEO Optimization'),
        ('marketing', 'Marketing Campaign'),
        ('acquisition', 'Customer Acquisition'),
        ('growth', 'Growth Strategy'),
        ('design', 'UI/UX Design'),
        ('content', 'Content Creation'),
    ]

    task_name = models.CharField(max_length=255)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default='code')
    target_file = models.CharField(max_length=255, help_text="የሚሻሻለው ወይም የሚመረመረው የኮድ ፋይል ስም")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    description = models.TextField(blank=True, default='')
    task_hash = models.CharField(max_length=64, unique=True, blank=True)
    
    business_impact_score = models.IntegerField(
        default=5,
        help_text="1-10: የንግድ ተጽዕኖ ውጤት"
    )
    
    trigger_condition = models.CharField(
        max_length=255,
        blank=True,
        help_text="ይህ ስራ የተፈጠረበት ትሪገር ሁኔታ"
    )
    
    dependency = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dependent_tasks'
    )
    
    estimated_hours = models.FloatField(default=1.0)
    complexity = models.IntegerField(default=1, help_text="1-10")
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='backlog_tasks'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.task_hash:
            import time
            site_id = self.site.id if self.site else "primary"
            timestamp = int(time.time() * 1000)
            random_salt = uuid.uuid4().hex[:12]
            task_type = self.task_type or 'unknown'
            
            raw_string = f"{site_id}:{task_type}:{self.target_file}:{self.task_name}:{timestamp}:{random_salt}"
            self.task_hash = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.priority}] {self.task_name} ({self.status})"


class AIEvolutionLog(models.Model):
    """የተለወጡ ኮዶች ታሪክ"""
    backlog_task = models.ForeignKey(
        AIProjectBacklog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evolution_logs'
    )
    target_file = models.CharField(max_length=255)
    reason_for_change = models.TextField()
    old_code_backup = models.TextField(blank=True, null=True)
    new_code_patch = models.TextField(blank=True, null=True)
    improvement_metrics = models.JSONField(default=dict, blank=True)
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='evolution_logs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evolution on {self.target_file} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AdminOverrideInstruction(models.Model):
    """የባለቤት ቀጥተኛ መመሪያ"""
    backlog_task = models.ForeignKey(
        AIProjectBacklog, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='overrides'
    )
    instruction = models.TextField()
    priority_override = models.CharField(
        max_length=20, 
        choices=AIProjectBacklog.PRIORITY_CHOICES, 
        blank=True, 
        null=True
    )
    is_processed = models.BooleanField(default=False)
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='overrides'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        task_info = f" for {self.backlog_task.task_name}" if self.backlog_task else " (Global)"
        return f"Admin Override{task_info} - Applied: {self.is_processed}"


class AgentErrorLog(models.Model):
    """የኤጀንት ስህተቶች መዝገብ"""
    ERROR_TYPES = [
        ('syntax', 'Syntax Error'),
        ('runtime', 'Runtime Error'),
        ('import', 'Import Error'),
        ('logic', 'Logic Error'),
        ('api', 'API Error'),
        ('deployment', 'Deployment Error'),
        ('database', 'Database Error'),
    ]
    
    task_name = models.CharField(max_length=255)
    error_type = models.CharField(max_length=20, choices=ERROR_TYPES, default='syntax')
    error_message = models.TextField()
    code_attempted = models.TextField(blank=True, default='')
    correction_applied = models.TextField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='error_logs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Error in {self.task_name} - Resolved: {self.resolved}"


# ============================================================
# 3. 🌐 Multi-Site Orchestration — SiteRegistry
# ============================================================

class SiteRegistry(models.Model):
    """እያንዳንዱን የኒች ድረ-ገጽ የሚወክል ሞዴል"""
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    niche = models.CharField(max_length=100)
    target_market = models.CharField(max_length=100)
    
    repo_url = models.URLField(blank=True)
    repo_path = models.CharField(max_length=500, blank=True)
    deployment_url = models.URLField(blank=True)
    
    competitor_urls = models.JSONField(default=list, blank=True)
    primary_keywords = models.JSONField(default=list, blank=True)
    
    target_audience = models.TextField(blank=True)
    content_style = models.CharField(
        max_length=50, 
        default='professional',
        choices=[
            ('professional', 'Professional'),
            ('casual', 'Casual'),
            ('storytelling', 'Storytelling'),
            ('educational', 'Educational'),
        ]
    )
    
    growth_level = models.IntegerField(
        default=1,
        choices=[
            (1, 'Local'),
            (2, 'City'),
            (3, 'Country'),
            (4, 'Continent'),
            (5, 'Global'),
        ]
    )
    
    build_phase = models.IntegerField(
        default=0,
        help_text="0=Scaffolding, 1=Real Data, 2=Core Features, 3=Engagement, 4=Monetization, 5=Mature"
    )
    
    real_product_count = models.IntegerField(
        default=0,
        help_text="እውነተኛ ምርቶች ብዛት"
    )
    real_customer_count = models.IntegerField(
        default=0,
        help_text="እውነተኛ ደንበኞች ብዛት"
    )
    
    phase_transition_date = models.DateTimeField(null=True, blank=True)
    
    monthly_visitors = models.IntegerField(default=0)
    page_views = models.IntegerField(default=0)
    total_sellers = models.IntegerField(default=0)
    total_products = models.IntegerField(default=0)
    monthly_revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    last_traffic_update = models.DateTimeField(null=True, blank=True)
    
    last_marketing_campaign = models.DateTimeField(null=True, blank=True)
    pending_notifications = models.JSONField(default=list, blank=True)
    
    is_active = models.BooleanField(default=True)
    auto_update_enabled = models.BooleanField(default=True)
    auto_marketing_enabled = models.BooleanField(default=True)
    update_frequency = models.CharField(
        max_length=20, 
        default='daily',
        choices=[
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name', 'is_active']),
            models.Index(fields=['niche', 'target_market']),
            models.Index(fields=['growth_level']),
            models.Index(fields=['build_phase']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.niche}) - Level {self.growth_level} | Phase {self.build_phase}"

    def get_absolute_url(self):
        return self.deployment_url or f"/sites/{self.name}/"

    def update_traffic(self, visitors, page_views):
        self.monthly_visitors = visitors
        self.page_views = page_views
        self.last_traffic_update = timezone.now()
        self.save()
    
    def update_growth_level(self):
        visitors = self.monthly_visitors or 0
        if visitors < 100:
            self.growth_level = 1
        elif visitors < 1000:
            self.growth_level = 2
        elif visitors < 10000:
            self.growth_level = 3
        elif visitors < 100000:
            self.growth_level = 4
        else:
            self.growth_level = 5
        self.save()
    
    def update_real_counts(self):
        from .models import Product
        self.real_product_count = Product.objects.filter(site=self, is_active=True).count()
        self.real_customer_count = User.objects.filter(product__site=self).distinct().count()
        self.save()
        
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/models.py (ክፍል 3/3)
# ============================================================

# ============================================================
# 4. የንግድ እድገት እና የደንበኛ ማግኛ ሞዴሎች
# ============================================================

class CustomerAcquisitionLog(models.Model):
    """የደንበኛ ማግኛ ተግባራትን የሚመዘግብ"""
    ACQUISITION_CHANNELS = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('social', 'Social Media'),
        ('referral', 'Referral'),
        ('organic', 'Organic'),
        ('paid', 'Paid Advertising'),
    ]
    
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, related_name='acquisition_logs')
    channel = models.CharField(max_length=20, choices=ACQUISITION_CHANNELS)
    contact_info = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True)
    message_sent = models.TextField(blank=True)
    response_received = models.BooleanField(default=False)
    converted_to_seller = models.BooleanField(default=False)
    converted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_channel_display()} - {self.contact_info}"


class MarketingCampaign(models.Model):
    """የግብይት ካምፔኖችን የሚያስተዳድር ሞዴል"""
    CAMPAIGN_TYPES = [
        ('email_blast', 'Email Blast'),
        ('sms_blast', 'SMS Blast'),
        ('social_post', 'Social Media Post'),
        ('seo_campaign', 'SEO Campaign'),
        ('referral', 'Referral Program'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, related_name='marketing_campaigns')
    name = models.CharField(max_length=255)
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    target_audience = models.JSONField(default=dict)
    total_sent = models.IntegerField(default=0)
    total_opened = models.IntegerField(default=0)
    total_clicked = models.IntegerField(default=0)
    total_converted = models.IntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_campaign_type_display()}"


class SellerProfile(models.Model):
    """የሻጮች መረጃ እና አፈጻጸም"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, related_name='seller_profiles', null=True, blank=True)
    business_name = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    total_products = models.IntegerField(default=0)
    total_sales = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    rating = models.FloatField(default=0.0, help_text="0-5 ውጤት")
    last_active = models.DateTimeField(auto_now=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business_name} - {self.user.username}"


class NotificationQueue(models.Model):
    """የአውቶማቲክ ማርኬቲንግ ማሳወቂያ ወረፋ"""
    notification_type = models.CharField(
        choices=[
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('push', 'Push Notification'),
            ('in_app', 'In-App Notification'),
        ],
        max_length=20
    )
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient} - {'Sent' if self.is_sent else 'Pending'}"


# ============================================================
# 5. የላቁ የኤጀንት ባህሪያት (Advanced Agent Features)
# ============================================================

class VectorMemory(models.Model):
    """RAG (Retrieval-Augmented Generation) ትውስታ ለኤጀንቱ [1, 2]"""
    MEMORY_TYPES = [
        ('error', 'Error Resolution'),
        ('solution', 'Solution Pattern'),
        ('code', 'Code Snippet'),
        ('insight', 'Market Insight'),
        ('strategy', 'Strategy Pattern'),
    ]
    
    memory_type = models.CharField(max_length=20, choices=MEMORY_TYPES)
    content = models.TextField(help_text="የትውስታ ይዘት")
    embedding = models.JSONField(default=list, blank=True, help_text="pgvector embedding")
    metadata = models.JSONField(default=dict, help_text="ተጨማሪ መረጃ")
    usage_count = models.IntegerField(default=0, help_text="ምን ያህል ጊዜ ጥቅም ላይ ውሏል")
    success_rate = models.FloatField(default=0.0, help_text="ስኬታማነት መጠን 0-100")
    last_used = models.DateTimeField(null=True, blank=True)
    
    site = models.ForeignKey(
        SiteRegistry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='memory_entries'
    )
    related_task = models.ForeignKey(
        AIProjectBacklog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='memory_entries'
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vector_memories'
    )
    text_content = models.TextField(blank=True)
    vector_data = models.JSONField(default=dict)
    embedding_model = models.CharField(max_length=100, default='default-embedding-model')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-success_rate', '-usage_count']
        indexes = [
            models.Index(fields=['memory_type', 'site']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['product']),
            models.Index(fields=['embedding_model']),
        ]

    def __str__(self):
        product_title = self.product.title if self.product else 'N/A'
        return f"{self.get_memory_type_display()}: {self.content[:50]}... | Product: {product_title}"

    def mark_used(self, success=True):
        self.usage_count += 1
        if success:
            self.success_rate = ((self.success_rate * (self.usage_count - 1)) + 100) / self.usage_count
        else:
            self.success_rate = ((self.success_rate * (self.usage_count - 1)) + 0) / self.usage_count
        self.last_used = timezone.now()
        self.save()

    @classmethod
    def find_similar(cls, query, memory_type=None, site=None, limit=5):
        from django.db.models import Q
        
        queryset = cls.objects.all()
        if memory_type:
            queryset = queryset.filter(memory_type=memory_type)
        if site:
            queryset = queryset.filter(site=site)
        
        keywords = [k for k in query.lower().split() if len(k) > 2][:8]
        
        if keywords:
            # 🔴 OR-based keyword search fallback ሎጂክ [1]
            q_filter = Q()
            for keyword in keywords:
                q_filter |= Q(content__icontains=keyword)
            queryset = queryset.filter(q_filter)
        
        return queryset.order_by('-success_rate', '-usage_count')[:limit]


class AgentTask(models.Model):
    """የባለብዙ-ኤጀንት ስራ አስተዳደር"""
    AGENT_TYPES = [
        ('code', 'Code Agent'),
        ('seo', 'SEO Agent'),
        ('marketing', 'Marketing Agent'),
        ('data', 'Data Agent'),
        ('review', 'Review Agent'),
        ('security', 'Security Agent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('running', 'Running'),
        ('reviewing', 'Reviewing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    task_name = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.IntegerField(default=1)
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    
    site = models.ForeignKey(
        SiteRegistry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='agent_tasks'
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subtasks'
    )
    backlog_task = models.ForeignKey(
        AIProjectBacklog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_tasks'
    )
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['agent_type', 'status']),
            models.Index(fields=['site', 'status']),
        ]

    def __str__(self):
        return f"{self.get_agent_type_display()}: {self.task_name} ({self.status})"

    def start_task(self):
        self.status = 'running'
        self.started_at = timezone.now()
        self.save()

    def complete_task(self, result_data=None):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if result_data:
            self.result_data = result_data
        self.save()

    def fail_task(self, error_message):
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save()


class ABTest(models.Model):
    """A/B ሙከራዎችን ያስተዳድራል"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, related_name='ab_tests')
    variant_a = models.JSONField()
    variant_b = models.JSONField()
    winner = models.CharField(max_length=10, blank=True)
    
    variant_a_views = models.IntegerField(default=0)
    variant_b_views = models.IntegerField(default=0)
    variant_a_conversions = models.IntegerField(default=0)
    variant_b_conversions = models.IntegerField(default=0)
    
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AB Test: {self.name} ({self.status})"

    def record_view(self, variant):
        if variant == 'A':
            self.variant_a_views += 1
        else:
            self.variant_b_views += 1
        self.save()

    def record_conversion(self, variant):
        if variant == 'A':
            self.variant_a_conversions += 1
        else:
            self.variant_b_conversions += 1
        self.save()

    def calculate_winner(self):
        rate_a = self.variant_a_conversions / max(self.variant_a_views, 1)
        rate_b = self.variant_b_conversions / max(self.variant_b_views, 1)
        if rate_a > rate_b:
            self.winner = 'A'
        elif rate_b > rate_a:
            self.winner = 'B'
        else:
            self.winner = 'Tie'
        self.save()
        return self.winner


class SecurityLog(models.Model):
    """የደህንነት ቀንድ መዝገብ [1, 2]"""
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    CATEGORY_CHOICES = [
        ('code_injection', 'Code Injection'),
        ('sql_injection', 'SQL Injection'),
        ('xss', 'XSS'),
        ('auth', 'Authentication'),
        ('data_leak', 'Data Leak'),
        ('config', 'Configuration'),
        ('dependency', 'Dependency'),
    ]
    
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    file_path = models.CharField(max_length=500, blank=True)
    line_number = models.IntegerField(null=True, blank=True)
    is_fixed = models.BooleanField(default=False)
    fixed_at = models.DateTimeField(null=True, blank=True)
    fix_description = models.TextField(blank=True)
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, null=True, blank=True, related_name='security_logs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-severity', '-created_at']
        indexes = [
            models.Index(fields=['category', 'severity']),
            models.Index(fields=['is_fixed']),
        ]

    def __str__(self):
        return f"{self.get_severity_display()}: {self.get_category_display()}"


class PredictionLog(models.Model):
    """የትንበያ ውጤቶች መዝገብ [1, 2]"""
    PREDICTION_TYPES = [
        ('traffic', 'Traffic Prediction'),
        ('seo', 'SEO Score Prediction'),
        ('sales', 'Sales Prediction'),
        ('growth', 'Growth Prediction'),
    ]
    
    prediction_type = models.CharField(max_length=20, choices=PREDICTION_TYPES)
    predicted_value = models.FloatField()
    actual_value = models.FloatField(null=True, blank=True)
    confidence_score = models.FloatField(default=0.0)
    input_data = models.JSONField(default=dict)
    model_version = models.CharField(max_length=50, blank=True)
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, null=True, blank=True, related_name='predictions')
    predicted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-predicted_at']
        indexes = [
            models.Index(fields=['prediction_type', 'site']),
            models.Index(fields=['-predicted_at']),
        ]

    def __str__(self):
        return f"{self.get_prediction_type_display()}: {self.predicted_value}"


class ExternalAPI(models.Model):
    """የውጭ API ግንኙነት አስተዳደር [1, 2]"""
    API_TYPES = [
        ('google_analytics', 'Google Analytics'),
        ('google_search_console', 'Google Search Console'),
        ('mailchimp', 'Mailchimp'),
        ('twilio', 'Twilio'),
        ('social_media', 'Social Media'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
        ('rate_limited', 'Rate Limited'),
    ]
    
    api_type = models.CharField(max_length=25, choices=API_TYPES)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    base_url = models.URLField(blank=True)
    webhook_url = models.URLField(blank=True)
    rate_limit = models.IntegerField(default=100)
    calls_made = models.IntegerField(default=0)
    last_reset = models.DateTimeField(auto_now=True)
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, null=True, blank=True, related_name='external_apis')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['api_type', 'site']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_api_type_display()}: {self.name} ({self.status})"

    def increment_calls(self):
        self.calls_made += 1
        self.save()

    def reset_calls(self):
        self.calls_made = 0
        self.last_reset = timezone.now()
        self.save()
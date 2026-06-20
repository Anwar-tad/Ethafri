# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/models.py
# 📝 ለውጥ፦ ሙሉ የተሻሻለ ስሪት — Multi-Site + Business Growth + Auto-Discovery
# 📅 ቀን፦ 2026-06-20
# ============================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import get_language
from django.utils import timezone
import uuid
import hashlib


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
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    image_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    location = models.CharField(max_length=255, default='Global / ኢትዮጵያ')
    specifications = models.JSONField(default=dict, blank=True)
    market_value_status = models.CharField(max_length=50, blank=True, default='Unknown')
    is_active = models.BooleanField(default=True)
    ai_tags = models.JSONField(default=list, blank=True)
    
    # 🆕 የምርት ትንተና መረጃ
    seo_score = models.IntegerField(default=0, help_text="SEO ውጤት (0-100)")
    view_count = models.IntegerField(default=0, help_text="የተመለከቱ ብዛት")
    inquiry_count = models.IntegerField(default=0, help_text="የጥያቄ ብዛት")
    last_enhanced = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="የሚለጠፍበት ድረ-ገጽ"
    )

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
        return f"Queue: {self.product.title} ({len(self.target_languages)} languages pending)"


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
    description = models.TextField(blank=True, default='', help_text="የስራው ዝርዝር መግለጫ እና ቅድሚያ የተሰጠበት ምክንያት")
    
    task_hash = models.CharField(
        max_length=64, 
        unique=True, 
        blank=True, 
        help_text="የስራ መደራረብን ለመከላከል በራስ-ሰር የሚመነጭ ልዩ ሃሽ"
    )
    
    dependency = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dependent_tasks',
        help_text="ይህ ስራ ከመሰራቱ በፊት አስቀድሞ መጠናቀቅ ያለበት ሌላ የባክሎግ ስራ"
    )
    
    estimated_hours = models.FloatField(default=1.0)
    complexity = models.IntegerField(default=1, help_text="1-10 (ቀላል እስከ ከባድ)")
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='backlog_tasks',
        help_text="ይህ ስራ የሚመለከተው የትኛውን ድረ-ገጽ ነው?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.task_hash:
            site_id = self.site.id if self.site else "primary"
            raw_string = f"{site_id}:{self.target_file}:{self.task_name}"
            self.task_hash = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.priority}] {self.task_name} ({self.status})"


class AIEvolutionLog(models.Model):
    """የተለወጡ ኮዶች ታሪክ፣ የተለወጠበት ምክንያት እና የድሮው ኮድ ባክአፕ መመዝገቢያ"""
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
    
    improvement_metrics = models.JSONField(default=dict, blank=True, help_text="SEO score, load time, etc.")
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='evolution_logs',
        help_text="ይህ ለውጥ የሚመለከተው የትኛውን ድረ-ገጽ ነው?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evolution on {self.target_file} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AdminOverrideInstruction(models.Model):
    """የዌብሳይቱ ባለቤት (አድሚን) ለኤጀንቱ የሚሰጠው የቁጥጥር ትዕዛዝ"""
    backlog_task = models.ForeignKey(
        AIProjectBacklog, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='overrides',
        help_text="ይህ መመሪያ የሚመለከተው የተወሰነ የባክሎግ ስራ ካለ"
    )
    instruction = models.TextField(help_text="ለኤጀንቱ የሚተላለፈው የባለቤት ትዕዛዝ")
    priority_override = models.CharField(
        max_length=20, 
        choices=AIProjectBacklog.PRIORITY_CHOICES, 
        blank=True, 
        null=True,
        help_text="የስራውን ቅድሚያ ደረጃ ለመቀየር ከተፈለገ"
    )
    is_processed = models.BooleanField(default=False)
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='overrides',
        help_text="ይህ መመሪያ የሚመለከተው የትኛውን ድረ-ገጽ ነው?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        task_info = f" for {self.backlog_task.task_name}" if self.backlog_task else " (Global Directive)"
        return f"Admin Override{task_info} - Applied: {self.is_processed}"


class AgentErrorLog(models.Model):
    """ኤጀንቱ የኮድ ማሻሻያ ሲያደርግ የሚገጥሙትን ስህተቶች መዝግቦ ለቀጣይ ራሱ ማስተካከያ የሚጠቀምበት"""
    
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
    error_message = models.TextField(help_text="የተፈጠረው የስህተት አይነት (Traceback)")
    code_attempted = models.TextField(help_text="ኤጀንቱ የሞከረው የኮድ ክፍል")
    correction_applied = models.TextField(null=True, blank=True, help_text="ስህተቱን ለማስተካከል የተጠቀመበት አዲስ ኮድ")
    resolved = models.BooleanField(default=False, help_text="ችግሩ ተፈቷል?")
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='error_logs',
        help_text="ይህ ስህተት የተከሰተው በየትኛው ድረ-ገጽ ላይ ነው?"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Error in {self.task_name} - Resolved: {self.resolved}"


# ============================================================
# 3. 🌐 Multi-Niche Site Orchestration — Site Registry
# ============================================================

class SiteRegistry(models.Model):
    """
    እያንዳንዱን የኒች ድረ-ገጽ የሚወክል ሞዴል
    ኤጀንቱ በርካታ ድረ-ገጾችን በአንድ ጊዜ እንዲያስተዳድር ያስችላል
    """
    name = models.CharField(max_length=100, unique=True, help_text="የጣቢያው ልዩ ስም")
    display_name = models.CharField(max_length=200, help_text="የሚታየው ስም")
    niche = models.CharField(max_length=100, help_text="የገበያ ኒች")
    target_market = models.CharField(max_length=100, help_text="ዒላማ ገበያ")
    
    repo_url = models.URLField(blank=True, help_text="የጂት ሪፖዚቶሪ አድራሻ")
    repo_path = models.CharField(max_length=500, blank=True, help_text="የአካባቢው የጂት ፎልደር መንገድ")
    deployment_url = models.URLField(blank=True, help_text="የተሰማራው ድረ-ገጽ አድራሻ")
    
    competitor_urls = models.JSONField(default=list, help_text="የተወዳዳሪ ድረ-ገጾች ዝርዝር")
    primary_keywords = models.JSONField(default=list, help_text="ዋና ቁልፍ ቃላት")
    target_audience = models.TextField(blank=True, help_text="ዒላማ ተመልካች መግለጫ")
    content_style = models.CharField(
        max_length=50, 
        default='professional',
        choices=[
            ('professional', 'Professional'),
            ('casual', 'Casual'),
            ('storytelling', 'Storytelling'),
            ('educational', 'Educational'),
        ],
        help_text="የይዘት አጻጻፍ ዘይቤ"
    )
    
    growth_level = models.IntegerField(
        default=1,
        choices=[
            (1, 'Local'),
            (2, 'City'),
            (3, 'Country'),
            (4, 'Continent'),
            (5, 'Global'),
        ],
        help_text="የአሁኑ የእድገት ደረጃ"
    )
    monthly_visitors = models.IntegerField(default=0, help_text="በወር ጎብኝዎች")
    page_views = models.IntegerField(default=0, help_text="ጠቅላላ ገጽ እይታዎች")
    total_sellers = models.IntegerField(default=0, help_text="ጠቅላላ ሻጮች ብዛት")
    total_products = models.IntegerField(default=0, help_text="ጠቅላላ ምርቶች ብዛት")
    monthly_revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0, help_text="በወር ገቢ")
    last_traffic_update = models.DateTimeField(null=True, blank=True, help_text="የመጨረሻ የትራፊክ መረጃ ማዘመኛ")
    
    last_marketing_campaign = models.DateTimeField(null=True, blank=True, help_text="የመጨረሻ ግብይት ካምፔን ቀን")
    pending_notifications = models.JSONField(default=list, help_text="ያልተላኩ ማሳወቂያዎች")
    
    is_active = models.BooleanField(default=True, help_text="ጣቢያው ንቁ ነው?")
    auto_update_enabled = models.BooleanField(default=True, help_text="ኤጀንቱ በራስ-ሰር ያሻሽለዋል?")
    auto_marketing_enabled = models.BooleanField(default=True, help_text="ራስ-ሰር ግብይት ያድርግ?")
    update_frequency = models.CharField(
        max_length=20, 
        default='daily',
        choices=[
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        help_text="ምን ያህል ጊዜ እንደሚሻሻል"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name', 'is_active']),
            models.Index(fields=['niche', 'target_market']),
            models.Index(fields=['growth_level']),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.niche}) - Level {self.growth_level}"

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


# ============================================================
# 4. 🆕 የንግድ እድገት እና የደንበኛ ማግኛ ሞዴሎች
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
    contact_info = models.CharField(max_length=255, help_text="ኢሜይል ወይም ስልክ ቁጥር")
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
    target_audience = models.JSONField(default=dict, help_text="ዒላማ ተመልካች መስፈርቶች")
    
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
    """የሻጮች መረጃ እና አፈጻጸም የሚተዳደርበት"""
    
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
        return f"{self.business_name or self.user.username}"


class NotificationQueue(models.Model):
    """ያልተላኩ ማሳወቂያዎችን የሚይዝ ወረፋ"""
    
    NOTIFICATION_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App Notification'),
    ]
    
    site = models.ForeignKey(SiteRegistry, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    recipient = models.CharField(max_length=255, help_text="ኢሜይል ወይም ስልክ ቁጥር")
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_notification_type_display()} to {self.recipient} - {'Sent' if self.is_sent else 'Pending'}"
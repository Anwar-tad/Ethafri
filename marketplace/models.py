# EthAfri/marketplace/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import get_language
import uuid
import hashlib

class Category(models.Model):
    """በ AI የሚፈጠሩ እና የሚደራጁ የምርት ምድቦች"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(blank=True, default='fa-tag', max_length=50)

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
    created_at = models.DateTimeField(auto_now_add=True)

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

class AISystemTask(models.Model):
    """[DEPRECATED] ለታሪክ ብቻ የተቀመጠ አሮጌ ሞዴል"""
    task_name = models.CharField(max_length=255)
    priority_reason = models.TextField()
    status = models.CharField(max_length=50, default='Completed')
    created_at = models.DateTimeField(auto_now_add=True)

class OwnerDirective(models.Model):
    """[DEPRECATED] ለታሪክ ብቻ የተቀመጠ አሮጌ መመሪያ ሞዴል"""
    instruction = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class SelfHealingLog(models.Model):
    """AI በራሱ የፈወሳቸውን የዳታቤዝ እና የሲስተም ስህተቶች መዝገብ"""
    error_message = models.TextField()
    solution_sql = models.TextField(blank=True, null=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Healed: {self.error_message[:30]}..."


# =====================================================================
# 🛠️ አዲሱ ልዕለ-አውቶኖመስ የማህደረ-ትውስታ እና የቁጥጥር መዋቅር (NEW ARCHITECTURE)
# =====================================================================

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
    ]

    task_name = models.CharField(max_length=255)
    target_file = models.CharField(max_length=255, help_text="የሚሻሻለው ወይም የሚመረመረው የኮድ ፋይል ስም")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    description = models.TextField(blank=True, default='', help_text="የስራው ዝርዝር መግለጫ እና ቅድሚያ የተሰጠበት ምክንያት")
    
    # 🛡️ ተደጋጋሚ ስራዎችን ለመከላከል የተገጠመ ልዩ መለያ
    task_hash = models.CharField(
        max_length=64, 
        unique=True, 
        blank=True, 
        help_text="የስራ መደራረብን ለመከላከል በራስ-ሰር የሚመነጭ ልዩ ሃሽ"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # ፋይሉንና የስራውን ስም በማገናኘት ልዩ ሃሽ ያመነጫል
        if not self.task_hash:
            raw_string = f"{self.target_file}:{self.task_name}"
            self.task_hash = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.priority}] {self.task_name} ({self.status})"


class AIEvolutionLog(models.Model):
    """የተለወጡ ኮዶች ታሪክ፣ የተለወጠበት ምክንያት እና የድሮው ኮድ ባክአፕ መመዝገቢያ"""
    # 🔗 ከዋናው ባክሎግ ስራ ጋር ማገናኛ (ስራው በራሱ ከቆመ ሊጠፋ ስለሚችል null=True ይፈቀዳል)
    backlog_task = models.ForeignKey(
        AIProjectBacklog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evolution_logs'
    )
    target_file = models.CharField(max_length=255)
    reason_for_change = models.TextField()
    old_code_backup = models.TextField(blank=True, null=True, help_text="የነበረው የድሮው ኮድ")
    new_code_patch = models.TextField(blank=True, null=True, help_text="የተተካው አዲሱ ኮድ")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evolution on {self.target_file} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class AdminOverrideInstruction(models.Model):
    """የዌብሳይቱ ባለቤት (አድሚን) 'ይህ ይቅደም' ወይም 'ይህ ይሻሻል' ሲል ለኤጀንቱ የሚሰጠው የቁጥጥር ትዕዛዝ"""
    backlog_task = models.ForeignKey(
        AIProjectBacklog, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='overrides',
        help_text="ይህ መመሪያ የሚመለከተው የተወሰነ የባክሎግ ስራ ካለ (ባዶ ከሆነ ለአጠቃላይ ሲስተም ያገለግላል)"
    )
    instruction = models.TextField(help_text="ለኤጀንቱ የሚተላለፈው የባለቤት ትዕዛዝ")
    priority_override = models.CharField(
        max_length=20, 
        choices=AIProjectBacklog.PRIORITY_CHOICES, 
        blank=True, 
        null=True,
        help_text="የስራውን ቅድሚያ ደረጃ ለመቀየር ከተፈለገ"
    )
    is_processed = models.BooleanField(default=False, help_text="ኤጀንቱ መመሪያውን አንብቦ ተግባራዊ አድርጎታል?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        task_info = f" for {self.backlog_task.task_name}" if self.backlog_task else " (Global Directive)"
        return f"Admin Override{task_info} - Applied: {self.is_processed}"

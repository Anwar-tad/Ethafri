# EthAfri/marketplace/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import get_language  # ⚠️ የቋንቋ መለያ (ለ i18n)
import uuid

class Category(models.Model):
    """በ AI የሚፈጠሩ እና የሚደራጁ የምርት ምድቦች"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(blank=True, default='fa-tag', max_length=50)

    def save(self, *args, **kwargs):
        if not self.slug:
            # መጀመሪያ ስሙን ወደ እንግሊዝኛ ለመቀየር ይሞክራል
            self.slug = slugify(self.name)
            # ስሙ አማርኛ ከሆነ slugify ባዶ ስለሚሆን በፍጹም የማይደገም አጭር ኮድ ይጨምራል
            if not self.slug:
                self.slug = f"cat-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    """የማርኬት ፕሌሱ ዋና የምርት መረጃ መያዣ"""
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)  # ነባሪው በእንግሊዝኛ ይገባል
    description = models.TextField()  # ነባሪው በእንግሊዝኛ ይገባል
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    image_url = models.URLField(blank=True, null=True)  # በ AI የሚመጡ ምስሎች ሊንክ
    image = models.ImageField(upload_to='products/', blank=True, null=True)  # ተጠቃሚ የሚጭነው ምስል
    location = models.CharField(max_length=255, default='Global / ኢትዮጵያ')
    specifications = models.JSONField(default=dict, blank=True) 
    market_value_status = models.CharField(max_length=50, blank=True, default='Unknown')
    is_active = models.BooleanField(default=True)
    ai_tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ⚠️ 1. የብዙ ቋንቋ ትርጉም በራሱ የሚለይበት ስማርት ሎጂክ (ምንም የዳታቤዝ ለውጥ ሳይፈልግ)
    def get_translated_title(self):
        lang = get_language()
        # ነባሪው ቋንቋ እንግሊዝኛ ከሆነ በቀጥታ ያሳያል
        if lang == 'en':
            return self.title
        
        # ወደ ሌሎች ቋንቋዎች ከተተረጎመ 'Title ||| Description' የሚለውን ሰብሮ ያወጣል
        translation = getattr(self, 'translations', None)
        if translation:
            # በቋንቋው ኮድ (am, om, ar, so) የተቀመጠውን ፅሁፍ ይፈልጋል
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
    """ምርቶችን በ 7 ቋንቋዎች በራስ-ሰር ተርጉሞ ለማከማቸት (በ 'Title ||| Description' ፎርማት)"""
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

# ⚠️ 1. የትርጉም ወረፋ ሰንጠረዥ ተጨምሯል (የጀሚኒ ኮታ ሲያልቅ ምርቶችን በወረፋ ይዞ ቆይቶ ለመተርጎም)
class TranslationQueue(models.Model):
    """በቀን ገደብ (Quota) ምክንያት ሳይተረጎሙ የቀሩ ምርቶችን በወረፋ ይዞ ቆይቶ ለመተርጎም"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pending_translations')
    target_languages = models.JSONField(default=list) # e.g., ['am', 'om', 'ar']
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Queue: {self.product.title} ({len(self.target_languages)} languages pending)"

class SiteConfig(models.Model):
    """የዌብሳይቱን ዲዛይን (Logo, Banner, Color) በ AI ለመቀየር"""
    key = models.CharField(max_length=100, unique=True)  # ምሳሌ፦ 'DYNAMIC_UI'
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
    """AI ራሱን ለመገንባት ቅድሚያ የሰጣቸውን ስራዎች መቆጣጠሪያ"""
    task_name = models.CharField(max_length=255)
    priority_reason = models.TextField()
    status = models.CharField(max_length=50, default='Completed')
    created_at = models.DateTimeField(auto_now_add=True)

class OwnerDirective(models.Model):
    """የዌብሳይቱ ባለቤት ለ AI የሚሰጠው ቀጥተኛ መመሪያ መመዝገቢያ"""
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
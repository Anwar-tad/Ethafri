# EthAfri/marketplace/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid

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
                # ለአማርኛ ስሞች ልዩ UUID በመጠቀም ስህተትን መከላከል
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
    image_url = models.URLField(blank=True, null=True) # በ AI የሚመጡ ምስሎች ሊንክ
    image = models.ImageField(upload_to='products/', blank=True, null=True) # ተጠቃሚ የሚጭነው ምስል
    location = models.CharField(max_length=255, default='Global / ኢትዮጵያ')
    specifications = models.JSONField(default=dict, blank=True) 
    
    # ⚠️ ይህ መስመር በላክኸው ፋይል ውስጥ ጠፍቶ ስለነበር ተመልሷል (ስህተቱን ይፈታል)
    market_value_status = models.CharField(max_length=50, blank=True, default='Unknown')
    
    is_active = models.BooleanField(default=True)
    ai_tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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

class SiteConfig(models.Model):
    """የዌብሳይቱን ዲዛይን (Logo, Banner, Color) በ AI ለመቀየር"""
    key = models.CharField(max_length=100, unique=True) # ምሳሌ፦ 'DYNAMIC_UI'
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
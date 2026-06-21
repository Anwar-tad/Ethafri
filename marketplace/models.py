# EthAfri/marketplace/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import get_language
from django.utils import timezone  # የሰዓት ዞን ማስመጪ
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
    
    # 🆕 የንዑስ ምድብ (Subcategory) ድጋፍ ፎሬን-ኬይ
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
    specifications = models.TextField(default='{}', blank=True) 
    market_value_status = models.CharField(max_length=50, blank=True, default='Unknown')
    is_active = models.BooleanField(default=True)
    ai_tags = models.TextField(default='[]', blank=True)
    
    # 🆕 አዳዲስ የምርት የትንተና እና የ SEO መለኪያ ሜዳዎች (ከአድሚን ጋር ለመጣጣም የተጨመሩ) [1]
    seo_score = models.IntegerField(default=0, help_text="SEO ውጤት (0-100)")
    view_count = models.IntegerField(default=0, help_text="የተመለከቱ ብዛት")
    inquiry_count = models.IntegerField(default=0, help_text="የጥያቄ ብዛት")
    last_enhanced = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
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
    """ምርቶችን በ 7 ቋንቋዎች በራስ-ሰር ተርጉሞ ለማከማቸት (በ 'Title ||| Description' ፎርማት)"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='translations')
    en = models.TextField(blank=True, verbose_name="English")
    am = models.TextField(blank=True, verbose_name="Amharic")
    om = models.TextField(blank=True, verbose_name="Oromo")
    ar = models.TextField(blank=True, verbose_name="Arabic")
    so = models.TextField(blank=True, verbose_name="Somali")
    
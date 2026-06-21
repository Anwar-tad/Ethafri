# ============================================================
# [31m\([0m\([34m[1m\([0m EthAfri/marketplace/models.py
# [33m\([0m [32m\([0m[1m\([0m [36m\([0m[1m\([0m [35m\([0m[1m\([0m [31m\([0m[1m\([0m [33m\([0m[1m\([0m [32m\([0m[1m\([0m All Models Complete (Merged)
# [34m\([0m[1m\([0m [36m\([0m[1m\([0m 2026-06-21
# ============================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import get_language
from django.utils import timezone
import uuid
import json


# ============================================================
# 1. [31m\([0m[1m\([0m [33m\([0m[1m\([0m [32m\([0m[1m\([0m [36m\([0m[1m\([0m [35m\([0m[1m\([0m [31m\([0m[1m\([0m [33m\([0m
# ============================================================

class Category(models.Model):
    """AI [32m\([0m[1m\([0m [36m\([0m[1m\([0m [35m\([0m[1m\([0m [31m\([0m[1m\([0m [33m\([0m[1m\([0m [32m\([0m[1m\([0m"""
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
    """[36m\([0m[1m\([0m [35m\([0m[1m\([0m [31m\([0m[1m\([0m [33m\([0m[1m\([0m [32m\([0m[1m\([0m [36m\([0m[1m\([0m [35m\([0m [31m\([0m"""
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    image_url = models.URLField(blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    location = models.CharField(max_length=255, default='Global / [32m\([0m[1m\([0m[36m\([0m[1m\([0m')
    specifications = models.JSONField(default=dict, blank=True)
    market_value_status = models.CharField(max_length=50, blank=True, default='Unknown')
    is_active = models.BooleanField(default=True)
    ai_tags = models.JSONField(default=list, blank=True)
    
    seo_score = models.IntegerField(default=0, help_text="SEO [32m\([0m[1m\([0m (0-100)")
    view_count = models.IntegerField(default=0, help_text="[36m\([0m[1m\([0m [35m\([0m[1m\([0m[31m\([0m[1m\([0m")
    inquiry_count = models.IntegerField(default=0, help_text="[33m\([0m[1m\([0m [32m\([0m[1m\([0m [36m\([0m[1m\([0m")
    last_enhanced = models.DateTimeField(null=True, blank=True)
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='products',
        help_text="[31m\([0m[1m\([0m [33m\([0m[1m\([0m [32m\([0m[1m\([0m [36m\([0m[1m\([0m [35m\([0m[1m\([0m [31m\([0m[1m\([0m"
    )
    
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
    
    def get_specifications(self):
        try:
            return json.loads(self.specifications) if isinstance(self.specifications, str) else self.specifications
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def get_ai_tags(self):
        try:
            return json.loads(self.ai_tags) if isinstance(self.ai_tags, str) else self.ai_tags
        except (json.JSONDecodeError, TypeError):
            return []


class SiteRegistry(models.Model):
    """Registry for all sites in the network"""
    site_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
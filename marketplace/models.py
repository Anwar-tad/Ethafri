# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/models.py
# 📝 ለውጥ፦ ሙሉ የተሻሻለ ስሪት — All Models Complete
# 📅 ቀን፦ 2026-06-21
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
    
    seo_score = models.IntegerField(default=0, help_text="SEO ውጤት (0-100)")
    view_count = models.IntegerField(default=0, help_text="የተመለከቱ ብዛት")
    inquiry_count = models.IntegerField(default=0, help_text="የጥያቄ ብዛት")
    last_enhanced = models.DateTimeField(null=True, blank=True)
    
    site = models.ForeignKey(
        'SiteRegistry',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='products',
        help_text="ይህ ምርት የሚለጠፍበትን ጣቢያ ይምረጡ"
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
        return self.title # Default fallback if no translation or 'en' 

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['seller']),
            models.Index(fields=['category']),
            models.Index(fields=['title']),
        ]


class VectorMemory(models.Model):
    """
    Stores vector embeddings for various content within the marketplace,
    primarily for products, to enable AI-driven features like similarity search and recommendations.
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='vector_memories',
        help_text="The product this vector memory is associated with."
    )
    # Can be extended to other models (e.g., Category, SiteRegistry) if their content needs vectorization.
    
    text_content = models.TextField(help_text="The original text content that was vectorized.")
    vector_data = models.JSONField(help_text="JSON representation of the vector embedding.")
    embedding_model = models.CharField(
        max_length=100, 
        default='default-embedding-model', 
        help_text="The name or identifier of the embedding model used to generate this vector."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        product_title = self.product.title if self.product else 'N/A'
        return f"Vector for Product: {product_title} | Model: {self.embedding_model}"

    class Meta:
        verbose_name_plural = "Vector Memories"
        indexes = [
            models.Index(fields=['product']), # Index for efficient lookups by product
            models.Index(fields=['embedding_model']), # Index for filtering by embedding model
        ]

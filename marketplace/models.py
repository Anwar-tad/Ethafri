from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(blank=True, default='', max_length=50)

    # ይህ ክፍል ነው Slugን በራሱ የሚፈጥረው
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # ስሙ በአማርኛ ከሆነ slugify ባዶ ሊመልስ ስለሚችል በጊዜያዊነት በ ID እንተካዋለን
            if not self.slug:
                import time
                self.slug = f"cat-{int(time.time())}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    # መሰረታዊ መረጃ
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=20, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    # ምስል እና ቦታ
    image = models.ImageField(upload_to='products/')
    location = models.CharField(max_length=255) # ለምሳሌ፡ አዲስ አበባ፣ መርካቶ
    
    # ስማርት ክፍሎች (ለማንኛውም አይነት እቃ የሚለዋወጥ መረጃ)
    # ለምሳሌ፡ ለመኪና (ኪሎ ሜትር)፣ ለቤት (የክፍል ብዛት) እዚህ ይገባል
    specifications = models.JSONField(default=dict, blank=True) 
    
    # AI - ራሱን የሚያሳድግበት መረጃ
    ai_tags = models.JSONField(default=list, blank=True) # AI የሚያወጣቸው መለያዎች
    market_value_status = models.CharField(max_length=50, blank=True) # Cheap, Fair, Expensive
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class MarketTrend(models.Model):
    """AI በየቀኑ ገበያውን አጥንቶ የሚያስቀምጥበት ቦታ"""
    niche_name = models.CharField(max_length=100) # ለምሳሌ፡ 'የፀሐይ ኃይል መሣሪያዎች'
    demand_level = models.IntegerField() # ከ 1-100
    ai_suggestion = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)
    
class UserSearch(models.Model):
    query = models.CharField(max_length=255) # ሰውየው የፈለገው ቃል
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    results_count = models.IntegerField(default=0) # ስንት እቃ ተገኘ?
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query
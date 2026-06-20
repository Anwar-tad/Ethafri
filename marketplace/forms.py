# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/forms.py
# 📝 ለውጥ፦ Multi-Site Support + Enhanced Product Form
# 📅 ቀን፦ 2026-06-20
# ============================================================

from django import forms
from django.contrib.auth.models import User
from .models import Product, Category, SiteRegistry


class ProductForm(forms.ModelForm):
    """የምርት መለጠፊያ ፎርም — Multi-Site ድጋፍ ያለው"""
    
    # 🆕 አዲስ መስክ — ለጣቢያ ምርጫ
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.filter(is_active=True),
        required=False,
        empty_label="Select Site (optional)",
        help_text="ይህ ምርት የሚለጠፍበትን ጣቢያ ይምረጡ"
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Select Category"
    )
    
    class Meta:
        model = Product
        fields = ['title', 'description', 'price', 'category', 'location', 'image', 'site']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product title...',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe your product in detail...',
                'required': True
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City, Country'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
    
    def clean_price(self):
        """የዋጋ ማረጋገጫ"""
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price
    
    def clean_title(self):
        """የርዕስ ማረጋገጫ"""
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 3:
            raise forms.ValidationError("Title must be at least 3 characters long.")
        return title.strip()
    
    def save(self, commit=True):
        """ፎርሙን በማስቀመጥ ላይ — Multi-Site ድጋፍ"""
        product = super().save(commit=False)
        
        # ጣቢያ ከተመረጠ የጣቢያውን ቦታ እና ምድብ አስተካክል
        site = self.cleaned_data.get('site')
        if site:
            # የጣቢያውን ቦታ እንደ ነባሪ አስቀምጥ
            if not product.location:
                product.location = site.target_market
        
        if commit:
            product.save()
            self.save_m2m()
        return product


class ProductSearchForm(forms.Form):
    """የምርት ፍለጋ ፎርም"""
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...',
            'aria-label': 'Search'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.filter(is_active=True),
        required=False,
        empty_label="All Sites",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max'
        })
    )


class SiteRegistrationForm(forms.ModelForm):
    """አዲስ ጣቢያ ለመመዝገብ ፎርም"""
    
    class Meta:
        model = SiteRegistry
        fields = ['name', 'display_name', 'niche', 'target_market', 'repo_path', 'deployment_url']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'site-name (no spaces)'
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'My Awesome Site'
            }),
            'niche': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. coffee, fashion, tech'
            }),
            'target_market': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. USA, Europe, Global'
            }),
            'repo_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '/path/to/repo'
            }),
            'deployment_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://mysite.com'
            }),
        }
    
    def clean_name(self):
        """የጣቢያ ስም ማረጋገጫ"""
        name = self.cleaned_data.get('name')
        if name and not name.replace('-', '').replace('_', '').isalnum():
            raise forms.ValidationError("Site name can only contain letters, numbers, hyphens, and underscores.")
        return name.lower()


class MarketingCampaignForm(forms.Form):
    """የግብይት ካምፔን መፍጠሪያ ፎርም"""
    
    CAMPAIGN_TYPES = [
        ('email_blast', 'Email Blast'),
        ('sms_blast', 'SMS Blast'),
        ('social_post', 'Social Media Post'),
        ('seo_campaign', 'SEO Campaign'),
        ('referral', 'Referral Program'),
    ]
    
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.filter(is_active=True),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    campaign_type = forms.ChoiceField(
        choices=CAMPAIGN_TYPES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Campaign Name'
        })
    )
    subject = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Subject (optional)'
        })
    )
    message = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': 'Enter your campaign message...'
        })
    )
    target_audience = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. All sellers, Premium users, etc.'
        })
    )
    scheduled_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
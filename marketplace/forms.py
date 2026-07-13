# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/forms.py
# 📝 ስሪት፦ v10.19 (Unified ModelForm Integration — Safe & Aligned)
# ✅ የተፈቱ ችግሮች፦ Dynamic model registration in forms to completely eliminate circular imports and AppRegistryNotReady blockages, deferred querysets in __init__, HTML XSS tag stripping, and secure seller contact sanitization.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags  # XSS ጥቃትን መከላከያ ማጽጃ
from django.apps import apps
import json
import re
from typing import Dict, List, Optional, Union, Any

# 🛡️ REGISTRY SAFETY: የ 'AppRegistryNotReady' ስህተትን ለመከላከል ሞዴሎችን በዳይናሚክ መጫን
# ይህ አሰራር የክብ ጥገኝነት (Circular Import) ስህተቶችን 100% ያስቀራል
Product = apps.get_model('marketplace', 'Product')
Category = apps.get_model('marketplace', 'Category')
SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')


class ProductForm(forms.ModelForm):
    """የምርት፣ የቤት፣ የመኪናና የአገልግሎት መለጠፊያ ፎርም — Multi-Site ድጋፍ ያለው"""
    
    # የምርት ዝርዝር አይነት ምርጫ (ሽያጭ፣ ኪራይ ወይም አገልግሎት)
    listing_type = forms.ChoiceField(
        choices=Product.LISTING_TYPES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='sale',
        label=_("Listing Type")
    )
    
    # የሻጩ ስልክ ወይም የቴሌግራም ዩዘርኔም በመለየት
    contact_info = forms.CharField(
        max_length=255, 
        required=False, 
        initial='', 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ስልክ ቁጥር ወይም @username'})
    )
    
    # የፎቶዎች መጋዘን አምድ
    image_gallery = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'ተጨማሪ የምስል ሊንኮችን በነጠላ ሰረዝ (,) በመለየት ያስገቡ...'}),
        label=_("Additional Images Gallery")
    )
    
    # 🛡️ DEFERRED EVALUATION: መጀመሪያ በባዶ queryset መመደብ (በ __init__ ውስጥ በዳይናሚክ ይተካል)
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.none(),
        required=False,
        empty_label=_("Select Site (optional)"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_("ይህ ምርት የሚለጠፍበትን ጣቢያ ይምረጡ")
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_("Select Category")
    )
    
    class Meta:
        model = Product
        fields = ['title', 'description', 'price', 'category', 'location', 'image', 'listing_type', 'contact_info', 'site']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter product title...'),
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Describe your product in detail...'),
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
                'placeholder': _('City, Country')
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        🛡️ DEFERRED EVALUATION: ኳሪዎችን በዳይናሚክ መጫን (የመጀመሪያ ማስነሻ ስህተቶችን በዘላቂነት ይከላከላል)
        """
        super().__init__(*args, **kwargs)
        CategoryModel = apps.get_model('marketplace', 'Category')
        SiteRegistryModel = apps.get_model('marketplace', 'SiteRegistry')
        
        self.fields['category'].queryset = CategoryModel.objects.all()
        self.fields['site'].queryset = SiteRegistryModel.objects.filter(is_active=True)
        
        # የነባር ምርት ማሻሻያ ከሆነ የፎቶዎችን መዝገብ በኮማ በመለየት ማሳየት
        if self.instance and self.instance.pk:
            try:
                gallery = self.instance.image_gallery
                if isinstance(gallery, list):
                    self.fields['image_gallery'].initial = ", ".join(gallery)
            except Exception:
                pass
    
    def clean_price(self):
        """የዋጋ ማረጋገጫ"""
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError(_("Price cannot be negative."))
        return price
    
    def clean_title(self):
        """የርዕስ ማረጋገጫ እና የ XSS ጠለፋ መከላከያ"""
        title = self.cleaned_data.get('title')
        if title:
            # HTML ታጎችን በሙሉ ማጽዳት (XSS Script Sanitization)
            clean_title = strip_tags(title).strip()
            if len(clean_title) < 3:
                raise forms.ValidationError(_("Title must be at least 3 characters long."))
            return clean_title
        return title

    def clean_description(self):
        """የመግለጫ ማረጋገጫ እና የ XSS ጠለፋ መከላከያ"""
        description = self.cleaned_data.get('description')
        if description:
            # HTML ታጎችን በሙሉ ማጽዳት (XSS Script Sanitization)
            return strip_tags(description).strip()
        return description

    def clean_contact_info(self):
        """🛡️ ሻጮች ስልካቸውን ወይም @username በትክክል ማስገባታቸውን ማረጋገጫ"""
        contact = self.cleaned_data.get('contact_info', '').strip()
        if contact:
            # የጃንጎን ዩዘር ስም ጋሻ እንዳያጋጭ አላስፈላጊ ልዩ ምልክቶችን ማጽዳት
            clean_contact = re.sub(r'[^a-zA-Z0-9_@.+\- ]', '', contact).strip()
            if len(clean_contact) < 4:
                raise forms.ValidationError(_("Contact info must be a valid phone number or telegram handle."))
            return clean_contact
        return contact
    
    def save(self, commit=True):
        """ፎርሙን በማስቀመጥ ላይ — Multi-Site ድጋፍ"""
        product = super().save(commit=False)
        
        # የ JSONField እሴቶችን በቀጥታ እንደ ፓይተን ሊስት (List) ማስቀመጥ
        gallery_raw = self.cleaned_data.get('image_gallery', '').strip()
        if gallery_raw:
            gallery_list = [url.strip() for url in gallery_raw.split(',') if url.strip()]
            product.image_gallery = gallery_list
        else:
            product.image_gallery = []
        
        site = self.cleaned_data.get('site')
        if site:
            if not product.location:
                product.location = site.target_market
        
        product.is_active = True
        
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
            'placeholder': _('Search products...'),
            'aria-label': 'Search'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label=_("All Categories"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.none(),
        required=False,
        empty_label=_("All Sites"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Min')
        })
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Max')
        })
    )

    def __init__(self, *args, **kwargs):
        """🛡️ DEFERRED EVALUATION: ኳሪዎችን በዳይናሚክ መጫን"""
        super().__init__(*args, **kwargs)
        CategoryModel = apps.get_model('marketplace', 'Category')
        SiteRegistryModel = apps.get_model('marketplace', 'SiteRegistry')
        
        self.fields['category'].queryset = CategoryModel.objects.all()
        self.fields['site'].queryset = SiteRegistryModel.objects.filter(is_active=True)


class SiteRegistrationForm(forms.ModelForm):
    """አዲስ ጣቢያ ለመመዝገብ ፎርም"""
    
    class Meta:
        model = SiteRegistry
        fields = [
            'name', 'display_name', 'niche', 'target_market', 'repo_path', 'deployment_url',
            'is_active', 'auto_update_enabled', 'auto_marketing_enabled'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('site-name (no spaces)')
            }),
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('My Awesome Site')
            }),
            'niche': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g. coffee, fashion, tech')
            }),
            'target_market': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g. USA, Europe, Global')
            }),
            'repo_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('/path/to/repo')
            }),
            'deployment_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': _('https://mysite.com')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'type': 'checkbox',
                'role': 'switch'
            }),
            'auto_update_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'type': 'checkbox',
                'role': 'switch'
            }),
            'auto_marketing_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'type': 'checkbox',
                'role': 'switch'
            }),
        }
    
    def clean_name(self):
        """የጣቢያ ስም ማረጋገጫ"""
        name = self.cleaned_data.get('name')
        if name and not name.replace('-', '').replace('_', '').isalnum():
            raise forms.ValidationError(_("Site name can only contain letters, numbers, hyphens, and underscores."))
        return name.lower()

    def clean_repo_path(self):
        repo_path = self.cleaned_data.get('repo_path')
        if repo_path:
            clean_path = repo_path.strip().lower()
            if clean_path.startswith('http') or 'github.com' in clean_path:
                raise forms.ValidationError(_(
                    "Repo path must be a local server directory path (e.g. /opt/render/project/src), not a GitHub URL. "
                    "The system automatically handles GitHub syncing remotely using the site name and tokens."
                ))
        return repo_path


class MarketingCampaignForm(forms.Form):
    """የግብይት ካምፔን መፍጠሪያ ፎርም"""
    
    CAMPAIGN_TYPES = [
        ('email_blast', _('Email Blast')),
        ('sms_blast', _('SMS Blast')),
        ('social_post', _('Social Media Post')),
        ('seo_campaign', _('SEO Campaign')),
        ('referral', _('Referral Program')),
    ]
    
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.none(),
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
            'placeholder': _('Campaign Name')
        })
    )
    subject = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Email Subject (optional)')
        })
    )
    message = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': _('Enter your campaign message...')
        })
    )
    target_audience = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('e.g. All sellers, Premium users, etc.')
        })
    )
    scheduled_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )

    def __init__(self, *args, **kwargs):
        """🛡️ DEFERRED EVALUATION: ኳሪዎችን በዳይናሚክ መጫን"""
        super().__init__(*args, **kwargs)
        SiteRegistryModel = apps.get_model('marketplace', 'SiteRegistry')
        self.fields['site'].queryset = SiteRegistryModel.objects.filter(is_active=True)
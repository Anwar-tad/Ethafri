# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/forms.py
# 📝 ለውጥ፦ v1.3 Site Registration Form — Dynamic Form Active Sync & i18n
# ✅ የተፈቱ ችግሮች፦ Form-level is_active default alignment, complete translation tags (i18n) for errors/help text
# 📅 ቀን፦ 2026-06-27
# ============================================================

from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _  # ✅ i18n ድጋፍ ተጨምሯል
from .models import Product, Category, SiteRegistry


class ProductForm(forms.ModelForm):
    """የምርት መለጠፊያ ፎርም — Multi-Site ድጋፍ ያለው"""
    
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.filter(is_active=True),
        required=False,
        empty_label=_("Select Site (optional)"),  # ✅ የትርጉም መለያ ተዋቅሯል
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_("ይህ ምርት የሚለጠፍበትን ጣቢያ ይምረጡ")  # ✅ የትርጉም መለያ ተዋቅሯል
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_("Select Category")
    )
    
    class Meta:
        model = Product
        fields = ['title', 'description', 'price', 'category', 'location', 'image', 'site']
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
    
    def clean_price(self):
        """የዋጋ ማረጋገጫ"""
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError(_("Price cannot be negative."))
        return price
    
    def clean_title(self):
        """የርዕስ ማረጋገጫ"""
        title = self.cleaned_data.get('title')
        if title and len(title.strip()) < 3:
            raise forms.ValidationError(_("Title must be at least 3 characters long."))
        return title.strip()
    
    def save(self, commit=True):
        """ፎርሙን በማስቀመጥ ላይ — Multi-Site ድጋፍ"""
        product = super().save(commit=False)
        
        site = self.cleaned_data.get('site')
        if site:
            if not product.location:
                product.location = site.target_market
        
        # ✅ v1.3 UX alignment: ምርቱ በፎርም ደረጃም ሲመዘገብ ወዲያውኑ መነሻ ገጹ ላይ እንዲነቃ ማድረግ
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
        queryset=Category.objects.all(),
        required=False,
        empty_label=_("All Categories"),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    site = forms.ModelChoiceField(
        queryset=SiteRegistry.objects.filter(is_active=True),
        required=False,
        empty_label=_("All Sites"),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
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
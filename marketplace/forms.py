# EthAfri/marketplace/forms.py

from django import forms
from .models import Product, Category, ProductTranslation
from .ai_utils import analyze_product_smartly

class ProductForm(forms.ModelForm):
    """
    ተጠቃሚዎች እቃ የሚለጥፉበት ቅጽ።
    የ AI ውህደት ያለው save() ዘዴን ያካተተ።
    """
    class Meta:
        model = Product
        fields = ['title', 'description', 'price', 'image', 'location']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control rounded-pill', 
                'placeholder': 'የእቃው ስም (ለምሳሌ፦ iPhone 13 Pro)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'ስለ እቃው ዝርዝር መግለጫ ይጻፉ...'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control rounded-pill', 
                'placeholder': 'ዋጋ በ ETB'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control rounded-pill', 
                'placeholder': 'ያሉበት ቦታ (ለምሳሌ፦ አዲስ አበባ፣ ቦሌ)'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }

    def save(self, commit=True):
        # 1. ፎርሙን በከፊል መቆጠብ (የምርቱን ID ለማግኘት)
        instance = super().save(commit=False)
        
        # 2. 🤖 AI አውቶኖመስ ካቴጎራይዜሽን እና ትርጉም
        ai_data = analyze_product_smartly(instance.title, instance.description, instance.price)
        
        # 3. 🛡️ የካቴጎሪ ፎሬን-ኬይ ደህንነት ጥበቃ
        category_name = 'General'
        if ai_data and 'category' in ai_data:
            category_name = ai_data['category']
            
        category_instance, _ = Category.objects.get_or_create(name=category_name)
        instance.category = category_instance
        
        # 4. 🛡️ የ ai_tags ሜዳ ማስተካከያ
        if ai_data and 'tags' in ai_data:
            instance.ai_tags = ai_data['tags']
        else:
            instance.ai_tags = []
        
        # 5. 🛡️ ምርቱን በመጀመሪያ ማስቀመጥ (ID እንዲኖረው)
        if commit:
            instance.save()
            
            # 6. የትርጉም ዳታዎችን ማዘጋጀት እና ማጠራቀም
            translations = ai_data.get('translations', {}) if ai_data else {}
            combined_fallback = f"{instance.title} ||| {instance.description}"
            
            # ProductTranslation ሰንጠረዥን በትክክል መፍጠር
            ProductTranslation.objects.update_or_create(
                product=instance,
                defaults={
                    'en': translations.get('en', combined_fallback),
                    'am': translations.get('am', combined_fallback),
                    'om': translations.get('om', combined_fallback),
                    'ar': translations.get('ar', combined_fallback),
                    'so': translations.get('so', combined_fallback),
                    'ti': translations.get('ti', combined_fallback),
                    'fr': translations.get('fr', combined_fallback),
                }
            )
            
        return instance

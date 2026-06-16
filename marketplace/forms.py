#EthAfri/marketplace/forms.py

from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    """
    ተጠቃሚዎች እቃ የሚለጥፉበት ቅጽ። 
    ካቴጎሪው በ AI ስለሚሞላ እዚህ ውስጥ አልተካተተም።
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
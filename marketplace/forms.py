from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        # image እና location ተጨምረዋል
        fields = ['title', 'description', 'price', 'image', 'location']
        
        # ምድብን (Category) ከዚህ አውጥተነዋል ምክንያቱም AIው በራሱ እንዲመድበው ስለምንፈልግ ነው
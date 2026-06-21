from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Product, Category
import json

def full_site_analysis(request):
    try:
        # Ensure we're working with a safe slice if needed
        products = Product.objects.all()[:1000]  # Limit to prevent memory issues
        categories = Category.objects.all()
        
        analysis_data = {
            'total_products': products.count(),
            'total_categories': categories.count(),
            'active_products': products.filter(is_active=True).count(),
            'products_by_category': {}
        }
        
        for category in categories:
            analysis_data['products_by_category'][str(category)] = products.filter(category=category).count()
        
        return JsonResponse(analysis_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
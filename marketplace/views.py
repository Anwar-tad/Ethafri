from django.shortcuts import render, redirect
from .models import Product, Category
from .ai_utils import analyze_product_smartly

def add_product(request):
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        image = request.FILES.get('image')
        location = request.POST.get('location')

        # 1. መጀመሪያ እቃውን ለጊዜው እናስቀምጥ
        product = Product.objects.create(
            seller=request.user,
            title=title,
            description=description,
            price=price,
            image=image,
            location=location
        )

        # 2. AI ኤጀንቱን ጠርተን መረጃውን እናበልጽግ
        ai_data = analyze_product_smartly(title, description, price)
        
        if ai_data:
            # ምድቡን ማስተካከል
            cat, _ = Category.objects.get_or_create(name=ai_data['category'])
            product.category = cat
            product.specifications = ai_data['specs']
            product.ai_tags = ai_data['tags']
            product.market_value_status = ai_data['valuation']
            product.save()

        return redirect('home')
    
    return render(request, 'marketplace/add_product.html')

# marketplace/views.py ላይ ጨምረው
from .growth_agent import run_daily_market_analysis
from .models import MarketTrend

def admin_growth_dashboard(request):
    # ይህ ገጽ ለባለቤቱ ብቻ የሚታይ ነው
    if not request.user.is_staff:
        return redirect('home')

    # AIው ገበያውን እንዲመረምር ትእዛዝ መስጠት
    analysis_report = None
    if 'run_analysis' in request.GET:
        analysis_report = run_daily_market_analysis()

    trends = MarketTrend.objects.all().order_by('-last_updated')
    return render(request, 'marketplace/growth_dashboard.html', {
        'trends': trends,
        'report': analysis_report
    })
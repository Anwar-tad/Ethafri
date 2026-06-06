from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, Category, MarketTrend, UserSearch
from .ai_utils import analyze_product_smartly
from .growth_agent import run_daily_market_analysis

# 1. ዋና ገጽ (እቃዎችን ማሳያ እና ፍለጋ መመዝገቢያ)
def home(request):
    query = request.GET.get('q')
    if query:
        # ሰዎች የሚፈልጉትን ቃል AIው እንዲያጠናው እንመዘግባለን
        products = Product.objects.filter(title__icontains=query)
        UserSearch.objects.create(
            query=query,
            results_count=products.count(),
            user=request.user if request.user.is_authenticated else None
        )
    else:
        products = Product.objects.filter(is_active=True).order_by('-created_at')

    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories
    })

# 2. እቃ መለጠፊያ (በ AI የሚታገዝ)
@login_required # እቃ ለመለጠፍ መግባት አለባቸው
def post_product(request):
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        image = request.FILES.get('image')
        location = request.POST.get('location')

        # መጀመሪያ እቃውን እናስቀምጥ
        product = Product.objects.create(
            seller=request.user,
            title=title,
            description=description,
            price=price,
            image=image,
            location=location
        )

        # AI ኤጀንቱን ጠርተን መረጃውን እናበልጽግ
        ai_data = analyze_product_smartly(title, description, price)
        
        if ai_data:
            cat, _ = Category.objects.get_or_create(name=ai_data.get('category', 'ሌሎች'))
            product.category = cat
            product.specifications = ai_data.get('specs', {})
            product.ai_tags = ai_data.get('tags', [])
            product.market_value_status = ai_data.get('valuation', 'Unknown')
            product.save()

        return render(request, 'marketplace/post_success.html', {'ai_data': ai_data})
    
    return render(request, 'marketplace/post_product.html')

# 3. የዕድገት ዴሽቦርድ (ለባለቤቱ)
def admin_growth_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')

    analysis_report = None
    if 'run_analysis' in request.GET:
        analysis_report = run_daily_market_analysis()

    trends = MarketTrend.objects.all().order_by('-last_updated')
    return render(request, 'marketplace/growth_dashboard.html', {
        'trends': trends,
        'report': analysis_report
    })
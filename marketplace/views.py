# EthAfri/marketplace/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

# እዚህ ጋር AISystemTask መጨመሩን ያረጋግጡ
from .models import Product, Category, MarketTrend, UserSearch, SiteConfig, ProductTranslation, AISystemTask
from .ai_utils import analyze_product_smartly
from .growth_agent import run_daily_market_analysis

# 1. የ AI ዲዛይን ቅንብርን ለሁሉም ገጾች የሚያቀርብ (Context Processor)
def theme_context(request):
    config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
    return {'theme': config.value if config else {}}

# 2. ዋና ገጽ
def home(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(title__icontains=query)
        UserSearch.objects.create(query=query, results_count=products.count())
    else:
        products = Product.objects.filter(is_active=True).order_by('-created_at')

    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories
    })

# 3. እቃ መለጠፊያ (ከ Anonymous Posting Logic ጋር)
def post_product(request):
    post_count = request.session.get('post_count', 0)
    if request.method == "POST":
        if not request.user.is_authenticated and post_count >= 5:
            return redirect('signup')

        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        location = request.POST.get('location')
        image = request.FILES.get('image')

        if request.user.is_authenticated:
            seller = request.user
        else:
            seller, _ = User.objects.get_or_create(username='guest_user', defaults={'email': 'guest@ethafri.com'})

        product = Product.objects.create(
            seller=seller,
            title=title,
            description=description,
            price=price if price else 0,
            location=location,
            image=image
        )

        ai_data = analyze_product_smartly(title, description, price)
        if ai_data:
            cat_name = ai_data.get('category', 'General')
            cat, _ = Category.objects.get_or_create(name=cat_name)
            product.category = cat
            product.ai_tags = ai_data.get('tags', [])
            product.save()

        request.session['post_count'] = post_count + 1
        return redirect('post_success')
    
    return render(request, 'marketplace/post_product.html', {'post_count': post_count})

# 4. የስኬት ገጽ
def post_success(request):
    return render(request, 'marketplace/post_success.html')

# 5. ራስ-ሰር የዕድገት መቀስቀሻ (Trigger) - አሁን ስህተቱ እዚህ ነበር የተፈጠረው
def trigger_evolution(request):
    secret_key = "evolve-now-secret-123"
    
    if request.user.is_staff or secret_key in request.path:
        # AIውን ያሰራዋል
        result = run_daily_market_analysis()
        
        # የቅርብ ጊዜውን የ AI ስራ ዝርዝር ያወጣል (አሁን AISystemTask ይታወቃል)
        try:
            latest_task = AISystemTask.objects.latest('created_at')
        except AISystemTask.DoesNotExist:
            latest_task = None

        if request.user.is_staff:
            return render(request, 'marketplace/evolution_result.html', {
                'status': result,
                'task': latest_task
            })
        return HttpResponse(f"Success: {result}")
    else:
        raise Http404("ገጹ አልተገኘም")

# 6. የዕድገት ዴሽቦርድ
def admin_growth_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')
    trends = MarketTrend.objects.all().order_by('-last_updated')
    return render(request, 'marketplace/growth_dashboard.html', {'trends': trends})

# Auth views (Signup, Login, Logout)
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'marketplace/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'marketplace/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')
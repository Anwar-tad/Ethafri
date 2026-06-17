# EthAfri/marketplace/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import get_language
from .models import Product, Category, MarketTrend, UserSearch, SiteConfig, ProductTranslation, OwnerDirective, AISystemTask
from .ai_utils import analyze_product_smartly
from .growth_agent import run_daily_market_analysis
from .self_coder import self_heal_failed_build 
# 📌 🛠️ አዲሱን የዲዛይን፣ የኮድ እና የዳታቤዝ ሐኪም ማገናኘት
from .self_doctor import heal_any_system_error, discover_and_heal_ui_design

# 1. የ AI ዲዛይን ቅንብርን ለሁሉም ገጾች የሚያቀርብ (Context Processor)
def theme_context(request):
    """AIው የወሰነውን የዌብሳይት ዲዛይን ዳታ (ቀለም፣ ባነር ወዘተ) ለሁሉም ገጾች ያዳርሳል።"""
    config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
    return {'theme': config.value if config else {}}

# 2. ዋና ገጽ (ማጣሪያ የተገጠመለት)
def home(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    try:
        if query:
            products = Product.objects.filter(title__icontains=query)
            UserSearch.objects.create(query=query, results_count=products.count())
        elif category_id:
            products = Product.objects.filter(category_id=category_id, is_active=True).order_by('-created_at')
        else:
            products = Product.objects.filter(is_active=True).order_by('-created_at')
    except Exception as db_err:
        # 📌 🛠️ በዋናው ገጽ ላይ የዳታቤዝ ስህተት ቢፈጠር ሐኪሙ ራሱ በጀርባ ያክመዋል
        heal_any_system_error('DATABASE', str(db_err), f"Home View Filter Query: {query or category_id}")
        products = Product.objects.none()

    categories = Category.objects.all()
    active_lang = get_language()

    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories,
        'active_category': int(category_id) if category_id else None,
        'active_lang': active_lang
    })

# 3. የእቃ ዝርዝር ገጽ
def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        raise Http404("እቃው አልተገኘም")
    return render(request, 'marketplace/product_detail.html', {'product': product})

# 4. እቃ መለጠፊያ (Anonymous Posting + 5 limit)
def post_product(request):
    """ተጠቃሚዎች እስከ 5 እቃ ያለ ሎግኢን መለጠፍ ይችላሉ። ከ 5 በላይ ሲሆን ግን እንዲመዘገቡ ይጠየቃሉ።"""
    post_count = request.session.get('post_count', 0)
    
    # 📌 🛠️ የደኅንነት ማጠናከሪያ፦ ተጠቃሚው ሳይመዘገብ 5 እቃ ከለጠፈ በ GET ጭምር ገጹን እንዳያገኘው መከልከል
    if not request.user.is_authenticated and post_count >= 5:
        return redirect('signup')

    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        location = request.POST.get('location')
        image = request.FILES.get('image')

        try:
            if request.user.is_authenticated:
                seller = request.user
            else:
                seller, _ = User.objects.get_or_create(
                    username='guest_user', 
                    defaults={'email': 'guest@ethafri.com'}
                )

            product = Product.objects.create(
                seller=seller, title=title, description=description,
                price=price if price else 0, location=location, image=image
            )

            # AI ትንተና (የእቃ ምድብ መለያ)
            ai_data = analyze_product_smartly(title, description, price)
            if ai_data:
                cat_name = ai_data.get('category', 'General')
                cat, _ = Category.objects.get_or_create(name=cat_name)
                product.category = cat
                product.ai_tags = ai_data.get('tags', [])
                product.save()

            # በሴሽን ውስጥ የለጠፉትን ቁጥር መጨመር
            request.session['post_count'] = post_count + 1
            return redirect('post_success')
            
        except Exception as exec_err:
            # 📌 🛠️ ምርት በሚለጠፍበት ወቅት የኮድ ወይም የሎጂክ ክራሽ ቢፈጠር ራሱን የማከም ዑደት
            heal_any_system_error('CODE_EXECUTION', str(exec_err), f"Post Product Crash: Title={title}")
            return HttpResponse("⚠️ System experienced a glitch. Auto-healing triggered, please retry.", status=500)
    
    return render(request, 'marketplace/post_product.html', {'post_count': post_count})

# 5. የስኬት ገጽ
def post_success(request):
    return render(request, 'marketplace/post_success.html')

# 6. ራስ-ሰር የዕድገት መቀስቀሻ (Core Evolution Engine)
def trigger_evolution(request):
    """ይህ URL በየ 5 ደቂቃው ሲቀሰቀስ የገበያ ጥናት፣ የኮድ ጥገና እና የዲዛይን አሰሳ በአንድ ላይ ይከናወናል።"""
    secret_key = "evolve-now-secret-123"
    
    if request.user.is_staff or secret_key in request.path:
        # ሀ. የገበያ ጥናት እና የዲዛይን ለውጥ ሞተር
        result = run_daily_market_analysis()
        
        # ለ. ራስ-ኮድ ጥገና ሞተር
        heal_result = self_heal_failed_build()
        print(f"Self-Coder Status: {heal_result}")
        
        # 📌 🛠️ ሐ. የዲዛይን አሰሳ እና የ UI ውበት ዝግመተ ለውጥ (ደጋግሞ እንዳይሰራ ትውስታን ይጠቀማል)
        config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
        current_color = config.value.get('theme_color', '#1a2a6c') if config else '#1a2a6c'
        discover_and_heal_ui_design(current_color, trend_context="Modern African E-Commerce Trend")

        if result.startswith("✅"):
            try:
                latest_task = AISystemTask.objects.latest('created_at')
            except AISystemTask.DoesNotExist:
                latest_task = None

            if request.user.is_staff:
                return render(request, 'marketplace/evolution_result.html', {
                    'status': f"{result} | Coder: {heal_result}",
                    'task': latest_task
                })
        else:
            return HttpResponse(
                f"<div style='padding:30px; font-family:sans-serif; color:red;'>"
                f"<h2>❌ የ AI ዕድገት አልተሳካም!</h2>"
                f"<p><b>ምክንያት፦</b> {result}</p>"
                f"<p><b>የኮድ ጥገና ሁኔታ፦</b> {heal_result}</p>"
                f"<p><a href='/'>ወደ ዋና ገጽ ተመለስ</a></p></div>", 
                status=400
            )
            
        return HttpResponse(f"Success: {result} | Coder: {heal_result}")
    else:
        raise Http404("ገጹ አልተገኘም")

# 7. የዕድገት ዴሽቦርድ
def admin_growth_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')
    trends = MarketTrend.objects.all().order_by('-last_updated')
    tasks = AISystemTask.objects.all().order_by('-created_at')
    return render(request, 'marketplace/growth_dashboard.html', {
        'trends': trends,
        'tasks': tasks
    })

# 8. የባለቤት መመሪያ ገጽ
@login_required
def owner_directive_view(request):
    if not request.user.is_staff:
        return redirect('home')
    if request.method == "POST":
        instruction = request.POST.get('instruction')
        if instruction:
            OwnerDirective.objects.all().update(is_active=False)
            OwnerDirective.objects.create(instruction=instruction, is_active=True)
            return HttpResponse("<script>alert('መመሪያዎ ለ AI ደርሷል!'); window.location.href='/';</script>")
    return render(request, 'marketplace/owner_directive.html')

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

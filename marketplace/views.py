# EthAfri/marketplace/views.py

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import get_language, gettext_lazy as _
import uuid

from .models import (
    Product, Category, MarketTrend, UserSearch, SiteConfig, 
    ProductTranslation, OwnerDirective, AISystemTask, TranslationQueue
)
from .ai_utils import analyze_product_smartly
from .growth_agent import run_daily_market_analysis
from .self_coder import self_heal_failed_build 
from .self_doctor import heal_any_system_error, discover_and_heal_ui_design

# 1. የ AI ዲዛይን ቅንብርን ለሁሉም ገጾች የሚያቀርብ (Context Processor)
def theme_context(request):
    config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
    return {'theme': config.value if config else {}}

# 2. ዋና ገጽ (ማጣሪያ የተገጠመለት)
from django.db.models import Prefetch

def home(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    try:
        # 1. select_related ለ Foreign Key (Category)
        # 2. prefetch_related ለ OneToOne/Many (Translations)
        products = Product.objects.select_related('category') \
            .prefetch_related('translations') \
            .filter(is_active=True)

        if query:
            products = products.filter(title__icontains=query)
            # የፍለጋ መዝገብን ከዋናው Query ለይተን እንስራ (Performance improvement)
            # UserSearch.objects.create(query=query, results_count=products.count())
        elif category_id:
            products = products.filter(category_id=category_id)
            
        products = products.order_by('-created_at')[:20]

    except Exception as db_err:
        heal_any_system_error('DATABASE', str(db_err), f"Home View Filter")
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
        raise Http404(_("Item not found"))
    return render(request, 'marketplace/product_detail.html', {'product': product})

# 4. እቃ መለጠፊያ (Anonymous Posting + 5 limit + ⚠️ Template Crash Protection)
def post_product(request):
    """ተጠቃሚዎች እስከ 5 እቃ ያለ ሎግኢን መለጠፍ ይችላሉ። ከ 5 በላይ ሲሆን ግን እንዲመዘገቡ ይጠየቃሉ።"""
    post_count = request.session.get('post_count', 0)
    
    if not request.user.is_authenticated and post_count >= 5:
        return redirect('signup')

    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        location = request.POST.get('location')
        image = request.FILES.get('image')

        try:
            # ዩኒክ እንግዳ አካውንት መፍጠር
            seller = request.user if request.user.is_authenticated else User.objects.create_user(
                username=f'guest_{uuid.uuid4().hex[:8]}', 
                password=uuid.uuid4().hex
            )

            product = Product.objects.create(
                seller=seller, title=title, description=description,
                price=price or 0, location=location, image=image
            )

            # AI ትንተና (ለትርጉም)
            ai_data = analyze_product_smartly(title, description, price)
            
            if ai_data:
                trans = ai_data.get('translations', {})
                ProductTranslation.objects.create(
                    product=product,
                    en=trans.get('en', f"{title} ||| {description}"),
                    am=trans.get('am', ''), om=trans.get('om', ''),
                    ar=trans.get('ar', ''), so=trans.get('so', ''),
                    ti=trans.get('ti', ''), fr=trans.get('fr', '')
                )
                cat, _ = Category.objects.get_or_create(name=ai_data.get('category', 'General'))
                product.category = cat
                product.ai_tags = ai_data.get('tags', [])
                product.save()
            else:
                # ⚠️ ራስ-ጥበቃ (Template Crash Protection)፦
                # የጀሚኒ ኮታ ካለቀ ባዶ የትርጉም ሰንጠረዥ በ fallback እንፈጥራለን። 
                # ይህ ካልተደረገ ዌብሳይቱ ላይ 'translations' የሚለው OneToOne ግንኙነት ባዶ ስለሚሆን ቴምፕሌቱ ይሰነጠቃል (500 Error)።
                combined_fallback = f"{title} ||| {description}"
                ProductTranslation.objects.create(
                    product=product,
                    en=combined_fallback,
                    am=combined_fallback, # ጀሚኒ እስኪከፈት በእንግሊዝኛ ያልፋል
                    om='', ar='', so='', ti='', fr=''
                )
                
                # ⚠️ የጀሚኒ ኮታ ካለቀ በወረፋ (Queue) መመዝገብ
                TranslationQueue.objects.create(
                    product=product, 
                    target_languages=['am', 'om', 'ar', 'so', 'ti', 'fr']
                )

            request.session['post_count'] = post_count + 1
            return redirect('post_success')
            
        except Exception as exec_err:
            heal_any_system_error('CODE_EXECUTION', str(exec_err), f"Post Product Crash")
            return HttpResponse(_("System busy, retry later."), status=500)
    
    return render(request, 'marketplace/post_product.html', {'post_count': post_count})

# 5. የስኬት ገጽ
def post_success(request):
    return render(request, 'marketplace/post_success.html')

# 6. ራስ-ሰር የዕድገት መቀስቀሻ (Core Evolution Engine)
def trigger_evolution(request):
    secret_key = "evolve-now-secret-123"
    
    if request.user.is_staff or secret_key in request.path:
        result = run_daily_market_analysis()
        heal_result = self_heal_failed_build()
        print(f"Self-Coder Status: {heal_result}")
        
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
                f"<h2>❌ AI Evolution Failed!</h2>"
                f"<p><b>Reason:</b> {result}</p>"
                f"<p><b>Self-Coder Status:</b> {heal_result}</p>"
                f"<p><a href='/'>Back to Home</a></p></div>", 
                status=400
            )
            
        return HttpResponse(f"Success: {result} | Coder: {heal_result}")
    else:
        raise Http404(_("Page not found"))

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
            return HttpResponse("<script>alert('Directive sent to AI successfully!'); window.location.href='/';</script>")
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
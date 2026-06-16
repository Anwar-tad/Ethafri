from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Product, Category, MarketTrend, UserSearch, SiteConfig, ProductTranslation
from .ai_utils import analyze_product_smartly
from .growth_agent import run_daily_market_analysis
from django.contrib.admin.views.decorators import staff_member_required
 # ይህ አድሚን ፓስወርድ እንዲጠይቅ ያደርጋል
# EthAfri/marketplace/views.py


# 1. የ AI ዲዛይን ቅንብርን ለሁሉም ገጾች የሚያቀርብ (Context Processor)
def theme_context(request):
    """
    AIው የወሰነውን የዌብሳይት ቀለም እና ባነር መረጃ ከዳታቤዝ አውጥቶ ለሁሉም ገጾች ያዳርሳል
    """
    config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
    return {'theme': config.value if config else {}}

# 2. ዋና ገጽ (እቃዎችን እና የ AI ውጤቶችን የሚያሳይ)
def home(request):
    query = request.GET.get('q')
    if query:
        products = Product.objects.filter(title__icontains=query)
        # ሰዎች የሚፈልጉትን ቃል AIው እንዲያጠናው እንመዘግባለን
        UserSearch.objects.create(query=query, results_count=products.count())
    else:
        products = Product.objects.filter(is_active=True).order_by('-created_at')

    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories
    })

# 3. እቃ መለጠፊያ (በ AI የሚታገዝ + Anonymous Posting Logic)
def post_product(request):
    """
    ተጠቃሚዎች እስከ 5 እቃ ያለ ሎግኢን መለጠፍ ይችላሉ። 
    ከ 5 በላይ ሲሆን ግን እንዲመዘገቡ ወደ signup ይመራቸዋል።
    """
    # በሴሽን (Session) ውስጥ ተጠቃሚው ስንት እቃ እንደለጠፈ እንቆጥራለን
    post_count = request.session.get('post_count', 0)

    if request.method == "POST":
        # ተጠቃሚው ካልገባ እና ከ 5 በላይ እቃ ከለጠፈ ወደ ሬጅስተር ይመራል
        if not request.user.is_authenticated and post_count >= 5:
            return redirect('signup')

        title = request.POST.get('title')
        description = request.POST.get('description')
        price = request.POST.get('price')
        location = request.POST.get('location')
        image = request.FILES.get('image')

        # ተጠቃሚው ካልገባ 'guest_user' በሚል ስም ይመዘገባል
        if request.user.is_authenticated:
            seller = request.user
        else:
            # የguest_user አካውንት ከሌለ ይፈጠራል
            seller, _ = User.objects.get_or_create(
                username='guest_user', 
                defaults={'email': 'guest@ethafri.com'}
            )

        # እቃውን መመዝገብ
        product = Product.objects.create(
            seller=seller,
            title=title,
            description=description,
            price=price if price else 0,
            location=location,
            image=image
        )

        # የ EthAfri AI እቃውን መርምሮ በራሱ ይመድባል
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
    
    return render(request, 'marketplace/post_product.html', {'post_count': post_count})

# 4. የስኬት ገጽ
def post_success(request):
    return render(request, 'marketplace/post_success.html')

# EthAfri/marketplace/views.py


def trigger_evolution(request):
    """
    ይህ ተግባር ያለ @staff_member_required መጻፍ አለበት።
    ደህንነቱ የሚጠበቀው በሚስጥራዊው የዩአርኤል ቁልፍ (Secret Key) ነው።
    """
    secret_key = "evolve-now-secret-123" # ይህ የእርስዎ ሚስጥራዊ ቁልፍ ነው
    
    # ቼክ፦ ሰውየው አድሚን ከሆነ ወይም ሊንኩ ሚስጥራዊውን ቁልፍ የያዘ ከሆነ ብቻ ይስራ
    if request.user.is_staff or secret_key in request.path:
        
        # 1. AIውን ያስነሳል
        result = run_daily_market_analysis()
        
        # 2. ውጤቱን ከዳታቤዝ ያወጣል
        try:
            latest_task = AISystemTask.objects.latest('created_at')
        except AISystemTask.DoesNotExist:
            latest_task = None

        # 3. ምላሽ አሰጣጥ፦
        if request.user.is_staff:
            # አንተ በተኑን ስትነካው ሪፖርቱን በሚያምር ገጽ ያሳይሃል
            return render(request, 'marketplace/evolution_result.html', {
                'status': result,
                'task': latest_task
            })
        else:
            # Cron-job (ሲስተሙ) ሲከፍተው አጭር ጽሁፍ ብቻ ይልካል
            return HttpResponse(f"Success: {result}")
            
    else:
        # ሚስጥራዊውን ቁልፍ የማያውቅ ተራ ሰው ሊከፍተው ቢሞክር "ገጹ የለም" ይለዋል
        raise Http404("ገጹ አልተገኘም")

# 6. የዕድገት ዴሽቦርድ (ለአስተዳዳሪው)
def admin_growth_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')
    trends = MarketTrend.objects.all().order_by('-last_updated')
    return render(request, 'marketplace/growth_dashboard.html', {'trends': trends})

# 7. አዲስ ተጠቃሚ መመዝገቢያ (Signup)
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

# 8. መግቢያ ገጽ (Login)
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

# 9. መውጫ (Logout)
def logout_view(request):
    logout(request)
    return redirect('home')
    

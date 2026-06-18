# EthAfri/marketplace/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse  # ⚠️ JsonResponse ተጨምሯል
from django.views.decorators.csrf import csrf_exempt  # ⚠️ csrf_exempt ተጨምሯል
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import get_language, gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch
import uuid

# አዲሶቹ የባክሎግ፣ የኢቮሉሽን ታሪክ እና የአድሚን ትዕዛዝ ሞዴሎች ተካተዋል
from .models import (
    Product, Category, MarketTrend, UserSearch, SiteConfig, 
    ProductTranslation, TranslationQueue,
    AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction
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
def home(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    try:
        # ⚠️ select_related በመጠቀም የዳታቤዝ ፍጥነትን ማሳደግ
        if query:
            products = Product.objects.select_related('translations', 'category').filter(title__icontains=query)
            UserSearch.objects.create(query=query, results_count=products.count())
        elif category_id:
            products = Product.objects.select_related('translations', 'category').filter(category_id=category_id, is_active=True).order_by('-created_at')
        else:
            products = Product.objects.select_related('translations', 'category').filter(is_active=True).order_by('-created_at')
    except Exception as db_err:
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
        raise Http404(_("Item not found"))
    return render(request, 'marketplace/product_detail.html', {'product': product})

# 4. እቃ መለጠፊያ (⚠️ ሕግ 1፦ መጀመሪያ በነባሪነት በእንግሊዝኛ ይመዘገባል)
def post_product(request):
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
            seller = request.user if request.user.is_authenticated else User.objects.create_user(
                username=f'guest_{uuid.uuid4().hex[:8]}', 
                password=uuid.uuid4().hex
            )

            # እቃው ወዲያውኑ ይመዘገባል (ምድቡ ለጊዜው General ይሆናል)
            cat, created = Category.objects.get_or_create(name='General')
            product = Product.objects.create(
                seller=seller, category=cat, title=title, description=description,
                price=price if price else 0, location=location, image=image,
                market_value_status='Unknown', is_active=True
            )

            # የትርጉም አጽም መፍጠር (Template crash ለመከላከል)
            combined_fallback = f"{title} ||| {description}"
            ProductTranslation.objects.create(
                product=product, en=combined_fallback, am=combined_fallback
            )

            # የ AI ትንተናውንና የብዙ ቋንቋ ትርጉሙን በጀርባ ለወረፋ መመዝገብ
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

# 6. የዕድገት ዴሽቦርድ (የባለቤት ልዕለ-ዕዝ ማዕከል)
# EthAfri/marketplace/views.py (የተስተካከለው የፈንክሽን ክፍል ብቻ)

def admin_growth_dashboard(request):
    if not request.user.is_staff:
        return redirect('home')
        
    # === የአድሚን የቁጥጥር ተግባራት (POST) ===
    if request.method == "POST":
        action = request.POST.get("action")
        
        # ሀ. የ AI የልማት ዑደትን በእጅ ለመቀስቀስ
        if action == "trigger_agent":
            result = run_daily_market_analysis()
            messages.info(request, f"የኤጀንት አፈጻጸም ውጤት፦ {result}")
            return redirect("growth_dashboard")  # ⚠️ ወደ 'growth_dashboard' ተስተካክሏል
            
        # ለ. ለተወሰነ ስራ ወይም ለአጠቃላይ ሲስተሙ ቀጥተኛ የባለቤት መመሪያ (Override) ለመስጠት
        elif action == "create_override":
            instruction_text = request.POST.get("instruction")
            task_id = request.POST.get("task_id")
            priority_override = request.POST.get("priority_override")
            
            task = None
            if task_id:
                task = get_object_or_404(AIProjectBacklog, id=task_id)
            
            if instruction_text:
                AdminOverrideInstruction.objects.create(
                    backlog_task=task,
                    instruction=instruction_text,
                    priority_override=priority_override if priority_override in ['Critical', 'High', 'Medium', 'Low'] else None
                )
                
                # መመሪያ ከተሰጠው ስራውን በድጋሚ እንዲሠራ 'Pending' ማድረግ
                if task:
                    task.status = 'Pending'
                    if priority_override:
                        task.priority = priority_override
                    task.save()
                    
                messages.success(request, "የባለቤት መመሪያህ ተመዝግቧል። ኤጀንቱ በቀጣይ ዑደት ላይ ተግባራዊ ያደርገዋል።")
            else:
                messages.error(request, "እባክህ መመሪያውን ባዶ አታድርገው።")
            return redirect("growth_dashboard")  # ⚠️ ወደ 'growth_dashboard' ተስተካክሏል
            
        # ሐ. የባክሎግ ስራዎችን ሁኔታ ወይም ቅድሚያ በቀጥታ ለመቀየር
        elif action == "update_task":
            task_id = request.POST.get("task_id")
            new_priority = request.POST.get("priority")
            new_status = request.POST.get("status")
            
            task = get_object_or_404(AIProjectBacklog, id=task_id)
            if new_priority:
                task.priority = new_priority
            if new_status:
                task.status = new_status
            task.save()
            messages.success(request, f"ስራ '{task.task_name}' በተሳካ ሁኔታ ተሻሽሏል።")
            return redirect("growth_dashboard")  # ⚠️ ወደ 'growth_dashboard' ተስተካክሏል

    # === ለገጹ የሚያስፈልጉ መረጃዎችን መሰብሰብ (GET) ===
    trends = MarketTrend.objects.all().order_by('-last_updated')
    tasks = AISystemTask.objects.all().order_by('-created_at')
    
    # አዲሶቹ የዕዝ ማዕከል መረጃዎች
    backlog_tasks = AIProjectBacklog.objects.all().order_by('-priority', '-created_at')
    evolution_logs = AIEvolutionLog.objects.all().order_by('-created_at')[:20]
    active_overrides = AdminOverrideInstruction.objects.filter(is_processed=False).order_by('-created_at')
    
    # የኤጀንቱን የመቆለፊያ ሁኔታ መፈተሽ
    lock = SiteConfig.objects.filter(key="EVOLUTION_LOCK").first()
    status_info = lock.value if lock else {"status": "idle", "last_run": "መረጃ የለም"}

    return render(request, 'marketplace/growth_dashboard.html', {
        'trends': trends,
        'tasks': tasks,
        'backlog_tasks': backlog_tasks,
        'evolution_logs': evolution_logs,
        'active_overrides': active_overrides,
        'status_info': status_info,
    })

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
    

# ⚠️ ከ cron-job.org የሚመጣን ውጫዊ ጥሪ ተቀብሎ ሞተሩን የሚያስነሳው ዋናው በር
@csrf_exempt
def trigger_autonomous_evolution(request):
    # ከደህንነት አንፃር የምስጢር ቁልፍ ማረጋገጫ ማከል ትችላለህ
    try:
        # አዲሱን አውቶኖመስ የአሰሳና የኮዲንግ ሞተር መቀስቀስ
        result_message = run_daily_market_analysis()
        
        # የሴፍቲኔት ክር እንዲያውቀው የፒንግ ሰዓቱን በቋሚነት መመዝገብ
        SiteConfig.objects.update_or_create(
            key="LAST_SUCCESSFUL_CRON_PING", 
            defaults={'value': {'time': timezone.now().isoformat()}}
        )
        
        return JsonResponse({"status": "success", "message": result_message}, status=200)
    except Exception as e:
        return JsonResponse({"status": "failed", "error": str(e)}, status=500)

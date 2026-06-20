# EthAfri/marketplace/views.py

import logging
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.utils.translation import get_language, gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch, Count, Sum, Q

# ሎገሩን በሞጁል ደረጃ ማዋቀር
logger = logging.getLogger(__name__)

# አዲሶቹን ሞዴሎች ማስመጣት
from .models import (
    Product, Category, UserSearch, ProductTranslation, 
    SiteConfig, MarketTrend, AISystemTask, OwnerDirective, SelfHealingLog,
    AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction, TranslationQueue,
    SiteRegistry, CustomerAcquisitionLog, MarketingCampaign, SellerProfile, 
    NotificationQueue, AgentErrorLog
)
from .ai_utils import analyze_product_smartly
from .growth_agent import run_daily_market_analysis, run_daily_market_analysis_for_site # ⚠️ የትክክለኛው ፈንክሽን ስም ተተክቷል [1]
from .self_coder import self_heal_failed_build 
from .self_doctor import heal_any_system_error, discover_and_heal_ui_design

# 🛡️ 1. የ 'discover_new_sites' የደህንነት ማስሞጫ ቼክ (Import Error Protection) [1]
try:
    from .growth_agent import discover_new_sites
except ImportError:
    # በ growth_agent.py ውስጥ ፈንክሽኑ ገና ሙሉ በሙሉ ካልተጫነ ሰርቨሩ እንዳይቋረጥ መከላከያ ፎልባክ
    def discover_new_sites():
        logger.warning("⚠️ 'discover_new_sites' is not fully implemented in growth_agent yet. Using fallback empty list.")
        return []


# ============================================================
# 1. የ AI ዲዛይን ቅንብርን ለሁሉም ገጾች የሚያቀርብ (Context Processor)
# ============================================================
def theme_context(request):
    config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
    return {'theme': config.value if config else {}}


# ============================================================
# 2. ዋና ገጽ (ማጣሪያ የተገጠመለት - N+1 Query Fix)
# ============================================================
def home(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    try:
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


# ============================================================
# 3. የእቃ ዝርዝር ገጽ
# ============================================================
def product_detail(request, pk):
    try:
        product = Product.objects.get(pk=pk)
    except Product.DoesNotExist:
        raise Http404(_("Item not found"))
    return render(request, 'marketplace/product_detail.html', {'product': product})


# ============================================================
# 4. እቃ መለጠፊያ (Anonymous Posting + 5 limit + Template Crash Protection)
# ============================================================
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

            cat, created = Category.objects.get_or_create(name='General')
            product = Product.objects.create(
                seller=seller, category=cat, title=title, description=description,
                price=price if price else 0, location=location, image=image,
                market_value_status='Unknown', is_active=True
            )

            combined_fallback = f"{title} ||| {description}"
            ProductTranslation.objects.create(
                product=product, en=combined_fallback, am=combined_fallback
            )

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


# ============================================================
# 5. የስኬት ገጽ
# ============================================================
def post_success(request):
    return render(request, 'marketplace/post_success.html')


# ============================================================
# ⚙️ 6. ራስ-ሰር የዕድገት መቀስቀሻ (Core Evolution Engine)
# ============================================================
@staff_member_required
def trigger_evolution(request):
    """
    አድሚኑ የ 5 ደቂቃ የክሮን ጊዜ ሳይጠብቅ የኤአይ የዕድገት ዑደትን በቀጥታ በእጅ የሚቀሰቅስበት ዋናው ቪው
    """
    result = "⚠️ የኤጀንት ዑደት አልተጀመረም"
    heal_result = "⚠️ Self-Coder አልተሄደም"
    
    try:
        result = run_daily_market_analysis()
    except Exception as e:
        error_msg = str(e)[:200]
        logger.error(f"❌ run_daily_market_analysis() ስህተት: {error_msg}")
        result = f"❌ የኤጀንት ዑደት ስህተት: {error_msg}"
        try:
            SelfHealingLog.objects.create(
                error_message=error_msg,
                source='trigger_evolution',
                resolved=False
            )
        except Exception:
            pass
    
    try:
        heal_result = self_heal_failed_build()
    except Exception as e:
        error_msg = str(e)[:200]
        logger.error(f"❌ self_heal_failed_build() ስህተት: {error_msg}")
        heal_result = f"❌ Self-Coder ስህተት: {error_msg}"
    
    print(f"Self-Coder Status: {heal_result}")
    
    try:
        config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
        current_color = '#1a2a6c'
        if config and config.value and isinstance(config.value, dict):
            current_color = config.value.get('theme_color', '#1a2a6c')
        discover_and_heal_ui_design(current_color, trend_context="Modern African E-Commerce Trend")
    except Exception as e:
        logger.error(f"❌ discover_and_heal_ui_design() ስህተት: {e}")

    SUCCESS_PREFIXES = ("✅", "🎉", "🧠", "💤", "⚠️")

    if result.startswith(SUCCESS_PREFIXES):
        try:
            latest_task = AIProjectBacklog.objects.latest('created_at')
        except AIProjectBacklog.DoesNotExist:
            try:
                latest_task = AISystemTask.objects.latest('created_at')
            except AISystemTask.DoesNotExist:
                latest_task = None

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


# ============================================================
# 🌐 7. Multi-Site Dashboard (አዲስ)
# ============================================================
@staff_member_required
def sites_dashboard(request):
    """
    ሁሉንም የተመዘገቡ ጣቢያዎች በአንድ ላይ የሚያሳይ ዳሽቦርድ
    """
    sites = SiteRegistry.objects.all().order_by('name')
    
    site_stats = []
    total_revenue = 0
    total_visitors = 0
    total_sellers = 0
    total_products = 0
    
    for site in sites:
        pending_tasks = AIProjectBacklog.objects.filter(site=site, status='Pending').count()
        running_tasks = AIProjectBacklog.objects.filter(site=site, status='Running').count()
        completed_tasks = AIProjectBacklog.objects.filter(site=site, status='Completed').count()
        recent_errors = AgentErrorLog.objects.filter(site=site, resolved=False).count()
        
        site_stats.append({
            'site': site,
            'pending_tasks': pending_tasks,
            'running_tasks': running_tasks,
            'completed_tasks': completed_tasks,
            'recent_errors': recent_errors,
            'growth_level_display': dict(SiteRegistry._meta.get_field('growth_level').choices).get(site.growth_level, 'Unknown')
        })
        
        total_revenue += site.monthly_revenue or 0
        total_visitors += site.monthly_visitors or 0
        total_sellers += site.total_sellers or 0
        total_products += site.total_products or 0
    
    context = {
        'sites': sites,
        'site_stats': site_stats,
        'total_sites': sites.count(),
        'total_revenue': total_revenue,
        'total_visitors': total_visitors,
        'total_sellers': total_sellers,
        'total_products': total_products,
    }
    
    return render(request, 'marketplace/sites_dashboard.html', context)


# ============================================================
# 🌐 8. Site Detail Page (አዲስ)
# ============================================================
@staff_member_required
def site_detail(request, site_id):
    """
    የአንድ የተወሰነ ጣቢያ ዝርዝር መረጃ የሚያሳይ ገጽ
    """
    site = get_object_or_404(SiteRegistry, id=site_id)
    
    backlog_tasks = AIProjectBacklog.objects.filter(site=site).order_by('-priority', '-created_at')
    evolution_logs = AIEvolutionLog.objects.filter(site=site).order_by('-created_at')[:50]
    error_logs = AgentErrorLog.objects.filter(site=site).order_by('-created_at')[:20]
    marketing_campaigns = MarketingCampaign.objects.filter(site=site).order_by('-created_at')[:10]
    acquisition_logs = CustomerAcquisitionLog.objects.filter(site=site).order_by('-created_at')[:20]
    
    context = {
        'site': site,
        'backlog_tasks': backlog_tasks,
        'evolution_logs': evolution_logs,
        'error_logs': error_logs,
        'marketing_campaigns': marketing_campaigns,
        'acquisition_logs': acquisition_logs,
        'growth_level_display': dict(SiteRegistry._meta.get_field('growth_level').choices).get(site.growth_level, 'Unknown')
    }
    
    return render(request, 'marketplace/site_detail.html', context)


# ============================================================
# 📊 9. የዕድገት ዴሽቦርድ (የተሻሻለ - Multi-Site)
# ============================================================
@staff_member_required
def admin_growth_dashboard(request):
    if request.method == "POST":
        action = request.POST.get("action")
        site_id = request.POST.get("site_id")
        
        if action == "trigger_agent":
            try:
                if site_id:
                    # ⚠️ ማስተካከያ፦ ትክክለኛው የነጠላ ድረ-ገጽ መቀስቀሻ ፈንክሽን ስም እዚህ ተተክሏል [1]
                    site = get_object_or_404(SiteRegistry, id=site_id)
                    result = run_daily_market_analysis_for_site(site)
                else:
                    result = run_daily_market_analysis()
                messages.info(request, f"የኤጀንት አፈጻጸም ውጤት፦ {result[:200]}")
            except Exception as e:
                messages.error(request, f"ስህተት፦ {str(e)[:100]}")
            return redirect("growth_dashboard")
            
        elif action == "create_override":
            instruction_text = request.POST.get("instruction")
            task_id = request.POST.get("task_id")
            priority_override = request.POST.get("priority_override")
            site_id = request.POST.get("site_id")
            
            task = None
            if task_id:
                task = get_object_or_404(AIProjectBacklog, id=task_id)
            
            site = None
            if site_id:
                site = get_object_or_404(SiteRegistry, id=site_id)
            
            if instruction_text:
                AdminOverrideInstruction.objects.create(
                    backlog_task=task,
                    site=site,
                    instruction=instruction_text,
                    priority_override=priority_override if priority_override in ['Critical', 'High', 'Medium', 'Low'] else None
                )
                
                if task:
                    task.status = 'Pending'
                    if priority_override:
                        task.priority = priority_override
                    task.save()
                    
                messages.success(request, "የባለቤት መመሪያህ ተመዝግቧል።")
            else:
                messages.error(request, "እባክህ መመሪያውን ባዶ አታድርገው።")
            return redirect("growth_dashboard")
            
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
            messages.success(request, f"ስራ '{task.task_name}' ተሻሽሏል።")
            return redirect("growth_dashboard")
        
        elif action == "discover_sites":
            new_sites = discover_new_sites()
            if new_sites:
                messages.success(request, f"🆕 {len(new_sites)} አዲስ ጣቢያዎች ተገኝተዋል!")
            else:
                messages.info(request, "ምንም አዲስ ጣቢያ አልተገኘም።")
            return redirect("growth_dashboard")

    # ለገጹ የሚያስፈልጉ መረጃዎችን መሰብሰብ (GET)
    trends = MarketTrend.objects.all().order_by('-last_updated')
    tasks = AISystemTask.objects.all().order_by('-created_at')
    
    sites = SiteRegistry.objects.filter(is_active=True)
    
    backlog_by_site = {}
    for site in sites:
        backlog_by_site[site.id] = AIProjectBacklog.objects.filter(
            site=site
        ).order_by('-priority', '-created_at')[:20]
    
    backlog_tasks = AIProjectBacklog.objects.all().order_by('-priority', '-created_at')[:50]
    evolution_logs = AIEvolutionLog.objects.all().order_by('-created_at')[:30]
    active_overrides = AdminOverrideInstruction.objects.filter(is_processed=False).order_by('-created_at')
    
    lock = SiteConfig.objects.filter(key="EVOLUTION_LOCK").first()
    status_info = lock.value if lock else {"status": "idle", "last_run": "መረጃ የለም"}
    
    total_sites = sites.count()
    total_pending = AIProjectBacklog.objects.filter(status='Pending').count()
    total_running = AIProjectBacklog.objects.filter(status='Running').count()
    total_completed = AIProjectBacklog.objects.filter(status='Completed').count()
    total_errors = AgentErrorLog.objects.filter(resolved=False).count()
    
    total_revenue = sum(site.monthly_revenue or 0 for site in sites)
    total_visitors = sum(site.monthly_visitors or 0 for site in sites)

    return render(request, 'marketplace/growth_dashboard.html', {
        'trends': trends,
        'tasks': tasks,
        'backlog_tasks': backlog_tasks,
        'backlog_by_site': backlog_by_site,
        'evolution_logs': evolution_logs,
        'active_overrides': active_overrides,
        'status_info': status_info,
        'sites': sites,
        'total_sites': total_sites,
        'total_pending': total_pending,
        'total_running': total_running,
        'total_completed': total_completed,
        'total_errors': total_errors,
        'total_revenue': total_revenue,
        'total_visitors': total_visitors,
    })


# ============================================================
# 📱 10. የማርኬቲንግ ዳሽቦርድ (አዲስ)
# ============================================================
@staff_member_required
def marketing_dashboard(request):
    """
    ሁሉንም የግብይት እንቅስቃሴዎች የሚያሳይ ዳሽቦርድ [1]
    """
    sites = SiteRegistry.objects.filter(is_active=True)
    campaigns = MarketingCampaign.objects.all().order_by('-created_at')[:50]
    notifications = NotificationQueue.objects.filter(is_sent=False).order_by('created_at')[:50]
    acquisition_logs = CustomerAcquisitionLog.objects.all().order_by('-created_at')[:50]
    
    campaign_stats = {
        'total': campaigns.count(),
        'running': campaigns.filter(status='running').count(),
        'completed': campaigns.filter(status='completed').count(),
        'scheduled': campaigns.filter(status='scheduled').count(),
        'total_sent': sum(c.total_sent for c in campaigns),
        'total_opened': sum(c.total_opened for c in campaigns),
        'total_converted': sum(c.total_converted for c in campaigns),
    }
    
    acquisition_stats = {
        'total': acquisition_logs.count(),
        'email': acquisition_logs.filter(channel='email').count(),
        'sms': acquisition_logs.filter(channel='sms').count(),
        'social': acquisition_logs.filter(channel='social').count(),
        'converted': acquisition_logs.filter(converted_to_seller=True).count(),
    }
    
    context = {
        'sites': sites,
        'campaigns': campaigns,
        'notifications': notifications,
        'acquisition_logs': acquisition_logs,
        'campaign_stats': campaign_stats,
        'acquisition_stats': acquisition_stats,
    }
    
    return render(request, 'marketplace/marketing_dashboard.html', context)


# ============================================================
# 11. የባለቤት መመሪያ ገጽ
# ============================================================
@staff_member_required
def owner_directive_view(request):
    if request.method == "POST":
        instruction = request.POST.get('instruction')
        if instruction:
            OwnerDirective.objects.all().update(is_active=False)
            OwnerDirective.objects.create(instruction=instruction, is_active=True)
            return HttpResponse("<script>alert('Directive sent to AI successfully!'); window.location.href='/';</script>")
    return render(request, 'marketplace/owner_directive.html')


# ============================================================
# 12. የተጠቃሚ ማንነት ማረጋገጫ (Authentication Views)
# ============================================================
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
    

# ============================================================
# 13. ውጫዊ መቀስቀሻ (External Cron Webhook Gateway)
# ============================================================
@csrf_exempt
def trigger_autonomous_evolution(request):
    logger.info("🌐 External Cron ping received! Starting evolutionary cycle...")
    try:
        result_message = run_daily_market_analysis()
        
        SiteConfig.objects.update_or_create(
            key="LAST_SUCCESSFUL_CRON_PING", 
            defaults={'value': {'time': timezone.now().isoformat()}}
        )
        
        return JsonResponse({"status": "success", "message": result_message}, status=200)
    except Exception as e:
        logger.error(f"❌ External Cron Trigger Error: {e}")
        return JsonResponse({"status": "failed", "error": str(e)}, status=500)
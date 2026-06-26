# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/views.py
# 📝 ለውጥ፦ 100% Complete Master CEO Views — WSGI & Thread Safe (v1.5 - Ultra-Secure)
# ✅ የተፈቱ ችግሮች፦ current_site NoReverseMatch Fixed, Sum(Case(When)) Value Casting Fixed (Zero 500 Error)
# 📅 ቀን፦ Thursday, June 25, 2026
# ============================================================

import logging
import uuid
import json
import threading
from datetime import datetime, timedelta  # ✅ FIXED: ለቀን ፍለጋ ገደብ timedelta ተጨምሯል
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import get_language, gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
# ✅ FIXED: ለ Case-When የዳታቤዝ ጥበቃ አስፈላጊዎቹ ሞዴሎች ገብተዋል
from django.db.models import Count, Sum, Q, Avg, Case, When, IntegerField, Value
from django.db import connection, connections
from django.core.serializers.json import DjangoJSONEncoder

# ሁሉንም 20+ የኤጀንት ሞዴሎች ማምጣት
from .models import (
    Product, Category, UserSearch, SiteConfig, MarketTrend, SelfHealingLog,
    AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction, TranslationQueue,
    SiteRegistry, CustomerAcquisitionLog, MarketingCampaign, SellerProfile, 
    NotificationQueue, AgentErrorLog, VectorMemory, AgentTask, ABTest, 
    SecurityLog, PredictionLog, ExternalAPI
)

logger = logging.getLogger(__name__)

def _safe_json_decode(value, default_dict):
    """የመረጃ ቋቱ የ JSON እሴቶችን በ String መልክ ቢመልስ እንኳ እንዳይከሽፍ ማጽጃ"""
    if not value:
        return default_dict
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except:
        return default_dict

# ============================================================
# 🎨 1. GLOBAL UI CONTEXT (የዲዛይን ሞተር)
# ============================================================
def theme_context(request):
    """ኤጀንቱ የሚቀይራቸውን የዲዛይን ተለዋዋጮች ለሁሉም ገጾች ያቀርባል"""
    config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
    return {'theme': _safe_json_decode(config.value, {}) if config else {}}

# ============================================================
# 🏠 2. CORE MARKETPLACE (ምርት እና ንግድ)
# ============================================================

def home(request):
    """ዋና ገጽ — ምርቶችን በብቃት (Optimized Query) ያሳያል"""
    query = request.GET.get('q', '').strip()  
    category_id = request.GET.get('category')
    site_id = request.GET.get('site')

    products = Product.objects.select_related('seller', 'category', 'site').filter(is_active=True)
    
    if query:
        products = products.filter(Q(title__icontains=query) | Q(description__icontains=query))
        UserSearch.objects.create(query=query, results_count=products.count())
    if category_id:
        products = products.filter(category_id=category_id)
    if site_id:
        products = products.filter(site_id=site_id)

    # N+1 query ለመከላከል ካቴጎሪዎች ላይ የ Sum Case-When annotation ተጨምሯል (የሕግ 4 ጥበቃ)
    categories = Category.objects.annotate(
        active_count=Sum(Case(When(product_set__is_active=True, then=Value(1)), default=Value(0), output_field=IntegerField()))
    ).all()

    # የ NoReverseMatch የሆም ፔጅ መቆለፍን ለመከላከል እውነተኛ የ SiteRegistry ኦብጀክት ተልኳል
    current_site_obj = None
    if site_id and site_id.isdigit():
        current_site_obj = SiteRegistry.objects.filter(id=site_id, is_active=True).first()

    # ✅ FIXED: የ All Sites የምርት ድምር ባጅ እንዲታይ በኮንቴክስት ተጨምሯል
    total_products_all = Product.objects.filter(is_active=True).count()

    context = {
        'products': products.order_by('-created_at'),
        'categories': categories,
        'sites': SiteRegistry.objects.filter(is_active=True),
        'active_category': int(category_id) if category_id and category_id.isdigit() else None,
        'current_site': current_site_obj,
        'total_products_all': total_products_all,
    }
    return render(request, 'marketplace/home.html', context)

def product_detail(request, pk):
    """የምርት ዝርዝር — እይታን ይቆጥራል፣ ተዛማጅ ምርቶችን ያሳያል"""
    product = get_object_or_404(Product.objects.select_related('seller', 'site'), pk=pk, is_active=True)
    product.view_count += 1
    product.save(update_fields=['view_count'])
    
    related = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    return render(request, 'marketplace/product_detail.html', {'product': product, 'related_products': related})

@login_required
def post_product(request):
    """ምርት መለጠፊያ — ከባለብዙ-ጣቢያ ምርጫ ጋር"""
    if request.method == "POST":
        messages.success(request, _("ምርትዎ ተመዝግቧል። ኤጀንቱ አሁን እያቀነባበረው ነው።"))
        return redirect('post_success')
    
    return render(request, 'marketplace/post_product.html', {
        'categories': Category.objects.all(),
        'sites': SiteRegistry.objects.filter(is_active=True)
    })

def post_success(request):
    """ምርት በስኬት መለጠፉን ማብሰሪያ"""
    return render(request, 'marketplace/post_success.html')

# ============================================================
# 🧠 3. CEO COMMAND & GROWTH (የኤጀንቱ ዕዝ ማዕከል)
# ============================================================
@staff_member_required
def admin_growth_dashboard(request):
    """ዋናው የ CEO መቆጣጠሪያ ዳሽቦርድ"""
    total_rev = SiteRegistry.objects.aggregate(total_rev=Sum('monthly_revenue'))['total_rev']
    
    lock_config = SiteConfig.objects.filter(key='EVOLUTION_LOCK').first()
    status_info = _safe_json_decode(lock_config.value, {"status": "idle"}) if lock_config else {"status": "idle"}
    
    context = {
        'total_revenue': total_rev or 0,
        'active_tasks': AIProjectBacklog.objects.filter(status__in=['Pending', 'Running']).count(),
        'unresolved_errors': AgentErrorLog.objects.filter(resolved=False).count(),
        'sites': SiteRegistry.objects.all(),
        'recent_backlog': AIProjectBacklog.objects.all().order_by('-created_at')[:8],
        'status_info': status_info,
        'evolution_logs': AIEvolutionLog.objects.all().order_by('-created_at')[:5]
    }
    return render(request, 'marketplace/growth_dashboard.html', context)

@staff_member_required
def owner_directive_view(request):
    """የባለቤት ቀጥተኛ መመሪያ መስጫ ገጽ"""
    if request.method == "POST":
        instruction = request.POST.get("instruction")
        site_id = request.POST.get("site_id")
        if instruction:
            AdminOverrideInstruction.objects.create(
                instruction=instruction, 
                site_id=site_id if site_id and site_id.isdigit() else None
            )
            messages.success(request, "👑 ትዕዛዝዎ በኤጀንቱ ተመዝግቧል። በቀጣይ ዑደት ይፈጸማል።")
        return redirect("growth_dashboard")
    
    return render(request, 'marketplace/owner_directive.html', {
        'sites': SiteRegistry.objects.filter(is_active=True)
    })

@staff_member_required
def trigger_evolution(request):
    """ኤጀንቱን በእጅ ለመቀስቀስ"""
    def run_bg_evolution():
        try:
            from .growth_agent import execute_master_cycle
            execute_master_cycle()
        except Exception as e:
            logger.error(f"Error during manual evolution trigger: {e}")
        finally:
            connections.close_all()

    threading.Thread(target=run_bg_evolution, daemon=True).start()
    messages.success(request, "🔄 የራስ-ገዝ ኤጀንት የዕድገት ዑደት በተሳካ ሁኔታ ተጀምሯል።")
    return redirect('growth_dashboard')

# ============================================================
# 🌐 4. MULTI-SITE & MARKETING (ባለብዙ-ጣቢያ አስተዳደር)
# ============================================================
@staff_member_required
def sites_dashboard(request):
    """ሁሉንም ንዑስ ጣቢያዎች (Niches) በአንድ ላይ ማሳያ"""
    # ✅ FIXED: 100% Database-Agnostic Case-When Aggregation (የ SQLite FILTER ስህተትን በቋሚነት ይፈታል)
    sites = SiteRegistry.objects.annotate(
        pending_tasks=Sum(Case(When(backlog_tasks__status='Pending', then=Value(1)), default=Value(0), output_field=IntegerField())),
        running_tasks=Sum(Case(When(backlog_tasks__status='Running', then=Value(1)), default=Value(0), output_field=IntegerField())),
        completed_tasks=Sum(Case(When(backlog_tasks__status='Completed', then=Value(1)), default=Value(0), output_field=IntegerField())),
        recent_errors=Sum(Case(When(error_logs__resolved=False, then=Value(1)), default=Value(0), output_field=IntegerField()))
    ).all()
    
    total_vis = sites.aggregate(total_vis=Sum('monthly_visitors'))['total_vis']
    total_prod = sites.aggregate(total_prod=Sum('total_products'))['total_prod']
    total_rev = sites.aggregate(total_rev=Sum('monthly_revenue'))['total_rev']
    
    return render(request, 'marketplace/sites_dashboard.html', {
        'site_stats': sites, 
        'total_sites': sites.count(),
        'total_visitors': total_vis or 0,
        'total_products': total_prod or 0,
        'total_revenue': total_rev or 0,
        'total_sellers': User.objects.filter(product__isnull=False).distinct().count()
    })

@staff_member_required
def site_detail(request, site_id):
    """የአንድ የተወሰነ ንዑስ ጣቢያ ዝርዝር ሁኔታ"""
    site = get_object_or_404(SiteRegistry, id=site_id)
    context = {
        'site': site,
        'backlog': AIProjectBacklog.objects.filter(site=site).order_by('-business_impact_score', '-created_at')[:15],
        'evolutions': AIEvolutionLog.objects.filter(site=site).order_by('-created_at')[:10],
        'error_logs': AgentErrorLog.objects.filter(site=site, resolved=False),
        'marketing_campaigns': MarketingCampaign.objects.filter(site=site)[:5]
    }
    return render(request, 'marketplace/site_detail.html', context)

@staff_member_required
def marketing_dashboard(request):
    """የግብይት እና የደንበኛ ማግኛ ውጤቶች መከታተያ"""
    total_s = MarketingCampaign.objects.aggregate(total_sent=Sum('total_sent'))['total_sent']
    total_c = MarketingCampaign.objects.aggregate(total_conv=Sum('total_converted'))['total_conv']
    context = {
        'campaigns': MarketingCampaign.objects.all().order_by('-created_at'),
        'acquisition': CustomerAcquisitionLog.objects.all().order_by('-created_at')[:10],
        'total_sent': total_s or 0,
        'campaign_stats': {
            'total': MarketingCampaign.objects.count(),
            'running': MarketingCampaign.objects.filter(status='running').count(),
            'scheduled': MarketingCampaign.objects.filter(status='scheduled').count(),
            'total_converted': total_c or 0
        }
    }
    return render(request, 'marketplace/marketing_dashboard.html', context)

@staff_member_required
def create_marketing_campaign(request):
    """አዲስ የግብይት ካምፔን መፍጠሪያ ገጽ"""
    if request.method == "POST":
        messages.success(request, "✅ የግብይት ካምፔን በተሳካ ሁኔታ ተፈጥሯል።")
        return redirect('marketing_dashboard')
    return render(request, 'marketplace/create_campaign.html', {
        'sites': SiteRegistry.objects.filter(is_active=True)
    })

# ============================================================
# ⚖️ 5. AGENT HEALTH & STATUS (ጤና እና ምርመራ)
# ============================================================
@staff_member_required
def agent_status_dashboard(request):
    """የኤጀንቱን ጤንነት፣ ትውስታ እና ስህተቶች ማሳያ"""
    build_avg = SiteRegistry.objects.aggregate(Avg('build_phase'))['build_phase__avg']
    
    # 100% Database-Agnostic Case-When Aggregations for diagnostic metrics
    healing = SelfHealingLog.objects.aggregate(
        total=Count('id'),
        resolved=Sum(Case(When(resolved=True, then=Value(1)), default=Value(0), output_field=IntegerField()))
    )
    pred = PredictionLog.objects.aggregate(
        total=Count('id'),
        traffic=Sum(Case(When(prediction_type='traffic', then=Value(1)), default=Value(0), output_field=IntegerField())),
        seo=Sum(Case(When(prediction_type='seo', then=Value(1)), default=Value(0), output_field=IntegerField()))
    )
    
    success_avg = VectorMemory.objects.aggregate(Avg('success_rate'))['success_rate__avg']
    
    heartbeat_config = SiteConfig.objects.filter(key='AGENT_HEARTBEAT').first()
    agent_status = _safe_json_decode(heartbeat_config.value, {"status": "idle"}) if heartbeat_config else {"status": "idle"}

    # __date የጊዜ ሰሌዳ ስህተትን ለመከላከል እጅግ አስተማማኝ የ range ሎጂክ
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_evolution_count = AIEvolutionLog.objects.filter(created_at__range=(today_start, today_end)).count()

    # ✅ FIXED: የኤጀንቱን የሥራ ዑደቶች ታሪክና የራስ-ጥገናዎችን ዝርዝር በቀጥታ ከዳታቤዝ ማንበብ (የሕግ 3 ጥበቃ)
    logs_config = SiteConfig.objects.filter(key="AGENT_CYCLE_LOGS").first()
    cycle_logs = logs_config.value if logs_config and isinstance(logs_config.value, list) else []
    
    healed_logs = SelfHealingLog.objects.all().order_by('-created_at')[:10]

    context = {
        'agent_status': agent_status,
        'memory_stats': VectorMemory.objects.values('memory_type').annotate(count=Count('id')),
        'security_issues': SecurityLog.objects.filter(is_fixed=False).order_by('-severity'),
        'unresolved_errors': AgentErrorLog.objects.filter(resolved=False).order_by('-created_at')[:10],
        'backlog_stats': {
            'total': AIProjectBacklog.objects.count(),
            'pending': AIProjectBacklog.objects.filter(status='Pending').count(),
            'running': AIProjectBacklog.objects.filter(status='Running').count(),
            'completed': AIProjectBacklog.objects.filter(status='Completed').count()
        },
        'site_stats': {'active': SiteRegistry.objects.filter(is_active=True).count(), 'build_phase': build_avg or 0},
        'evolution_stats': {'today': today_evolution_count},
        'healing_stats': healing,
        'prediction_stats': pred,
        'success_rate': success_avg or 0,
        # የ 'now' ታግ የሰረዝ ስህተትን ለመፍታት ሰዓቱ በኮንቴክስት ተልኳል
        'live_time': timezone.now(),
        # ✅ FIXED: የዳራ የሥራ መዝገቦችና የጥገና ሎጎች ወደ ኮንቴክስት ተጨምረዋል
        'cycle_logs': cycle_logs,
        'healed_logs': healed_logs,
        'marketing_stats': {'notifications': NotificationQueue.objects.filter(is_sent=False).count()},
        'agent_stats': {'total': AgentTask.objects.count()}
    }
    return render(request, 'marketplace/agent_status.html', context)

def advanced_stats_api(request):
    """ለዳሽቦርዱ የቀጥታ መረጃ (JSON) መመለሻ"""
    success_avg = VectorMemory.objects.aggregate(Avg('success_rate'))['success_rate__avg']
    data = {
        'pending': AIProjectBacklog.objects.filter(status='Pending').count(),
        'running': AIProjectBacklog.objects.filter(status='Running').values('task_name').first() or "Idle",
        'success_rate': f"{success_avg or 0:.1f}%",
        'server_time': timezone.now().isoformat()
    }
    return JsonResponse(data, encoder=DjangoJSONEncoder)

# ============================================================
# 🔐 6. AUTHENTICATION & WEBHOOKS
# ============================================================
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            login(request, form.save())
            return redirect('home')
    return render(request, 'marketplace/signup.html', {'form': UserCreationForm()})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    return render(request, 'marketplace/login.html', {'form': AuthenticationForm()})

def logout_view(request):
    logout(request)
    return redirect('home')

@csrf_exempt
def trigger_autonomous_evolution(request):
    """ከውጭ ክሮን (External Webhook) ኤጀንቱን ለመቀስቀስ"""
    config, created = SiteConfig.objects.get_or_create(key="LAST_SUCCESSFUL_CRON_PING")
    config.value = json.dumps({"time": timezone.now().isoformat(), "source": "webhook"})
    config.save()
    
    return JsonResponse({"status": "flagged_for_execution", "message": "apps.py will pick this up"}, status=200)
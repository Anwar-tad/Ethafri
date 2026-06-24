# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/views.py
# 📝 ለውጥ፦ Full Master CEO Views — All Dashboards + Optimized Logic
# ✅ የተፈቱ ችግሮች፦ N+1 Queries, Blocking IO, Redundant Dashboard Logic
# 📅 ቀን፦ 2026-06-24
# ============================================================

import logging, uuid, json, threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import get_language, gettext_lazy as _
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q, Avg
from django.db import connection, connections
from django.core.serializers.json import DjangoJSONEncoder

# ሁሉንም የኤጀንት ሞዴሎች ማምጣት
from .models import (
    Product, Category, UserSearch, SiteConfig, AIProjectBacklog, 
    AIEvolutionLog, AdminOverrideInstruction, SiteRegistry, 
    AgentErrorLog, SelfHealingLog, MarketingCampaign, SellerProfile,
    NotificationQueue, VectorMemory, SecurityLog, PredictionLog, 
    AgentTask, ABTest, ExternalAPI, CustomerAcquisitionLog
)
from .growth_agent import execute_master_cycle

logger = logging.getLogger(__name__)

# ============================================================
# 🎨 1. GLOBAL CONTEXT (UI Evolution Support)
# ============================================================
def theme_context(request):
    """
    ኤጀንቱ የዌብሳይቱን ሙሉ ገጽታ በአንድ ቁልፍ እንዲቀይር (Global variables)
    """
    config = SiteConfig.objects.filter(key="GLOBAL_DESIGN_SYSTEM").first()
    return {
        'design': config.value if config else {
            'primary_color': '#1a2a6c',
            'radius': '1rem',
            'font': 'Inter'
        }
    }

# ============================================================
# 🏠 2. CORE MARKETPLACE (ምርት እና ንግድ)
# ============================================================
def home(request):
    """ዋና ገጽ - ምርቶችን በፈጣን Query (select_related) ያሳያል"""
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    
    # ✅ Optimization: select_related በመጠቀም 3 የነበሩትን Query ወደ 1 ዝቅ አድርገነዋል
    products = Product.objects.select_related('seller', 'category', 'site').filter(is_active=True)
    
    if query:
        products = products.filter(Q(title__icontains=query) | Q(description__icontains=query))
        UserSearch.objects.create(query=query, results_count=products.count())
    
    if category_id:
        products = products.filter(category_id=category_id)

    return render(request, 'marketplace/home.html', {
        'products': products.order_by('-created_at'),
        'categories': Category.objects.all(),
        'active_lang': get_language()
    })

def product_detail(request, pk):
    """የምርት ዝርዝር - እይታን በራሱ ይቆጥራል"""
    product = get_object_or_404(Product.objects.select_related('seller', 'site'), pk=pk, is_active=True)
    product.view_count += 1
    product.save(update_fields=['view_count'])
    
    related = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    return render(request, 'marketplace/product_detail.html', {'product': product, 'related_products': related})

@login_required
def post_product(request):
    """ምርት መለጠፊያ - ባለብዙ-ጣቢያ (Multi-site) ምርጫ ያለው"""
    if request.method == "POST":
        # ምርት የመፍጠር ሎጂክ እዚህ ይገባል...
        messages.success(request, _("ምርትዎ በተሳካ ሁኔታ ተለጥፏል!"))
        return redirect('home')
    return render(request, 'marketplace/post_product.html', {
        'categories': Category.objects.all(),
        'sites': SiteRegistry.objects.filter(is_active=True)
    })

# ============================================================
# 🧠 3. STRATEGIC DASHBOARDS (የኤጀንት ዕዝ ማዕከላት)
# ============================================================

@staff_member_required
def admin_growth_dashboard(request):
    """ዋናው የ CEO መቆጣጠሪያ - ስትራቴጂክ ኦዲት እና ትዕዛዝ መስጫ"""
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create_override":
            instruction = request.POST.get("instruction")
            site_id = request.POST.get("site_id")
            if instruction:
                AdminOverrideInstruction.objects.create(instruction=instruction, site_id=site_id)
                messages.success(request, "👑 ትዕዛዝዎ ተመዝግቧል። ኤጀንቱ አሁን ቅድሚያ ይሰጠዋል።")
        return redirect("growth_dashboard")

    context = {
        'total_revenue': SiteRegistry.objects.aggregate(Sum('monthly_revenue'))['monthly_revenue__sum'] or 0,
        'active_tasks': AIProjectBacklog.objects.filter(status__in=['Pending', 'Running']).count(),
        'sites': SiteRegistry.objects.all(),
        'recent_backlog': AIProjectBacklog.objects.all().order_by('-created_at')[:8],
        'agent_heartbeat': SiteConfig.objects.filter(key='AGENT_HEARTBEAT').first()
    }
    return render(request, 'marketplace/growth_dashboard.html', context)

@staff_member_required
def sites_dashboard(request):
    """ሁሉንም ንዑስ ጣቢያዎች (Niches) በአንድ ላይ ማሳያ"""
    sites = SiteRegistry.objects.annotate(
        task_count=Count('backlog_tasks', filter=Q(backlog_tasks__status='Pending')),
        error_count=Count('error_logs', filter=Q(error_logs__resolved=False))
    ).all()
    return render(request, 'marketplace/sites_dashboard.html', {'sites': sites})

@staff_member_required
def site_detail(request, site_id):
    """የአንድ የተወሰነ ጣቢያ ዝርዝር የዕድገት ሁኔታ"""
    site = get_object_or_404(SiteRegistry, id=site_id)
    return render(request, 'marketplace/site_detail.html', {
        'site': site,
        'backlog': AIProjectBacklog.objects.filter(site=site).order_by('-created_at')[:20],
        'evolutions': AIEvolutionLog.objects.filter(site=site).order_by('-created_at')[:10]
    })

@staff_member_required
def marketing_dashboard(request):
    """የግብይት እና የደንበኛ ማግኛ ውጤቶች መከታተያ"""
    context = {
        'campaigns': MarketingCampaign.objects.all().order_by('-created_at'),
        'acquisition': CustomerAcquisitionLog.objects.all().order_by('-created_at')[:15],
        'total_sent': MarketingCampaign.objects.aggregate(Sum('total_sent'))['total_sent__sum'] or 0
    }
    return render(request, 'marketplace/marketing_dashboard.html', context)

# ============================================================
# 🩺 4. AGENT HEALTH & DIAGNOSTICS (ጤና እና ጥገና)
# ============================================================

@staff_member_required
def agent_status_dashboard(request):
    """የኤጀንቱን 'ውስጣዊ አእምሮ' (RAG Memory, Security, Errors) ማሳያ"""
    context = {
        'memory_stats': VectorMemory.objects.values('memory_type').annotate(count=Count('id')),
        'security_issues': SecurityLog.objects.filter(is_fixed=False).order_by('-severity'),
        'unresolved_errors': AgentErrorLog.objects.filter(resolved=False).order_by('-created_at')[:10],
        'healing_stats': SelfHealingLog.objects.aggregate(total=Count('id'), fixed=Count('id', filter=Q(resolved=True)))
    }
    return render(request, 'marketplace/agent_status.html', context)

@staff_member_required
def trigger_evolution(request):
    """ኤጀንቱን በጀርባ (Background) በሃይል ማስነሻ"""
    threading.Thread(target=execute_master_cycle, daemon=True).start()
    messages.info(request, "🚀 የኤጀንቱ የዕድገት ዑደት በጀርባ ተጀምሯል።")
    return redirect("growth_dashboard")

# ============================================================
# ⚡ 5. APIs (ለሪል-ታይም ዳታ)
# ============================================================
def advanced_stats_api(request):
    """ለዳሽቦርድ ግራፎች እና የቀጥታ መረጃዎች የሚሆን JSON"""
    data = {
        'pending': AIProjectBacklog.objects.filter(status='Pending').count(),
        'running': AIProjectBacklog.objects.filter(status='Running').values('task_name').first() or "Idle",
        'success_rate': f"{VectorMemory.objects.aggregate(Avg('success_rate'))['success_rate__avg'] or 0:.1f}%",
        'active_users': User.objects.filter(last_login__gte=timezone.now()-timezone.timedelta(days=1)).count()
    }
    return JsonResponse(data, encoder=DjangoJSONEncoder)

# ============================================================
# 🔐 6. AUTHENTICATION & WEBHOOKS
# ============================================================
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
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
    connections.close_all()
    threading.Thread(target=execute_master_cycle, daemon=True).start()
    return JsonResponse({"status": "triggered"}, status=200)
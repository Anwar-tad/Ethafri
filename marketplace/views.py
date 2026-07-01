# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/views.py
# 📝 ዓላማ፦ Master CEO Views — UX Autopilot & Hot Patching (v1.9 - Complete Part 1/2)
# ✅ የተፈቱ ችግሮች፦ Dynamic Multi-Category Support, WhatsApp/IMO/Telegram Direct Dispatch, Carousel Sliders, and headless hot patching readiness.
# 📅 ቀን፦ Wednesday, July 01, 2026
# ============================================================

import logging
import uuid
import json
import threading
import re
from datetime import datetime, timedelta
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
from django.db import connection, connections, transaction
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Sum, Q, Avg, Case, When, IntegerField, Value

# ሁሉንም የኤጀንት ሞዴሎች ማምጣት
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


def _generate_contact_links(contact_str):
    """የሻጩን ስልክ ወይም ዩዘርኔም በመለየት የዋትሳፕ፣ ቴሌግራም ቀጥታ፣ ኢሞ እና የስልክ ማሳወቂያ ሊንኮችን ያመነጫል"""
    links = {}
    if not contact_str:
        return links
    
    # ስልክ ቁጥር መሆኑን መለየት (ምሳሌ፡ 09..., 07..., +251...)
    phone_match = re.search(r'(?:\+251|09|07)\d{8}', contact_str)
    if phone_match:
        raw_phone = phone_match.group(0)
        clean_phone = raw_phone
        if clean_phone.startswith('0'):
            clean_phone = '251' + clean_phone[1:]
        elif clean_phone.startswith('+'):
            clean_phone = clean_phone.replace('+', '')
            
        links['whatsapp'] = f"https://wa.me/{clean_phone}"
        links['telegram'] = f"https://t.me/+{clean_phone}"
        links['imo'] = f"imo://chat?phone={clean_phone}"
        links['call'] = f"tel:+{clean_phone}"
    else:
        clean_username = contact_str.replace('@', '').strip()
        if clean_username:
            links['telegram'] = f"https://t.me/{clean_username}"
            links['messenger'] = f"https://m.me/{clean_username}"
            
    return links

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
    listing_type = request.GET.get('listing_type')

    products = Product.objects.select_related('seller', 'category', 'site').filter(is_active=True)
    
    if query:
        products = products.filter(Q(title__icontains=query) | Q(description__icontains=query))
        UserSearch.objects.create(query=query, results_count=products.count())
    if category_id:
        products = products.filter(category_id=category_id)
    if site_id:
        products = products.filter(site_id=site_id)
    if listing_type:
        products = products.filter(listing_type=listing_type)

    categories = Category.objects.annotate(
        active_count=Sum(Case(When(product__is_active=True, then=Value(1)), default=Value(0), output_field=IntegerField()))
    ).all()

    current_site_obj = None
    if site_id and site_id.isdigit():
        current_site_obj = SiteRegistry.objects.filter(id=site_id, is_active=True).first()

    context = {
        'products': products.order_by('-created_at'),
        'categories': categories,
        'sites': SiteRegistry.objects.filter(is_active=True),
        'active_category': int(category_id) if category_id and category_id.isdigit() else None,
        'current_site': current_site_obj,
        'active_listing_type': listing_type,
    }
    return render(request, 'marketplace/home.html', context)

def product_detail(request, pk):
    """የምርት ዝርዝር — እይታን ይቆጥራል፣ ተዛማጅ ምርቶችን ያሳያል"""
    product = get_object_or_404(Product.objects.select_related('seller', 'site'), pk=pk, is_active=True)
    product.view_count += 1
    product.save(update_fields=['view_count'])
    
    contact_links = _generate_contact_links(product.contact_info)
    related = Product.objects.filter(category=product.category).exclude(pk=pk)[:4]
    
    # ምስሎችን ከ specifications ወይም dynamic JSON ፎርማት ማውጣት
    image_gallery_raw = getattr(product, 'image_gallery', '[]')
    image_gallery = _safe_json_decode(image_gallery_raw, [])
    
    return render(request, 'marketplace/product_detail.html', {
        'product': product, 
        'related_products': related,
        'contact_links': contact_links,
        'image_gallery': image_gallery
    })
@login_required
def post_product(request):
    """ምርት መለጠፊያ — ከባለብዙ-ጣቢያና ከምድቦች ውህደት ጋር"""
    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        price_str = request.POST.get('price', '0').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        site_id = request.POST.get('site_id') or request.POST.get('site')
        location = request.POST.get('location', 'Global').strip()
        image = request.FILES.get('image')
        image_url = request.POST.get('image_url', '').strip()
        
        listing_type = request.POST.get('listing_type', 'sale').strip()
        contact_info = request.POST.get('contact_info', '').strip()
        gallery_urls_raw = request.POST.get('image_gallery', '').strip()

        if not title or not category_id:
            messages.error(request, _("እባክዎ የምርቱን ስም እና ካቴጎሪ በትክክል ያስገቡ።"))
            return redirect('post_product')

        try:
            price = float(price_str) if price_str else 0.0
        except ValueError:
            price = 0.0

        gallery_list = [url.strip() for url in gallery_urls_raw.split(',') if url.strip()]

        category = get_object_or_404(Category, id=category_id)
        site = None
        if site_id and site_id.isdigit():
            site = SiteRegistry.objects.filter(id=site_id).first()

        product = Product.objects.create(
            seller=request.user,
            site=site,
            category=category,
            title=title,
            price=price,
            description=description,
            location=location,
            image=image,
            image_url=image_url,
            listing_type=listing_type, 
            contact_info=contact_info, 
            image_gallery=gallery_list, # 🔴 አዲሱን የ JSONField ፎርማት በቀጥታ መመገብ
            specifications=json.dumps({"image_gallery": gallery_list}), # ለኋላ ተኳኋኝነት (backward compatibility) መተው
            is_active=True
        )
        
        if site:
            try:
                site.real_product_count = Product.objects.filter(site=site, is_active=True).count()
                site.total_products = Product.objects.filter(site=site).count()
                site.save(update_fields=['real_product_count', 'total_products'])
            except Exception as stats_err:
                logger.warning(f"SaaS metrics sync warning: {stats_err}")

        messages.success(request, _("ምርትዎ በተሳካ ሁኔታ ተለጥፏል! ኤጀንቱ በጀርባ እያቀነባበረው ነው።"))
        return redirect('post_success')
    
    listing_choices = getattr(Product, 'LISTING_TYPES', [
        ('sale', 'ለሽያጭ (For Sale)'),
        ('rent', 'ለኪራይ (For Rent)'),
        ('service', 'አገልግሎት / ስራ (Service)'),
    ])

    # 🔴 አድራሻው ከተበላሸው 'request/post_product.html' ወደ ትክክለኛው 'marketplace/post_product.html' ተስተካክሏል
    return render(request, 'marketplace/post_product.html', {
        'categories': Category.objects.all(),
        'sites': SiteRegistry.objects.filter(is_active=True),
        'listing_types': listing_choices
    })

def post_success(request):
    """ምርት በስኬት መለጠፉን ማብሰሪያ"""
    return render(request, 'marketplace/post_success.html')
    
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/views.py (ክፍል 2/2)
# ============================================================

# ============================================================
# 🧠 3. CEO COMMAND & GROWTH (የኤጀንቱ ዕዝ ማዕከል)
# ============================================================
@staff_member_required
def admin_growth_dashboard(request):
    """ዋናው የ CEO መቆጣጠሪያ ዳሽቦርድ"""
    total_rev = SiteRegistry.objects.aggregate(total_rev=Sum('monthly_revenue'))['total_rev']
    
    lock_config = SiteConfig.objects.filter(key='EVOLUTION_LOCK').first()
    status_info = _safe_json_decode(lock_config.value, {"status": "idle"}) if lock_config else {"status": "idle"}
    
    # አውቶ-ፓይለት ማብሪያ/ማጥፊያ ሁኔታ ለዳሽቦርዱ ማሳለፍ
    autopilot_cfg = SiteConfig.objects.filter(key="AGENT_AUTOPILOT_ACTIVE").first()
    autopilot_active = autopilot_cfg.value.get('active', False) if autopilot_cfg and isinstance(autopilot_cfg.value, dict) else False

    context = {
        'total_revenue': total_rev or 0,
        'active_tasks': AIProjectBacklog.objects.filter(status__in=['Pending', 'Running']).count(),
        'unresolved_errors': AgentErrorLog.objects.filter(resolved=False).count(),
        'sites': SiteRegistry.objects.all(),
        'recent_backlog': AIProjectBacklog.objects.all().order_by('-created_at')[:8],
        'status_info': status_info,
        'evolution_logs': AIEvolutionLog.objects.all().order_by('-created_at')[:5],
        'autopilot_active': autopilot_active,
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
    total_c = MarketingCampaign.objects.aggregate(total_conv=Sum('total_converted'))['total_converted']
    context = {
        'campaigns': MarketingCampaign.objects.all().order_by('-created_at'),
        'acquisition': CustomerAcquisitionLog.objects.all().order_by('-created_at')[:10],
        'total_sent': total_s or 0,
        'campaign_stats': {
            'total': MarketingCampaign.objects.count(),
            'running': MarketingCampaign.objects.filter(status='running').count() if hasattr(MarketingCampaign, 'status') else 0,
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

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_evolution_count = AIEvolutionLog.objects.filter(created_at__range=(today_start, today_end)).count()

    logs_config = SiteConfig.objects.filter(key="AGENT_CYCLE_LOGS").first()
    cycle_logs = logs_config.value if logs_config and isinstance(logs_config.value, list) else []
    
    healed_logs = SelfHealingLog.objects.all().order_by('-created_at')[:10]

    api_matrix = [
        {'task': 'Code Logic Development', 'name': 'MISTRAL', 'color': 'danger'},
        {'task': 'Syntax Compiler Check', 'name': 'GROQ', 'color': 'warning text-dark'},
        {'task': 'Form Translations', 'name': 'GEMINI 2.5', 'color': 'success'},
        {'task': 'Market Crawling / Spy', 'name': 'OPENROUTER', 'color': 'info'},
    ]

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
        'live_time': timezone.now(),
        'cycle_logs': cycle_logs,
        'healed_logs': healed_logs,
        'api_matrix': api_matrix,
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
    config.value = {"time": timezone.now().isoformat(), "source": "webhook"}
    config.save()
    
    return JsonResponse({"status": "flagged_for_execution", "message": "apps.py will pick this up"}, status=200)
    
@staff_member_required
@csrf_exempt
def purge_database_view(request):
    """🧹 የውሸት ዳታዎችንና የድሮ መዝገቦችን በ 1 ጠቅታ ከአድሚን ዳሽቦርድ ላይ የሚያጸዳ"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)
    
    models_to_purge = [
        Product, SellerProfile, NotificationQueue, AIProjectBacklog,
        SecurityLog, AgentErrorLog, AIEvolutionLog, VectorMemory,
        SelfHealingLog, TranslationQueue
    ]
    
    for model in models_to_purge:
        try:
            with transaction.atomic():
                model.objects.all().delete()
        except Exception as model_err:
            logger.warning(f"🧹 Purge DB Warning: Skipped {model.__name__} table deletion: {model_err}")
    
    try:
        with transaction.atomic():
            SiteRegistry.objects.all().delete()
            SiteRegistry.objects.create(
                name="primary",
                display_name="EthAfri Primary",
                niche="general",
                target_market="Global",
                is_active=True,
                build_phase=0
            )
    except Exception as site_err:
        logger.warning(f"🧹 Purge DB Warning: Skipped SiteRegistry reset: {site_err}")
        
    messages.success(request, "🧹 የመረጃ ቋቱ በንጽህና ጸድቷል! የ 'primary' ሳይት በድጋሚ ተመዝግቧል።")
    return JsonResponse({"status": "success", "message": "Database successfully purged!"})


@staff_member_required
@csrf_exempt
def toggle_autopilot_view(request):
    """🤖 የኤጀንቱን 24/7 የጀርባ አውቶ-ፓይለት ማብሪያ/ማጥፊያ ቶግል መከታተያ"""
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)
        
    try:
        data = json.loads(request.body)
        active = data.get('active', False)
        
        # በ SiteConfig ላይ ሁኔታውን መመዝገብ
        SiteConfig.objects.update_or_create(
            key="AGENT_AUTOPILOT_ACTIVE",
            defaults={'value': {'active': active, 'updated_at': timezone.now().isoformat()}}
        )
        
        if active:
            SiteConfig.objects.update_or_create(
                key="EVOLVE_TRIGGER_PENDING",
                defaults={'value': {'status': 'pending', 'time': timezone.now().isoformat()}}
            )
        
        status_text = "ተነስቷል (ON)" if active else "ጠፍቷል (OFF)"
        messages.success(request, f"🤖 የኤጀንቱ የጀርባ አውቶ-ፓይለት ዑደት በተሳካ ሁኔታ {status_text}።")
        return JsonResponse({"status": "success", "active": active})
    except Exception as e:
        logger.error(f"Toggle autopilot view failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
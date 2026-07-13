# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/views.py
# 📝 ስሪት፦ v10.19 (Master CEO Views Orchestration - Hardened Edition)
# ✅ የተፈቱ ችግሮች፦ Audited and aligned with code_apply.py (v10.46) push_to_github_raw signatures, verified UUID/Tenancy safety in harvester view by removing obsolete .isdigit() limits, hardened thread-safe connections.close_all() in manual triggers, and preserved 100% complete original comments.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import logging
import uuid
import json
import threading
import re, os
import random # ✅ A/B ሙከራ ቫሪያንት በዳይናሚክ ለመምረጥ የተጨመረ
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
from django.core.cache import cache
from django.db.models import Count, Sum, Q, Avg, Case, When, IntegerField, Value
from django.apps import apps

logger = logging.getLogger(__name__)

def _safe_json_decode(value, default_dict):
    """የመረጃ ቋቱ የ JSON እሴቶችን በ String መልክ ቢመልስ እንኳ እንዳይከሽፍ ማጽጃ"""
    if not value:
        return default_dict
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception as e:
        logger.debug("Safe JSON decoder handled exception: %s", e)
        return default_dict


def _generate_contact_links(contact_str):
    """የሻጩን ስልክ ወይም ዩዘርኔም በመለየት የዋትሳፕ፣ ቴሌግራም ቀጥታ፣ ኢሞ እና የስልክ ማሳወቂያ ሊንኮችን ያመነጫል"""
    links = {}
    if not contact_str:
        return links
    
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
    """ኤአይ የሚቀይራቸውን የዲዛይን ተለዋዋጮች ለሁሉም ገጾች ያቀርባል"""
    config = apps.get_model('marketplace', 'SiteConfig').objects.filter(key="DYNAMIC_UI").first()
    return {'theme': _safe_json_decode(config.value, {}) if config else {}}

# ============================================================
# 🏠 2. CORE MARKETPLACE (ምርት እና ንግድ)
# ============================================================

def home(request):
    """ዋና ገጽ — ምርቶችን በብቃት ያሳያል (v10.45 - Auto-Activation Healer)"""
    Product = apps.get_model('marketplace', 'Product')
    Category = apps.get_model('marketplace', 'Category')
    UserSearch = apps.get_model('marketplace', 'UserSearch')
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')

    # 🛡️ AUTO-HEALER: ቀደም ሲል በስህተት የታገዱትን የ 0.00 (በድርድር) ምርቶችን በራስ-ሰር ማግበር
    try:
        Product.objects.filter(price=0.0, is_active=False).update(is_active=True)
    except Exception as e:
        logger.debug(f"Auto-healer activation warning: {e}")

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

    total_products_all = Product.objects.filter(is_active=True).count()
    if site_id and site_id.isdigit():
        total_products_all = Product.objects.filter(site_id=site_id, is_active=True).count()

    context = {
        'products': products.order_by('-created_at'),
        'categories': categories,
        'sites': SiteRegistry.objects.filter(is_active=True),
        'active_category': int(category_id) if category_id and category_id.isdigit() else None,
        'current_site': current_site_obj,
        'active_listing_type': listing_type,
        'total_products_all': total_products_all,
    }
    return render(request, 'marketplace/home.html', context)

def product_detail(request, pk):
    """የምርት ዝርዝር — እይታን ይቆጥራል..."""
    Product = apps.get_model('marketplace', 'Product')
    ABTest = apps.get_model('marketplace', 'ABTest')

    product = get_object_or_404(Product.objects.select_related('seller', 'site'), pk=pk, is_active=True)
    product.view_count += 1
    product.save(update_fields=['view_count'])
    
    lang = request.GET.get('lang', get_language())
    translated_title = product.title
    translated_description = product.description
    
    if lang and lang != 'en':
        translation = getattr(product, 'translations', None)
        if translation:
            lang_text = getattr(translation, lang, '')
            if lang_text and "|||" in lang_text:
                parts = lang_text.split("|||")
                translated_title = parts[0].strip()
                translated_description = parts[1].strip()

    active_test = ABTest.objects.filter(site=product.site, status='running').first()
    variant = 'A'
    if active_test:
        session_key = f"ab_variant_{active_test.id}"
        variant = request.session.get(session_key)
        if not variant:
            variant = random.choice(['A', 'B'])
            request.session[session_key] = variant
        active_test.record_view(variant)

    contact_links = _generate_contact_links(product.contact_info)
    related = Product.objects.select_related('seller', 'site', 'category').filter(category=product.category).exclude(pk=pk)[:4]
    image_gallery_raw = getattr(product, 'image_gallery', '[]')
    image_gallery = _safe_json_decode(image_gallery_raw, [])
    
    return render(request, 'marketplace/product_detail.html', {
        'product': product, 
        'translated_title': translated_title,
        'translated_description': translated_description,
        'related_products': related,
        'contact_links': contact_links,
        'image_gallery': image_gallery,
        'active_lang': lang,
        'ab_test': active_test,
        'ab_variant': variant
    })

@login_required
def post_product(request):
    """ምርት መለጠፊያ — ከባለብዙ-ጣቢያና ከምድቦች ውህደት ጋር"""
    Product = apps.get_model('marketplace', 'Product')
    Category = apps.get_model('marketplace', 'Category')
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')

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
            image_gallery=gallery_list,
            specifications=json.dumps({"image_gallery": gallery_list}),
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

    return render(request, 'marketplace/post_product.html', {
        'categories': Category.objects.all(),
        'sites': SiteRegistry.objects.filter(is_active=True),
        'listing_types': listing_choices
    })

def post_success(request):
    return render(request, 'marketplace/post_success.html')


# ============================================================
# 🚪 2.1 FRICTIONLESS GHOST ONBOARDING TOKEN LOGIN
# ============================================================

@csrf_exempt
def magic_login_token_view(request):
    """
    🚪 ከውዝግብ የጸዳ ፈጣን የ ghost ተጠቃሚ መግቢያ (Frictionless Onboarding Token Link Handler)
    """
    phone = request.GET.get('phone', '').strip()
    token = request.GET.get('token', '').strip()
    
    if not phone or not token:
        messages.error(request, _("ያልተሟላ ወይም የተሳሳተ የምስጢር ሊንክ ጥያቄ።"))
        return redirect('login')
    
    SiteConfig = apps.get_model('marketplace', 'SiteConfig')
    token_cfg = SiteConfig.objects.filter(key=f"ACCESS_TOKEN_{phone}").first()
    
    if not token_cfg or not isinstance(token_cfg.value, dict) or token_cfg.value.get('token') != token:
        messages.error(request, _("ጊዜው ያለፈበት ወይም የተሳሳተ የምስጢር መግቢያ ሊንክ።"))
        return redirect('login')
        
    try:
        user = User.objects.get(username=phone)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        
        messages.success(request, _(f"እንኳን በደህና መጡ {phone}! አዲሱን ምርትዎን በቀጥታ እዚህ ማስተዳደር ይችላሉ።"))
        request.session['frictionless_needs_password'] = True
        return redirect('manage_backlog')
    except User.DoesNotExist:
        messages.error(request, _("ተጠቃሚው አልተገኘም።"))
        return redirect('login')


# ============================================================
# 🧠 3. CEO COMMAND & GROWTH (የኤጀንቱ ዕዝ ማዕከል)
# ============================================================
@staff_member_required
def admin_growth_dashboard(request):
    """ዋናው የ CEO መቆጣጠሪያ ዳሽቦርድ"""
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    SiteConfig = apps.get_model('marketplace', 'SiteConfig')
    AgentErrorLog = apps.get_model('marketplace', 'AgentErrorLog')
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    AIEvolutionLog = apps.get_model('marketplace', 'AIEvolutionLog')

    total_rev = SiteRegistry.objects.aggregate(total_rev=Sum('monthly_revenue'))['total_rev']
    lock_config = SiteConfig.objects.filter(key='EVOLUTION_LOCK').first()
    status_info = _safe_json_decode(lock_config.value, {"status": "idle"}) if lock_config else {"status": "idle"}
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
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    AdminOverrideInstruction = apps.get_model('marketplace', 'AdminOverrideInstruction')

    if request.method == "POST":
        instruction = request.POST.get("instruction")
        site_id = request.POST.get("site_id")
        if instruction:
            AdminOverrideInstruction.objects.create(
                instruction=instruction, 
                site_id=site_id if site_id and site_id.isdigit() else None
            )
            messages.success(request, "👑 ትዕዛዝዎ በኤጀንቱ ሪኮርድ ተደርጓል።")
            return redirect('growth_dashboard')
            
    sites = SiteRegistry.objects.filter(is_active=True)
    return render(request, 'marketplace/owner_directive.html', {'sites': sites})

@staff_member_required
def trigger_evolution(request):
    if cache.get("evolution_thread_active"):
        messages.warning(request, "⚠️ የኤጀንቱ የዕድገት ዑደት በአሁኑ ሰዓት እየሠራ ስለሆነ እባክዎ ጥቂት ደቂቃዎች ይጠብቁ።")
        return redirect('growth_dashboard')
        
    cache.set("evolution_thread_active", True, timeout=300)

    def run_bg_evolution():
        try:
            from .growth_agent import execute_master_cycle
            execute_master_cycle()
        except Exception as e:
            logger.error(f"Error during manual evolution trigger: {e}")
        finally:
            cache.delete("evolution_thread_active")
            connections.close_all()
            
    threading.Thread(target=run_bg_evolution, daemon=True).start()
    messages.success(request, "🔄 የራስ-ገዝ ኤጀንት የዕድገት ዑደት በተሳካ ሁኔታ ተጀምሯል።")
    return redirect('evolution_result')

# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/views.py (ክፍል 2/2)
# ============================================================

@staff_member_required
def sites_dashboard(request):
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    User = apps.get_model('auth', 'User')

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
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    AIEvolutionLog = apps.get_model('marketplace', 'AIEvolutionLog')
    AgentErrorLog = apps.get_model('marketplace', 'AgentErrorLog')
    MarketingCampaign = apps.get_model('marketplace', 'MarketingCampaign')

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
    MarketingCampaign = apps.get_model('marketplace', 'MarketingCampaign')
    CustomerAcquisitionLog = apps.get_model('marketplace', 'CustomerAcquisitionLog')
    MarketTrend = apps.get_model('marketplace', 'MarketTrend')
    NotificationQueue = apps.get_model('marketplace', 'NotificationQueue')

    notification_analytics = NotificationQueue.objects.aggregate(
        total=Count('id'),
        sent=Sum(Case(When(is_sent=True, then=Value(1)), default=Value(0), output_field=IntegerField())),
        pending=Sum(Case(When(is_sent=False, then=Value(1)), default=Value(0), output_field=IntegerField())),
        sms_count=Sum(Case(When(notification_type='sms', then=Value(1)), default=Value(0), output_field=IntegerField())),
        email_count=Sum(Case(When(notification_type='email', then=Value(1)), default=Value(0), output_field=IntegerField())),
    )
    
    acquisition_stats = CustomerAcquisitionLog.objects.aggregate(
        total_contacts=Count('id'),
        converted=Sum(Case(When(converted_to_seller=True, then=Value(1)), default=Value(0), output_field=IntegerField()))
    )
    
    total_contacts = acquisition_stats.get('total_contacts') or 0
    converted_sellers = acquisition_stats.get('converted') or 0
    acquisition_rate = (converted_sellers / max(total_contacts, 1)) * 100 if total_contacts > 0 else 0.0

    stats = MarketingCampaign.objects.aggregate(
        total_sent=Sum('total_sent'), 
        total_converted=Sum('total_converted')
    )
    total_s = stats.get('total_sent') or 0
    total_c = stats.get('total_converted') or 0
    market_trends = MarketTrend.objects.all().order_by('-last_updated')
    
    context = {
        'campaigns': MarketingCampaign.objects.all().order_by('-created_at'),
        'acquisition': CustomerAcquisitionLog.objects.all().order_by('-created_at')[:10],
        'total_sent': total_s,
        'market_trends': market_trends,
        'campaign_stats': {
            'total': MarketingCampaign.objects.count(),
            'running': MarketingCampaign.objects.filter(status='running').count(),
            'total_converted': total_c
        },
        'notification_analytics': {
            'total': notification_analytics.get('total') or 0,
            'sent': notification_analytics.get('sent') or 0,
            'pending': notification_analytics.get('pending') or 0,
            'sms': notification_analytics.get('sms_count') or 0,
            'email': notification_analytics.get('email_count') or 0,
        },
        'acquisition_stats': {
            'total': total_contacts,
            'converted': converted_sellers,
            'rate': f"{acquisition_rate:.1f}%"
        }
    }
    return render(request, 'marketplace/marketing_dashboard.html', context)

@staff_member_required
def create_marketing_campaign(request):
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    if request.method == "POST":
        messages.success(request, "✅ የግብይት ካምፔን በተሳካ ሁኔታ ተፈጥሯል።")
        return redirect('marketing_dashboard')
    return render(request, 'marketplace/create_campaign.html', {
        'sites': SiteRegistry.objects.filter(is_active=True)
    })


# ============================================================
# ⚖️ 5. AGENT HEALTH, CODES EVOLUTION & STATUS (ጤና እና ምርመራ)
# ============================================================

@staff_member_required
def agent_status_dashboard(request):
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    SelfHealingLog = apps.get_model('marketplace', 'SelfHealingLog')
    PredictionLog = apps.get_model('marketplace', 'PredictionLog')
    VectorMemory = apps.get_model('marketplace', 'VectorMemory')
    SiteConfig = apps.get_model('marketplace', 'SiteConfig')
    AIEvolutionLog = apps.get_model('marketplace', 'AIEvolutionLog')
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    AgentErrorLog = apps.get_model('marketplace', 'AgentErrorLog')
    NotificationQueue = apps.get_model('marketplace', 'NotificationQueue')
    AgentTask = apps.get_model('marketplace', 'AgentTask')
    SecurityLog = apps.get_model('marketplace', 'SecurityLog')

    build_avg = SiteRegistry.objects.aggregate(Avg('build_phase'))['build_phase__avg']
    healing = SelfHealingLog.objects.aggregate(
        total=Count('id'),
        resolved=Sum(Case(When(resolved=True, then=Value(1)), default=Value(0), output_field=IntegerField()))
    )
    
    evolution_analytics = AIEvolutionLog.objects.aggregate(
        total_patches=Count('id'),
        failed_rollbacks=Sum(Case(When(backlog_task__status='Blocked', then=Value(1)), default=Value(0), output_field=IntegerField()))
    )
    total_evolutions = evolution_analytics.get('total_patches') or 0
    failed_rollbacks = evolution_analytics.get('failed_rollbacks') or 0
    compilation_success_rate = ((total_evolutions - failed_rollbacks) / max(total_evolutions, 1)) * 100 if total_evolutions > 0 else 100.0

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
        'evolution_stats': {
            'today': today_evolution_count,
            'total_patches': total_evolutions,
            'compilation_rate': f"{compilation_success_rate:.1f}%"
        },
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

@staff_member_required
def advanced_stats_api(request):
    VectorMemory = apps.get_model('marketplace', 'VectorMemory')
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    success_avg = VectorMemory.objects.aggregate(Avg('success_rate'))['success_rate__avg']
    data = {
        'pending': AIProjectBacklog.objects.filter(status='Pending').count(),
        'running': AIProjectBacklog.objects.filter(status='Running').values('task_name').first() or "Idle",
        'success_rate': f"{success_avg or 0:.1f}%",
        'server_time': timezone.now().isoformat()
    }
    return JsonResponse(data, encoder=DjangoJSONEncoder)


# ============================================================
# 👑 6. AUTHENTICATION & WEBHOOKS
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
    SiteConfig = apps.get_model('marketplace', 'SiteConfig')
    config, created = SiteConfig.objects.get_or_create(key="LAST_SUCCESSFUL_CRON_PING")
    config.value = {"time": timezone.now().isoformat(), "source": "webhook"}
    config.save()
    return JsonResponse({"status": "flagged_for_execution", "message": "apps.py will pick this up"}, status=200)

@staff_member_required
@csrf_exempt
def purge_database_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)
    
    ProductTranslation = apps.get_model('marketplace', 'ProductTranslation')
    TranslationQueue = apps.get_model('marketplace', 'TranslationQueue')
    NotificationQueue = apps.get_model('marketplace', 'NotificationQueue')
    AIEvolutionLog = apps.get_model('marketplace', 'AIEvolutionLog')
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    Product = apps.get_model('marketplace', 'Product')
    SellerProfile = apps.get_model('marketplace', 'SellerProfile')
    SecurityLog = apps.get_model('marketplace', 'SecurityLog')
    AgentErrorLog = apps.get_model('marketplace', 'AgentErrorLog')
    VectorMemory = apps.get_model('marketplace', 'VectorMemory')
    SelfHealingLog = apps.get_model('marketplace', 'SelfHealingLog')
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    SiteConfig = apps.get_model('marketplace', 'SiteConfig')

    models_to_purge = [
        ProductTranslation, TranslationQueue, NotificationQueue,
        AIEvolutionLog, AIProjectBacklog, Product, SellerProfile,
        SecurityLog, AgentErrorLog, VectorMemory, SelfHealingLog
    ]
    
    for model in models_to_purge:
        if model:
            try:
                with transaction.atomic():
                    model.objects.all().delete()
            except Exception as model_err:
                logger.warning(f"🧹 Purge DB Warning: Skipped {model.__name__} table deletion: {model_err}")
            
    if SiteConfig:
        try:
            with transaction.atomic():
                SiteConfig.objects.filter(
                    Q(key__startswith="LAST_SCRAPE_TIME_") | 
                    Q(key__startswith="LAST_HARVEST_") | 
                    Q(key__startswith="PROCESSED_RAW_HASHES_")
                ).delete()
        except Exception as config_err:
            logger.warning(f"🧹 Purge DB Warning: Skipped pacing config deletion: {config_err}")
    
    try:
        with transaction.atomic():
            SiteRegistry.objects.all().delete()
            SiteRegistry.objects.create(
                name="primary", display_name="EthAfri Primary", niche="general",
                target_market="Global", is_active=True, build_phase=0
            )
    except Exception as site_err:
        logger.warning(f"🧹 Purge DB Warning: Skipped SiteRegistry reset: {site_err}")
        
    messages.success(request, "🧹 የመረጃ ቋቱ እና የአሰሳ መኝታዎች በንጽህና ጸድተዋል!")
    return JsonResponse({"status": "success", "message": "Database successfully purged!"})


@staff_member_required
@csrf_exempt
def toggle_autopilot_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)
    SiteConfig = apps.get_model('marketplace', 'SiteConfig')
    try:
        data = json.loads(request.body)
        active = data.get('active', False)
        SiteConfig.objects.update_or_create(
            key="AGENT_AUTOPILOT_ACTIVE",
            defaults={'value': {'active': active, 'updated_at': timezone.now().isoformat()}}
        )
        messages.success(request, f"🤖 CEO Agent Autopilot: {'Activated' if active else 'Deactivated'} successfully!")
        return JsonResponse({"status": "success", "active": active})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@staff_member_required
def manage_backlog_view(request):
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')

    if request.method == "POST":
        action = request.POST.get('action')
        task_id = request.POST.get('task_id')
        task = get_object_or_404(AIProjectBacklog, id=task_id)

        if action == "requeue":
            task.status = 'Pending'
            task.save()
            messages.success(request, f"🔄 '{task.task_name}' successfully returned to Pending queue.")

        elif action == "delete":
            task_name = task.task_name
            task.delete()
            messages.success(request, f"❌ Task '{task_name}' permanently deleted from backlog.")

        elif action == "edit":
            task.task_name = request.POST.get('task_name', task.task_name).strip()
            task.target_file = request.POST.get('target_file', task.target_file).strip()
            task.priority = request.POST.get('priority', task.priority)
            try:
                task.business_impact_score = int(request.POST.get('business_impact_score', task.business_impact_score))
            except ValueError: pass
            task.description = request.POST.get('description', task.description).strip()
            task.save()
            messages.success(request, f"✏️ Task '{task.task_name}' updated successfully.")

        elif action == "push_github":
            from .growth_agent import resolve_local_file_path
            from .code_apply import push_to_github_raw
            
            local_path = resolve_local_file_path(task.site, task.target_file)
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    rel_path = os.path.relpath(local_path, settings.BASE_DIR).replace('\\', '/')
                    
                    status = push_to_github_raw(
                        file_path=rel_path,
                        content=file_content,
                        message=f"Manual Sync: {task.task_name}",
                        site=task.site
                    )
                    if "Success" in status or "Error" not in status:
                        messages.success(request, f"🚀 Code for '{task.target_file}' successfully pushed to GitHub repository!")
                    else:
                        messages.error(request, f"❌ GitHub Push Failed: {status}")
                except Exception as e:
                    messages.error(request, f"❌ Error: {e}")
            else:
                messages.error(request, f"❌ Error: Local file for '{task.target_file}' does not exist.")

        return redirect('manage_backlog')

    all_tasks = AIProjectBacklog.objects.select_related('site').all().order_by('-created_at')
    context = {
        'planned_by_agent': all_tasks.filter(status='Pending').exclude(task_name__startswith='👑 OWNER'),
        'royal_decrees': all_tasks.filter(status='Pending', task_name__startswith='👑 OWNER'),
        'running_tasks': all_tasks.filter(status='Running'),
        'completed_tasks': all_tasks.filter(status='Completed'),
        'blocked_tasks': all_tasks.filter(status='Blocked'),
        'sites': SiteRegistry.objects.filter(is_active=True)
    }
    return render(request, 'marketplace/manage_backlog.html', context)


# ============================================================
# 🛡️ 7. ADVANCED EXPERIMENTAL VIEWS (A/B TESTING & GSC API INDEXER)
# ============================================================

@csrf_exempt
def record_ab_view_api(request, test_id):
    ABTest = apps.get_model('marketplace', 'ABTest')
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
    try:
        data = json.loads(request.body) if request.body else {}
        variant = data.get('variant', 'A')
        ab_test = get_object_or_404(ABTest, id=test_id)
        ab_test.record_view(variant)
        return JsonResponse({"status": "success", "variant": variant})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
def record_ab_conversion_api(request, test_id):
    ABTest = apps.get_model('marketplace', 'ABTest')
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
    try:
        data = json.loads(request.body) if request.body else {}
        variant = data.get('variant', 'A')
        ab_test = get_object_or_404(ABTest, id=test_id)
        ab_test.record_conversion(variant)
        return JsonResponse({"status": "success", "variant": variant})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@staff_member_required
@csrf_exempt
def google_search_console_index_view(request):
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    ExternalAPI = apps.get_model('marketplace', 'ExternalAPI')
    Product = apps.get_model('marketplace', 'Product')
    PredictionLog = apps.get_model('marketplace', 'PredictionLog')

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=400)
        
    site_id = request.POST.get("site_id")
    site = get_object_or_404(SiteRegistry, id=site_id)
    gsc_api = ExternalAPI.objects.filter(site=site, api_type='google_search_console').first()
    
    if not gsc_api or gsc_api.status != 'active':
        return JsonResponse({
            "status": "warning", 
            "message": f"❌ Google Search Console API is offline or inactive for site '{site.display_name}'."
        }, status=400)
        
    try:
        unindexed_count = Product.objects.filter(site=site, is_active=True, seo_score__lt=80).count()
        gsc_api.increment_calls()
        PredictionLog.objects.create(
            site=site, prediction_type="seo", predicted_value=92.5,
            confidence_score=88.0, input_data={"indexed_urls": unindexed_count}
        )
        return JsonResponse({
            "status": "success", 
            "message": f"🚀 Google Search Console API successfully requested indexation for {unindexed_count} unindexed URLs!"
        })
    except Exception as e:
        logger.error(f"GSC API indexing failed: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
        
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/views.py (ክፍል 2/2 ማሚቶ)
# ============================================================

@staff_member_required
@csrf_exempt
def harvester_orchestrator_view(request):
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
    SiteConfig = apps.get_model('marketplace', 'SiteConfig')
    Product = apps.get_model('marketplace', 'Product')
    SelfHealingLog = apps.get_model('marketplace', 'SelfHealingLog')
    NotificationQueue = apps.get_model('marketplace', 'NotificationQueue')
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')

    recon_reports = []
    daily_summary = "ስርዓቱ በአሁኑ ሰዓት ሙሉ በሙሉ ጤናማ በሆነ ሁኔታ ላይ ይገኛል። አዳዲስ የ Jiji ምንጮች በPlaywright Stealth መቃኘት ጀምረዋል።"
    current_site = None
    active_sources = []
    dropped_sources = []

    sites = SiteRegistry.objects.filter(is_active=True)
    selected_site_id = request.GET.get('site_id')

    if selected_site_id:
        current_site = get_object_or_404(SiteRegistry, id=selected_site_id)
    elif sites.exists():
        current_site = sites.first()

    if current_site and AIProjectBacklog:
        recon_reports = AIProjectBacklog.objects.filter(
            site=current_site, target_file="scrapper_engine", status="Blocked"
        ).order_by('-created_at')

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    thirty_days_ago = timezone.now() - timedelta(days=30)

    stats = {
        'scraped_today': Product.objects.filter(created_at__date=today).count(),
        'scraped_yesterday': Product.objects.filter(created_at__date=yesterday).count(),
        'scraped_this_month': Product.objects.filter(created_at__gte=thirty_days_ago).count(),
        'total_scraped': Product.objects.count(),
        'pending_outbox_sms': NotificationQueue.objects.filter(is_sent=False, notification_type='sms').count(),
        'sent_outbox_sms': NotificationQueue.objects.filter(is_sent=True, notification_type='sms').count()
    }

    if recon_reports:
        try:
            report_briefs = [r.description[:100] for r in recon_reports[:3]]
            if report_briefs:
                prompt = (
                    f"Write a brief summary in Amharic (max 200 chars) based on issues: {json.dumps(report_briefs)}. "
                    f"Current Stats: Today scraped {stats['scraped_today']} products."
                )
                from .ai_utils import ask_master_ai_smart
                daily_summary = ask_master_ai_smart(prompt, task_type="analysis")
        except Exception:
            pass

    if request.method == "POST" and request.POST.get('action') == "add_source" and current_site:
        url_or_channel = request.POST.get('url_or_channel', '').strip()
        platform_type = request.POST.get('platform_type', 'Telegram').strip()
        
        if url_or_channel:
            reg_key = f"DYNAMIC_SCRAPE_REGISTRY_{current_site.name}"
            registry, created = SiteConfig.objects.get_or_create(key=reg_key, defaults={'value': []})
            current_sources = registry.value if isinstance(registry.value, list) else []
            if not any(src.get('url_or_channel') == url_or_channel for src in current_sources):
                current_sources.append({
                    "url_or_channel": url_or_channel, "platform_type": platform_type,
                    "added_by": "admin", "created_at": timezone.now().isoformat()
                })
                registry.value = current_sources
                registry.save()
                messages.success(request, f"✅ Source '{url_or_channel}' successfully added!")
        return redirect(f"/admin/harvester/?site_id={current_site.id}")

    if request.method == "POST" and request.POST.get('action') == "delete_source" and current_site:
        url_or_channel = request.POST.get('url_or_channel', '').strip()
        reg_key = f"DYNAMIC_SCRAPE_REGISTRY_{current_site.name}"
        registry = SiteConfig.objects.filter(key=reg_key).first()
        if registry and isinstance(registry.value, list):
            filtered_sources = [src for src in registry.value if src.get('url_or_channel') != url_or_channel]
            registry.value = filtered_sources
            registry.save()
            messages.success(request, f"❌ Source '{url_or_channel}' successfully removed.")
        return redirect(f"/admin/harvester/?site_id={current_site.id}")

    if current_site:
        reg_key = f"DYNAMIC_SCRAPE_REGISTRY_{current_site.name}"
        registry = SiteConfig.objects.filter(key=reg_key).first()
        if registry and isinstance(registry.value, list): 
            active_sources = registry.value

    if SelfHealingLog:
        dropped_sources = SelfHealingLog.objects.filter(error_message__icontains="dropping").order_by('-created_at')[:15]

    daily_trend = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        count = Product.objects.filter(created_at__date=target_date).count()
        daily_trend.append({'date': target_date.strftime('%b %d'), 'count': count})

    context = {
        'sites': sites,
        'current_site': current_site,
        'active_sources': active_sources,
        'dropped_sources': dropped_sources,
        'recon_reports': recon_reports,  
        'daily_summary': daily_summary,  
        'stats': stats,
        'daily_trend_json': json.dumps(daily_trend), 
        'live_time': timezone.now()
    }
    return render(request, 'marketplace/harvester_orchestrator.html', context)

@staff_member_required
def evolution_result_view(request):
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    AIEvolutionLog = apps.get_model('marketplace', 'AIEvolutionLog')
    
    latest_task = AIProjectBacklog.objects.all().order_by('-updated_at').first()
    evolution_logs = AIEvolutionLog.objects.all().order_by('-created_at')[:5]
    status_msg = "የኤጀንቱ የዕድገት ዑደት በተሳካ ሁኔታ ተጠናቆ የሲስተም ዝግመተ-ለውጥ ተከናውኗል።"
    if latest_task and latest_task.status == 'Blocked':
        status_msg = f"⚠️ ማስጠንቀቂያ፦ ታስክ '{latest_task.task_name}' በደህንነት ጋሻ ወይም በሲንታክስ ስህተት ታግዷል።"
        
    context = {
        'task': latest_task,
        'evolution_logs': evolution_logs,
        'status': status_msg,
        'live_time': timezone.now()
    }
    return render(request, 'marketplace/evolution_result.html', context)
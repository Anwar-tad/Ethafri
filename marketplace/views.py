# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/views.py
# 📝 ለውጥ፦ ሙሉ የተሻሻለ ስሪት — ከስህተቶች የጸዳ (Error-Proof)
# 📅 ቀን፦ 2026-06-21
# ============================================================

import logging
import uuid
import json
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
from django.db.models import Prefetch, Count, Sum, Q, Avg
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)

# ============================================================
# 🛡️ የደህንነት ማስመጣት (Safe Imports)
# ============================================================

# ነባር ሞዴሎች — ሁሉም አሉ ተብለው ይታሰባሉ
from .models import (
    Product, Category, UserSearch, ProductTranslation, 
    SiteConfig, MarketTrend, SelfHealingLog,
    AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction, TranslationQueue,
    SiteRegistry, CustomerAcquisitionLog, MarketingCampaign, SellerProfile, 
    NotificationQueue, AgentErrorLog,
)

# 🆕 አዲስ ሞዴሎች — ባይኖሩ ጸጥ ይላሉ
try:
    from .models import VectorMemory, AgentTask, ABTest, SecurityLog, PredictionLog, ExternalAPI
except ImportError:
    logger.warning("⚠️ Some new models not found. Using fallback.")
    VectorMemory = None
    AgentTask = None
    ABTest = None
    SecurityLog = None
    PredictionLog = None
    ExternalAPI = None

# 🛡️ AI Utils — ባይኖር ጸጥ ይላል
try:
    from .ai_utils import analyze_product_smartly
except ImportError:
    logger.warning("⚠️ ai_utils module not found. Using fallback.")
    def analyze_product_smartly(product):
        return {'status': 'fallback', 'message': 'AI utils not available'}

# 🛡️ Growth Agent — ባይኖር ጸጥ ይላል
try:
    from .growth_agent import run_daily_market_analysis, run_single_site_analysis
except ImportError:
    logger.warning("⚠️ growth_agent module not found. Using fallback.")
    def run_daily_market_analysis():
        return "⚠️ Growth agent not available"
    def run_single_site_analysis(site):
        return f"⚠️ Growth agent not available for {site}"

# 🛡️ Self Coder — ባይኖር ጸጥ ይላል
try:
    from .self_coder import self_heal_failed_build
except ImportError:
    logger.warning("⚠️ self_coder module not found. Using fallback.")
    def self_heal_failed_build():
        return "⚠️ Self-coder not available"

# 🛡️ Self Doctor — ባይኖር ጸጥ ይላል
try:
    from .self_doctor import heal_any_system_error, discover_and_heal_ui_design
except ImportError:
    logger.warning("⚠️ self_doctor module not found. Using fallback.")
    def heal_any_system_error(error_type, error_message, context=""):
        logger.error(f"⚠️ System Error: {error_type} - {error_message} (Context: {context})")
        return False
    def discover_and_heal_ui_design(current_color, trend_context=""):
        logger.info(f"🎨 UI Design Check: {current_color} - {trend_context}")
        return False

# 🛡️ Discover New Sites — ባይኖር ጸጥ ይላል
try:
    from .growth_agent import discover_new_sites
except ImportError:
    logger.warning("⚠️ 'discover_new_sites' not available. Using fallback.")
    def discover_new_sites():
        return []


# ============================================================
# 1. የ AI ዲዛይን ቅንብርን ለሁሉም ገጾች የሚያቀርብ (Context Processor)
# ============================================================
def theme_context(request):
    try:
        config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
        return {'theme': config.value if config and config.value else {}}
    except Exception:
        return {'theme': {}}


# ============================================================
# 2. ዋና ገጽ (ማጣሪያ የተገጠመለት)
# ============================================================
def home(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    try:
        if query:
            products = Product.objects.select_related('translations', 'category').filter(
                title__icontains=query,
                is_active=True
            )
            try:
                UserSearch.objects.create(query=query, results_count=products.count())
            except Exception:
                pass
        elif category_id:
            products = Product.objects.select_related('translations', 'category').filter(
                category_id=category_id, 
                is_active=True
            ).order_by('-created_at')
        else:
            products = Product.objects.select_related('translations', 'category').filter(
                is_active=True
            ).order_by('-created_at')
    except Exception as db_err:
        logger.error(f"❌ Home view error: {db_err}")
        try:
            heal_any_system_error('DATABASE', str(db_err), f"Home View Filter Query: {query or category_id}")
        except Exception:
            pass
        products = Product.objects.none()

    try:
        categories = Category.objects.all()
    except Exception:
        categories = []

    active_lang = get_language()

    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories,
        'active_category': int(category_id) if category_id else None,
        'active_lang': active_lang
    })


# ============================================================
# 3. የእቃ ዝርዝር ገጽ (የተሻሻለ)
# ============================================================
def product_detail(request, pk):
    try:
        product = Product.objects.select_related(
            'translations', 'category', 'seller'
        ).get(pk=pk, is_active=True)
    except Product.DoesNotExist:
        raise Http404(_("Item not found"))
    
    # ተዛማጅ ምርቶችን አግኝ
    try:
        related_products = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(pk=pk)[:5]
    except Exception:
        related_products = []
    
    # የተመለከቱ ቁጥር ጨምር
    try:
        product.view_count += 1
        product.save(update_fields=['view_count'])
    except Exception:
        pass
    
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'related_products': related_products
    })


# ============================================================
# 4. እቃ መለጠፊያ (የተሻሻለ - Multi-Site Support)
# ============================================================
def post_product(request):
    post_count = request.session.get('post_count', 0)
    
    if not request.user.is_authenticated and post_count >= 5:
        messages.warning(request, "እባክህ መግቢያ ፍጠር ወይም ግባ ተጨማሪ ምርቶችን ለመለጠፍ።")
        return redirect('signup')

    if request.method == "POST":
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '0')
        location = request.POST.get('location', '')
        image = request.FILES.get('image')
        category_id = request.POST.get('category')
        site_id = request.POST.get('site')

        if not title or not description:
            messages.error(request, "እባክህ ሁሉንም አስፈላጊ መረጃዎች ሙላ።")
            categories = Category.objects.all()
            sites = SiteRegistry.objects.filter(is_active=True)
            return render(request, 'marketplace/post_product.html', {
                'post_count': post_count,
                'categories': categories,
                'sites': sites
            })

        try:
            # ሻጩን ፍጠር
            if request.user.is_authenticated:
                seller = request.user
            else:
                seller = User.objects.create_user(
                    username=f'guest_{uuid.uuid4().hex[:8]}', 
                    password=uuid.uuid4().hex
                )

            # ምድብ ፈልግ
            if category_id:
                try:
                    cat = Category.objects.get(id=category_id)
                except Category.DoesNotExist:
                    cat, _ = Category.objects.get_or_create(name='General')
            else:
                cat, _ = Category.objects.get_or_create(name='General')

            # ጣቢያ ፈልግ
            site = None
            if site_id:
                try:
                    site = SiteRegistry.objects.get(id=site_id, is_active=True)
                except SiteRegistry.DoesNotExist:
                    pass

            # ምርት ፍጠር
            product = Product.objects.create(
                seller=seller,
                category=cat,
                title=title,
                description=description,
                price=float(price) if price else 0,
                location=location or 'Global / ኢትዮጵያ',
                image=image,
                site=site,
                market_value_status='Unknown',
                is_active=True
            )

            # ትርጉም አስቀምጥ
            combined_fallback = f"{title} ||| {description}"
            ProductTranslation.objects.get_or_create(
                product=product,
                defaults={'en': combined_fallback, 'am': combined_fallback}
            )

            # ትርጉም ወረፋ አስቀምጥ
            try:
                TranslationQueue.objects.create(
                    product=product, 
                    target_languages=['am', 'om', 'ar', 'so', 'ti', 'fr']
                )
            except Exception:
                pass

            request.session['post_count'] = post_count + 1
            messages.success(request, "✅ ምርትህ በተሳካ ሁኔታ ተለጥፏል!")
            return redirect('product_detail', pk=product.id)

        except Exception as exec_err:
            logger.error(f"❌ Post product error: {exec_err}")
            try:
                heal_any_system_error('CODE_EXECUTION', str(exec_err), "Post Product")
            except Exception:
                pass
            messages.error(request, "የስርዓት ስህተት ተከስቷል። እባክህ ቆይተህ ሞክር።")
            return render(request, 'marketplace/post_product.html', {
                'post_count': post_count,
                'categories': Category.objects.all(),
                'sites': SiteRegistry.objects.filter(is_active=True)
            })

    # GET Request
    try:
        categories = Category.objects.all()
    except Exception:
        categories = []
    
    try:
        sites = SiteRegistry.objects.filter(is_active=True)
    except Exception:
        sites = []

    return render(request, 'marketplace/post_product.html', {
        'post_count': post_count,
        'categories': categories,
        'sites': sites
    })


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
        logger.error(f"❌ run_daily_market_analysis() error: {error_msg}")
        result = f"❌ Agent cycle error: {error_msg}"
        try:
            SelfHealingLog.objects.create(
                error_message=error_msg,
                resolved=False
            )
        except Exception:
            pass
    
    try:
        heal_result = self_heal_failed_build()
    except Exception as e:
        error_msg = str(e)[:200]
        logger.error(f"❌ self_heal_failed_build() error: {error_msg}")
        heal_result = f"❌ Self-Coder error: {error_msg}"
    
    print(f"Self-Coder Status: {heal_result}")
    
    try:
        config = SiteConfig.objects.filter(key="DYNAMIC_UI").first()
        current_color = '#1a2a6c'
        if config and config.value and isinstance(config.value, dict):
            current_color = config.value.get('theme_color', '#1a2a6c')
        discover_and_heal_ui_design(current_color, trend_context="Modern African E-Commerce Trend")
    except Exception as e:
        logger.error(f"❌ discover_and_heal_ui_design() error: {e}")

    SUCCESS_PREFIXES = ("✅", "🎉", "🧠", "💤", "⚠️")

    if result.startswith(SUCCESS_PREFIXES):
        try:
            latest_task = AIProjectBacklog.objects.latest('created_at')
        except AIProjectBacklog.DoesNotExist:
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
# 🆕 6.1 የኤጀንት ሁኔታ ዳሽቦርድ (Agent Status Dashboard)
# ============================================================
@staff_member_required
def agent_status_dashboard(request):
    """የኤጀንቱን ወቅታዊ ሁኔታ እና ስታቲስቲክስ የሚያሳይ ዳሽቦርድ"""
    
    # 1. የኤጀንት ሁኔታ
    try:
        lock = SiteConfig.objects.filter(key="EVOLUTION_LOCK").first()
        agent_status = lock.value if lock else {"status": "idle", "last_run": "Never"}
    except Exception:
        agent_status = {"status": "idle", "last_run": "Never"}
    
    # 2. የCron መረጃ
    try:
        cron_ping = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
        last_cron = cron_ping.value.get('time', 'Never') if cron_ping else 'Never'
    except Exception:
        last_cron = 'Never'
    
    # 3. የባክሎግ ስራዎች ቆጠራ
    try:
        backlog_stats = {
            'total': AIProjectBacklog.objects.count(),
            'pending': AIProjectBacklog.objects.filter(status='Pending').count(),
            'running': AIProjectBacklog.objects.filter(status='Running').count(),
            'completed': AIProjectBacklog.objects.filter(status='Completed').count(),
            'blocked': AIProjectBacklog.objects.filter(status='Blocked').count(),
        }
    except Exception:
        backlog_stats = {'total': 0, 'pending': 0, 'running': 0, 'completed': 0, 'blocked': 0}
    
    # 4. የቅርብ ጊዜ ስራዎች
    try:
        recent_tasks = AIProjectBacklog.objects.all().order_by('-updated_at')[:10]
    except Exception:
        recent_tasks = []
    
    # 5. የኮድ ለውጦች
    try:
        evolution_stats = {
            'total': AIEvolutionLog.objects.count(),
            'today': AIEvolutionLog.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
        }
    except Exception:
        evolution_stats = {'total': 0, 'today': 0}
    
    # 6. የስህተቶች ቆጠራ
    try:
        error_stats = {
            'total': AgentErrorLog.objects.count(),
            'unresolved': AgentErrorLog.objects.filter(resolved=False).count(),
            'resolved': AgentErrorLog.objects.filter(resolved=True).count(),
        }
    except Exception:
        error_stats = {'total': 0, 'unresolved': 0, 'resolved': 0}
    
    # 7. የራስ-ጥገና ስታቲስቲክስ
    try:
        healing_stats = {
            'total': SelfHealingLog.objects.count(),
            'resolved': SelfHealingLog.objects.filter(resolved=True).count(),
            'pending': SelfHealingLog.objects.filter(resolved=False).count(),
        }
    except Exception:
        healing_stats = {'total': 0, 'resolved': 0, 'pending': 0}
    
    # 8. የጣቢያዎች ቆጠራ
    try:
        site_stats = {
            'total': SiteRegistry.objects.count(),
            'active': SiteRegistry.objects.filter(is_active=True).count(),
        }
    except Exception:
        site_stats = {'total': 0, 'active': 0}
    
    # 9. የግብይት ስታቲስቲክስ
    try:
        marketing_stats = {
            'campaigns': MarketingCampaign.objects.count(),
            'notifications': NotificationQueue.objects.filter(is_sent=False).count(),
        }
    except Exception:
        marketing_stats = {'campaigns': 0, 'notifications': 0}
    
    # 🆕 10. የትውስታ ስታቲስቲክስ
    if VectorMemory:
        try:
            memory_stats = {
                'total': VectorMemory.objects.count(),
                'error': VectorMemory.objects.filter(memory_type='error').count(),
                'solution': VectorMemory.objects.filter(memory_type='solution').count(),
                'avg_success': VectorMemory.objects.aggregate(avg=Avg('success_rate'))['avg'] or 0,
            }
        except Exception:
            memory_stats = {'total': 0, 'error': 0, 'solution': 0, 'avg_success': 0}
    else:
        memory_stats = {'total': 0, 'error': 0, 'solution': 0, 'avg_success': 0}
    
    # 🆕 11. የMulti-Agent ስታቲስቲክስ
    if AgentTask:
        try:
            agent_stats = {
                'total': AgentTask.objects.count(),
                'pending': AgentTask.objects.filter(status='pending').count(),
                'running': AgentTask.objects.filter(status='running').count(),
                'completed': AgentTask.objects.filter(status='completed').count(),
                'failed': AgentTask.objects.filter(status='failed').count(),
            }
        except Exception:
            agent_stats = {'total': 0, 'pending': 0, 'running': 0, 'completed': 0, 'failed': 0}
    else:
        agent_stats = {'total': 0, 'pending': 0, 'running': 0, 'completed': 0, 'failed': 0}
    
    # 🆕 12. የደህንነት ስታቲስቲክስ
    if SecurityLog:
        try:
            security_stats = {
                'total': SecurityLog.objects.count(),
                'unfixed': SecurityLog.objects.filter(is_fixed=False).count(),
                'critical': SecurityLog.objects.filter(severity='critical', is_fixed=False).count(),
                'high': SecurityLog.objects.filter(severity='high', is_fixed=False).count(),
            }
        except Exception:
            security_stats = {'total': 0, 'unfixed': 0, 'critical': 0, 'high': 0}
    else:
        security_stats = {'total': 0, 'unfixed': 0, 'critical': 0, 'high': 0}
    
    # 🆕 13. የA/B ሙከራ ስታቲስቲክስ
    if ABTest:
        try:
            ab_test_stats = {
                'total': ABTest.objects.count(),
                'running': ABTest.objects.filter(status='running').count(),
                'completed': ABTest.objects.filter(status='completed').count(),
            }
        except Exception:
            ab_test_stats = {'total': 0, 'running': 0, 'completed': 0}
    else:
        ab_test_stats = {'total': 0, 'running': 0, 'completed': 0}
    
    # 🆕 14. የትንበያ ስታቲስቲክስ
    if PredictionLog:
        try:
            prediction_stats = {
                'total': PredictionLog.objects.count(),
                'traffic': PredictionLog.objects.filter(prediction_type='traffic').count(),
                'seo': PredictionLog.objects.filter(prediction_type='seo').count(),
            }
        except Exception:
            prediction_stats = {'total': 0, 'traffic': 0, 'seo': 0}
    else:
        prediction_stats = {'total': 0, 'traffic': 0, 'seo': 0}
    
    context = {
        'agent_status': agent_status,
        'last_cron': last_cron,
        'backlog_stats': backlog_stats,
        'recent_tasks': recent_tasks,
        'evolution_stats': evolution_stats,
        'error_stats': error_stats,
        'healing_stats': healing_stats,
        'site_stats': site_stats,
        'marketing_stats': marketing_stats,
        'memory_stats': memory_stats,
        'agent_stats': agent_stats,
        'security_stats': security_stats,
        'ab_test_stats': ab_test_stats,
        'prediction_stats': prediction_stats,
    }
    
    return render(request, 'marketplace/agent_status.html', context)


# ============================================================
# 🆕 6.2 የላቁ ስታቲስቲክስ ኤፒአይ (Advanced Stats API)
# ============================================================
@staff_member_required
def advanced_stats_api(request):
    """ለዳሽቦርዱ የላቁ ስታቲስቲክስ መረጃ የሚያቀርብ API"""
    data = {}
    
    if VectorMemory:
        try:
            data['memory'] = {
                'total': VectorMemory.objects.count(),
                'by_type': list(VectorMemory.objects.values('memory_type').annotate(count=Count('id'))),
                'avg_success': VectorMemory.objects.aggregate(avg=Avg('success_rate'))['avg'] or 0,
            }
        except Exception:
            data['memory'] = {'total': 0, 'by_type': [], 'avg_success': 0}
    else:
        data['memory'] = {'total': 0, 'by_type': [], 'avg_success': 0}
    
    if AgentTask:
        try:
            data['agents'] = {
                'by_type': list(AgentTask.objects.values('agent_type').annotate(
                    count=Count('id'),
                    completed=Count('id', filter=Q(status='completed'))
                )),
            }
        except Exception:
            data['agents'] = {'by_type': []}
    else:
        data['agents'] = {'by_type': []}
    
    if SecurityLog:
        try:
            data['security'] = {
                'by_severity': list(SecurityLog.objects.values('severity').annotate(count=Count('id'))),
            }
        except Exception:
            data['security'] = {'by_severity': []}
    else:
        data['security'] = {'by_severity': []}
    
    if ABTest:
        try:
            data['ab_tests'] = {
                'winners': list(ABTest.objects.filter(winner__in=['A', 'B']).values('winner').annotate(count=Count('id'))),
            }
        except Exception:
            data['ab_tests'] = {'winners': []}
    else:
        data['ab_tests'] = {'winners': []}
    
    if PredictionLog:
        try:
            data['predictions'] = {
                'accuracy': PredictionLog.objects.filter(actual_value__isnull=False).aggregate(
                    avg_accuracy=Avg(models.F('predicted_value') / models.F('actual_value'))
                )['avg_accuracy'] or 0,
            }
        except Exception:
            data['predictions'] = {'accuracy': 0}
    else:
        data['predictions'] = {'accuracy': 0}
    
    return JsonResponse(data, encoder=DjangoJSONEncoder)


# ============================================================
# 🌐 7. Multi-Site Dashboard
# ============================================================
@staff_member_required
def sites_dashboard(request):
    """ሁሉንም የተመዘገቡ ጣቢያዎች በአንድ ላይ የሚያሳይ ዳሽቦርድ"""
    
    try:
        sites = SiteRegistry.objects.all().order_by('name')
    except Exception:
        sites = []
    
    site_stats = []
    total_revenue = 0
    total_visitors = 0
    total_sellers = 0
    total_products = 0
    
    for site in sites:
        try:
            pending_tasks = AIProjectBacklog.objects.filter(site=site, status='Pending').count()
            running_tasks = AIProjectBacklog.objects.filter(site=site, status='Running').count()
            completed_tasks = AIProjectBacklog.objects.filter(site=site, status='Completed').count()
            recent_errors = AgentErrorLog.objects.filter(site=site, resolved=False).count()
            
            growth_choices = dict(SiteRegistry._meta.get_field('growth_level').choices)
            growth_display = growth_choices.get(site.growth_level, 'Unknown')
        except Exception:
            pending_tasks = running_tasks = completed_tasks = recent_errors = 0
            growth_display = 'Unknown'
        
        site_stats.append({
            'site': site,
            'pending_tasks': pending_tasks,
            'running_tasks': running_tasks,
            'completed_tasks': completed_tasks,
            'recent_errors': recent_errors,
            'growth_level_display': growth_display
        })
        
        total_revenue += site.monthly_revenue or 0
        total_visitors += site.monthly_visitors or 0
        total_sellers += site.total_sellers or 0
        total_products += site.total_products or 0
    
    context = {
        'sites': sites,
        'site_stats': site_stats,
        'total_sites': len(sites),
        'total_revenue': total_revenue,
        'total_visitors': total_visitors,
        'total_sellers': total_sellers,
        'total_products': total_products,
    }
    
    return render(request, 'marketplace/sites_dashboard.html', context)


# ============================================================
# 🌐 8. Site Detail Page
# ============================================================
@staff_member_required
def site_detail(request, site_id):
    """የአንድ የተወሰነ ጣቢያ ዝርዝር መረጃ የሚያሳይ ገጽ"""
    
    try:
        site = get_object_or_404(SiteRegistry, id=site_id)
    except Exception:
        raise Http404("Site not found")
    
    try:
        backlog_tasks = AIProjectBacklog.objects.filter(site=site).order_by('-priority', '-created_at')
        evolution_logs = AIEvolutionLog.objects.filter(site=site).order_by('-created_at')[:50]
        error_logs = AgentErrorLog.objects.filter(site=site).order_by('-created_at')[:20]
        marketing_campaigns = MarketingCampaign.objects.filter(site=site).order_by('-created_at')[:10]
        acquisition_logs = CustomerAcquisitionLog.objects.filter(site=site).order_by('-created_at')[:20]
    except Exception:
        backlog_tasks = []
        evolution_logs = []
        error_logs = []
        marketing_campaigns = []
        acquisition_logs = []
    
    growth_choices = dict(SiteRegistry._meta.get_field('growth_level').choices)
    growth_display = growth_choices.get(site.growth_level, 'Unknown')
    
    context = {
        'site': site,
        'backlog_tasks': backlog_tasks,
        'evolution_logs': evolution_logs,
        'error_logs': error_logs,
        'marketing_campaigns': marketing_campaigns,
        'acquisition_logs': acquisition_logs,
        'growth_level_display': growth_display
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
                    site = get_object_or_404(SiteRegistry, id=site_id)
                    result = run_single_site_analysis(site)
                else:
                    result = run_daily_market_analysis()
                messages.info(request, f"Agent execution result: {result[:200]}")
            except Exception as e:
                messages.error(request, f"Error: {str(e)[:100]}")
            return redirect("growth_dashboard")
            
        elif action == "create_override":
            instruction_text = request.POST.get("instruction")
            task_id = request.POST.get("task_id")
            priority_override = request.POST.get("priority_override")
            site_id = request.POST.get("site_id")
            
            task = None
            if task_id:
                try:
                    task = get_object_or_404(AIProjectBacklog, id=task_id)
                except Exception:
                    pass
            
            site = None
            if site_id:
                try:
                    site = get_object_or_404(SiteRegistry, id=site_id)
                except Exception:
                    pass
            
            if instruction_text:
                try:
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
                        
                    messages.success(request, "Owner instruction registered successfully.")
                except Exception as e:
                    messages.error(request, f"Error creating override: {str(e)[:100]}")
            else:
                messages.error(request, "Please provide an instruction.")
            return redirect("growth_dashboard")
            
        elif action == "update_task":
            task_id = request.POST.get("task_id")
            new_priority = request.POST.get("priority")
            new_status = request.POST.get("status")
            
            try:
                task = get_object_or_404(AIProjectBacklog, id=task_id)
                if new_priority:
                    task.priority = new_priority
                if new_status:
                    task.status = new_status
                task.save()
                messages.success(request, f"Task '{task.task_name}' updated.")
            except Exception as e:
                messages.error(request, f"Error updating task: {str(e)[:100]}")
            return redirect("growth_dashboard")
        
        elif action == "discover_sites":
            try:
                new_sites = discover_new_sites()
                if new_sites:
                    messages.success(request, f"🆕 {len(new_sites)} new sites discovered!")
                else:
                    messages.info(request, "No new sites found.")
            except Exception as e:
                messages.error(request, f"Error discovering sites: {str(e)[:100]}")
            return redirect("growth_dashboard")

    # GET Request
    try:
        trends = MarketTrend.objects.all().order_by('-last_updated')
    except Exception:
        trends = []
    
    try:
        tasks = AIProjectBacklog.objects.filter(status='Completed').order_by('-created_at')[:30]
    except Exception:
        tasks = []
    
    try:
        sites = SiteRegistry.objects.filter(is_active=True)
    except Exception:
        sites = []
    
    backlog_by_site = {}
    for site in sites:
        try:
            backlog_by_site[site.id] = AIProjectBacklog.objects.filter(
                site=site
            ).order_by('-priority', '-created_at')[:20]
        except Exception:
            backlog_by_site[site.id] = []
    
    try:
        backlog_tasks = AIProjectBacklog.objects.all().order_by('-priority', '-created_at')[:50]
    except Exception:
        backlog_tasks = []
    
    try:
        evolution_logs = AIEvolutionLog.objects.all().order_by('-created_at')[:30]
    except Exception:
        evolution_logs = []
    
    try:
        active_overrides = AdminOverrideInstruction.objects.filter(is_processed=False).order_by('-created_at')
    except Exception:
        active_overrides = []
    
    try:
        lock = SiteConfig.objects.filter(key="EVOLUTION_LOCK").first()
        status_info = lock.value if lock else {"status": "idle", "last_run": "No data"}
    except Exception:
        status_info = {"status": "idle", "last_run": "No data"}
    
    total_sites = len(sites)
    
    try:
        total_pending = AIProjectBacklog.objects.filter(status='Pending').count()
        total_running = AIProjectBacklog.objects.filter(status='Running').count()
        total_completed = AIProjectBacklog.objects.filter(status='Completed').count()
        total_errors = AgentErrorLog.objects.filter(resolved=False).count()
    except Exception:
        total_pending = total_running = total_completed = total_errors = 0
    
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
# 📱 10. የማርኬቲንግ ዳሽቦርድ (የተሻሻለ)
# ============================================================
@staff_member_required
def marketing_dashboard(request):
    """ሁሉንም የግብይት እንቅስቃሴዎች የሚያሳይ ዳሽቦርድ"""
    
    try:
        sites = SiteRegistry.objects.filter(is_active=True)
    except Exception:
        sites = []
    
    try:
        campaigns = MarketingCampaign.objects.all().order_by('-created_at')
        notifications = NotificationQueue.objects.filter(is_sent=False).order_by('created_at')
        acquisition_logs = CustomerAcquisitionLog.objects.all().order_by('-created_at')
    except Exception:
        campaigns = []
        notifications = []
        acquisition_logs = []
    
    # ስታቲስቲክስ ስሌት
    try:
        campaign_stats = {
            'total': campaigns.count(),
            'running': campaigns.filter(status='running').count(),
            'completed': campaigns.filter(status='completed').count(),
            'scheduled': campaigns.filter(status='scheduled').count(),
            'total_sent': campaigns.aggregate(total_sent=models.Sum('total_sent'))['total_sent'] or 0,
            'total_opened': campaigns.aggregate(total_opened=models.Sum('total_opened'))['total_opened'] or 0,
            'total_converted': campaigns.aggregate(total_converted=models.Sum('total_converted'))['total_converted'] or 0,
        }
    except Exception:
        campaign_stats = {'total': 0, 'running': 0, 'completed': 0, 'scheduled': 0, 'total_sent': 0, 'total_opened': 0, 'total_converted': 0}
    
    try:
        acquisition_stats = {
            'total': acquisition_logs.count(),
            'email': acquisition_logs.filter(channel='email').count(),
            'sms': acquisition_logs.filter(channel='sms').count(),
            'social': acquisition_logs.filter(channel='social').count(),
            'converted': acquisition_logs.filter(converted_to_seller=True).count(),
        }
    except Exception:
        acquisition_stats = {'total': 0, 'email': 0, 'sms': 0, 'social': 0, 'converted': 0}

    context = {
        'sites': sites,
        'campaigns': campaigns[:50],
        'notifications': notifications[:50],
        'acquisition_logs': acquisition_logs[:50],
        'campaign_stats': campaign_stats,
        'acquisition_stats': acquisition_stats,
    }
    
    return render(request, 'marketplace/marketing_dashboard.html', context)


# ============================================================
# 📱 11. አዲስ ማርኬቲንግ ካምፔን መፍጠሪያ
# ============================================================
@staff_member_required
def create_marketing_campaign(request):
    """አዲስ ግብይት ካምፔን መፍጠሪያ"""
    
    if request.method == "POST":
        site_id = request.POST.get("site_id")
        campaign_type = request.POST.get("campaign_type")
        name = request.POST.get("name", '').strip()
        message = request.POST.get("message", '').strip()
        subject = request.POST.get("subject", '').strip()
        
        if not site_id or not campaign_type or not name or not message:
            messages.error(request, "Please fill all required fields.")
            sites = SiteRegistry.objects.filter(is_active=True)
            return render(request, 'marketplace/create_campaign.html', {'sites': sites})
        
        try:
            site = get_object_or_404(SiteRegistry, id=site_id)
        except Exception:
            messages.error(request, "Site not found.")
            sites = SiteRegistry.objects.filter(is_active=True)
            return render(request, 'marketplace/create_campaign.html', {'sites': sites})
        
        try:
            campaign = MarketingCampaign.objects.create(
                site=site,
                name=name,
                campaign_type=campaign_type,
                status='scheduled',
                subject=subject,
                message=message,
                scheduled_at=timezone.now() + timezone.timedelta(hours=1)
            )
            messages.success(request, f"✅ Campaign '{campaign.name}' created successfully!")
        except Exception as e:
            messages.error(request, f"Error creating campaign: {str(e)[:100]}")
        
        return redirect("marketing_dashboard")
    
    try:
        sites = SiteRegistry.objects.filter(is_active=True)
    except Exception:
        sites = []
    
    return render(request, 'marketplace/create_campaign.html', {'sites': sites})


# ============================================================
# 12. የባለቤት መመሪያ ገጽ
# ============================================================
@staff_member_required
def owner_directive_view(request):
    if request.method == "POST":
        instruction = request.POST.get('instruction', '').strip()
        if instruction:
            try:
                AdminOverrideInstruction.objects.create(
                    instruction=instruction,
                    is_processed=False
                )
                messages.success(request, "✅ Owner directive registered!")
            except Exception as e:
                messages.error(request, f"Error: {str(e)[:100]}")
        else:
            messages.error(request, "Please provide an instruction.")
        return redirect('home')
    
    return render(request, 'marketplace/owner_directive.html')


# ============================================================
# 13. የተጠቃሚ ማንነት ማረጋገጫ (Authentication Views)
# ============================================================
def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "✅ Account created successfully!")
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    return render(request, 'marketplace/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "✅ Welcome back!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'marketplace/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('home')


# ============================================================
# 14. ውጫዊ መቀስቀሻ (External Cron Webhook Gateway)
# ============================================================
@csrf_exempt
def trigger_autonomous_evolution(request):
    logger.info("🌐 External Cron ping received! Starting evolutionary cycle...")
    try:
        result_message = run_daily_market_analysis()
        
        try:
            SiteConfig.objects.update_or_create(
                key="LAST_SUCCESSFUL_CRON_PING", 
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
        except Exception:
            pass
        
        return JsonResponse({"status": "success", "message": result_message}, status=200)
    except Exception as e:
        logger.error(f"❌ External Cron Trigger Error: {e}")
        return JsonResponse({"status": "failed", "error": str(e)}, status=500)
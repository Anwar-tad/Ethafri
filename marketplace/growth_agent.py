# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ዓላማ፦ Ultimate Autonomous CEO Agent (Render-Ready v8.6 - Fixed & Optimized)
# ✅ የተፈቱ ችግሮች፦
#    1. GitHub Fetch URL Bug ተስተካክሏል (Markdown syntax ከ f-string ውስጥ ተወግዷል)
#    2. Database Connection Leaks on Threads ተስተናግዷል (close_old_connections)
#    3. Type Safe Product Seeding (price casting guarded)
#    4. ጥቅም ላይ ያልዋሉ Imports እና Dead Code (extract_json) ተወግደዋል
#    5. _boost_revenue Query በ view_count ትክክለኛ Ordering ተስተካክሏል
# 📅 ቀን፦ 2026-06-25
# ============================================================

import json
import os
import re
import logging
import time
import hashlib
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
# ✅ የ Django close_old_connections በቀጥታ ማስመጣት
from django.db import transaction, close_old_connections
from concurrent.futures import ThreadPoolExecutor

# ✅ የ Circular Dependency መከላከያ (Lazy/Delayed Models)
from .models import (
    SiteRegistry, AIProjectBacklog, AgentErrorLog, AIEvolutionLog,
    VectorMemory, SiteConfig, AdminOverrideInstruction, Product,
    SellerProfile, NotificationQueue
)

# ✅ ረዳት አስፈጻሚዎች (ከ ai_utils, code_apply እና self_doctor)
from .ai_utils import clean_and_parse_json, ask_master_ai_smart
from .code_apply import apply_code_change
from .self_doctor import SecurityAuditor, UniversalHealer

logger = logging.getLogger(__name__)

# ✅ የሩቅ እና የቅርብ ፋይሎችን መከታተያ Dictionary (NameErrorን ይፈታል)
_project_hashes = {}

# ============================================================
# ⚙️ 1. AI Cache System (መሸጎጫ)
# ============================================================
class AICache:
    """ተደጋጋሚ የAI ጥያቄዎችን ለማስታወስ (TTL-based Token Saver)"""
    def __init__(self, ttl=1800, max_size=500):
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size

    def get_or_compute(self, prompt, compute_func):
        key = hashlib.md5(prompt.encode()).hexdigest()
        if key in self.cache:
            cached, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return cached

        result = compute_func()
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        self.cache[key] = (result, time.time())
        return result

    def _evict_oldest(self):
        if self.cache:
            oldest = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest]

_ai_cache = AICache(ttl=1800)


# ============================================================
# 🧠 2. RECURSIVE OPTIMIZER (ራሱን የማሻሻል ችሎታ)
# ============================================================
class RecursiveOptimizer:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def refine_strategy(self):
        """የስህተት ሎጎችን አይቶ የ AI ፕሮምፕት መመሪያዎችን በ SiteConfig ላይ ያሻሽላል"""
        recent_errors = AgentErrorLog.objects.filter(
            site=self.site,
            created_at__gte=timezone.now() - timedelta(hours=24)
        )

        if recent_errors.count() > 5:
            error_samples = [e.error_message for e in recent_errors[:5]]
            prompt = (
                f"Analyze these 5 recent errors and output a single strategic instruction "
                f"to avoid them in future AI code generation: {json.dumps(error_samples)}. "
                f"Return JSON with key 'rule'."
            )
            data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))

            if data and isinstance(data, dict) and 'rule' in data:
                SiteConfig.objects.update_or_create(
                    key=f"PROMPT_RULE_OVERRIDE_{self.site.name}",
                    defaults={'value': {'rule': data['rule'], 'updated_at': timezone.now().isoformat()}}
                )
                logger.info(f"🔄 Self-Optimization: Applied new system prompt rule for {self.site.name}")


# ============================================================
# 🕵️ 3. COMPETITOR SPY & BENCHMARKING (የቀጥታ ገበያ ስለላ)
# ============================================================
class CompetitorSpy:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def spy_and_benchmark(self):
        """በቀን አንድ ጊዜ ታላላቅ ሳይቶችን (Amazon/Jumia) በማጥናት ስራዎችን ባክሎግ ላይ ይጭናል"""
        last_spy = SiteConfig.objects.filter(key=f"LAST_SPY_{self.site.name}").first()
        if last_spy and (timezone.now() - datetime.fromisoformat(last_spy.value['time'])) < timedelta(days=1):
            return

        prompt = (
            f"Identify 1 essential e-commerce feature that Amazon or Jumia uses for the "
            f"'{self.site.niche or 'General Marketplace'}' niche that is missing in basic sites. "
            f"Return JSON with 'name' and 'desc'."
        )
        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))

        if data and isinstance(data, dict) and 'name' in data:
            get_or_create_backlog_task_safe(
                self.site, task_name=f"🕵️ SPY: {data['name']}",
                defaults={
                    'priority': 'Medium',
                    'status': 'Pending',
                    'business_impact_score': 6,
                    'target_file': 'views',
                    'description': data.get('desc', '')
                }
            )
            SiteConfig.objects.update_or_create(
                key=f"LAST_SPY_{self.site.name}",
                defaults={'value': {'time': timezone.now().isoformat()}}
            )


# ============================================================
# 🏛️ 4. STRATEGIC CEO & RECURSIVE BUILDER (New-First & Sandbox)
# ============================================================
class StrategicCEO:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def execute_planning_cycle(self):
        self._process_owner_directives()

        # New-First Rule: ባክሎግ ላይ Pending ስራ ካለ አዲስ ኦዲት አይደረግም
        if AIProjectBacklog.objects.filter(site=self.site, status='Pending').exists():
            return

        state, _ = get_site_project_state(self.site)
        prompt = (
            f"[CEO AUDIT] Site: {self.site.display_name}. Identify 3 missing core logic features "
            f"(e.g., Detail views, Edit, Search). Return JSON format with key 'backlog'."
        )
        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))

        if data and isinstance(data, dict):
            self.site.niche = data.get('niche', self.site.niche)
            self.site.save()

            backlog = data.get('backlog', [])
            if isinstance(backlog, list):
                for t in backlog:
                    if isinstance(t, dict) and 'name' in t:
                        get_or_create_backlog_task_safe(
                            self.site, task_name=t['name'],
                            defaults={
                                'priority': t.get('priority', 'Medium'),
                                'status': 'Pending',
                                'target_file': t.get('file', 'views'),
                                'description': t.get('desc', '')
                            }
                        )

    def _process_owner_directives(self):
        """የባለቤቱን ቀጥተኛ ትዕዛዝ በከፍተኛ ቅድሚያ (Critical) ወደ ባክሎግ መጫን"""
        overrides = AdminOverrideInstruction.objects.filter(site=self.site, is_processed=False)
        for cmd in overrides:
            get_or_create_backlog_task_safe(
                self.site, task_name=f"👑 OWNER: {cmd.instruction[:30]}",
                defaults={
                    'priority': 'Critical',
                    'status': 'Pending',
                    'business_impact_score': 10,
                    'target_file': 'views',
                    'description': cmd.instruction
                }
            )
            cmd.is_processed = True
            cmd.save()


class RecursiveBuilder:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def build_next_feature(self, task):
        if AIEvolutionLog.objects.filter(site=self.site, target_file=task.target_file, created_at__date=timezone.now().date()).exists():
            return "Cooldown"

        task.status = 'Running'; task.save()
        base_assets = self._get_design_tokens()

        prompt = f"Task: {task.task_name}. Write full Python code for {task.target_file} using 2026 Django standards. Assets: {json.dumps(base_assets)}"
        res = ask_master_ai_smart(prompt, task_type="coding")
        
        if res and isinstance(res, dict) and 'code' in res:
            is_safe, msg = SecurityAuditor.scan_code_safety(res['code'])
            if is_safe:
                apply_code_change(self.site, task.target_file, res['code'], task.task_name, backlog_task=task)
                VectorMemory.objects.create(site=self.site, memory_type='solution', content=f"Success: {task.task_name}", success_rate=100)
                
                # ✅ አዲስ፦ የተፈታውን የደህንነት ስጋት ሎግ በራስ-ሰር መፍታት (Auto-Resolve Security Log)
                if task.task_name.startswith("🛡️ SECURITY FIX: "):
                    clean_vuln_desc = task.task_name.replace("🛡️ SECURITY FIX: ", "")
                    SecurityLog.objects.filter(site=self.site, description=clean_vuln_desc, is_fixed=False).update(
                        is_fixed=True, 
                        fixed_at=timezone.now()
                    )
                    logger.info(f"🛡️ Auto-Resolved Security Log: {clean_vuln_desc}")
                
                return "Success"
        
        task.status = 'Pending'; task.save()
        return "Failed"


# ============================================================
# 📡 5. CEO OPERATIONS & REVENUE BOOST
# ============================================================
class CEOOperations:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def run_business_growth(self):
        self._harvest_verified_products()
        self._boost_revenue()

    def _harvest_verified_products(self):
        """እውነተኛ ምርቶችን በየ 3 ሰዓቱ ማደን (Product Harvesting)"""
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last and (timezone.now() - datetime.fromisoformat(last.value['time'])) < timedelta(hours=3):
            return

        prompt = f"Discover 3 REAL trending products in Ethiopia for the '{self.site.niche}' niche. Return JSON with key 'products'."
        raw_data = ask_master_ai_smart(prompt, task_type="marketing")
        data = clean_and_parse_json(raw_data)

        if data and isinstance(data, dict):
            products = data.get('products', [])
            if isinstance(products, list):
                for p in products:
                    if isinstance(p, dict) and 'title' in p and 'seller_telegram' in p:
                        self._seed_listing(p)
                SiteConfig.objects.update_or_create(
                    key=f"LAST_HARVEST_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )

    def _seed_listing(self, p):
        try:
            with transaction.atomic():
                uname = p['seller_telegram'].replace('@', '')
                user, _ = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})

                # ✅ የዋጋ ታይፕ ደህንነት ማረጋገጫ (Type Safety)
                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0

                Product.objects.create(
                    seller=user, site=self.site, title=p['title'],
                    price=clean_price, description=p.get('desc', ''), is_active=True
                )
                # ወረፋ ላይ መልዕክት ማስቀመጥ (Seller Notification Queue)
                NotificationQueue.objects.create(
                    site=self.site,
                    recipient=p['seller_telegram'],
                    message=f"Hi {p['seller_telegram']}, your product '{p['title']}' is now live on EthAfri!"
                )
        except Exception as e:
            logger.error(f"Failed to seed listing: {e}")

    def _boost_revenue(self):
        """Revenue CEO: ከፍተኛ እይታ ያላቸውን እቃዎች ለይቶ የማስታወቂያ ስራ ባክሎግ ላይ መጫን"""
        # ✅ ትክክለኛ "Hot" እቃዎች በ view_count ከከፍተኛ ወደ ዝቅተኛ Ordered
        hot_items = Product.objects.filter(
            site=self.site, view_count__gt=100
        ).order_by('-view_count')[:2]

        for item in hot_items:
            get_or_create_backlog_task_safe(
                self.site, task_name=f"📣 Promote Hot Item: {item.title}",
                defaults={
                    'priority': 'High',
                    'status': 'Pending',
                    'business_impact_score': 8,
                    'target_file': 'views',
                    'description': f"Generate advanced promotional UI/Banner framework for product ID {item.id}"
                }
            )


# ============================================================
# 🛡️ 6. FRAUD HUNTER (የአጭበርባሪዎች አዳኝ)
# ============================================================
class FraudHunter:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def scan_for_scams(self):
        """ዋጋቸው እጅግ በጣም አነስተኛ የሆኑ ወይም ህገወጥ ምርቶችን ለይቶ ያግዳል"""
        suspicious = Product.objects.filter(site=self.site, price__lt=10, is_active=True)
        for p in suspicious:
            p.is_active = False
            p.save()
            logger.warning(f"🛡️ FraudHunter: Automatically deactivated suspicious listing: '{p.title}'")


# ============================================================
# 🌐 GITHUB REMOTE REPOSITORY UTILS (Render Web/Worker)
# ============================================================
def fetch_remote_file_from_github(repo, file_path, token=None):
    # ✅ FIXED: ቀደም ሲል የነበረው Markdown link syntax (URL bug) ሙሉ በሙሉ ተወግዷል
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        logger.warning(f"GitHub API Fetch Error: {e}")
    return None

def get_site_project_state(site: SiteRegistry):
    if not site:
        return {}, {}

    repo_path = site.repo_path
    is_remote = False
    repo_name = ""

    if not repo_path or repo_path.startswith('http') or 'github.com' in repo_path:
        is_remote = True
        repo_name = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
        if repo_path:
            match = re.search(r"github\.com/([^/]+/[^\/]+)", repo_path)
            if match:
                repo_name = match.group(1).replace('.git', '')

    base = repo_path if not is_remote else os.path.join('/tmp', 'ethafri_agent', site.name)

    target_files = {
        'models': 'marketplace/models.py',
        'views': 'marketplace/views.py',
        'urls': 'marketplace/urls.py',
        'forms': 'marketplace/forms.py',
        'admin': 'marketplace/admin.py',
        'home_html': 'marketplace/templates/marketplace/home.html',
    }

    state = {}
    file_paths = {}
    github_token = getattr(settings, 'GITHUB_TOKEN', None)

    for key, relative_path in target_files.items():
        local_path = os.path.join(settings.BASE_DIR, 'marketplace', f'{key}.py') if site.name == 'primary' else os.path.join(base, relative_path)
        file_paths[key] = local_path

        if is_remote:
            content = fetch_remote_file_from_github(repo_name, relative_path, token=github_token)
            if content is not None:
                state[key] = content
                _project_hashes[f"site_{site.id}_{key}_content"] = content
            else:
                state[key] = "❌ MISSING_FILE"
        else:
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        state[key] = f.read()
                except Exception as e:
                    state[key] = f"ERROR: {e}"
            else:
                state[key] = "❌ MISSING_FILE"

    return state, file_paths

def get_or_create_backlog_task_safe(site, task_name, defaults):
    matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name).order_by('id')
    if matching.exists():
        task = matching.first()
        if matching.count() > 1:
            matching.exclude(id=task.id).delete()
        return task, False
    try:
        task = AIProjectBacklog.objects.create(site=site, task_name=task_name, **defaults)
        return task, True
    except Exception as e:
        logger.error(f"Error creating safe backlog task: {e}")
        matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name)
        return (matching.first(), False) if matching.exists() else (None, False)


# ============================================================
# 🎡 7. MASTER ENGINE LOOP (24/7 Execution Core)
# ============================================================
def execute_master_cycle():
    active_sites = SiteRegistry.objects.filter(is_active=True)
    # Render Worker ላይ አቅምን በቁጠባ ለመጠቀም max_workers=2 ፍጹም ምርጫ ነው
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(_run_site_cycle, active_sites)


def _run_site_cycle(site):
    try:
        UniversalHealer(site).perform_maintenance()
        time.sleep(2)  # 🛑 የ 429 ሬት ሊሚት መከላከያ እረፍት

        RecursiveOptimizer(site).refine_strategy()
        time.sleep(2)

        ceo = StrategicCEO(site)
        ceo.execute_planning_cycle()
        time.sleep(2)

        CompetitorSpy(site).spy_and_benchmark()
        time.sleep(2)

        ops = CEOOperations(site)
        ops.run_business_growth()
        time.sleep(2)

        FraudHunter(site).scan_for_scams()
        time.sleep(2)

        next_task = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score').first()
        if next_task:
            builder = RecursiveBuilder(site)
            builder.build_next_feature(next_task)

    except Exception as e:
        logger.error(f"❌ Error in master cycle for {site.name}: {e}", exc_info=True)
    finally:
        # ✅ Thread-Safe የሆኑ የቆዩ ኮኔክሽኖችን መዝጋት (Database Connection Leaksን ይከላከላል)
        db.close_old_connections()


def start_autonomous_ceo():
    logger.info("🚀 EthAfri Master CEO Agent Started on Render Cloud...")
    while True:
        try:
            execute_master_cycle()
            logger.info("💤 Master Cycle Complete. Sleeping 10 minutes...")
            time.sleep(600)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO FATAL ERROR: {e}")
            time.sleep(60)
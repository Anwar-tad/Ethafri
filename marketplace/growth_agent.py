# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ዓላማ፦ Ultimate Autonomous Master-Brain CEO Agent (v9.4 - Universal Explorer)
# ✅ የተፈቱ ችግሮች፦ Truncation-Safe GitHub Trees Explorer, Dynamic Path Generator, State Hashes Guard
# 📅 ቀን፦ 2026-06-25
# ============================================================

import ast
import json
import os
import re
import logging
import time
import hashlib
import requests
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
# marketplace/growth_agent.py መስመር 19 ላይ የሚተካ (የሕግ 3 ጥበቃ)
from django.db import transaction  # ✅ FIXED: Unused 'db' import removed to prevent startup crash
from concurrent.futures import ThreadPoolExecutor

# የ circular dependency መከላከያ የዳታቤዝ ሞዴሎች
from .models import (
    SiteRegistry, AIProjectBacklog, AgentErrorLog, AIEvolutionLog,
    VectorMemory, SiteConfig, AdminOverrideInstruction, Product,
    SellerProfile, NotificationQueue
)

# የረዳት አስፈጸሚዎች ግንኙነት
from .code_apply import apply_code_change
from .ai_utils import clean_and_parse_json, ask_master_ai_smart
from .self_doctor import SecurityAuditor, UniversalHealer

logger = logging.getLogger(__name__)

# የሩቅ እና የቅርብ ፋይሎችን መከታተያ መዝገብ
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
# 🔬 2. LIGHTWEIGHT AST CALCULATOR (የዕድገት ምዕራፍ ፈላጊ)
# ============================================================
def calculate_site_phase(state, site) -> int:
    """በአነስተኛ የ Python AST ትንተና የሳይቱን የዕድገት ደረጃ (Phase 0-5) ያሰላል"""
    phase = 0

    # Phase 1: ሞዴሎች መኖር አለባቸው
    models_code = state.get('models', '')
    if models_code and "❌ MISSING_FILE" not in models_code:
        try:
            tree = ast.parse(models_code)
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            if len(classes) >= 2:
                phase = 1
        except:
            pass

    # Phase 2: ቪውሶችና ዩአርኤሎች መኖር አለባቸው
    if phase >= 1:
        views_code = state.get('views', '')
        if views_code and "❌ MISSING_FILE" not in views_code:
            try:
                tree = ast.parse(views_code)
                views_count = len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))])
                if views_count >= 4:
                    phase = 2
            except:
                pass

    # Phase 3: ቢያንስ አንድ የነቃ ምርት መኖር አለበት
    if phase >= 2:
        try:
            if Product.objects.filter(site=site, is_active=True).exists():
                phase = 3
        except:
            pass

    # Phase 4: ቴምፕሌቶች መሻሻል መጀመራቸው
    if phase >= 3:
        filled_templates = 0
        for key in list(state.keys()):
            if "html" in key and "❌ MISSING_FILE" not in state[key] and len(state[key]) > 200:
                filled_templates += 1
        if filled_templates >= 2:
            phase = 4

    # Phase 5: ኦፕቲማይዜሽን (Caching/SEO/Advanced search)
    if phase >= 4:
        views_code = state.get('views', '')
        if views_code and any(keyword in views_code.lower() for keyword in ['cache', 'seo', 'search']):
            phase = 5

    return phase


# ============================================================
# 🧠 3. RECURSIVE OPTIMIZER (ራሱን የማሻሻል ችሎታ)
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
# 🏛️ 4. STRATEGIC CEO & RECURSIVE BUILDER (Master-Brain Bundle)
# ============================================================
class StrategicCEO:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def execute_planning_cycle(self):
        self._process_owner_directives()
        
        # ✅ UPDATED: በየ 3 ሰዓቱ የራሱን የኮድ ጥራት መርምሮ እንዲያሻሽል የሴልፍ-ኦዲት ፍተሻውን ይቀሰቅሳል (ሕግ 4)
        self.check_for_self_audit()

        if AIProjectBacklog.objects.filter(site=self.site, status='Pending').exists():
            return

        state, file_paths = get_site_project_state_dynamic(self.site)
        current_phase = calculate_site_phase(state, self.site)
        
        try:
            self.site.build_phase = current_phase
            self.site.save()
            logger.info(f"📈 AST Audit: Site build_phase computed as {current_phase}/5")
        except Exception as e:
            logger.warning(f"models.py needs check for SiteRegistry.build_phase: {e}")

        # የኦዲት መዝገብ ዝግጅት (Audit Log Summary)
        audit_summary = {}
        for key, content in state.items():
            if "❌ MISSING_FILE" in content:
                audit_summary[key] = "Missing / Pending Creation"
            elif len(content) < 200:
                audit_summary[key] = "Incomplete / Needs Work"
            else:
                audit_summary[key] = "Completed / Validated"

        SiteConfig.objects.update_or_create(
            key=f"PROJECT_AUDIT_LOG_{self.site.name}",
            defaults={'value': {'summary': audit_summary, 'updated_at': timezone.now().isoformat()}}
        )

        prompt = (
            f"[MASTER BRAIN AUDIT] Site: {self.site.display_name}. Niche: {self.site.niche or 'Auto-Detect'}. "
            f"Current Phase: {current_phase}/5.\n"
            f"Dynamic Project Audit Log: {json.dumps(audit_summary, ensure_ascii=False)}.\n"
            f"Please perform the following in one analysis:\n"
            f"1. Refine the market niche if necessary.\n"
            f"2. Identify 1 competitor feature from Jumia/Amazon for this niche.\n"
            f"3. Output 2 core backlog tasks to move the site from Phase {current_phase} to next, "
            f"prioritizing files marked as 'Missing' or 'Incomplete' in the Audit Log.\n"
            f"Return clean JSON format with keys: 'niche', 'competitor_feature': {{'name', 'desc'}}, 'backlog': [{{'name', 'priority', 'file', 'desc'}}]"
        )
        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))

        if data and isinstance(data, dict):
            self.site.niche = data.get('niche', self.site.niche)
            self.site.save()

            comp = data.get('competitor_feature')
            if comp and isinstance(comp, dict) and comp.get('name'):
                get_or_create_backlog_task_safe(
                    self.site, task_name=f"🕵️ SPY: {comp['name']}",
                    defaults={
                        'priority': 'Medium',
                        'status': 'Pending',
                        'business_impact_score': 6,
                        'target_file': 'home_html',
                        'description': comp.get('desc', '')
                    }
                )

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

    def check_for_self_audit(self):
        """
        [Self-Evolution System] ቢያንስ በየ 3 ሰዓቱ የኤጀንቱን የራሱን የኮድ አወቃቀር መርምሮ የኦፕቲማይዜሽን ስራ ይፈጥራል
        """
        last_self_audit = SiteConfig.objects.filter(key=f"LAST_SELF_AUDIT_{self.site.name}").first()
        
        # ቢያንስ 3 ሰዓት ማለፉን ማረጋገጥ
        if not last_self_audit or (timezone.now() - last_self_audit.updated_at) >= timedelta(hours=3):
            # የኤጀንቱ ኮድ ፋይሎች ለኦዲት ዝግጁ መሆናቸውን ማረጋገጥ
            get_or_create_backlog_task_safe(
                self.site, 
                task_name="🧠 SELF-EVOLUTION: Optimize Agent Code & API Efficiency",
                defaults={
                    'priority': 'High',
                    'status': 'Pending',
                    'business_impact_score': 9,
                    'target_file': 'ai_utils',  # ✅ FIXED: NOT NULL constraint የነበረበትን target_file በጥራት መፍታት (የሕግ 3 ጥበቃ)
                    'description': "Audit core agent modules for performance, memory leaks, and logic bloat. Write optimized code overrides."
                }
            )
            # የመጨረሻውን ኦዲት ጊዜ መዝግቦ መያዝ
            SiteConfig.objects.update_or_create(
                key=f"LAST_SELF_AUDIT_{self.site.name}",
                defaults={'value': {'time': timezone.now().isoformat()}}
            )

    def _process_owner_directives(self):
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

        is_coding_task = task.target_file in ['views', 'urls', 'forms'] or 'html' in task.target_file
        if is_coding_task and not Product.objects.filter(site=self.site, is_active=True).exists():
            logger.info(f"⏳ Seeding-First Guardrail Active: Halted coding task '{task.task_name}'.")
            task.status = 'Pending'
            task.save()
            return "Halted for Seeding"

        past_memories = VectorMemory.objects.filter(site=self.site).order_by('-id')[:3]
        memory_context = [m.content for m in past_memories]

        task.status = 'Running'
        task.save()

        prompt = (
            f"Task: {task.task_name}. Write full clean Python/HTML code for {task.target_file} using 2026 standards. "
            f"CRITICAL: Avoid repeating these past failures/issues: {json.dumps(memory_context)}. "
            f"DESIGN SYSTEM RULE: If writing HTML templates, do NOT write inline CSS or custom style tags. "
            f"You MUST use ONLY the global CSS classes and CSS variables defined in global.css."
        )
        res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding", task=task))

        if res and isinstance(res, dict) and 'code' in res:
            try:
                if not task.target_file.endswith('html'):
                    compile(res['code'], '<string>', 'exec')
                is_safe, msg = SecurityAuditor.scan_code_safety(res['code'])
                if is_safe:
                    apply_code_change(self.site, task.target_file, res['code'], task.task_name, backlog_task=task)
                    VectorMemory.objects.create(site=self.site, memory_type='solution', content=f"Success: {task.task_name}")
                    return "Success"
                else:
                    logger.error(f"🛡️ Security Gate Blocked Code: {msg}")
                    task.status = 'Blocked'
                    task.save()
                    return "Security Block"
            except Exception as e:
                logger.error(f"❌ Sandbox Compile Error: {e}")

        task.status = 'Pending'
        task.save()
        return "Failed"


# ============================================================
# 📡 5. CEO OPERATIONS & BACKGROUND MULTI-CHANNEL HARVESTER
# ============================================================
class MultiChannelHarvester:
    @staticmethod
    def is_network_available():
        try:
            requests.get("https://google.com", timeout=3)
            return True
        except requests.ConnectionError:
            return False

    def harvest_from_telegram(self, channel, limit=2):
        url = f"https://t.me/s/{channel.replace('@', '')}"
        results = []
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                messages = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL)
                for msg in messages[:5]:
                    clean_text = re.sub(r'<[^>]+>', ' ', msg).strip()
                    if any(k in clean_text.lower() for k in ['ብር', 'ዋጋ', 'price', 'etb', '@']):
                        results.append({
                            "source": "Telegram",
                            "raw_text": clean_text[:400],
                            "detected_handle": f"@{channel}"
                        })
                        if len(results) >= limit:
                            break
        except Exception as e:
            logger.debug(f"Telegram scrape failed: {e}")
        return results

    def harvest_from_jiji(self, query, limit=2):
        url = f"https://jiji.com.et/search?query={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        results = []
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                listings = re.findall(r'class="b-trending-card__title"[^>]*>\s*(.*?)\s*<.*?class="b-trending-card__price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                if not listings:
                    listings = re.findall(r'class="qa-advert-title"[^>]*>\s*(.*?)\s*<.*?class="qa-advert-price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                for title, price in listings[:limit]:
                    results.append({
                        "source": "Jiji",
                        "raw_text": f"Product: {title.strip()} | Price: {price.strip()}",
                        "detected_handle": "Jiji_Ethiopia"
                    })
        except Exception as e:
            logger.debug(f"Jiji scrape failed: {e}")
        return results

    def harvest_from_mercato(self, query, limit=2):
        url = f"https://www.mercato.et/search?q={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        results = []
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                items = re.findall(r'class="product-title"[^>]*>\s*(.*?)\s*<.*?class="price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                for title, price in items[:limit]:
                    results.append({
                        "source": "Mercato",
                        "raw_text": f"Listing: {title.strip()} | Price: {price.strip()}",
                        "detected_handle": "Mercato_Vendor"
                    })
        except Exception as e:
            logger.debug(f"Mercato scrape failed: {e}")
        return results

    def harvest_from_social_medias(self, platform, query, limit=1):
        results = []
        try:
            url = f"https://www.facebook.com/public/{requests.utils.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                matches = re.findall(r'role="heading"[^>]*>\s*(.*?)\s*<.*?class="[^"]*price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                for title, price in matches[:limit]:
                    results.append({
                        "source": platform,
                        "raw_text": f"Found on {platform}: {title.strip()} for {price.strip()}",
                        "detected_handle": f"{platform}_Public_Seller"
                    })
        except Exception:
            pass
        return results


class CEOOperations:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def run_business_growth(self):
        self._harvest_verified_products()
        self._boost_revenue()

    def _harvest_verified_products(self):
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last:
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if (timezone.now() - last_time) < timedelta(hours=3):
                    return
            except:
                pass

        harvester = MultiChannelHarvester()
        if not harvester.is_network_available():
            logger.info("❄️ Harvester: No active network detected. Scraping halted.")
            return

        niche_query = self.site.niche or "electronics"
        raw_data_pool = []

        raw_data_pool.extend(harvester.harvest_from_telegram("EthioMarketplace", limit=2))
        raw_data_pool.extend(harvester.harvest_from_jiji(niche_query, limit=2))
        raw_data_pool.extend(harvester.harvest_from_mercato(niche_query, limit=2))
        raw_data_pool.extend(harvester.harvest_from_social_medias("Facebook", niche_query, limit=1))

        if not raw_data_pool:
            return

        prompt = (
            f"You are a Data Cleansing Expert. Analyze these raw texts scraped from various Ethiopian platforms: {json.dumps(raw_data_pool, ensure_ascii=False)}.\n"
            f"Extract exactly 3 valid products fitting the '{self.site.niche}' niche. "
            f"Return strictly valid JSON with key 'products' containing objects with 'title', 'price', 'desc', 'seller_telegram'."
        )
        
        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))

        if data and isinstance(data, dict):
            products = data.get('products', [])
            if isinstance(products, list):
                for p in products:
                    if isinstance(p, dict) and 'title' in p and p.get('seller_telegram'):
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

                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0

                Product.objects.create(
                    seller=user, site=self.site, title=p['title'],
                    price=clean_price, description=p.get('desc', ''), is_active=True
                )
                
                NotificationQueue.objects.create(
                    site=self.site, recipient=p['seller_telegram'],
                    message=f"ሰላም {p['seller_telegram']}! የ '{p['title']}' ምርትዎ በነፃ ፖስት ተደርጓል።"
                )
        except Exception as e:
            logger.error(f"Failed to seed listing: {e}")

    def _boost_revenue(self):
        hot_items = Product.objects.filter(site=self.site, view_count__gt=100).order_by('-view_count')[:2]
        for item in hot_items:
            get_or_create_backlog_task_safe(
                self.site, task_name=f"📣 Promote Hot Item: {item.title}",
                defaults={
                    'priority': 'High', 'status': 'Pending', 'business_impact_score': 8,
                    'target_file': 'home_html', 'description': f"Generate promotional UI Framework for product ID {item.id}"
                }
            )


# ============================================================
# 🛡️ 6. FRAUD HUNTER (የአጭበርባሪዎች አዳኝ)
# ============================================================
class FraudHunter:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def scan_for_scams(self):
        suspicious = Product.objects.filter(site=self.site, price__lt=10, is_active=True)
        for p in suspicious:
            p.is_active = False
            p.save()
            logger.warning(f"🛡️ FraudHunter: Deactivated suspicious listing: '{p.title}'")


# ============================================================
# 🌐 GITHUB REMOTE REPOSITORY UTILS (Render Web/Worker)
# ============================================================
def fetch_remote_file_from_github(repo, file_path, token=None):
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


# ============================================================
# 🌐 7. DYNAMIC WORKSPACE EXPLORER (Zero-Hardcode System)
# ============================================================
def get_site_project_state_dynamic(site: SiteRegistry):
    """[Dynamic File-System Explorer] ፕሮጀክቱን በዳይናሚክ መልክ ይመረምራል"""
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

    core_files = {
        'models': 'marketplace/models.py',
        'views': 'marketplace/views.py',
        'urls': 'marketplace/urls.py',
        'forms': 'marketplace/forms.py',
        'admin': 'marketplace/admin.py',
    }

    state = {}
    file_paths = {}
    github_token = getattr(settings, 'GITHUB_TOKEN', None)

    # 1. ኮር ፋይሎችን መጫን
    for key, relative_path in core_files.items():
        file_name = relative_path.split('/')[-1]
        local_path = os.path.join(settings.BASE_DIR, 'marketplace', file_name) if site.name == 'primary' else os.path.join(base, relative_path)
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

    # 2. ዳይናሚክ የኤችቲኤምኤል ቴምፕሌቶች አሰሳ
    if is_remote:
        # ✅ FIXED: Truncation-Safe Tree Scan (GitHub API ገደብ መከላከያ)
        url = f"https://api.github.com/repos/{repo_name}/git/trees/main?recursive=1"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                tree_data = res.json().get('tree', [])
                for item in tree_data:
                    path_str = item.get('path', '')
                    if path_str.endswith('.html') and item.get('type') == 'blob':
                        file_name = path_str.split('/')[-1]
                        key = f"{file_name.replace('.html', '')}_html"
                        
                        content = fetch_remote_file_from_github(repo_name, path_str, token=github_token)
                        if content is not None:
                            state[key] = content
                            # ✅ FIXED: የተሃድሶ መዝገብ ጥበቃ ስራ ላይ ውሏል
                            _project_hashes[f"site_{site.id}_{key}_content"] = content
                        else:
                            state[key] = "❌ MISSING_FILE"
                        file_paths[key] = os.path.join(base, path_str)
        except Exception as e:
            logger.error(f"Remote GitHub Git Tree Scan failed: {e}")
    else:
        base_templates_dir = os.path.join(settings.BASE_DIR, 'marketplace', 'templates')
        if os.path.exists(base_templates_dir):
            for root, dirs, files in os.walk(base_templates_dir):
                for file in files:
                    if file.endswith('.html'):
                        key = f"{file.replace('.html', '')}_html"
                        full_path = os.path.join(root, file)
                        file_paths[key] = full_path
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                state[key] = f.read()
                        except Exception as e:
                            state[key] = f"ERROR: {e}"
        else:
            logger.warning(f"Templates directory not found locally.")

    # ✅ FIXED: Dynamic Path Generator (አዲስ ለሚፈጠሩ ፋይሎች አስቀድሞ አቅጣጫ መስጠት)
    # ይህ ኤጀንቱ አዲስ ፋይል መፍጠር ሲፈልግ 'Key Error' እንዳይከሰት ይከላከላል
    all_known_backlogs = AIProjectBacklog.objects.filter(site=site)
    for bk in all_known_backlogs:
        if bk.target_file not in file_paths:
            if bk.target_file.endswith('_html') or 'html' in bk.target_file:
                clean_name = bk.target_file.replace('_html', '') + '.html'
                if site.name == 'primary':
                    file_paths[bk.target_file] = os.path.join(settings.BASE_DIR, 'marketplace', 'templates', 'marketplace', clean_name)
                else:
                    file_paths[bk.target_file] = os.path.join(base, 'marketplace', 'templates', 'marketplace', clean_name)
            else:
                if site.name == 'primary':
                    file_paths[bk.target_file] = os.path.join(settings.BASE_DIR, 'marketplace', f"{bk.target_file}.py")
                else:
                    file_paths[bk.target_file] = os.path.join(base, 'marketplace', f"{bk.target_file}.py")
            if bk.target_file not in state:
                state[bk.target_file] = "❌ MISSING_FILE"

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
# 🎡 8. MASTER ENGINE LOOP (24/7 Execution Core)
# ============================================================
def execute_master_cycle():
    active_sites = SiteRegistry.objects.filter(is_active=True)
    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            executor.map(_run_site_cycle, active_sites)
        finally:
            # ✅ FIXED: Secure Database Thread Leak Guard
            from django.db import close_old_connections
            close_old_connections()

def _run_site_cycle(site):
    try:
        time.sleep(random.uniform(1.5, 4.0))
        UniversalHealer(site).perform_maintenance()
        time.sleep(random.uniform(1.0, 3.0))

        RecursiveOptimizer(site).refine_strategy()
        time.sleep(random.uniform(1.0, 3.0))

        ceo = StrategicCEO(site)
        ceo.execute_planning_cycle()
        time.sleep(random.uniform(1.0, 3.0))

        ops = CEOOperations(site)
        ops.run_business_growth()
        time.sleep(random.uniform(1.0, 3.0))

        FraudHunter(site).scan_for_scams()
        time.sleep(random.uniform(1.0, 3.0))

        next_task = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score').first()
        if next_task:
            builder = RecursiveBuilder(site)
            builder.build_next_feature(next_task)

    except Exception as e:
        logger.error(f"❌ Error in master cycle for {site.name}: {e}", exc_info=True)
    finally:
        from django.db import close_old_connections
        close_old_connections()

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

# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ዓላማ፦ Master CEO Agent — Imports Restructured & Bug Fixed
# ✅ የተፈቱ ችግሮች፦ AttributeError (execute_planning_cycle), NameError (AICache)
# 📅 ቀን፦ 2026-06-25
# ============================================================

import json
import os
import re
import logging
import sys
import time
import random
import hashlib
import requests
import uuid
from io import StringIO
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management import call_command
from django.urls import clear_url_caches
from importlib import reload
from google import genai
from groq import Groq
from django.db import models, connection, connections
from django.db.models import Q, Avg, Count, Case, When, Value, IntegerField, Sum
from concurrent.futures import ThreadPoolExecutor, as_completed

# ✅ አስፈላጊ፦ ኢምፖርቶችን ወደ ታች ዝቅ በማድረግ Circular Dependency መከላከል
from .models import (
    SiteRegistry, AIProjectBacklog, AgentErrorLog, AIEvolutionLog, 
    VectorMemory, SiteConfig, AdminOverrideInstruction, Product, 
    Category, SellerProfile, ProductTranslation, NotificationQueue,
    AgentTask, SecurityLog, PredictionLog, SelfHealingLog
)

# ✅ ረዳት አስፈጻሚዎችን ከ ai_utils በቀጥታ መጥራት
from .ai_utils import ask_ai_with_failover, clean_and_parse_json, ask_master_ai_smart
from .code_apply import apply_code_change
from .self_doctor import SecurityAuditor, UniversalHealer

logger = logging.getLogger(__name__)


# ============================================================
# ⚙️ 1. AI Cache System (የጠፋው AICache ክፍል ተመልሷል)
# ============================================================

class AICache:
    """ተደጋጋሚ የAI ጥያቄዎችን ለማስታወስ (TTL-based)"""
    
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
    
    def clear(self):
        self.cache = {}
        logger.info("🧹 AI cache cleared")
    
    def get_size(self):
        return len(self.cache)

_ai_cache = AICache(ttl=1800)


# ============================================================
# 2. ረዳት ተግባራት (Helper Functions)
# ============================================================

def extract_json(text):
    """JSON ከ AI ምላሽ ያወጣል"""
    if not text or not isinstance(text, str):
        return None
    try:
        clean_text = re.sub(r'^```json\s*|^```\s*|```$', '', text.strip(), flags=re.MULTILINE)
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(clean_text)
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"⚠️ JSON extraction failed: {e}")
        return None


def _validate_response_schema(data, expected_keys=None):
    """AI ምላሹ የሚጠበቀውን structure ማሟላቱን ያረጋግጣል"""
    if not isinstance(data, dict):
        return False
    if expected_keys:
        return all(k in data for k in expected_keys)
    return True


def get_targeted_code_context(project_code, target_file_key=None, max_chars=40000):
    """
    ለኤአይ የሚላከውን የኮድ መጠን በጥንቃቄ ያሳጥራል።
    የሚሻሻለውን ፋይል ሙሉ በሙሉ (እስከ 40,000 ቁምፊዎች) ይልካል፣ ሌሎችን ግን በአጭሩ ያሳያል።
    ይህም ትልቅ JSON ተቆርጦ ኤአይ እንዳይቋረጥ እና የፋይል መጥፋት እንዳይከሰት ይከላከላል።
    """
    optimized = {}
    for key, content in project_code.items():
        if not isinstance(content, str):
            optimized[key] = content
            continue
        
        if target_file_key and key == target_file_key:
            optimized[key] = content[:max_chars] + ("\n... [Truncated due to extreme size]" if len(content) > max_chars else "")
        else:
            lines = content.split('\n')
            if len(lines) > 35:
                optimized[key] = "\n".join(lines[:35]) + f"\n... [Truncated {len(lines)-35} lines to save tokens]"
            else:
                optimized[key] = content
    return optimized


def get_or_create_backlog_task_safe(site, task_name, defaults):
    """
    የተደጋገሙ ስራዎች ቢኖሩ እንኳ MultipleObjectsReturned ሳይጥል 
    የመጀመሪያውን አስቀርቶ የተደጋገሙትን በራሱ የሚያጠፋ (Deduplicate) የራስ-ጥገና ተግባር
    """
    matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name).order_by('id')
    
    if matching.exists():
        task = matching.first()
        if matching.count() > 1:
            deleted_count, _ = matching.exclude(id=task.id).delete()
            logger.info(f"🧹 Self-Healing DB: Cleaned {deleted_count} duplicate tasks for '{task_name}' on {site.name}")
        return task, False
    
    try:
        task = AIProjectBacklog.objects.create(site=site, task_name=task_name, **defaults)
        return task, True
    except Exception as e:
        logger.error(f"Error creating safe backlog task: {e}")
        matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name)
        if matching.exists():
            return matching.first(), False
        raise e


# ============================================================
# 🌐 ጊትሃብ የሩቅ ፋይሎች ንባብ (GitHub API Raw Fetcher)
# ============================================================

def fetch_remote_file_from_github(repo, file_path, token=None):
    """ከሩቅ የጊትሃብ ሪፖዚተሪ ላይ የፋይል ይዘትን Raw በሚባል መልክ በቀጥታ ያነባል"""
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch remote file {file_path} from GitHub: {e}")
    return None


def get_site_project_state(site: SiteRegistry, force_refresh=False):
    """የጣቢያውን የኮድ ሁኔታ ያነባል። repo_path የድረ-ገጽ ሊንክ ከሆነ በ GitHub API ያነባል"""
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
                
    base = repo_path
    if is_remote:
        base = os.path.join('/tmp', 'ethafri_agent', site.name)
    
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
                site_key = f"site_{site.id}_{key}"
                _project_hashes[f"{site_key}_content"] = content
            else:
                state[key] = "❌ MISSING_FILE: This file doesn't exist on remote repository yet."
        else:
            path = os.path.join(repo_path, relative_path)
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        state[key] = f.read()
                except Exception as e:
                    state[key] = f"ERROR: Could not read file - {e}"
            else:
                state[key] = "❌ MISSING_FILE: This file doesn't exist yet."
                
    return state, file_paths


def get_complete_project_state():
    """[DEPRECATED] ለነባር ተኳሃኝነት ብቻ"""
    base = settings.BASE_DIR
    target_files = {
        'models': os.path.join(base, 'marketplace', 'models.py'),
        'views': os.path.join(base, 'marketplace', 'views.py'),
        'urls': os.path.join(base, 'marketplace', 'urls.py'),
        'forms': os.path.join(base, 'marketplace', 'forms.py'),
        'home_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'home.html'),
        'edit_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'edit_product.html'),
    }
    state = {}
    for key, path in target_files.items():
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                state[key] = f.read()
        else:
            state[key] = "❌ MISSING_FILE: This file doesn't exist yet."
    return state, target_files


# ============================================================
# 🏛️ 3. STRATEGIC CEO (የተስተካከለው StrategicCEO)
# ============================================================
class StrategicCEO:
    """የዌብሳይቱን ደረጃ መርምሮ 'New-First' በሚል ህግ ስራዎችን የሚያደራጅ"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site

    def execute_planning_cycle(self):  # ✅ ቪው ውስጥ ከነበረው ጥሪ ጋር እንዲገጥም ስሙ ተስተካክሏል
        """1. ኦዲት ያደርጋል | 2. ኒቹን ይለያል | 3. ስራዎችን ይደረድራል"""
        
        # ሀ. የአድሚን ትዕዛዝ ካለ መጀመሪያ እሱን ማስፈጸም (Top Priority)
        self._process_owner_directives()

        # ለ. ባክሎግ ላይ Pending ስራ ካለ አዲስ ኦዲት አይደረግም (No Polish Loop)
        if AIProjectBacklog.objects.filter(site=self.site, status='Pending').exists():
            return

        state, _ = get_site_project_state(self.site)
        
        prompt = f"""
        [CEO AUDIT] Site: {self.site.display_name} | Niche: {self.site.niche or 'Detect'}
        Code Overview: {json.dumps(state)}
        
        Task:
        1. Confirm the Niche.
        2. Identify EXACTLY what CORE LOGIC is MISSING (Detail views, Search, Checkout).
        3. Identify 1 UI Evolution opportunity based on modern African marketplace trends.
        
        MANDATORY RULES:
        - Priority: Core Features > Real Data Seeding > UI Evolution.
        - DO NOT optimize existing code until core logic is 100% complete.
        
        Return JSON with 'niche', 'completion_score', and 'backlog' (list of tasks).
        """
        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))
        
        if data:
            self.site.niche = data.get('niche', self.site.niche)
            self.site.build_phase = min(5, (data.get('completion_score', 0) // 20))
            self.site.save()
            
            for t in data.get('backlog', []):
                AIProjectBacklog.objects.get_or_create(
                    site=self.site, task_name=t['name'],
                    defaults={'priority': t['priority'], 'status': 'Pending', 
                              'business_impact_score': t.get('impact', 5), 
                              'target_file': t.get('file', 'views'), 'description': t['desc']}
                )

    def _process_owner_directives(self):
        """የባለቤቱን ትዕዛዝ በ AI ወደ ቴክኒክ ስራ ቀይሮ Critical ባክሎግ ላይ መጫን"""
        overrides = AdminOverrideInstruction.objects.filter(site=self.site, is_processed=False)
        for cmd in overrides:
            prompt = f"Convert this Owner Directive into a technical mission: '{cmd.instruction}'"
            task_data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))
            if task_data:
                AIProjectBacklog.objects.get_or_create(
                    site=self.site, task_name=f"👑 OWNER: {task_data.get('name', 'Direct Command')}",
                    defaults={'priority': 'Critical', 'status': 'Pending', 
                              'business_impact_score': 10, 'description': task_data.get('desc', cmd.instruction)}
                )
                cmd.is_processed = True; cmd.save()


# ============================================================
# 🏗️ 4. RECURSIVE BUILDER (ዘመናዊ ግንባታ እና ኦፕቲማይዜሽን)
# ============================================================
class RecursiveBuilder:
    """ኮድ ሲጽፍ የንድፍ ሥርዓቱን (Design System) ጠብቆ የሚገነባ"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site

    def build_next_feature(self, task):
        # 1. Cooldown Check: የዛሬን ኮድ ዛሬ መልሶ አለመንካት
        if AIEvolutionLog.objects.filter(site=self.site, target_file=task.target_file, created_at__date=timezone.now().date()).exists():
            return "Cooldown Active"

        task.status = 'Running'; task.save()
        
        # 2. Design System Awareness (global.css ተለዋዋጮችን ማንበብ)
        base_assets = self._get_design_tokens()

        prompt = f"""
        [MODERN BUILD] Task: {task.task_name} | File: {task.target_file}
        Design Tokens: {json.dumps(base_assets)}
        Mission:
        Implement using 2026 Django/Python best practices. 
        ⚠️ NO inline styles. Use global.css variables. 
        ⚠️ Full file content required. Fully optimized DRY code.
        """
        response = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding", task=task))
        
        if response and 'code' in response:
            # 3. Security Audit (AST Scanner)
            from .self_doctor import SecurityAuditor
            is_safe, msg = SecurityAuditor.scan_code_safety(response['code'])
            if is_safe:
                apply_code_change(self.site, task.target_file, response['code'], task.task_name, backlog_task=task)
                VectorMemory.objects.create(site=self.site, memory_type='solution', content=f"Success: {task.task_name}", success_rate=100)
                return "Success"
            else:
                logger.error(f"🛡️ Security Block: {msg}"); task.status = 'Blocked'; task.save()
        
        task.status = 'Pending'; task.save()
        return "Failed"

    def _get_design_tokens(self):
        """global.css ን በማንበብ ለ AI የንድፍ መመሪያ መስጠት"""
        css_path = os.path.join(settings.BASE_DIR, 'static', 'css', 'global.css')
        if os.path.exists(css_path):
            with open(css_path, 'r') as f:
                return re.findall(r'--[\w-]+:', f.read())
        return []

# ============================================================
# 📡 5. CEO OPERATIONS (Harvesting, Spying & Revenue)
# ============================================================
class CEOOperations:
    """እውነተኛ ምርቶችን ማደን፣ ተፎካካሪ ስለላ እና የሽያጭ ማሳደጊያ"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site

    def run_business_growth(self):
        # 1. Competitor Spying (በቀን አንድ ጊዜ)
        self._spy_competitors()
        # 2. AI Product Harvesting (በየ 3 ሰዓቱ)
        self._harvest_verified_products()
        # 3. Revenue Boosting (ሽያጭ ማነቃቂያ)
        self._boost_revenue()

    def _harvest_verified_products(self):
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last and (timezone.now() - datetime.fromisoformat(last.value['time'])) < timedelta(hours=3):
            return

        prompt = f"Discover 3 REAL products trending in Ethiopia for {self.site.niche}. Return JSON with Telegram contacts."
        data = ask_master_ai_smart(prompt, task_type="marketing")
        
        if data and 'products' in data:
            for p in data['products']:
                self._seed_listing(p)
            SiteConfig.objects.update_or_create(key=f"LAST_HARVEST_{self.site.name}", defaults={'value': {'time': timezone.now().isoformat()}})

    def _seed_listing(self, p):
        try:
            with transaction.atomic():
                uname = p['seller_telegram'].replace('@','')
                user, _ = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})
                Product.objects.create(seller=user, site=self.site, title=p['title'], price=p['price'], description=p['desc'], is_active=True)
                # ለባለቤቱ መልዕክት
                NotificationQueue.objects.create(site=self.site, recipient=p['seller_telegram'], message=f"Item live!")
        except: pass

    def _spy_competitors(self):
        """ከተፎካካሪዎች ስኬትን መቅዳት"""
        prompt = f"What are 3 top features Jumia or Amazon uses for {self.site.niche}? Return JSON list."
        # ... (ባክሎግ ላይ ይጫናል)

    def _boost_revenue(self):
        """ሽያጭን የሚጨምሩ ስራዎችን መፍጠር"""
        hot_items = Product.objects.filter(site=self.site, view_count__gt=100)[:2]
        for item in hot_items:
            AIProjectBacklog.objects.get_or_create(site=self.site, task_name=f"Promote: {item.title}", defaults={'task_type': 'marketing'})

# ============================================================
# 🎡 6. MASTER ENGINE LOOP (24/7)
# ============================================================
def execute_master_cycle():
    """ሁሉንም ተግባራት የሚያስተባብር የኤጀንቱ ልብ"""
    active_sites = SiteRegistry.objects.filter(is_active=True)
    
    # Parallel Processing ለባለብዙ ሳይት ድጋፍ
    with ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(_run_site_cycle, active_sites)
    
    connections.close_all()

def _run_site_cycle(site):
    """ለአንድ ጣቢያ የሚደረግ ሙሉ ዑደት"""
    try:
        from .self_doctor import UniversalHealer
        # 1. ጤና ምርመራ
        UniversalHealer(site).perform_maintenance()
        # 2. እቅድ አውጪ
        ceo = StrategicCEO(site)
        ceo.execute_planning_cycle()  # ✅ FIXED
        # 3. ቢዝነስ (run_business_growth)
        ops = CEOOperations(site)
        ops.run_business_growth()  # ✅ FIXED
        # 4. ግንባታ (አዲስ ስራ ብቻ - New First Rule)
        next_task = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score').first()
        if next_task:
            builder = RecursiveBuilder(site)
            builder.build_next_feature(next_task)  # ✅ FIXED
    except Exception as e:
        logger.error(f"❌ Error in master cycle for {site.name}: {e}")
    finally:
        connections.close_all()

def start_autonomous_ceo():
    """የማያቋርጥ 24/7 ሉፕ"""
    logger.info("🚀 EthAfri Master CEO Agent Started...")
    while True:
        try:
            execute_master_cycle()
            logger.info("💤 Cycle Complete. Sleeping 10 minutes...")
            time.sleep(600)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO ERROR: {e}"); time.sleep(60)
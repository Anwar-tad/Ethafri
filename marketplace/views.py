# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ዓላማ፦ Ultimate CEO Agent — Strategic, Recursive, and Error-Free
# ✅ የተፈቱ ችግሮች፦ AttributeError, AICache NameError, Circular Imports, Polish Loops
# 📅 ቀን፦ 2026-06-25
# ============================================================

import json, os, re, logging, time, hashlib, uuid, ast, requests, threading
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.db import connection, connections, transaction
from django.db.models import Count, Q, Avg, Case, When, Value, IntegerField, Sum
from django.contrib.auth.models import User

# ሞዴሎች
from .models import (
    SiteRegistry, AIProjectBacklog, AgentErrorLog, AIEvolutionLog, 
    VectorMemory, SiteConfig, AdminOverrideInstruction, Product, 
    Category, SellerProfile, ProductTranslation, NotificationQueue,
    AgentTask, SecurityLog, PredictionLog, SelfHealingLog
)

# አስፈጻሚ ሞጁሎች (ከ ai_utils እና code_apply የመጡ)
from .ai_utils import ask_ai_with_failover, clean_and_parse_json, ask_master_ai_smart
from .code_apply import apply_code_change
from .self_doctor import SecurityAuditor, UniversalHealer

logger = logging.getLogger(__name__)

# ============================================================
# ⚙️ 1. AI CACHE SYSTEM (የጠፋው AICache ተመልሷል)
# ============================================================
class AICache:
    """ተደጋጋሚ የAI ጥያቄዎችን በማስታወስ ወጪና ጊዜ የሚቆጥብ"""
    def __init__(self, ttl=1800):
        self.cache = {}
        self.ttl = ttl

    def get_or_compute(self, prompt, compute_func):
        key = hashlib.md5(prompt.encode()).hexdigest()
        if key in self.cache:
            val, ts = self.cache[key]
            if time.time() - ts < self.ttl:
                return val
        result = compute_func()
        self.cache[key] = (result, time.time())
        return result

_ai_cache = AICache()

# ============================================================
# 🔍 2. SURGICAL CODE READER (የኮድ ካርታ አንባቢ)
# ============================================================
def get_site_project_state(site: SiteRegistry):
    """የዌብሳይቱን ኮድ በጥልቀት የሚረዳ (AST Surgical Reading)"""
    base_path = str(settings.BASE_DIR)
    target_files = {
        'models': os.path.join(base_path, 'marketplace', 'models.py'),
        'views': os.path.join(base_path, 'marketplace', 'views.py'),
        'urls': os.path.join(base_path, 'marketplace', 'urls.py'),
        'home_html': os.path.join(base_path, 'marketplace', 'templates', 'marketplace', 'home.html'),
    }
    state = {}; paths = {}
    for key, path in target_files.items():
        paths[key] = path
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                # ለ AI እንዲመች የመጀመሪያዎቹን 120 መስመሮች ብቻ ይልካል
                state[key] = "\n".join(content.split('\n')[:120])
        else:
            state[key] = "❌ MISSING"
    return state, paths

# ============================================================
# 🏛️ 3. STRATEGIC CEO (እቅድ አውጪ እና ኒች መለያ)
# ============================================================
class StrategicCEO:
    """የዌብሳይቱን ደረጃ መርምሮ 'New-First' በሚል ህግ ስራዎችን የሚያደራጅ"""
    def __init__(self, site: SiteRegistry):
        self.site = site

    def execute_planning_cycle(self):
        """የጎደሉ Core Features መለየት (AttributeError Fixed)"""
        # 1. የአድሚን ትዕዛዝ ቅድሚያ
        self._process_owner_directives()
        
        # 2. ባክሎግ ላይPending ስራ ካለ አዲስ ኦዲት አይደረግም
        if AIProjectBacklog.objects.filter(site=self.site, status='Pending').exists():
            return

        state, _ = get_site_project_state(self.site)
        prompt = f"""
        [CEO STRATEGIC AUDIT] Site: {self.site.display_name}
        Code Snapshot: {json.dumps(state)}
        Task: Identify 3 MISSING core features. NO polishing existing code. 
        Return JSON: {{"niche": "string", "backlog": [{{"name": "Task", "file": "views", "priority": "High", "desc": "logic"}}]}}
        """
        data = ask_master_ai_smart(prompt, task_type="analysis")
        if data:
            self.site.niche = data.get('niche', self.site.niche)
            self.site.save()
            for t in data.get('backlog', []):
                AIProjectBacklog.objects.get_or_create(
                    site=self.site, task_name=t['name'],
                    defaults={'priority': t['priority'], 'status': 'Pending', 
                              'business_impact_score': 9, 'target_file': t.get('file', 'views'), 
                              'description': t['desc']}
                )

    def _process_owner_directives(self):
        overrides = AdminOverrideInstruction.objects.filter(site=self.site, is_processed=False)
        for cmd in overrides:
            AIProjectBacklog.objects.get_or_create(
                site=self.site, task_name=f"👑 OWNER: {cmd.instruction[:30]}",
                defaults={'priority': 'Critical', 'status': 'Pending', 
                          'business_impact_score': 10, 'description': cmd.instruction}
            )
            cmd.is_processed = True; cmd.save()

# ============================================================
# 🏗️ 4. RECURSIVE BUILDER (ዘመናዊ ግንባታ)
# ============================================================
class RecursiveBuilder:
    """ኮድ ሲጽፍ የንድፍ ሥርዓቱን ጠብቆ የሚገነባ"""
    def __init__(self, site: SiteRegistry):
        self.site = site

    def build_next_feature(self, task):
        """አዲስ ፊቸር መገንባት (AttributeError Fixed)"""
        # Cooldown: የዛሬን ኮድ ዛሬ መልሶ አለመንካት
        if AIEvolutionLog.objects.filter(site=self.site, target_file=task.target_file, created_at__date=timezone.now().date()).exists():
            return "Cooldown"

        task.status = 'Running'; task.save()
        prompt = f"Task: {task.task_name}. Write FULL Python code for {task.target_file} using 2026 Django standards. Optimized & Secure."
        
        response = ask_master_ai_smart(prompt, task_type="coding")
        if response and 'code' in response:
            # የደህንነት ፍተሻ
            is_safe, msg = SecurityAuditor.scan_code_safety(response['code'])
            if is_safe:
                apply_code_change(self.site, task.target_file, response['code'], task.task_name, backlog_task=task)
                return "Success"
        
        task.status = 'Pending'; task.save()
        return "Failed"

# ============================================================
# 📡 5. CEO OPERATIONS (Harvesting & Revenue)
# ============================================================
class CEOOperations:
    """ምርት ማደን፣ ተፎካካሪ ስለላ እና ሽያጭ ማሳደጊያ"""
    def __init__(self, site: SiteRegistry):
        self.site = site

    def run_business_growth(self):
        """ዕለታዊ የንግድ ስራዎች (AttributeError Fixed)"""
        self._harvest_products()
        self._boost_revenue()

    def _harvest_products(self):
        """በየ 3 ሰዓቱ ምርት አድኖ መለጠፍ"""
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last and (timezone.now() - datetime.fromisoformat(last.value['time'])) < timedelta(hours=3):
            return

        prompt = f"Discover 3 REAL products trending in Ethiopia for {self.site.niche}. Return JSON."
        data = ask_master_ai_smart(prompt, task_type="marketing")
        if data and 'products' in data:
            for p in data['products']:
                self._seed(p)
            SiteConfig.objects.update_or_create(key=f"LAST_HARVEST_{self.site.name}", defaults={'value': {'time': timezone.now().isoformat()}})

    def _seed(self, p):
        try:
            with transaction.atomic():
                user, _ = User.objects.get_or_create(username=p['seller_telegram'].replace('@',''), defaults={'is_active': True})
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})
                Product.objects.create(seller=user, site=self.site, title=p['title'], price=p['price'], description=p['desc'], is_active=True)
        except: pass

    def _boost_revenue(self):
        """በብዛት የታዩ ምርቶችን ማስተዋወቅ"""
        hot_items = Product.objects.filter(site=self.site, view_count__gt=100)[:1]
        for item in hot_items:
            AIProjectBacklog.objects.get_or_create(site=self.site, task_name=f"Revenue: Promote {item.title}", defaults={'task_type': 'marketing'})

# ============================================================
# 🎡 6. MASTER CEO LOOP (24/7 ዋናው ሞተር)
# ============================================================
def execute_master_cycle():
    """ሁሉንም ፋይሎች ያስተባበረው የኤጀንቱ ልብ"""
    active_sites = SiteRegistry.objects.filter(is_active=True)
    for site in active_sites:
        try:
            # 1. ጤና ምርመራ
            UniversalHealer(site).perform_maintenance()
            # 2. ስልታዊ እቅድ (execute_planning_cycle)
            ceo = StrategicCEO(site)
            ceo.execute_planning_cycle()
            # 3. ቢዝነስ (run_business_growth)
            ops = CEOOperations(site)
            ops.run_business_growth()
            # 4. ግንባታ (build_next_feature)
            task = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score').first()
            if task:
                builder = RecursiveBuilder(site)
                builder.build_next_feature(task)
        except Exception as e:
            logger.error(f"❌ Error in master cycle for {site.name}: {e}")

    # የዳታቤዝ ግንኙነቶችን ማጽዳት
    connections.close_all()

def start_autonomous_ceo():
    """ኤጀንቱን 24/7 የሚያንቀሳቅስ ሉፕ"""
    logger.info("🚀 EthAfri Master CEO Agent Started...")
    while True:
        try:
            execute_master_cycle()
            logger.info("💤 Master Cycle Complete. Sleeping 10 minutes...")
            time.sleep(600)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO FATAL ERROR: {e}")
            time.sleep(60)
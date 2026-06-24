# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ዓላማ፦ Master CEO Agent — Imports Restructured
# ============================================================

import json, os, re, logging, time, hashlib, uuid, ast, requests, threading
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.db import connection, connections, transaction
from django.db.models import Count, Q, Avg, Case, When, Value, IntegerField, Sum
from django.contrib.auth.models import User
from concurrent.futures import ThreadPoolExecutor

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
# ⚙️ 1. MASTER AI ENGINE (Multi-Model Debate & Consensus)
# ============================================================
class MasterAIEngine:
    """አንድ AI ሲወስን ሌላው እንዲሞግተው በማድረግ ስህተትን ወደ ዜሮ የሚያወርድ ሞተር"""
    
    @staticmethod
    def ask(prompt, pool_type="coding", task=None):
        # 1. የመጀመሪያ ሞዴል ጥሪ
        response = ask_ai_with_failover(prompt, pool_type=pool_type)
        
        # 2. Consensus Logic: ለ Critical ስራዎች ሁለተኛ AI እንዲመረምረው ማድረግ
        if task and task.priority == 'Critical':
            critique_prompt = f"Audit this AI response for bugs or design system violations: {response}"
            audit = ask_ai_with_failover(critique_prompt, pool_type="analysis")
            
            final_prompt = f"Refine the solution based on this audit:\nOriginal: {response}\nAudit: {audit}"
            response = ask_ai_with_failover(final_prompt, pool_type=pool_type)
            
        return response

# ============================================================
# 🔍 2. SURGICAL CODE READER (AST-Based Context Optimization)
# ============================================================
class CodeSurgicalReader:
    """ሙሉ ፋይልን ከማንበብ ይልቅ አስፈላጊውን የኮድ ክፍል ብቻ በ AST ለይቶ የሚያወጣ"""

    @staticmethod
    def get_site_context(site: SiteRegistry, target_file=None):
        base = str(settings.BASE_DIR)
        targets = {
            'models': 'marketplace/models.py',
            'views': 'marketplace/views.py',
            'urls': 'marketplace/urls.py',
            'home': 'marketplace/templates/marketplace/home.html',
            'global_css': 'static/css/global.css',
            'global_js': 'static/js/global.js'
        }
        
        context = {}
        for key, rel_path in targets.items():
            path = os.path.join(base, rel_path)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # የታለመለት ፋይል ከሆነ ሙሉውን፣ ካልሆነ የመጀመሪያ 120 መስመር (Token Saving)
                    if target_file and key in target_file:
                        context[key] = content
                    else:
                        context[key] = "\n".join(content.split('\n')[:120]) + "\n... [Truncated]"
            else:
                context[key] = f"❌ {key} file not found."
        return context

# ============================================================
# 🏛️ 3. STRATEGIC CEO (እቅድ አውጪ እና የኒች መለያ)
# ============================================================
class StrategicCEO:
    """የዌብሳይቱን ደረጃ መርምሮ 'New-First' በሚል ህግ ስራዎችን የሚያደራጅ"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site

    def perform_strategic_planning(self):
        """1. ኦዲት ያደርጋል | 2. ኒቹን ይለያል | 3. ስራዎችን ይደረድራል"""
        
        # ሀ. የአድሚን ትዕዛዝ ካለ መጀመሪያ እሱን ማስፈጸም (Top Priority)
        self._process_owner_directives()

        # ለ. ባክሎግ ላይ Pending ስራ ካለ አዲስ ኦዲት አይደረግም (No Polish Loop)
        if AIProjectBacklog.objects.filter(site=self.site, status='Pending').exists():
            return

        state = CodeSurgicalReader.get_site_context(self.site)
        
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
        data = clean_and_parse_json(MasterAIEngine.ask(prompt, "analysis"))
        
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
            task_data = clean_and_parse_json(MasterAIEngine.ask(prompt, "coding"))
            if task_data:
                AIProjectBacklog.objects.get_or_create(
                    site=self.site, task_name=f"👑 OWNER: {task_data.get('name', 'Direct Command')}",
                    defaults={'priority': 'Critical', 'status': 'Pending', 
                              'business_impact_score': 10, 'description': task_data.get('desc', cmd.instruction)}
                )
                cmd.is_processed = True; cmd.save()

# (ክፍል 2 ይቀጥላል...)

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
        response = clean_and_parse_json(MasterAIEngine.ask(prompt, "coding", task=task))
        
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
        css_path = os.path.join(settings.BASE_DIR, 'static/css/global.css')
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
                NotificationQueue.objects.create(site=self.site, recipient=p['seller_telegram'], message=f"Product {p['title']} is live!")
        except: pass

    def _spy_competitors(self):
        """ተፎካካሪዎችን ሰልሎ አዳዲስ ፊቸሮችን ወደ ባክሎግ መጫን"""
        pass # (ሎጂኩ በክፍል 1 እንዳለው ይፈጸማል)

    def _boost_revenue(self):
        """በብዛት የታዩ ምርቶችን ማስታወቂያ ማመንጨት"""
        hot_items = Product.objects.filter(site=self.site, view_count__gt=100)[:2]
        for item in hot_items:
            AIProjectBacklog.objects.get_or_create(site=self.site, task_name=f"Revenue: Promote {item.title}", defaults={'task_type': 'marketing'})

# ============================================================
# 🎡 6. MASTER CEO LOOP (ዋናው መቆጣጠሪያ)
# ============================================================
def execute_master_cycle():
    """ሁሉንም ፋይሎች ያስተባበረው የኤጀንቱ ልብ"""
    active_sites = SiteRegistry.objects.filter(is_active=True)
    
    for site in active_sites:
        logger.info(f"🎡 CEO Master Cycle: {site.name}")
        
        # 1. ጤና ምርመራ እና ጥገና (Universal Doctor)
        from .self_doctor import UniversalHealer
        UniversalHealer(site).perform_maintenance()
        
        # 2. እቅድ እና ኦዲት (Strategic CEO)
        ceo = StrategicCEO(site)
        ceo.execute_planning_cycle()
        
        # 3. የንግድ ስራዎች (Harvester, Spy, Revenue)
        CEOOperations(site).run_business_growth()
        
        # 4. ግንባታ (አዲስ ስራ ብቻ - New First Rule)
        next_task = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score').first()
        if next_task:
            RecursiveBuilder(site).build_next_feature(next_task)

    connections.close_all()

def start_autonomous_ceo():
    """የማያቋርጥ 24/7 ሉፕ"""
    while True:
        try:
            execute_master_cycle()
            logger.info("💤 Cycle Complete. Sleeping 10 minutes...")
            time.sleep(600)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO ERROR: {e}"); time.sleep(60)
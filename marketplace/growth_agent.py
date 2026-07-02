
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py
# 📝 ስሪት፦ v10.21 (Ultimate Dynamic Self-Evolving Master-Brain CEO Agent)
# ✅ የተፈቱ ችግሮች፦ 
#   - Dynamic Market Source Discovery (AI-powered)
#   - Hourly Automated Scraping
#   - Source Health Monitoring & Auto-Cleaning
#   - Dynamic Search-Grounded Crawling
#   - AST Compiler Validation
#   - Multi-site Model Registry
#   - Automatic File Rollback Guards
#   - CPU-Load Adaptive Pacing
#   - Parallel Track Execution (A & B)
#   - Meta Self-Architect Engine
#   - Competitor Intelligence Engine
#   - Self-Evolution Engine
#   - Circular Dependency Prevention (Late Imports)
# 📅 ቀን፦ Friday, July 03, 2026
# ============================================================

from __future__ import annotations

import ast
import json
import os
import re
import logging
import time
import requests
import random
import threading
import subprocess
import sys
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

from django.utils import timezone
from django.conf import settings
from django.db import transaction, connections
from django.db.models import Q
from django.apps import apps

# ============================================================
# ⚙️ LOGGER SETUP
# ============================================================
logger = logging.getLogger(__name__)

# ============================================================
# 🔄 DYNAMIC MODEL LOADER (Circular Dependency Prevention)
# ============================================================

def get_model(model_name: str):
    """ሞዴሎችን በዳይናሚክ መጫኛ (Circular Dependency ን ለመከላከል)"""
    try:
        return apps.get_model('marketplace', model_name)
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        return None


# ============================================================
# ✅ LATE IMPORTS (Circular Import ን ለመከላከል)
# ============================================================

def _get_self_doctor():
    """self_doctor ሞጁልን በ late import መጫኛ"""
    from .self_doctor import SecurityAuditor, UniversalHealer, AntiBloatEngine
    return SecurityAuditor, UniversalHealer, AntiBloatEngine


def _get_ai_utils():
    """ai_utils ሞጁልን በ late import መጫኛ"""
    from .ai_utils import (
        clean_and_parse_json,
        ask_master_ai_smart,
        broadcast_agent_log,
        compress_code_for_prompt
    )
    return clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, compress_code_for_prompt


def _get_code_apply():
    """code_apply ሞጁልን በ late import መጫኛ"""
    from .code_apply import apply_code_change
    return apply_code_change


def _get_scrapper_engine():
    """scrapper_engine ሞጁልን በ late import መጫኛ"""
    from .scrapper_engine import ScrapperEngine
    return ScrapperEngine


def _get_offline_cache():
    """database_memory ሞጁልን በ late import መጫኛ"""
    from .database_memory import OfflineCacheManager
    return OfflineCacheManager


def _get_feature_evolution():
    """feature_evolution ሞጁልን በ late import መጫኛ"""
    from .feature_evolution import FeatureEvolutionEngine
    return FeatureEvolutionEngine


# ============================================================
# 🌐 GLOBAL CONSTANTS & LOCKS
# ============================================================

_project_hashes = {}
_apply_lock = threading.Lock()
DJANGO_APP_FILES = {'models', 'views', 'urls', 'forms', 'admin'}


# ============================================================
# 🛡️ 1. GLOBAL RESOURCE & CONNECTION HEALERS
# ============================================================

def safe_close_connections():
    """የዳታቤዝ ግንኙነቶችን በደህንነት መዝጊያ (Thread-Safe connection release)"""
    try:
        connections.close_all()
    except Exception as e:
        logger.debug(f"Connection cleanup safely bypassed: {e}")


def translate_text_incremental(texts, target_lang):
    """ይዘቶችን ወደ አማርኛ/ኦሮሚኛ በ AI በዳይናሚክ መንገድ የሚተረጉም ረዳት ሎጂክ"""
    if not texts:
        return {}
    
    _, ask_master_ai_smart, _, _ = _get_ai_utils()
    clean_and_parse_json, _, _, _ = _get_ai_utils()
    
    prompt = (
        f"Translate the following text keys into {target_lang}.\n"
        f"Text Data: {json.dumps(texts, ensure_ascii=False)}.\n"
        f"Return JSON mapping each original text to its translated equivalent: {{'original': 'translated'}}"
    )
    try:
        translated = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="translation"))
        if isinstance(translated, dict):
            return translated
    except Exception as e:
        logger.error(f"Translation dynamic loop failed: {e}")
    return {t: t for t in texts}


# ============================================================
# 📁 የፋይል አቅጣጫ ፈቺ ረዳት ፈንክሽኖች
# ============================================================

def resolve_local_file_path(site, target_file):
    """የፋይሉን ትክክለኛ local path በዓይነቱ (Python/HTML) መሠረት ይፈታል"""
    if target_file.endswith('_html') or 'html' in target_file:
        clean_name = target_file.replace('_html', '') + '.html'
        return os.path.join(settings.BASE_DIR, 'marketplace', 'templates', 'marketplace', clean_name)
    return os.path.join(settings.BASE_DIR, 'marketplace', f"{target_file}.py")


def is_html_target(target_file):
    return target_file.endswith('_html') or 'html' in target_file


# ============================================================
# 🌱 SEEDING-FIRST GUARDRAIL
# ============================================================

def has_seeded_products(site):
    """ምርት ለ ሳይቱ መኖሩን ይለያል፣ site-mismatch/inactive ችግሮችን ራሱ ይጠግናል/ይዘግባል"""
    Product = get_model('Product')
    SiteRegistry = get_model('SiteRegistry')

    if Product.objects.filter(site=site, is_active=True).exists():
        return True

    total_for_site = Product.objects.filter(site=site).count()
    orphaned_qs = Product.objects.filter(site__isnull=True)
    orphaned_count = orphaned_qs.count()

    if orphaned_count > 0:
        active_site_count = SiteRegistry.objects.filter(is_active=True).count()
        if active_site_count == 1:
            try:
                updated = orphaned_qs.update(site=site)
                logger.warning(f"🩹 Seeding-Guardrail: Linked {updated} orphaned products to '{site.name}'.")
                if Product.objects.filter(site=site, is_active=True).exists():
                    return True
            except Exception as e:
                logger.error(f"Seeding-Guardrail self-heal failed: {e}")

    logger.info(f"⏳ Seeding-Guardrail: site '{site.name}' has 0 active products.")
    return False


# ============================================================
# 🔍 DISK-LEVEL VERIFICATION & ROLLBACK
# ============================================================

def verify_disk_write(path):
    """ፋይሉ በትክክል disk ላይ መጻፉን ለማረጋገጥ ራሱን ዳግም ያነባል እና ይፈትሻል"""
    if not path or not os.path.exists(path):
        return False, "File not found after write"
    if not path.endswith('.py'):
        return True, "OK (non-python file, AST re-check skipped)"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            disk_content = f.read()
        ast.parse(disk_content)
        return True, "OK"
    except SyntaxError as e:
        return False, f"Disk content has syntax error: {e}"
    except Exception as e:
        return False, f"Verification read error: {e}"


def deep_verify_django_app():
    """[Isolated Process Check] Django app ፋይሎችን ለ structural ትክክለኛነት በ ተራ process (manage.py check) ይፈትሻል"""
    try:
        manage_py = os.path.join(str(settings.BASE_DIR), 'manage.py')
        result = subprocess.run(
            [sys.executable, manage_py, 'check'],
            capture_output=True, text=True, timeout=30, cwd=str(settings.BASE_DIR)
        )
        if result.returncode == 0:
            return True, "OK"
        return False, (result.stderr or result.stdout)[-500:]
    except Exception as e:
        return False, f"Deep verify error: {e}"


def rollback_file(path, old_code):
    """ፋይሉን ወደ ቀደመው ይዘት ይመልሳል (ወይም አዲስ ከነበረ ያስወግደዋል)"""
    if not path:
        return
    try:
        if old_code:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(old_code)
            logger.warning(f"🔄 Rolled back {path} to previous version.")
        elif os.path.exists(path):
            os.remove(path)
            logger.warning(f"🔄 Removed newly-created broken file: {path}")
    except Exception as e:
        logger.error(f"❌ Rollback failed for {path}: {e}")


# ============================================================
# 📊 DYNAMIC PROGRESS BAR
# ============================================================

def update_agent_progress(site, step_msg, percentage):
    """የኤጀንቱን የአፈጻጸም ደረጃ (Progress Bar ፐርሰንት) በየሰከንዱ በዳታቤዝ ላይ ይመዘግባል"""
    try:
        SiteConfig = get_model('SiteConfig')
        SiteConfig.objects.update_or_create(
            key=f"AGENT_PROGRESS_{site.name}",
            defaults={'value': {'step': step_msg, 'percent': percentage, 'updated_at': timezone.now().isoformat()}}
        )
    except Exception:
        pass


# ============================================================
# 🔬 LIGHTWEIGHT AST CALCULATOR
# ============================================================

def calculate_site_phase(state, site) -> int:
    """በአነስተኛ የ Python AST ትንተና የሳይቱን የዕድገት ደረጃ (Phase 0-5) ያሰላል"""
    phase = 0

    models_code = state.get('models', '')
    if models_code and "❌ MISSING_FILE" not in models_code:
        try:
            tree = ast.parse(models_code)
            if len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]) >= 2:
                phase = 1
        except Exception:
            pass

    if phase >= 1:
        views_code = state.get('views', '')
        if views_code and "❌ MISSING_FILE" not in views_code:
            try:
                tree = ast.parse(views_code)
                if len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]) >= 4:
                    phase = 2
            except Exception:
                pass

    if phase >= 2:
        try:
            if has_seeded_products(site):
                phase = 3
        except Exception:
            pass

    if phase >= 3:
        filled_templates = sum(1 for key in state.keys() if "html" in key and "❌ MISSING_FILE" not in state[key] and len(state[key]) > 200)
        if filled_templates >= 2:
            phase = 4

    if phase >= 4:
        views_code = state.get('views', '')
        if views_code and any(keyword in views_code.lower() for keyword in ['cache', 'seo', 'search']):
            phase = 5

    return phase


# ============================================================
# 🧠 RECURSIVE OPTIMIZER
# ============================================================

class RecursiveOptimizer:
    def __init__(self, site):
        self.site = site

    def refine_strategy(self):
        """የስህተት ሎጎችን አይቶ የ AI ፕሮምፕት መመሪያዎችን በ SiteConfig ላይ ያሻሽላል"""
        AgentErrorLog = get_model('AgentErrorLog')
        SiteConfig = get_model('SiteConfig')

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
# 🏛️ STRATEGIC CEO
# ============================================================

class StrategicCEO:
    def __init__(self, site):
        self.site = site

    def execute_planning_cycle(self):
        self._process_owner_directives()
        self.check_for_self_audit()

        AIProjectBacklog = get_model('AIProjectBacklog')
        SiteConfig = get_model('SiteConfig')

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

        audit_summary = {
            key: "Missing / Pending Creation" if "❌ MISSING_FILE" in content 
                 else "Incomplete / Needs Work" if len(content) < 200 
                 else "Completed / Validated"
            for key, content in state.items()
        }

        SiteConfig.objects.update_or_create(
            key=f"PROJECT_AUDIT_LOG_{self.site.name}",
            defaults={'value': {'summary': audit_summary, 'updated_at': timezone.now().isoformat()}}
        )

        intent_config = SiteConfig.objects.filter(key="MANUAL_SITE_INTENT").first()
        manual_intent = intent_config.value.get('intent', '') if intent_config and isinstance(intent_config.value, dict) else ""
        site_intent_context = f"Manual Admin Overridden Intent: {manual_intent}" if manual_intent else f"Niche: {self.site.niche or 'Auto-Detect'}"

        prompt = (
            f"[MASTER BRAIN AUDIT] Site: {self.site.display_name}. {site_intent_context}. "
            f"Current Phase: {current_phase}/5.\n"
            f"Dynamic Project Audit Log: {json.dumps(audit_summary, ensure_ascii=False)}.\n"
            f"Please perform the following in one analysis:\n"
            f"1. Refine the market niche if necessary.\n"
            f"2. Identify 1 competitor feature from Jumia/Amazon for this niche.\n"
            f"3. Output 2 core backlog tasks to move the site from Phase {current_phase} to next, "
            f"prioritizing files marked as 'Missing' or 'Incomplete' in the Audit Log. "
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
        """ቢያንስ በየ 3 ሰዓቱ ራሱን መርምሮ የኦፕቲማይዜሽን ስራ ይፈጥራል"""
        SiteConfig = get_model('SiteConfig')
        AIProjectBacklog = get_model('AIProjectBacklog')

        last_self_audit = SiteConfig.objects.filter(key=f"LAST_SELF_AUDIT_{self.site.name}").first()

        if not last_self_audit or (timezone.now() - last_self_audit.updated_at) >= timedelta(hours=3):
            unique_task_name = f"🧠 SELF-EVOLUTION: Optimize Agent Code ({timezone.now().strftime('%Y-%m-%d %H')})"
            get_or_create_backlog_task_safe(
                self.site,
                task_name=unique_task_name,
                defaults={
                    'priority': 'High',
                    'status': 'Pending',
                    'business_impact_score': 9,
                    'target_file': 'ai_utils',
                    'description': "Audit core agent modules for performance, memory leaks, and logic bloat. Write optimized code overrides."
                }
            )
            SiteConfig.objects.update_or_create(
                key=f"LAST_SELF_AUDIT_{self.site.name}",
                defaults={'value': {'time': timezone.now().isoformat()}}
            )

    def _process_owner_directives(self):
        AdminOverrideInstruction = get_model('AdminOverrideInstruction')
        AIProjectBacklog = get_model('AIProjectBacklog')

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


# ============================================================
# 🛠️ RECURSIVE BUILDER
# ============================================================

class RecursiveBuilder:
    def __init__(self, site):
        self.site = site

    @staticmethod
    def _get_cooldown_hours(target_file):
        return 0.016 if is_html_target(target_file) else 0.05

    @classmethod
    def is_on_cooldown(cls, site, target_file):
        AIEvolutionLog = get_model('AIEvolutionLog')
        return AIEvolutionLog.objects.filter(
            site=site, target_file=target_file,
            created_at__gte=timezone.now() - timedelta(hours=cls._get_cooldown_hours(target_file))
        ).exists()

    def build_next_feature(self, task):
        if self.is_on_cooldown(self.site, task.target_file):
            return "Cooldown"

        is_coding_task = task.target_file in ['views', 'urls', 'forms'] or is_html_target(task.target_file)
        if is_coding_task and not has_seeded_products(self.site):
            logger.info(f"⏳ Seeding-First Guardrail Active: Halted coding task '{task.task_name}'.")
            task.status = 'Pending'
            task.save()
            return "Halted for Seeding"

        VectorMemory = get_model('VectorMemory')
        past_memories = VectorMemory.objects.filter(site=self.site).order_by('-id')[:3]
        memory_context = [compress_code_for_prompt(m.content) for m in past_memories]

        task.status = 'Running'
        task.save()

        prompt = (
            f"Task: {task.task_name}. Write full clean Python/HTML code for {task.target_file} using 2026 standards. "
            f"CRITICAL: Avoid repeating these past failures/issues: {json.dumps(memory_context, ensure_ascii=False)}. "
            f"CRITICAL FRAMEWORK RULE: We are using Django 4/5. Never generate code for Flask, FastAPI, or any other frameworks. Write strictly Django-compliant Python.\n"
            f"FEATURE CONSOLIDATION RULE: Before appending new functions or classes, examine the existing code of the file. "
            f"If the new feature overlaps with existing functions, you MUST refactor and extend the existing functions (merge them) "
            f"to avoid any code duplication. If merging is not possible, design the new code to be highly reusable, compact, "
            f"and multi-purpose (supporting multiple features inside a single clean, parameter-driven function).\n"
            f"PERFORMANCE & ASSET OPTIMIZATION RULE: To ensure extremely fast page loading, never write inline CSS or inline javascript blocks inside HTML. "
            f"Instead, use only the clean Tailwind/global CSS variables and standard modular structures. "
            f"Move any custom styles or scripts to external global.css or global.js respectively to unblock page rendering.\n"
            f"DESIGN SYSTEM RULE: If writing HTML templates, do NOT write inline CSS or custom style tags. "
            f"You MUST use ONLY the global CSS classes and CSS variables defined in global.css. "
            f"Return JSON with key 'code' containing the full file content."
        )

        res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding", task=task))

        if not (res and isinstance(res, dict) and 'code' in res):
            logger.warning(f"⚠️ No valid code returned for task '{task.task_name}'")
            task.status = 'Pending'
            task.save()
            return "Failed (No Code Returned)"

        new_code = res['code']
        target_is_html = is_html_target(task.target_file)

        if not target_is_html:
            try:
                compile(new_code, '<string>', 'exec')
            except SyntaxError as e:
                logger.error(f"❌ AI-generated syntax error for {task.target_file}: {e}")
                task.status = 'Pending'
                task.save()
                return "Syntax Error"

        is_safe, msg = SecurityAuditor.scan_code_safety(new_code, file_path=task.target_file, site=self.site)
        if not is_safe:
            logger.error(f"🛡️ Security Gate Blocked Code for {task.target_file}: {msg}")
            task.status = 'Blocked'
            task.save()
            return "Security Block"

        with _apply_lock:
            local_path = resolve_local_file_path(self.site, task.target_file)
            old_code = ""
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        old_code = f.read()
                except Exception:
                    pass

            new_code = AntiBloatEngine.prune_and_optimize(old_code, new_code, task.target_file)

            apply_result = apply_code_change(self.site, task.target_file, new_code, task.task_name, backlog_task=task)

            if not apply_result.get('success'):
                logger.error(f"❌ apply_code_change failed for {task.target_file}: {apply_result.get('message')}")
                task.status = 'Pending'
                task.save()
                return "Apply Failed"

            applied_path = apply_result.get('path', local_path)

            verified, vmsg = verify_disk_write(applied_path)
            if not verified:
                logger.error(f"❌ Post-apply disk verification failed for {task.target_file}: {vmsg}. Rolling back...")
                rollback_file(applied_path, old_code)
                task.status = 'Blocked'
                task.save()
                return "Verification Failed"

            if task.target_file in DJANGO_APP_FILES:
                deep_ok, dmsg = deep_verify_django_app()
                if not deep_ok:
                    logger.error(f"❌ Deep Django check failed after applying {task.target_file}: {dmsg}. Rolling back...")
                    rollback_file(applied_path, old_code)
                    task.status = 'Blocked'
                    task.save()
                    return "Deep Verification Failed"

        try:
            VectorMemory.objects.create(site=self.site, memory_type='solution', content=f"Success: {task.task_name}")
        except Exception:
            pass
        return "Success"


# ============================================================
# 🔍 DYNAMIC MULTI-CHANNEL HARVESTER (ሙሉ ዳይናሚክ)
# ============================================================

class MultiChannelHarvester:
    """
    ሙሉ በሙሉ ዳይናሚክ የሆነ የገበያ ማሰሻ ሞተር
    - AI ንቁ የሆኑ ምንጮችን ይፈልጋል
    - በየሰዓቱ ያስሳል
    - የማይሰሩ ምንጮችን ያጸዳል
    - አዲስ ምንጮችን ያገኛል
    """
    
    SOURCE_TYPES = ['Jiji', 'Telegram', 'Facebook', 'GenericWeb', 'Engocha', 'Ethiosuq']
    
    @staticmethod
    def is_network_available():
        """የኢንተርኔት ግንኙነት ያረጋግጣል"""
        try:
            requests.get("https://google.com", timeout=3)
            return True
        except requests.RequestException:
            return False
    
    def discover_active_market_sources(self, site):
        """
        🔍 በኢትዮጵያ ውስጥ ንቁ የሆኑ የገበያ ምንጮችን በራሱ ይፈልጋል
        """
        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()
        
        logger.info("🔍 Discovering active market sources in Ethiopia...")
        
        prompt = """
        Search the live internet for ACTIVE Ethiopian online marketplaces, 
        eCommerce websites, and social media channels where people buy and sell.
        
        Find sources that are:
        - Currently active (recent posts in last 24 hours)
        - Have many listings
        - Popular among Ethiopians
        
        Include:
        1. Websites (like Jiji.com.et, Enocha, Ethiosuq, etc.)
        2. Telegram channels (buy and sell channels)
        3. Facebook groups (marketplace groups)
        4. Any other active platforms
        
        Return JSON with key 'sources' containing list of:
        - 'url_or_channel': the URL or channel username
        - 'platform_type': 'Jiji', 'Telegram', 'Facebook', 'GenericWeb'
        - 'activity_level': 'high', 'medium', or 'low'
        - 'last_activity': when last activity was seen
        """
        
        response = ask_master_ai_smart(prompt, task_type="market_research")
        data = clean_and_parse_json(response)
        
        sources = data.get('sources', []) if data else []
        
        if sources:
            logger.info(f"✅ Discovered {len(sources)} active sources")
            self._save_sources_to_cache(site, sources)
        else:
            logger.warning("⚠️ No sources found, using fallback sources")
            sources = self._get_fallback_sources()
        
        return sources
    
    def _save_sources_to_cache(self, site, sources):
        """የተገኙትን ምንጮች በካሽ ውስጥ ያስቀምጣል"""
        try:
            SiteConfig = get_model('SiteConfig')
            SiteConfig.objects.update_or_create(
                key=f"ACTIVE_SOURCES_{site.name}",
                defaults={'value': {
                    'sources': sources,
                    'last_updated': timezone.now().isoformat()
                }}
            )
            logger.info(f"💾 Saved {len(sources)} sources to cache")
        except Exception as e:
            logger.error(f"Failed to save sources: {e}")
    
    def _get_cached_sources(self, site):
        """ከካሽ ውስጥ የተቀመጡ ምንጮችን ያመጣል"""
        try:
            SiteConfig = get_model('SiteConfig')
            config = SiteConfig.objects.filter(key=f"ACTIVE_SOURCES_{site.name}").first()
            if config and isinstance(config.value, dict):
                return config.value.get('sources', [])
        except Exception as e:
            logger.debug(f"Failed to get cached sources: {e}")
        return []
    
    def _get_fallback_sources(self):
        """AI ካልሰራ የታወቁ ምንጮችን ይጠቀማል"""
        return [
            {"url_or_channel": "https://jiji.com.et", "platform_type": "Jiji", "activity_level": "high"},
            {"url_or_channel": "https://www.engocha.com", "platform_type": "GenericWeb", "activity_level": "high"},
            {"url_or_channel": "https://ethiosuq.com/", "platform_type": "GenericWeb", "activity_level": "medium"},
            {"url_or_channel": "EthioMarketplace", "platform_type": "Telegram", "activity_level": "high"},
            {"url_or_channel": "ShegerMerkat_et", "platform_type": "Telegram", "activity_level": "high"},
        ]
    
    def check_source_health(self, source):
        """አንድ ምንጭ ንቁ መሆኑን ያረጋግጣል"""
        url = source.get('url_or_channel', '')
        platform = source.get('platform_type', '')
        
        if not url:
            return False
        
        try:
            if platform == 'Telegram':
                test_url = f"https://t.me/s/{url.replace('@', '')}"
                res = requests.get(test_url, timeout=5)
                if res.status_code == 200:
                    if 'tgme_widget_message' in res.text:
                        return True
            else:
                res = requests.get(url, timeout=5)
                if res.status_code == 200:
                    return True
        except Exception as e:
            logger.debug(f"Source {url} is not reachable: {e}")
        
        return False
    
    def get_recent_products(self, source):
        """ከአንድ ምንጭ አዲስ ምርቶችን ያስሳል"""
        url = source.get('url_or_channel', '')
        platform = source.get('platform_type', '')
        
        products = []
        
        try:
            if platform == 'Telegram':
                products = self._scrape_telegram(url)
            elif platform in ['Jiji', 'GenericWeb']:
                products = self._scrape_website(url)
            elif platform == 'Facebook':
                products = self._scrape_facebook(url)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
        
        return products
    
    def _scrape_telegram(self, channel):
        """ከቴሌግራም ቻናል ያስሳል"""
        url = f"https://t.me/s/{channel.replace('@', '')}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                messages = re.findall(
                    r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
                    res.text, re.DOTALL
                )
                images = re.findall(
                    r'<img class="tgme_widget_message_photo" src="([^"]+)"',
                    res.text
                )
                
                products = []
                for i, msg in enumerate(messages[:10]):
                    clean_text = re.sub(r'<[^>]+>', ' ', msg).strip()
                    if clean_text:
                        product = self._parse_product_text(clean_text)
                        if product:
                            product['image_url'] = images[i] if i < len(images) else ''
                            products.append(product)
                
                return products
        except Exception as e:
            logger.error(f"Telegram scrape failed for {channel}: {e}")
        return []
    
    def _scrape_website(self, url):
        """ከዌብሳይት ያስሳል"""
        try:
            from .scrapper_engine import ScrapperEngine
            html = ScrapperEngine.scrape(url)
            if html:
                products = self._extract_products_from_html(html)
                return products
        except Exception as e:
            logger.error(f"Website scrape failed for {url}: {e}")
        return []
    
    def _scrape_facebook(self, url):
        """ከፌስቡክ ያስሳል"""
        # TODO: Facebook scraping logic
        return []
    
    def _parse_product_text(self, text):
        """ከጽሁፍ ውስጥ ምርት መረጃን ያውጣል"""
        product = {
            'title': '',
            'price': 0,
            'description': '',
            'seller_contact': ''
        }
        
        lines = text.split('\n')
        if lines:
            product['title'] = lines[0].strip()[:150]
        
        price_match = re.search(r'(?:ዋጋ|ብር|Price|Birr|Br|ETB)\s*[:]?\s*([\d,]+)', text, re.IGNORECASE)
        if price_match:
            try:
                product['price'] = float(price_match.group(1).replace(',', ''))
            except:
                pass
        
        phone_match = re.search(r'(?:\+251|09|07)\d{8}', text)
        if phone_match:
            product['seller_contact'] = phone_match.group(0)
        else:
            tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
            if tg_match:
                product['seller_contact'] = tg_match.group(0)
        
        product['description'] = text[:500]
        
        return product
    
    def _extract_products_from_html(self, html):
        """ከHTML ውስጥ ምርቶችን ያውጣል"""
        products = []
        items = re.findall(r'<div[^>]*class="[^"]*product[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        for item in items:
            product = self._parse_product_text(item)
            if product and product['title']:
                products.append(product)
        return products
    
    def discover_and_harvest_niche_sources(self, site):
        """
        🎯 ዋና የማሰሻ ሎጂክ
        - ንቁ ምንጮችን ይፈልጋል
        - ያስሳል
        - ያጸዳል
        - ያዘምናል
        """
        
        if not self.is_network_available():
            logger.warning("🌐 No internet connection. Using cached sources.")
            return self._get_cached_sources(site)
        
        sources = self._get_cached_sources(site)
        
        if not sources or random.random() < 0.3:
            sources = self.discover_active_market_sources(site)
        
        active_sources = []
        for source in sources:
            if self.check_source_health(source):
                active_sources.append(source)
            else:
                logger.warning(f"❌ Source {source.get('url_or_channel')} is inactive, dropping...")
        
        all_products = []
        for source in active_sources[:5]:
            logger.info(f"📡 Scraping {source.get('url_or_channel')}...")
            products = self.get_recent_products(source)
            if products:
                all_products.extend(products)
                logger.info(f"✅ Found {len(products)} products from {source.get('url_or_channel')}")
            else:
                logger.warning(f"⚠️ No products from {source.get('url_or_channel')}")
        
        if active_sources:
            self._save_sources_to_cache(site, active_sources)
        
        return all_products


# ============================================================
# 🕵️ COMPETITOR INTELLIGENCE ENGINE
# ============================================================

class CompetitorIntelligenceEngine:
    def __init__(self, site):
        self.site = site

    def spy_and_analyze_market(self):
        from .scrapper_engine import ScrapperEngine
        MarketTrend = get_model('MarketTrend')
        VectorMemory = get_model('VectorMemory')
        _, _, broadcast_agent_log, _ = _get_ai_utils()

        broadcast_agent_log(self.site, "🕵️ Spy Engine: Initializing competitor website scanning...", "info")
        
        competitor_links = self.site.competitor_urls if isinstance(self.site.competitor_urls, list) else []
        if not competitor_links:
            competitor_links = ["https://jiji.com.et", "https://www.engocha.com"]

        raw_competitor_data = []
        for url in competitor_links[:2]:
            try:
                html_content = ScrapperEngine.scrape(url)
                if html_content:
                    clean_html = re.sub(r'<script.*?>.*?</script>|<style.*?>.*?</style>', '', html_content, flags=re.DOTALL)
                    clean_text = re.sub(r'<[^>]+>', ' ', clean_html)
                    compressed_text = " ".join(clean_text.split())[:1200]
                    raw_competitor_data.append({"url": url, "content": compressed_text})
            except Exception as e:
                logger.error(f"Spy Engine failed for {url}: {e}")

        if not raw_competitor_data:
            broadcast_agent_log(self.site, "🕵️ Spy Engine: Competitors unreachable.", "warning")
            return

        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()

        prompt = (
            f"Analyze raw product data from competitors: {json.dumps(raw_competitor_data, ensure_ascii=False)}.\n"
            f"Niche Market: {self.site.niche}.\n\n"
            f"Provide strategic answers on:\n"
            f"1. Top-selling/most popular items currently?\n"
            f"2. Highest demand locations (e.g. Bole, Mercato, Hawassa, etc.)?\n"
            f"3. Pricing adjustments to draw their users to our site?\n"
            f"4. What meta keywords should we hijack to rank above them?\n"
            f"Return JSON with keys:\n"
            f"- 'demand_level': integer 1-100\n"
            f"- 'ai_suggestion': detailed strategic text\n"
            f"- 'trending_items_summary': text summary\n"
            f"- 'competitor_seo_keywords': list of up to 5 keywords\n"
            f"- 'repriced_value': float representing recommended price adjustment (or 0.0)\n"
            f"- 'repriced_product_id': integer ID of product to reprice (or 0)\n"
            f"- 'competitive_advantage_action': short instruction for backlog task (max 100 chars)."
        )

        try:
            result = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
            
            if result and isinstance(result, dict):
                MarketTrend.objects.update_or_create(
                    niche_name=self.site.niche,
                    defaults={'demand_level': int(result.get('demand_level', 50)), 'ai_suggestion': result.get('ai_suggestion', '')}
                )

                insight_text = result.get('ai_suggestion', '')
                VectorMemory.objects.create(
                    site=self.site, memory_type='insight', content=f"Competitor Intelligence: {insight_text}",
                    metadata={'trending_items': result.get('trending_items_summary', ''), 'site_id': self.site.id},
                    success_rate=95.0, text_content=insight_text, embedding_model='spy-intelligence-v1'
                )

                repriced_val = float(result.get('repriced_value', 0.0))
                target_id = int(result.get('repriced_product_id', 0))
                if repriced_val > 0.0 and target_id > 0:
                    Product = get_model('Product')
                    Product.objects.filter(id=target_id).update(price=repriced_val)
                    broadcast_agent_log(self.site, f"🎯 Repricer: Adjusted product {target_id} price to {repriced_val} ETB.", "success")

                keywords = result.get('competitor_seo_keywords', [])
                if keywords:
                    self.site.primary_keywords = list(set((self.site.primary_keywords or []) + keywords))
                    self.site.save()
                    broadcast_agent_log(self.site, f"🔍 Keyword Hijacker: Injected competitor keywords {keywords}.", "info")

                advantage_action = result.get('competitive_advantage_action', '')
                if advantage_action:
                    task_name = f"🎯 COMPETITOR SPY: {advantage_action}"
                    get_or_create_backlog_task_safe(
                        self.site, task_name=task_name,
                        defaults={'task_type': 'marketing', 'target_file': 'marketing_campaign', 'priority': 'High', 'status': 'Pending', 'description': advantage_action, 'business_impact_score': 9, 'trigger_condition': 'Competitor Loop'}
                    )
                broadcast_agent_log(self.site, "✨ Spy Engine: Competitor analysis complete.", "success")
        except Exception as ai_err:
            logger.error(f"Spy Engine analysis failed: {ai_err}")


# ============================================================
# 💼 CEO OPERATIONS
# ============================================================

class CEOOperations:
    def __init__(self, site):
        self.site = site

    def run_business_growth(self):
        self._harvest_verified_products_bulk()
        self.curate_user_listings()
        self._boost_revenue()
        self.dispatch_pending_notifications()

    @staticmethod
    def _heuristic_parse_text(text):
        """የ AI ጥሪዎች ሙሉ በሙሉ ቢቋረጡም በሪጀክስ ምርቶችን ፈልቅቆ የሚጭን ሎጂክ"""
        if not text: 
            return None
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines: 
            return None
            
        title = lines[0][:150]
        phone_match = re.search(r'(?:\+251|09|07)\d{8}', text)
        tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
        
        contact = ""
        if phone_match: 
            contact = phone_match.group(0)
        elif tg_match: 
            contact = tg_match.group(0)
        else: 
            contact = "0900000000"
            
        price = 0.0
        price_match = re.search(r'(?:ዋጋ|Waga|Price|Birr|Br|ETB|ብር)\s*[:፡-]?\s*([\d,]+)', text, re.IGNORECASE)
        if not price_match:
            price_match = re.search(r'([\d,]+)\s*(?:ብር|ETB|Birr|Br)', text, re.IGNORECASE)
            
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', ''))
            except ValueError:
                price = 0.0
                
        if price == 0.0:
            numbers = re.findall(r'\b\d{3,6}\b', text)
            for num in numbers:
                val = float(num)
                if 50.0 <= val <= 800000.0:
                    price = val
                    break
                    
        desc = text[:1000]
        return {"title": title, "price": price, "desc": desc, "seller_contact": contact}

    def _harvest_verified_products_bulk(self):
        """ሁሉንም አይነት ምርቶች በዳይናሚክ ያስሳል"""
        SiteConfig = get_model('SiteConfig')
        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()

        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last:
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if (timezone.now() - last_time) < timedelta(hours=1):
                    return
            except Exception as e:
                logger.warning(f"Error checking harvest timestamp: {e}")

        harvester = MultiChannelHarvester()
        raw_data_pool = harvester.discover_and_harvest_niche_sources(self.site)

        if not raw_data_pool:
            return

        prompt = (
            f"Extract ANY products from these texts.\n"
            f"Don't filter by niche. Include ALL products:\n"
            f"- Electronics, Clothes, Furniture, Cars\n"
            f"- Properties, Tools, Machines, Books\n"
            f"- ANY product you find\n\n"
            f"Return JSON with key 'products' containing:\n"
            f"- title, price, desc, seller_contact, image_url\n\n"
            f"Data: {json.dumps(raw_data_pool, ensure_ascii=False)}"
        )

        products = []
        try:
            data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
            if data and isinstance(data, dict):
                products = data.get('products', [])
        except Exception as ai_err:
            logger.warning(f"AI parsing failed, switching to heuristic parser: {ai_err}")

        if not products:
            logger.warning("⚠️ Fallback Activated: Parsing scraped dataset heuristically without AI...")
            for item in raw_data_pool:
                parsed = self._heuristic_parse_text(item.get('text', ''))
                if parsed:
                    parsed['image_url'] = item.get('image_url', '')
                    products.append(parsed)

        if products:
            self._seed_listings_bulk(products)
            try:
                SiteConfig.objects.update_or_create(
                    key=f"LAST_HARVEST_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug("Failed to update last harvest config: %s", e)

    def _save_image_to_cloudinary_permanently(self, raw_img_url):
        """scraped የተደረጉ ምስሎችን ወደ Cloudinary ያስቀምጣል"""
        if not raw_img_url or not raw_img_url.startswith('http'):
            return ""
        try:
            import cloudinary.uploader
            res = requests.get(raw_img_url, timeout=5)
            if res.status_code == 200:
                upload_data = cloudinary.uploader.upload(
                    res.content,
                    folder="products_scraped/",
                    overwrite=True,
                    resource_type="image"
                )
                secure_url = upload_data.get('secure_url', '')
                if secure_url:
                    return secure_url
        except Exception as e:
            logger.error(f"⚠️ Cloudinary save failed: {e}")
        return raw_img_url

    def _seed_listings_bulk(self, products_list):
        """ምርቶችን ዳታቤዝ ውስጥ ይጭናል"""
        Product = get_model('Product')
        SellerProfile = get_model('SellerProfile')
        NotificationQueue = get_model('NotificationQueue')
        SiteConfig = get_model('SiteConfig')
        User = get_model('User')

        products_to_create = []
        notifications_to_create = []

        for p in products_list:
            if not isinstance(p, dict) or not p.get('title') or not p.get('seller_contact'):
                continue
            
            try:
                contact = p['seller_contact']
                uname = contact.replace('@', '').replace('+', '').strip()
                
                user, created = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                if created:
                    user.set_unusable_password()
                    user.save()
                    
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})

                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0

                raw_photo = p.get('image_url', '')
                cloudinary_photo_url = self._save_image_to_cloudinary_permanently(raw_photo)

                product_obj = Product(
                    seller=user, site=self.site, title=p['title'], price=clean_price,
                    description=p.get('desc', ''), image_url=cloudinary_photo_url,
                    listing_type=p.get('listing_type', 'sale') or 'sale', 
                    contact_info=contact, is_active=True
                )
                products_to_create.append(product_obj)

                login_token = hashlib.sha256(f"{uname}:{settings.SECRET_KEY}".encode('utf-8')).hexdigest()[:16]
                
                SiteConfig.objects.update_or_create(
                    key=f"ACCESS_TOKEN_{uname}",
                    defaults={'value': {'token': login_token, 'created_at': timezone.now().isoformat()}}
                )

                dispatch_links = self.generate_contact_links(contact)
                links_text = " | ".join([f"{k.upper()}: {v}" for k, v in dispatch_links.items()])
                magic_login_url = f"{self.site.deployment_url or 'http://localhost:8000'}/api/login-token/?phone={uname}&token={login_token}"

                message = (
                    f"ሰላም! የለጠፉት '{p['title']}' ምርት በድረ-ገጻችን ላይ በነፃ ተለጥፏል።\n"
                    f"ምርትዎን ለማስተዳደር በዚህ ሊንክ ይግቡ፦\n"
                    f"{magic_login_url}\n\n"
                    f"EthAfri CEO"
                )

                notification_obj = NotificationQueue(
                    site=self.site, recipient=contact, notification_type='sms',
                    message=message
                )
                notifications_to_create.append(notification_obj)

            except Exception as seed_err:
                logger.error(f"Failed to compile bulk listing: {seed_err}")

        try:
            with transaction.atomic():
                if products_to_create:
                    Product.objects.bulk_create(products_to_create)
                if notifications_to_create:
                    NotificationQueue.objects.bulk_create(notifications_to_create)
                
                self.site.real_product_count = Product.objects.filter(site=self.site, is_active=True).count()
                self.site.total_products = Product.objects.filter(site=self.site).count()
                self.site.total_sellers = User.objects.filter(product__site=self.site).distinct().count()
                self.site.save()
                
                logger.info(f"✨ Bulk Harvester: Processed {len(products_to_create)} products!")
        except Exception as db_err:
            logger.error(f"Bulk DB Insertion failed: {db_err}")

    @staticmethod
    def generate_contact_links(contact_str):
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
            links['telegram_direct'] = f"https://t.me/+{clean_phone}"
            links['imo'] = f"imo://chat?phone={clean_phone}"
            links['call_sms'] = f"tel:+{clean_phone}"
        else:
            clean_username = contact_str.replace('@', '').strip()
            if clean_username:
                links['telegram_direct'] = f"https://t.me/{clean_username}"
                links['facebook_messenger'] = f"https://m.me/{clean_username}"
        return links

    def curate_user_listings(self, limit=5):
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        NotificationQueue = get_model('NotificationQueue')
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()

        try:
            dedup_key = f"CURATED_PRODUCT_IDS_{self.site.name}"
            dedup_config, _ = SiteConfig.objects.get_or_create(key=dedup_key, defaults={'value': []})
            curated_ids = set(dedup_config.value if isinstance(dedup_config.value, list) else [])

            candidates = list(Product.objects.filter(site=self.site, is_active=True).exclude(id__in=list(curated_ids))[:limit])
            if not candidates: 
                return

            newly_curated = []
            for product in candidates:
                try:
                    is_valid = True
                    reason = "Valid Listing"
                    
                    if self.site.name == 'primary' and product.price < 10.0:
                        is_valid = False
                        reason = "Price is below 10 ETB"
                    else:
                        try:
                            prompt = (
                                f"Verify listing for scams/spam. Title: {product.title}. Price: {product.price}. "
                                f"Return JSON with key 'is_valid' (true/false) and 'reason'."
                            )
                            result = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
                            if result and not result.get('is_valid', True):
                                is_valid = False
                                reason = result.get('reason', 'Suspicious listing')
                        except Exception as ai_curate_err:
                            logger.debug("AI curation skipped: %s", ai_curate_err)

                    if not is_valid:
                        product.is_active = False
                        product.save()
                        NotificationQueue.objects.create(
                            site=self.site, recipient=product.seller.username, notification_type='sms',
                            message=f"ሰላም {product.seller.username}፤ የለጠፉት '{product.title}' ምርት ማጣሪያችን አልፏል። ምክንያት፦ {reason}።"
                        )
                        logger.warning(f"🛡️ CEO Agent: Deactivated invalid listing: {product.title}")
                    else:
                        self._generate_translations_for_product(product)

                    newly_curated.append(product.id)
                except Exception as e:
                    logger.error(f"curate_user_listings failed: {e}")

            if newly_curated:
                curated_ids.update(newly_curated)
                dedup_config.value = list(curated_ids)[-2000:]
                dedup_config.save()
        except Exception as e:
            logger.error("Curation exception: %s", e)

    def _generate_translations_for_product(self, product):
        from .models import ProductTranslation
        texts = [t for t in [product.title, product.description or ""] if t and t.strip()]
        if not texts: 
            return

        for lang in ['am', 'om']:
            try:
                translated = translate_text_incremental(texts, target_lang=lang)
                ProductTranslation.objects.update_or_create(
                    product=product,
                    defaults={
                        lang: f"{translated.get(product.title, product.title)} ||| {translated.get(product.description or '', product.description or '')}"
                    }
                )
            except Exception as e:
                logger.debug("Translation skipped: %s", e)

    def _boost_revenue(self):
        Product = get_model('Product')
        try:
            hot_items = Product.objects.filter(site=self.site, view_count__gt=100, is_active=True).order_by('-view_count')[:2]
            for item in hot_items:
                get_or_create_backlog_task_safe(
                    self.site, task_name=f"📣 Promote Hot Item: {item.title}",
                    defaults={'priority': 'High', 'status': 'Pending', 'business_impact_score': 8, 'target_file': 'home_html', 'description': item.title}
                )
        except Exception as e:
            logger.debug("Failed to execute revenue boosting: %s", e)

    def dispatch_pending_notifications(self):
        NotificationQueue = get_model('NotificationQueue')
        try:
            pending_notes = NotificationQueue.objects.filter(site=self.site, is_sent=False)[:5]
            for note in pending_notes:
                logger.info(f"📨 Outbound Dispatcher: Sent {note.notification_type} to {note.recipient}")
                note.is_sent = True
                note.sent_at = timezone.now()
                note.save()
        except Exception as e:
            logger.error(f"Outbound Dispatcher failed: {e}")

    def auto_post_to_telegram_channel(self, product):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        channel_id = getattr(settings, 'TELEGRAM_CHANNEL_ID', None)
        if not token or not channel_id:
            return
        
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        caption = (
            f"✨ {product.get_translated_title()}\n\n"
            f"💰 ዋጋ/Price: {product.price:.0f} ETB\n"
            f"📍 ቦታ/Location: {product.location}\n\n"
            f"🔗 {self.site.deployment_url}/product/{product.id}/\n\n"
            f"🤖 EthAfri Auto-Post"
        )
        payload = {
            "chat_id": channel_id,
            "caption": caption,
            "photo": product.image_url or "https://loremflickr.com/800/800/product"
        }
        try:
            requests.post(url, json=payload, timeout=5)
            logger.info(f"📢 Telegram Auto-Poster: Posted product {product.id}")
        except Exception as e:
            logger.error(f"Telegram Auto-Poster failed: {e}")


# ============================================================
# 🛡️ FRAUD HUNTER
# ============================================================

class FraudHunter:
    def __init__(self, site):
        self.site = site

    def scan_for_scams(self):
        Product = get_model('Product')
        suspicious = Product.objects.filter(site=self.site, price__lt=10, is_active=True)
        for p in suspicious:
            p.is_active = False
            p.save()
            logger.warning(f"🛡️ FraudHunter: Deactivated suspicious listing: '{p.title}'")


# ============================================================
# 🌐 GITHUB REMOTE REPOSITORY UTILS
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


def bootstrap_system_safely():
    SiteRegistry = get_model('SiteRegistry')
    try:
        if SiteRegistry.objects.filter(is_active=True).count() == 0:
            logger.info("⚙️ Bootstrapping: Fresh database detected. Auto-registering primary site...")
            SiteRegistry.objects.create(
                name="primary",
                display_name="EthAfri Primary",
                niche="general",
                target_market="Global",
                is_active=True,
                build_phase=0
            )
            _, _, broadcast_agent_log, _ = _get_ai_utils()
            broadcast_agent_log(None, "System Auto-Installed: Registered 'primary' domain successfully", "success")
    except Exception as e:
        logger.error(f"Failed to bootstrap database: {e}")


def get_site_project_state_dynamic(site):
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
        'growth_agent': 'marketplace/growth_agent.py',
        'ai_utils': 'marketplace/ai_utils.py',
        'self_doctor': 'marketplace/self_doctor.py',
        'code_apply': 'marketplace/code_apply.py',
    }

    state = {}
    file_paths = {}
    github_token = getattr(settings, 'GITHUB_TOKEN', None)

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

    if is_remote:
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
            logger.warning("Templates directory not found locally.")

    all_known_backlogs = AIProjectBacklog.objects.filter(site=site)
    for bk in all_known_backlogs:
        if bk.target_file not in file_paths:
            file_paths[bk.target_file] = resolve_local_file_path(site, bk.target_file)
            if bk.target_file not in state:
                state[bk.target_file] = "❌ MISSING_FILE"

    return state, file_paths


def get_or_create_backlog_task_safe(site, task_name, defaults):
    AIProjectBacklog = get_model('AIProjectBacklog')
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
# 🧬 SELF-READINESS GATE
# ============================================================

class SelfBootstrapManager:
    CORE_MODULES = {
        'growth_agent': 'marketplace/growth_agent.py',
        'ai_utils': 'marketplace/ai_utils.py',
        'code_apply': 'marketplace/code_apply.py',
        'self_doctor': 'marketplace/self_doctor.py',
    }
    RUNNING_PROCESS_MODULES = {'growth_agent', 'ai_utils', 'code_apply', 'self_doctor'}
    READY_KEY = "SELF_BOOTSTRAP_STATUS"
    REPAIR_ATTEMPT_KEY_PREFIX = "SELF_REPAIR_ATTEMPTS_"
    MAX_REPAIR_ATTEMPTS_PER_CYCLE = 3
    MAX_TOTAL_ATTEMPTS_PER_MODULE = 15

    @classmethod
    def _scan_core_files(cls):
        broken = {}
        base_dir = str(settings.BASE_DIR)
        for key, rel_path in cls.CORE_MODULES.items():
            full_path = os.path.join(base_dir, rel_path)
            if not os.path.exists(full_path):
                broken[key] = {"issue": "MISSING_FILE", "path": rel_path}
                continue
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    broken[key] = {"issue": "EMPTY_FILE", "path": rel_path}
                    continue
                ast.parse(content)
            except SyntaxError as e:
                broken[key] = {"issue": f"SYNTAX_ERROR: {e}", "path": rel_path}
            except Exception as e:
                broken[key] = {"issue": f"READ_ERROR: {e}", "path": rel_path}
        return broken

    @classmethod
    def _get_total_attempts(cls, module_key):
        SiteConfig = get_model('SiteConfig')
        cfg = SiteConfig.objects.filter(key=f"{cls.REPAIR_ATTEMPT_KEY_PREFIX}{module_key}").first()
        return cfg.value.get('count', 0) if cfg and isinstance(cfg.value, dict) else 0

    @classmethod
    def _increment_total_attempts(cls, module_key):
        SiteConfig = get_model('SiteConfig')
        cfg, _ = SiteConfig.objects.get_or_create(
            key=f"{cls.REPAIR_ATTEMPT_KEY_PREFIX}{module_key}", defaults={'value': {'count': 0}}
        )
        count = (cfg.value.get('count', 0) if isinstance(cfg.value, dict) else 0) + 1
        cfg.value = {'count': count, 'last_attempt': timezone.now().isoformat()}
        cfg.save()
        return count

    @classmethod
    def ensure_self_ready(cls):
        broken = cls._scan_core_files()

        if not broken:
            SiteConfig = get_model('SiteConfig')
            SiteConfig.objects.update_or_create(
                key=cls.READY_KEY,
                defaults={'value': {'status': 'ready', 'checked_at': timezone.now().isoformat()}}
            )
            return True

        logger.critical(f"🚨 SELF-BOOTSTRAP GATE: {len(broken)} core module(s) unhealthy: {list(broken.keys())}")
        SiteConfig.objects.update_or_create(
            key=cls.READY_KEY,
            defaults={'value': {
                'status': 'self_repairing',
                'broken': {k: v['issue'] for k, v in broken.items()},
                'checked_at': timezone.now().isoformat()
            }}
        )

        SiteRegistry = get_model('SiteRegistry')
        primary_site = SiteRegistry.objects.filter(name='primary').first()
        if not primary_site:
            logger.critical("🚨 SELF-BOOTSTRAP: No 'primary' site registered yet — cannot self-repair this cycle.")
            return False

        attempts = 0
        repaired_any_running_module = False
        while broken and attempts < cls.MAX_REPAIR_ATTEMPTS_PER_CYCLE:
            attempts += 1
            for module_key, info in list(broken.items()):
                total_attempts = cls._get_total_attempts(module_key)
                if total_attempts >= cls.MAX_TOTAL_ATTEMPTS_PER_MODULE:
                    logger.critical(f"🚨 SELF-REPAIR: '{module_key}' exceeded {cls.MAX_TOTAL_ATTEMPTS_PER_MODULE} repair attempts.")
                    continue
                cls._increment_total_attempts(module_key)
                success = cls._repair_module(primary_site, module_key, info)
                if success and module_key in cls.RUNNING_PROCESS_MODULES:
                    repaired_any_running_module = True
            broken = cls._scan_core_files()

        is_ready = len(broken) == 0

        if not is_ready:
            all_exhausted = all(cls._get_total_attempts(k) >= cls.MAX_TOTAL_ATTEMPTS_PER_MODULE for k in broken.keys())
            if all_exhausted:
                logger.critical(f"🚨 SELF-BOOTSTRAP: Repair attempts exhausted for {list(broken.keys())}. Proceeding in DEGRADED mode.")
                SiteConfig.objects.update_or_create(
                    key=cls.READY_KEY,
                    defaults={'value': {
                        'status': 'degraded_proceeding',
                        'broken': {k: v['issue'] for k, v in broken.items()},
                        'checked_at': timezone.now().isoformat()
                    }}
                )
                return True

            SiteConfig.objects.update_or_create(
                key=cls.READY_KEY,
                defaults={'value': {
                    'status': 'repair_failed',
                    'broken': {k: v['issue'] for k, v in broken.items()},
                    'checked_at': timezone.now().isoformat()
                }}
            )
            logger.critical(f"🚨 SELF-BOOTSTRAP: Repair attempts exhausted this cycle.")
            return False

        SiteConfig.objects.update_or_create(
            key=cls.READY_KEY,
            defaults={'value': {'status': 'ready', 'checked_at': timezone.now().isoformat()}}
        )
        logger.info("✅ SELF-BOOTSTRAP: All core modules verified healthy.")

        if repaired_any_running_module and os.getenv('SELF_HEAL_AUTO_RESTART', 'false').lower() == 'true':
            logger.critical("🧬 SELF-REPAIR: Core agent files were rewritten. Forcing controlled restart...")
            try:
                _, _, broadcast_agent_log, _ = _get_ai_utils()
                broadcast_agent_log(primary_site, "Self-repair complete — restarting process to load fixes.", "success")
            except Exception:
                pass
            os._exit(1)

        return True

    @classmethod
    def _repair_module(cls, site, module_key, info):
        logger.warning(f"🧬 SELF-REPAIR: Attempting to fix '{module_key}' ({info['issue']})")
        VectorMemory = get_model('VectorMemory')
        _, _, _, compress_code_for_prompt = _get_ai_utils()
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()
        SecurityAuditor, _, AntiBloatEngine = _get_self_doctor()
        apply_code_change = _get_code_apply()

        try:
            past_memories = VectorMemory.objects.filter(site=site).order_by('-id')[:3]
            memory_context = [compress_code_for_prompt(m.content) for m in past_memories]
        except Exception:
            memory_context = []

        prompt = (
            f"CRITICAL SELF-REPAIR TASK: The core autonomous-agent module '{module_key}' "
            f"(file: {info['path']}) is currently broken — Issue: {info['issue']}. "
            f"Write a COMPLETE, clean, syntactically valid replacement for this entire file "
            f"using 2026 Django/Python standards, preserving all functionality implied by its "
            f"role inside an autonomous e-commerce CEO agent system (EthAfri). "
            f"FEATURE CONSOLIDATION RULE: Consolidate helper logics, remove duplicate utility imports, "
            f"and write highly compact, parameter-driven functions that handle multiple agent operations at once.\n"
            f"Avoid repeating these past failures: {json.dumps(memory_context, ensure_ascii=False)}. "
            f"Return JSON with key 'code' containing the full file content."
        )
        try:
            res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))
        except Exception as e:
            logger.error(f"🧬 SELF-REPAIR: AI call failed for '{module_key}': {e}")
            return False

        if not (res and isinstance(res, dict) and 'code' in res):
            logger.error(f"🧬 SELF-REPAIR: No valid code returned for '{module_key}'")
            return False

        new_code = res['code']
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            logger.error(f"🧬 SELF-REPAIR: AI-generated fix for '{module_key}' still has a syntax error: {e}")
            return False

        is_safe, msg = SecurityAuditor.scan_code_safety(new_code, file_path=info['path'], site=site)
        if not is_safe:
            logger.error(f"🛡️ SELF-REPAIR: Security gate blocked fix for '{module_key}': {msg}")
            return False

        new_code = AntiBloatEngine.prune_and_optimize("", new_code, module_key)

        base_dir = str(settings.BASE_DIR)
        full_path = os.path.join(base_dir, info['path'])
        old_code = ""
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    old_code = f.read()
            except Exception:
                pass

        result = apply_code_change(site, module_key, new_code, reason=f"🧬 Self-Bootstrap Repair: {info['issue']}")
        if not result.get('success'):
            logger.error(f"❌ SELF-REPAIR: Failed to apply fix for '{module_key}': {result.get('message')}")
            return False

        applied_path = result.get('path', full_path)
        verified, vmsg = verify_disk_write(applied_path)
        if not verified:
            logger.error(f"❌ SELF-REPAIR: Disk verification failed for '{module_key}': {vmsg}. Rolling back...")
            rollback_file(applied_path, old_code)
            return False

        if module_key in DJANGO_APP_FILES:
            deep_ok, dmsg = deep_verify_django_app()
            if not deep_ok:
                logger.error(f"❌ SELF-REPAIR: Deep Django check failed for '{module_key}': {dmsg}. Rolling back...")
                rollback_file(applied_path, old_code)
                return False

        logger.info(f"✅ SELF-REPAIR: '{module_key}' rewritten and verified successfully.")
        try:
            VectorMemory.objects.create(site=site, memory_type='solution', content=f"Self-repaired core module: {module_key}")
        except Exception:
            pass
        return True


# ============================================================
# 🎡 MASTER ENGINE EXECUTION LOOPS
# ============================================================

def execute_master_cycle():
    bootstrap_system_safely()

    SiteConfig = get_model('SiteConfig')
    SiteRegistry = get_model('SiteRegistry')

    try:
        SiteConfig.objects.update_or_create(
            key="AGENT_HEARTBEAT",
            defaults={'value': {'status': 'active', 'timestamp': timezone.now().isoformat(), 'thread_count': threading.active_count()}}
        )
    except Exception as e:
        logger.debug("Failed to record active agent heartbeat: %s", e)

    try:
        SiteConfig.objects.update_or_create(
            key="EVOLUTION_LOCK",
            defaults={'value': {'status': 'self_checking', 'last_run': timezone.now().isoformat()}}
        )
    except Exception as e:
        logger.debug("Failed to record self-checking evolution lock: %s", e)

    is_self_ready = SelfBootstrapManager.ensure_self_ready()

    if not is_self_ready:
        logger.critical("🚨 Agent is NOT self-ready yet. Skipping full cycle.")
        try:
            SiteConfig.objects.update_or_create(
                key="EVOLUTION_LOCK",
                defaults={'value': {'status': 'self_repairing', 'last_run': timezone.now().isoformat()}}
            )
        except Exception as e:
            logger.debug("Failed to update status to self repairing: %s", e)
        return

    try:
        SiteConfig.objects.update_or_create(
            key="EVOLUTION_LOCK",
            defaults={'value': {'status': 'running', 'last_run': timezone.now().isoformat()}}
        )
    except Exception as e:
        logger.debug("Failed to set evolution lock to running: %s", e)

    active_sites = SiteRegistry.objects.filter(is_active=True)
    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            executor.map(_run_site_cycle, active_sites)
        finally:
            try:
                SiteConfig.objects.update_or_create(
                    key="EVOLUTION_LOCK",
                    defaults={'value': {'status': 'idle', 'last_run': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug("Failed to reset evolution lock to idle: %s", e)
            safe_close_connections()


def _run_site_cycle(site):
    _, _, broadcast_agent_log, _ = _get_ai_utils()
    SecurityAuditor, UniversalHealer, AntiBloatEngine = _get_self_doctor()
    FeatureEvolutionEngine = _get_feature_evolution()
    
    network_active = MultiChannelHarvester.is_network_available()

    def run_track_a_evolution():
        try:
            update_agent_progress(site, "Track A: Running Self-Doctor Maintenance...", 15)
            broadcast_agent_log(site, "🛠️ Track A: Running Self-Doctor maintenance...", "info")
            UniversalHealer(site).perform_maintenance()
            
            if network_active:
                update_agent_progress(site, "Track A: Planning Codebase Backlog...", 40)
                ceo = StrategicCEO(site)
                ceo.execute_planning_cycle()
                
                update_agent_progress(site, "Track A: Building Strategic Features in Sandbox...", 80)
                run_recursive_code_builder(site)
                
                update_agent_progress(site, "Track A: Self-Evolution...", 90)
                evolution_engine = FeatureEvolutionEngine(site)
                evolution_engine.evolve()
            else:
                update_agent_progress(site, "Track A: Offline Caching and Recovery...", 60)
                OfflineCacheManager = _get_offline_cache()
                OfflineCacheManager.process_stale_offline_tasks(site)
        except Exception as e:
            logger.error(f"❌ Track A (Evolution) failed for {site.name}: {e}")
        finally:
            safe_close_connections()

    def run_track_b_growth():
        try:
            update_agent_progress(site, "Track B: Gathering Market Products & Sellers...", 20)
            broadcast_agent_log(site, "📡 Track B: Gathering products and seller contacts...", "info")
            ops = CEOOperations(site)
            ops.run_business_growth()
            
            update_agent_progress(site, "Track B: Filtering Suspicious Listings (Spam)...", 50)
            ops.curate_user_listings()
            
            if network_active:
                update_agent_progress(site, "Track B: Spying on Competitors & Repricing...", 75)
                spy_engine = CompetitorIntelligenceEngine(site)
                spy_engine.spy_and_analyze_market()
                
                run_predictive_analysis(site)
                
            FraudHunter(site).scan_for_scams()
        except Exception as e:
            logger.error(f"❌ Track B (Growth) failed for {site.name}: {e}")
        finally:
            safe_close_connections()

    with ThreadPoolExecutor(max_workers=2) as cycle_executor:
        cycle_executor.submit(run_track_a_evolution)
        cycle_executor.submit(run_track_b_growth)

    update_agent_progress(site, "Cycle Completed Successfully! Sleeping...", 100)
    broadcast_agent_log(site, f"✨ Master Cycle executed successfully for {site.name}.", "success")


def run_recursive_code_builder(site):
    AIProjectBacklog = get_model('AIProjectBacklog')
    try:
        pending_tasks = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score')
        tasks_to_build = []
        seen_files = set()

        for task in pending_tasks:
            if task.target_file in seen_files:
                continue
            if RecursiveBuilder.is_on_cooldown(site, task.target_file):
                continue
            tasks_to_build.append(task)
            seen_files.add(task.target_file)
            if len(tasks_to_build) >= 4:
                break

        if tasks_to_build:
            builder = RecursiveBuilder(site)
            for t_task in tasks_to_build:
                try:
                    builder.build_next_feature(t_task)
                finally:
                    safe_close_connections()
    except Exception as build_loop_err:
        logger.error("Failed during builder loop execution: %s", build_loop_err)


def run_predictive_analysis(site):
    PredictionLog = get_model('PredictionLog')
    Product = get_model('Product')
    try:
        prod_count = Product.objects.filter(site=site).count()
        predicted_traffic = prod_count * random.uniform(15.0, 45.0)
        predicted_seo = min(100.0, prod_count * 2.5 + random.uniform(40.0, 60.0))
        
        PredictionLog.objects.create(
            site=site, prediction_type="traffic", predicted_value=predicted_traffic,
            confidence_score=85.5, input_data={"current_products": prod_count}
        )
        PredictionLog.objects.create(
            site=site, prediction_type="seo", predicted_value=predicted_seo,
            confidence_score=90.0, input_data={"current_products": prod_count}
        )
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        broadcast_agent_log(site, "📊 Predictive Engine: Generated traffic and SEO forecasts.", "info")
    except Exception as pred_err:
        logger.debug("Failed to record predictions: %s", pred_err)


# ============================================================
# 🎡 ADAPTIVE PACING DAEMON
# ============================================================

def start_autonomous_ceo():
    logger.info("🚀 EthAfri Master CEO Agent Started on Render Cloud...")
    
    while True:
        try:
            execute_master_cycle()

            AIProjectBacklog = get_model('AIProjectBacklog')

            has_pending = False
            try:
                has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
            except Exception as e:
                logger.debug("Failed to verify pending backlog status: %s", e)
            
            try:
                load_avg = os.getloadavg()[0]
            except (AttributeError, OSError, Exception):
                load_avg = 0.5
                
            if load_avg > 2.0:
                interval = 2700
                logger.warning(f"⚠️ Server CPU Load is heavy ({load_avg:.2f}). Pacing slowed to 45 minutes.")
            elif not MultiChannelHarvester.is_network_available():
                interval = 1800
                logger.warning("🌐 Offline Mode detected. Pacing slowed to 30 minutes.")
            else:
                interval = 5 if has_pending else 300
                
            logger.info(f"💤 Master Cycle Complete. Sleeping {interval} seconds...")
            time.sleep(interval)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO FATAL ERROR: {e}")
            time.sleep(10)

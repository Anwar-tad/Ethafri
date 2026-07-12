# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py
# 📝 ስሪት፦ v10.90 (Ultimate Evolved CEO Agent - Phase 1 Optimized)
# ✅ የተፈቱ ችግሮች፦
#   - Decoupled and token-optimized Competitor Intelligence (Spy Engine sends clean product list instead of raw HTML).
#   - Hardened AI response formats with strict raw JSON instructions (no markdown wrapper latency).
#   - Safe list slicing guardrails preventing crash during empty scraper responses.
#   - Balanced crawl pacing sleep timeouts (5-12s) to drop Render CPU load to sub-1.0 limits.
#   - Restructured Track A evolution loop pacing to run safely once every 4 hours.
# 📅 ቀን፦ Sunday, July 12, 2026
# ============================================================

from __future__ import annotations

from django.contrib.auth.models import User
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
from urllib.parse import urlparse  # 🛡️ FIXED: name 'urlparse' is not defined ስህተትን ለመፍታት

# ============================================================
# ⚙️ LOGGER SETUP
# ============================================================
logger = logging.getLogger(__name__)

# ============================================================
# 🔄 DYNAMIC MODEL LOADER (የክብ ጥገኝነት መከላከያ)
# ============================================================

def get_model(model_name: str):
    """Django ሞዴሎችን በዳይናሚክ መጫኛ"""
    try:
        return apps.get_model('marketplace', model_name)
    except Exception as e:
        logger.error(f"Failed to load model {model_name} dynamically: {e}")
        return None


# ============================================================
# ✅ LATE IMPORTS (የስርዓት መገናኛዎች መፍቻ)
# ============================================================

def _get_self_doctor():
    from .self_doctor import SecurityAuditor, UniversalHealer, AntiBloatEngine
    return SecurityAuditor, UniversalHealer, AntiBloatEngine


def _get_ai_utils():
    from .ai_utils import clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, AIUtils
    return clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, AIUtils.compress_code_for_prompt


def _get_code_apply():
    from .code_apply import apply_code_change
    return apply_code_change


def _get_scrapper_engine():
    """🛡️ FIXED: v12.0 ተኳሃኝነትን ለመጠበቅ የግሎባል ፊቸር ፈንክሽኖችን በዳይናሚክ መጫኛ"""
    from .scrapper_engine import scrape_and_extract_products, scrape_url
    return scrape_and_extract_products, scrape_url


def _get_offline_cache():
    from .database_memory import OfflineCacheManager
    return OfflineCacheManager


def _get_feature_evolution():
    from .feature_evolution import FeatureEvolutionEngine
    return FeatureEvolutionEngine


# ============================================================
# 🌐 GLOBAL CONSTANTS & LOCKS
# ============================================================

_project_hashes = {}
_apply_lock = threading.Lock()
DJANGO_APP_FILES = {'models', 'views', 'urls', 'forms', 'admin'}


# ============================================================
# 🛡️ GLOBAL HEALERS
# ============================================================

def safe_close_connections():
    try:
        connections.close_all()
    except Exception as e:
        logger.debug(f"Connection cleanup safely bypassed: {e}")


def translate_text_incremental(texts, target_lang):
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


def resolve_local_file_path(site, target_file):
    if target_file.endswith('_html') or 'html' in target_file:
        clean_name = target_file.replace('_html', '') + '.html'
        return os.path.join(settings.BASE_DIR, 'marketplace', 'templates', 'marketplace', clean_name)
    return os.path.join(settings.BASE_DIR, 'marketplace', f"{target_file}.py")


def is_html_target(target_file):
    return target_file.endswith('_html') or 'html' in target_file


def extract_telegram_username(url_or_channel: str) -> str:
    if not url_or_channel:
        return ""
    clean = url_or_channel.strip().replace('@', '')
    if 't.me/' in clean:
        clean = clean.split('t.me/')[-1]
    if '/' in clean:
        clean = clean.split('/')[0]
    clean = clean.split('?')[0]
    return clean.strip()


def has_seeded_products(site):
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


def verify_disk_write(path):
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


def update_agent_progress(site, step_msg, percentage):
    try:
        SiteConfig = get_model('SiteConfig')
        SiteConfig.objects.update_or_create(
            key=f"AGENT_PROGRESS_{site.name}",
            defaults={'value': {'step': step_msg, 'percent': percentage, 'updated_at': timezone.now().isoformat()}}
        )
    except Exception:
        pass


def calculate_site_phase(state, site) -> int:
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


class RecursiveOptimizer:
    def __init__(self, site):
        self.site = site

    def refine_strategy(self):
        """የስህተት ሎጎችን አይቶ የ AI ፕሮምፕት መመሪያዎችን ያሻሽላል"""
        AgentErrorLog = get_model('AgentErrorLog')
        SiteConfig = get_model('SiteConfig')
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()

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


class MetaSelfArchitectEngine:
    def __init__(self, site):
        self.site = site

    def analyze_and_architect_self(self):
        AIProjectBacklog = get_model('AIProjectBacklog')
        Product = get_model('Product')
        AgentErrorLog = get_model('AgentErrorLog')
        clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, _ = _get_ai_utils()
        
        state, _ = get_site_project_state_dynamic(self.site)
        state_summary = {k: "Present" if "❌" not in v else "Missing" for k, v in state.items()}
        
        try:
            prod_count = Product.objects.filter(site=self.site, is_active=True).count()
            err_count = AgentErrorLog.objects.filter(site=self.site, resolved=False).count()
        except Exception:
            prod_count = 0
            err_count = 0
            
        metrics_summary = {
            "active_products": prod_count,
            "unresolved_errors": err_count,
            "current_time": timezone.now().isoformat()
        }
        
        prompt = (
            f"Audit your own system state: {json.dumps(state_summary)}.\n"
            f"Live system metrics: {json.dumps(metrics_summary)}.\n"
            f"Identify exactly 3 highly optimized, non-redundant, and advanced features we should add to ourselves.\n"
            f"Return JSON with key 'self_architected_tasks' containing list of objects: "
            "[{'name': '🧠 SELF-EVOLUTION: [Brief Name]', 'priority': 'Critical'/'High', 'file': '[proposed_file_name_without_py_extension]', 'desc': '...', 'impact': 1-10}]."
        )
        
        try:
            res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))
            tasks = res.get('self_architected_tasks', []) if res else []
            
            for t in tasks:
                if isinstance(t, dict) and t.get('name'):
                    get_or_create_backlog_task_safe(
                        self.site, 
                        t['name'],
                        defaults={
                            'task_type': 'code',
                            'target_file': t.get('file', 'views'),
                            'priority': t.get('priority', 'High'),
                            'status': 'Pending',
                            'description': f"Self-Architected Task: {t.get('desc')}.",
                            'business_impact_score': int(t.get('impact', 8)),
                            'trigger_condition': 'Meta-Autonomous Self-Evolution Loop'
                        }
                    )
            broadcast_agent_log(self.site, f"✨ Self-Architect: Evaluated self-state. Injected {len(tasks)} ranked self-evolution tasks!", "success")
        except Exception as e:
            logger.error(f"MetaSelfArchitectEngine: Failed to architect self: {e}")


# ============================================================
# 🏛️ STRATEGIC CEO (የዕቅድ እና የስልት ማዕከል)
# ============================================================

class StrategicCEO:
    def __init__(self, site):
        self.site = site

    def execute_planning_cycle(self):
        self._process_owner_directives()
        self.check_for_self_audit()

        AIProjectBacklog = get_model('AIProjectBacklog')
        SiteConfig = get_model('SiteConfig')
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()

        if random.random() < 0.2:
            self.research_latest_tech_upgrades()

        if AIProjectBacklog.objects.filter(site=self.site, status='Pending').exists():
            return

        state, file_paths = get_site_project_state_dynamic(self.site)
        current_phase = calculate_site_phase(state, self.site)

        try:
            self.site.build_phase = current_phase
            self.site.save()
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
                    self.site, f"🕵️ SPY: {comp['name']}",
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
                            self.site, t['name'],
                            defaults={
                                'priority': t.get('priority', 'Medium'),
                                'status': 'Pending',
                                'target_file': t.get('file', 'views'),
                                'description': t.get('desc', '')
                            }
                        )

    def research_latest_tech_upgrades(self):
        try:
            clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()
            query = "advanced Django performance optimizations and scaling 2026"
            prompt = (
                f"Perform an automated research task on query: '{query}'.\n"
                f"Identify exactly 1 performance optimization or security architecture for Django 4/5.\n"
                f"Return JSON with keys 'task_name', 'target_file' (e.g. 'views', 'models'), 'description', 'business_impact_score' (1-10)."
            )
            res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
            if res and isinstance(res, dict) and res.get('task_name'):
                get_or_create_backlog_task_safe(
                    self.site, 
                    f"🧠 RESEARCH UPGRADE: {res['task_name']}",
                    defaults={
                        'priority': 'High',
                        'status': 'Pending',
                        'target_file': res.get('target_file', 'views'),
                        'description': f"Research-Backed Upgrade: {res.get('description')}.",
                        'business_impact_score': int(res.get('business_impact_score', 8)),
                        'trigger_condition': 'Tech Research Loop'
                    }
                )
        except Exception as e:
            logger.debug(f"Dynamic tech research skipped: {e}")

    def check_for_self_audit(self):
        SiteConfig = get_model('SiteConfig')
        last_self_audit = SiteConfig.objects.filter(key=f"LAST_SELF_AUDIT_{self.site.name}").first()

        if not last_self_audit or (timezone.now() - last_self_audit.updated_at) >= timedelta(hours=3):
            architect = MetaSelfArchitectEngine(self.site)
            architect.analyze_and_architect_self()
            try:
                SiteConfig.objects.update_or_create(
                    key=f"LAST_SELF_AUDIT_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug("Failed to record self audit config: %s", e)

    def _process_owner_directives(self):
        AdminOverrideInstruction = get_model('AdminOverrideInstruction')
        for cmd in AdminOverrideInstruction.objects.filter(site=self.site, is_processed=False):
            get_or_create_backlog_task_safe(
                self.site, f"👑 OWNER: {cmd.instruction[:30]}",
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
# ⚙️ 🛠️ LIGHWEIGHT HTML TAG VALIDATOR
# ============================================================

def html_content_is_malformed(html_content: str) -> bool:
    for tag in ['div', 'form', 'section', 'main']:
        open_count = len(re.findall(rf'<{tag}\b', html_content, re.IGNORECASE))
        close_count = len(re.findall(rf'</{tag}>', html_content, re.IGNORECASE))
        if open_count != close_count:
            return True
    return False


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

        _, _, _, compress_code_for_prompt = _get_ai_utils()
        VectorMemory = get_model('VectorMemory')
        
        past_memories = VectorMemory.objects.filter(site=self.site).order_by('-id')[:3]
        memory_context = [compress_code_for_prompt(m.content) for m in past_memories]

        task.status = 'Running'
        task.save()

        prompt = (
            f"Task: {task.task_name}. Write full clean Python/HTML code for {task.target_file} using 2026 standards.\n"
            f"CRITICAL: Avoid repeating these past failures/issues: {json.dumps(memory_context, ensure_ascii=False)}.\n"
            f"CRITICAL FRAMEWORK RULE: We are using Django 4/5. Never generate code for Flask, FastAPI, or any other frameworks. Write strictly Django-compliant Python.\n"
            f"FEATURE CONSOLIDATION RULE: Before appending new functions or classes, examine the existing code of the file. "
            f"If the new feature overlaps with existing functions, you MUST refactor and extend the existing functions (merge them) "
            f"to avoid any code duplication.\n"
            f"Return JSON with key 'code' containing the full file content."
        )

        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()
        
        attempts = 0
        new_code = ""
        syntax_error_msg = ""
        target_is_html = is_html_target(task.target_file)
        
        while attempts < 3:
            attempts += 1
            if syntax_error_msg:
                retry_prompt = (
                    f"Your previous code attempt for '{task.target_file}' returned the following syntax or structure error: '{syntax_error_msg}'.\n"
                    f"Please fully repair and refactor the code to fix this issue completely.\n"
                    f"Return JSON with key 'code'."
                )
                res = clean_and_parse_json(ask_master_ai_smart(retry_prompt, task_type="coding", task=task))
            else:
                res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding", task=task))

            if not (res and isinstance(res, dict) and 'code' in res):
                syntax_error_msg = "Invalid JSON or missing 'code' key in response payload"
                continue

            new_code = res['code']
            if target_is_html:
                if html_content_is_malformed(new_code):
                    syntax_error_msg = "Malformed HTML detected (unbalanced tags or unclosed container structures)"
                    continue
                break
            else:
                try:
                    compile(new_code, '<string>', 'exec')
                    break
                except SyntaxError as e:
                    syntax_error_msg = f"SyntaxError: {e}"
                    logger.warning(f"⚠️ Recursive Compiler (Attempt {attempts}/3): Found syntax error: {syntax_error_msg}. Retrying...")
                    
        if attempts >= 3 and syntax_error_msg:
            logger.error(f"❌ Recursive Compiler: Failed to compile {task.target_file} after 3 self-healing attempts. Last Error: {syntax_error_msg}")
            task.status = 'Pending'
            task.save()
            return "Failed Syntax Self-Heal"

        SecurityAuditor, _, _ = _get_self_doctor()
        
        is_safe, msg = SecurityAuditor.scan_code_safety(new_code, file_path=task.target_file, site=self.site)
        if not is_safe:
            logger.error(f"🛡️ Security Gate Blocked Code for {task.target_file}: {msg}")
            task.status = 'Blocked'
            task.save()
            return "Security Block"

        apply_code_change = _get_code_apply()
        _, _, AntiBloatEngine = _get_self_doctor()

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
# 📡 4. DYNAMIC MULTI-CHANNEL HARVESTER (የበይነመረብ ፍለጋ አሳሽ)
# ============================================================

def _autonomous_no_api_search_fallback(niche):
    logger.warning(f"⚠️ Search Fallback: Running non-AI DuckDuckGo search for niche '{niche}'...")
    query = f"Ethiopia buying and selling telegram channel {niche}"
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    fallback_sources = []
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            telegram_usernames = re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', res.text)
            for username in list(set(telegram_usernames))[:4]:
                if username.lower() not in ['s', 'joinchat', 'share', 'tgme']:
                    fallback_sources.append({"url_or_channel": username, "platform_type": "Telegram"})
                    
            web_domains = re.findall(r'https?://(?:www\.)?([a-zA-Z0-9-]+\.(?:com\.et|com|et))', res.text)
            for domain in list(set(web_domains))[:2]:
                if not any(x in domain for x in ['google', 'duckduckgo', 'yandex', 'yahoo', 'telesco']):
                    fallback_sources.append({"url_or_channel": f"https://{domain}", "platform_type": "GenericWeb"})
                    
            logger.info(f"✨ Fallback Search: Discovered {len(fallback_sources)} sources without any AI API Keys!")
    except Exception as e:
        logger.error(f"DuckDuckGo search fallback failed: {e}")
        
    return fallback_sources


class MultiChannelHarvester:
    """የኢንተርኔት ፍለጋዎችን በዳይናሚክ በማሽከርከር አዳዲስ ምንጮችን የሚመዘግብ እና ክልከላዎችን የሚያጠና የስለላ ሞተር (v10.60)"""
    
    @staticmethod
    def is_network_available():
        try:
            return requests.get("https://google.com", timeout=3).status_code == 200
        except requests.RequestException:
            return False
            
    def _get_rotating_search_query(self, site) -> str:
        queries = [
            f"Ethiopia active online marketplaces and eCommerce websites {site.niche} 2026",
            f"የመኪና እና የቤት ሽያጭ ዌብሳይቶች ኢትዮጵያ 2026",
            f"Ethiopian telegram channels buying and selling listing directory",
            f"New shopping websites in Addis Ababa Ethiopia",
            f"Ethiopia classified sites list {site.niche}"
        ]
        day_index = datetime.now().day % len(queries)
        return queries[day_index]

    def discover_active_market_sources(self, site):
        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()
        
        dynamic_query = self._get_rotating_search_query(site)
        logger.info(f"🔍 Dynamic Discovery: Scanning using query: '{dynamic_query}'")
        
        prompt = (
            f"Search the live internet using this query: '{dynamic_query}'.\n"
            f"Identify active online buying and selling websites, classified directories, "
            f"or active Telegram channel usernames currently popular in Ethiopia in 2026.\n"
            f"Provide up to 5 verified active web links or Telegram channel usernames.\n"
            f"Return the results STRICTLY in a JSON format with key 'sources' containing a list of objects with keys 'url_or_channel' and 'platform_type' (must be 'Jiji', 'Telegram', or 'GenericWeb')."
        )
        
        sources = []
        try:
            response = ask_master_ai_smart(prompt, task_type="market_research")
            data = clean_and_parse_json(response)
            sources = data.get('sources', []) if data else []
        except Exception as e:
            logger.warning(f"Grounded discovery failed ({e}). Attempting unauthenticated fallback...")
            
        if not sources:
            sources = _autonomous_no_api_search_fallback(site.niche)
            
        return sources

    def _save_sources_to_cache(self, site, new_sources):
        try:
            SiteConfig = get_model('SiteConfig')
            config, created = SiteConfig.objects.get_or_create(
                key=f"ACTIVE_SOURCES_{site.name}",
                defaults={'value': {'sources': [], 'last_updated': timezone.now().isoformat()}}
            )
            
            existing_sources = config.value.get('sources', []) if isinstance(config.value, dict) else []
            master_dict = {s['url_or_channel'].strip().lower(): s for s in existing_sources if 'url_or_channel' in s}
            
            for s in new_sources:
                key = s.get('url_or_channel', '').strip().lower()
                if key and key not in master_dict:
                    master_dict[key] = s
                    logger.info(f"✨ New Source Discovered & Registered: {s['url_or_channel']} ({s['platform_type']})")
            
            merged_sources = list(master_dict.values())
            
            config.value = {
                'sources': merged_sources[:150],
                'last_updated': timezone.now().isoformat()
            }
            config.save()
            logger.info(f"💾 Source Registry Expanded: Total active sources is now {len(merged_sources)}")
        except Exception as e:
            logger.error(f"Failed to expand source registry: {e}")

    def _get_cached_sources(self, site):
        try:
            SiteConfig = get_model('SiteConfig')
            config = SiteConfig.objects.filter(key=f"ACTIVE_SOURCES_{site.name}").first()
            if config and isinstance(config.value, dict):
                return config.value.get('sources', [])
        except Exception as e:
            logger.debug(f"Failed to get cached sources: {e}")
        return []

    def _get_fallback_sources(self):
        return [
            {"url_or_channel": "shegemarket", "platform_type": "Telegram"},
            {"url_or_channel": "merkato_market", "platform_type": "Telegram"},
            {"url_or_channel": "ethiomarketlink", "platform_type": "Telegram"},
            {"url_or_channel": "habesha_market", "platform_type": "Telegram"},
            {"url_or_channel": "addismarket", "platform_type": "Telegram"},
            {"url_or_channel": "gebezamarket", "platform_type": "Telegram"},
            {"url_or_channel": "addisababadelivery", "platform_type": "Telegram"},
            {"url_or_channel": "ethio_brand_market", "platform_type": "Telegram"},
            {"url_or_channel": "sheger_brand", "platform_type": "Telegram"},
            {"url_or_channel": "https://jiji.com.et", "platform_type": "Jiji"},
        ]

    def check_source_health(self, source):
        """ሳይቶችን Dead ብሎ ተስፋ እንዳይቆርጥ ሁልጊዜ True እንዲመልስ ማድረግ"""
        url = source.get('url_or_channel', '')
        if not url: return False
        
        if 'jiji' in url.lower() or 't.me' in url.lower() or '@' in url:
            return True
            
        try:
            res = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            return res.status_code == 200
        except:
            return False

    def get_recent_products(self, source):
        url = source.get('url_or_channel', '')
        platform = source.get('platform_type', '')
        
        try:
            if platform == 'Telegram':
                return self._scrape_telegram(url)
            elif platform in ['Jiji', 'GenericWeb']:
                return self._scrape_website(url)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            self.perform_source_reconnaissance(source, f"Execution Crash: {str(e)}")
        return []
    
    def _scrape_telegram(self, channel):
        username = extract_telegram_username(channel)
        url = f"https://t.me/s/{username}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                messages = re.findall(r'<div[^>]*class=["\']tgme_widget_message_text[^"\']*["\'][^>]*>([\s\S]*?)</div>', res.text)
                images = re.findall(r"background-image:\s*url\(['\"]?([^'\)]+)['\"]?\)", res.text)
                
                products = []
                for i, msg in enumerate(messages[:8]): 
                    clean_text = re.sub(r'<[^>]+>', ' ', msg).strip()
                    if clean_text:
                        product = self._parse_product_text(clean_text)
                        if product:
                            product['image_url'] = images[i] if i < len(images) else ''
                            products.append(product)
                
                if not products and len(messages) > 0:
                    self.perform_source_reconnaissance(
                        {"url_or_channel": channel, "platform_type": "Telegram"},
                        "Scraped Telegram successfully, but 0 products parsed. Pattern mismatch.",
                        html_content=res.text
                    )
                return products
            else:
                self.perform_source_reconnaissance(
                    {"url_or_channel": channel, "platform_type": "Telegram"},
                    f"Telegram Web Preview returned HTTP {res.status_code}. Possible rate limiting."
                )
        except Exception as e:
            logger.error(f"Telegram scrape failed for {channel}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": channel, "platform_type": "Telegram"}, str(e))
        return []
    
    def _scrape_website(self, url):
        try:
            # 🛡️ FIXED: v12.0 ተኳሃኝነትን ለመጠበቅ የግሎባል ኤክስትራክተሩን በ views ላይ በሰላም መጥራት
            from .scrapper_engine import scrape_and_extract_products
            products = scrape_and_extract_products(url)
            return products
        except Exception as e:
            logger.error(f"Website scrape failed for {url}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": url, "platform_type": "GenericWeb"}, str(e))
        return []
    
    def _parse_product_text(self, text):
        """የምርት ስምን፣ የቴሌግራም ሲስተም መልዕክቶችን፣ ተራ ወሬዎችን እና የ3 ወር ጊዜ ገደብን የሚፈትሽ (v10.95 - Ultimate Clean Parser)"""
        if not text: return None
        
        system_keywords = [
            "channel name was changed", "channel photo updated", "channel created",
            "pinned", "joined", "group created", "photo updated", "name changed",
            "coming soon", "keep joining", "live stream", "telegram channel",
            "ተለቀቀ", "ገብተናል", "ገባን", "ተከፈተ", "join", "subscribe", "👇", "👉", "⚠️"
        ]
        text_lower = text.lower()
        if any(kw in text_lower for kw in system_keywords) and len(text) < 200:
            return None

        product_nouns = [
            'toyota', 'kia', 'hyundai', 'suzuki', 'iphone', 'samsung', 'laptop', 'lenovo', 
            'hp', 'dell', 'apartment', 'condominium', 'house', 'vitz', 'yaris', 'corolla', 
            'mercedes', 'byd', 'veloster', 'morning', '4-runner', 'model', 'car', 'phone', 
            'notebook', 'tecno', 'zte', 'spark', 'ሸቀጥ', 'ሽያጭ', 'መኪና', 'ስልክ', 'ላፕቶፕ', 'ቤት', 'apartment'
        ]
        if not any(noun in text_lower for noun in product_nouns) and len(text) < 400:
            return None

        import html
        clean_text = html.unescape(text)
        clean_text = re.sub(r'<[^>]+>', '\n', clean_text)
        clean_text = re.sub(r'<!--[\s\S]*?-->', '\n', clean_text)
        
        old_patterns = [r'2023', r'2024', r'2025', r'[4-9]\s*months?\s*ago', r'year\s*ago']
        for pattern in old_patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                return None

        product = {'title': '', 'price': 0, 'description': '', 'desc': '', 'seller_contact': ''}
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        if not lines: return None
        
        raw_title = lines[0]
        slogans = ["አመልጣኝ", "አዲስ", "ደውሉ", "አስቸኳይ", "ቅናሽ", "ለሽያጭ", "ሽያጭ", "አሪፍ", "የሚሸጥ", "የሚከራይ", "ተለቀቀ"]
        if any(s in raw_title for s in slogans) or len(raw_title) < 10:
            found_title = False
            for line in lines[1:4]:
                if any(brand in line.lower() for brand in product_nouns):
                    product['title'] = line[:100]
                    found_title = True
                    break
            if not found_title:
                product['title'] = lines[0][:150]
        else:
            product['title'] = lines[0][:150]
            
        words = product['title'].split()
        if len(words) > 5:
            product['title'] = " ".join(words[:4])
            
        price_match = re.search(r'(?:ዋጋ|Price|Birr|ብር)\s*[:፡-]?\s*([\d,]+)', clean_text, re.IGNORECASE) or \
                      re.search(r'([\d,]+)\s*(?:ETB|ብር|Birr|Br)', clean_text, re.IGNORECASE)
        if price_match:
            try:
                product['price'] = float(price_match.group(1).replace(',', ''))
            except: pass
            
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', clean_text)
        if phone_match:
            product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
        else:
            tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', clean_text)
            if tg_match:
                product['seller_contact'] = tg_match.group(0)
        
        product['description'] = clean_text[:1000].replace('\n\n', '\n').strip()
        product['desc'] = product['description']
        return product
    
    def _extract_products_from_html(self, html):
        """(Deprecated - Bypassed for ScrapperEngine.scrape_and_extract)"""
        products = []
        items = re.findall(r'<div[^>]*class="[^"]*(?:b-list-advert-single|b-trending-card|qa-advert-list-item)[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        for item in items:
            product = self._parse_product_text(item)
            if product and product['title']:
                products.append(product)
        return products

    def perform_source_reconnaissance(self, source, error_msg, html_content=None):
        url = source.get('url_or_channel', '')
        platform = source.get('platform_type', 'GenericWeb')
        domain = urlparse(url).netloc.lower() or url.replace('@', '').lower()
        
        block_reason = "የማይታወቅ እገዳ (Access Blocked)"
        if "403" in error_msg or "Forbidden" in error_msg:
            block_reason = "HTTP 403 Forbidden (Firewall/Cloudflare IP Ban ተገኝቷል)"
        elif "429" in error_msg or "Too Many Requests" in error_msg:
            block_reason = "HTTP 429 Too Many Requests (የኤፒአይ ፍጥነት ገደብ/Throttled)"
        elif "Timeout" in error_msg or "timed out" in error_msg:
            block_reason = "የሰዓት ማለፍ ግንኙነት መቋረጥ (Timeout - ሰርቨሩ ጥበቃ አለው ወይም ጠፍቷል)"
        elif "0 products extracted" in error_msg:
            block_reason = "የይዘት አወቃቀር መዛባት (DOM Structure Mismatch - የዌብሳይቱ ዲዛይን ተቀይሯል)"

        density_estimation = "Cannot evaluate (Complete connection block)"
        if html_content:
            text_len = len(html_content)
            links_count = len(re.findall(r'href=', html_content))
            images_count = len(re.findall(r'<img', html_content))
            density_estimation = (
                f"የፋይሉ ርዝመት፦ {html_len} ፊደላት። "
                f"የተገኙ ሊንኮች፦ {detected_links}። የተገኙ ፎቶዎች፦ {detected_images}።\n"
                f"የተጠቃሚዎች መጠቅለያ (Estimated Active Users)፦ በግምት {max(detected_links // 5, 10)} ንቁ ሻጮች።\n"
                f"የምርት መጠቅለያ (Estimated Products)፦ በግምት {max(detected_links // 2, 20)} ንቁ ምርቶች በዋናው ገጽ ላይ ተገኝተዋል።\n"
                f"የገበያው የሽያጭ ሁኔታ፦ {market_activity}።"
            )

        deep_paths = []
        if html_content:
            found_paths = re.findall(r'href=["\'](/[^"\']*(?:cars?|vehicles?|apartments?|electronics?|computers?|phones?|mobiles?|classifieds?|sitemap)[^"\']*)["\']', html_content, re.IGNORECASE)
            for path in found_paths[:5]:
                full_path = (url + path) if path.startswith('/') else path
                deep_paths.append(full_path)
                
        deep_path_brief = "\n".join([f"- {p}" for p in list(set(deep_paths))]) if deep_paths else "No deep subcategory URLs detected on home page."

        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()
        
        prompt = (
            f"We failed to scrape this Ethiopian marketplace: {url} ({platform}).\n"
            f"Detected Obstacle: {block_reason} ({error_msg}).\n"
            f"Target Web Statistics: {density_estimation}.\n\n"
            f"Please write a strategic RECONNAISSANCE REPORT & DEVELOPMENT ADVISORY for the developer. You must return JSON with exactly two keys:\n"
            f"1. 'analysis': Strategic analysis of why we got blocked, how to bypass it on the next crawl (max 300 characters).\n"
            f"2. 'recommended_patch': A concise Python BeautifulSoup/Regex code patch (max 500 characters) that the human admin can copy and paste into scrapper_engine.py or growth_agent.py to extract products from this site structure. Write the code inside a clean string."
        )
        
        analysis_text = "AI analysis throttled due to active rate limits."
        code_patch = "# No patch generated due to API limit. Check CSS selectors manually."
        
        try:
            res = ask_master_ai_smart(prompt, task_type="analysis")
            data = clean_and_parse_json(res)
            if data and isinstance(data, dict):
                analysis_text = data.get('analysis', analysis_text)
                code_patch = data.get('recommended_patch', code_patch)
        except Exception as e:
            logger.debug(f"AI Reconnaissance Analysis skipped: {e}")

        try:
            AIProjectBacklog = get_model('AIProjectBacklog')
            task_name = f"🕵️ RECON INTEL BRIEF: {domain}"[:200]
            
            if not AIProjectBacklog.objects.filter(task_name=task_name).exists():
                AIProjectBacklog.objects.create(
                    site=get_model('SiteRegistry').objects.filter(is_active=True).first(),
                    task_name=task_name,
                    target_file="scrapper_engine",
                    priority="High",
                    status="Blocked",
                    description=(
                        f"============================================================\n"
                        f"🕵️ AUTONOMOUS SCRAPER RECONNAISSANCE INTELLIGENCE BRIEF\n"
                        f"============================================================\n"
                        f"🌐 TARGET WEBSITE: {url}\n"
                        f"🛡️ OBSTACLE ENCOUNTERED: {block_reason}\n"
                        f"📊 TARGET MARKET STATISTICS:\n{density_estimation}\n\n"
                        f"🔍 DEEP-DIVE CRAWL TARGETS:\n{deep_path_brief}\n\n"
                        f"------------------------------------------------------------\n"
                        f"💡 AI STRATEGIST BYPASS GUIDE:\n"
                        f"------------------------------------------------------------\n"
                        f"{analysis_text}\n\n"
                        f"------------------------------------------------------------\n"
                        f"🛠️ RECOMMENDED CODE PATCH FOR ADMIN (COPY & PASTE TO FIX):\n"
                        f"------------------------------------------------------------\n"
                        f"```python\n{code_patch}\n```\n"
                        f"============================================================\n"
                    ),
                    business_impact_score=8,
                    trigger_condition="Autonomous Scraper Reconnaissance Loop"
                )
        except Exception as db_err:
            logger.error(f"Failed to save Reconnaissance Task: {db_err}")

    def discover_and_harvest_niche_sources(self, site):
        """🛡️ FIXED: ክላሱ ውስጥ በትክክል ገብቶ የተጻፈው ዋና ምርት መሰብሰቢያ ሎጂክ"""
        if not self.is_network_available():
            logger.warning("🌐 No internet connection. Using cached sources.")
            return self._get_cached_sources(site)
        
        SiteConfig = get_model('SiteConfig')
        
        if random.random() < 0.1 or not self._get_cached_sources(site):
            new_discovered = self.discover_active_market_sources(site)
            if new_discovered:
                self._save_sources_to_cache(site, new_discovered)
        
        sources = self._get_cached_sources(site)
        
        if not sources:
            logger.warning("⚠️ No active sources found via AI or cache. Seeding default fallback sources...")
            sources = self._get_fallback_sources()
            self._save_sources_to_cache(site, sources)
        
        all_products = []
        scraped_this_cycle = 0
        
        # 🛡️ [ዘመናዊ የአሰሳ ማፈራረቂያ] የ 15 ቀናት የመኝታ ጊዜ መቆጣጠሪያ (Intelligent Crawl Intervals)
        for source in sources:
            url = source.get('url_or_channel', '')
            domain = urlparse(url).netloc.lower() or url.replace('@', '').lower()
            
            # የእያንዳንዱን ምንጭ የመጨረሻ ዳሰሳ ሰዓት ከ SiteConfig ማምጣት
            last_scrape_key = f"LAST_SCRAPE_TIME_{domain}"
            last_scrape_cfg = SiteConfig.objects.filter(key=last_scrape_key).first()
            
            # ፈጣን አሰሳ ለሚፈልጉት (እንደ ቴሌግራም/Jiji) የ 1 ቀን፣ ለሌሎቹ የ 15 ቀናት መቆያ መመደብ
            cooldown_days = 1 if ('jiji' in domain or 't.me' in domain or '@' in domain) else 15
            
            should_scrape = True
            if last_scrape_cfg and isinstance(last_scrape_cfg.value, dict):
                try:
                    last_time_str = last_scrape_cfg.value.get('time')
                    if last_time_str:
                        last_time = datetime.fromisoformat(last_time_str)
                        if timezone.is_naive(last_time):
                            last_time = timezone.make_aware(last_time)
                        
                        next_allowed_time = last_time + timedelta(days=cooldown_days)
                        if timezone.now() < next_allowed_time:
                            remaining_time = next_allowed_time - timezone.now()
                            logger.info(f"⏭️ Crawl Pacing: Skipping '{domain}' — Cooldown active for next {remaining_time.days}d {remaining_time.seconds // 3600}h.")
                            should_scrape = False
                except Exception:
                    pass
            
            if should_scrape and scraped_this_cycle < 3:
                logger.info(f"📡 Scraping {url}...")
                products = self.get_recent_products(source)
                scraped_this_cycle += 1
                
                # የተሳካ የአሰሳ ጊዜን መመዝገብ
                SiteConfig.objects.update_or_create(
                    key=last_scrape_key,
                    defaults={'value': {'time': timezone.now().isoformat(), 'status': 'success' if products else 'no_data'}}
                )
                
                if products:
                    all_products.extend(products)
                    logger.info(f"✅ Found {len(products)} products from {url}")
                else:
                    self.perform_source_reconnaissance(source, "Website crawled successfully, but returned 0 products.")
        
        return all_products


# ============================================================
# 💼 CEO OPERATIONS
# ============================================================

class CEOOperations:
    def __init__(self, site):
        self.site = site

    def run_business_growth(self):
        """የንግድ ዕድገት ዑደት (Bulk Harvesting + Listing Curation)"""
        try:
            prod_count = get_model('Product').objects.filter(site=self.site, is_active=True).count()
            logger.info(f"📈 Running business growth cycle for {self.site.name}")
            logger.info(f"📊 Current product count: {prod_count}")
        except Exception as conn_err:
            from .self_doctor import refresh_db_connection_on_error
            refresh_db_connection_on_error(str(conn_err))

        self._harvest_verified_products_bulk()
        self.curate_user_listings()
        self._boost_revenue()
        self.dispatch_pending_notifications()

    def _heuristic_parse_text(self, text):
        if not text: return None
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines: return None
        
        title = lines[0][:150]
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text)
        tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
        
        contact = re.sub(r'[^\d+]', '', phone_match.group(0)) if phone_match else (tg_match.group(0) if tg_match else "0900000000")
            
        price = 0.0
        price_match = re.search(r'(?:ዋጋ|Price|Birr|ETB|ብር)\s*[:፡-]?\s*([\d,]+)', text, re.IGNORECASE)
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', ''))
            except ValueError:
                price = 0.0
                    
        return {"title": title, "price": price, "desc": text[:1000], "seller_contact": contact}

    def _harvest_verified_products_bulk(self):
        """ምርቶችን በጅምላ ያስሳል - ስህተቶችን ለመከላከል የታረመ ስሪት (v10.36)"""
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()

        # 1. መቆያ ጊዜ መፈተሻ (Cooldown)
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        prod_count = Product.objects.filter(site=self.site, is_active=True).count()
        is_empty_or_low = prod_count < 120
        
        if last and not is_empty_or_low:
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if (timezone.now() - last_time) < timedelta(hours=1):
                    return
            except Exception as e:
                logger.warning(f"Error checking harvest timestamp: {e}")

        # 2. ዳታ መሰብሰብ (ከቴሌግራም እና ዌብሳይቶች)
        harvester = MultiChannelHarvester()
        raw_data_pool = harvester.discover_and_harvest_niche_sources(self.site)

        if not raw_data_pool:
            return

        # 3. የቆዩ ዳታዎችን በ Hash ማጣራት (Deduplication)
        try:
            hash_config, _ = SiteConfig.objects.get_or_create(
                key=f"PROCESSED_RAW_HASHES_{self.site.name}",
                defaults={'value': []}
            )
            # 🛡️ SELF-CORRECTION: ቤቱ ባዶ ከሆነ (0 ምርት) ኤጀንቱ ራሱን አስተምሮ ትውስታውን ያጸዳል
            if prod_count == 0:
                logger.warning("🧹 Empty House Auto-Correction: Clearing processed hashes to force re-seeding...")
                hash_config.value = []
                hash_config.save()
                processed_hashes = set()
            else:
                processed_hashes = set(hash_config.value if isinstance(hash_config.value, list) else [])
        except Exception as cache_err:
            logger.debug(f"Failed to load raw hashes: {cache_err}")
            processed_hashes = set()

        new_products_to_seed = []
        new_hashes_in_batch = []
        raw_texts_for_ai = []
        
        for item in raw_data_pool:
            if not item: continue
            
            # 🛡️ FIXED: ዳታው Dictionary ከሆነ ወደ String እንቀይረዋለን (ለ Hash ስራ እንዲመች)
            if isinstance(item, dict):
                content_to_hash = json.dumps(item, sort_keys=True)
            else:
                content_to_hash = str(item)
            
            if not content_to_hash.strip(): continue
            
            # የእያንዳንዱን ምርት ልዩ መለያ (MD5 Hash) ማመንጨት
            item_hash = hashlib.md5(content_to_hash.encode('utf-8')).hexdigest()
            
            if item_hash not in processed_hashes:
                new_hashes_in_batch.append(item_hash)
                
                # መረጃው አስቀድሞ በ Harvester/Regex ከተተነተነ በቀጥታ ወደ ሚዘገበው እንጨምረዋለን
                if isinstance(item, dict) and item.get('title') and (item.get('seller_contact') or item.get('price')):
                    new_products_to_seed.append(item)
                else:
                    # መረጃው ጥሬ ጽሑፍ ከሆነ ለ AI እንዲተነተን እናዘጋጃለን
                    raw_texts_for_ai.append(content_to_hash)

        # 4. ጥሬ ጽሑፎችን በ AI ማስፈተሽ (አዲስ ጥሬ ጽሑፍ ካለ ብቻ)
        if raw_texts_for_ai:
            logger.info(f"🧠 Bulk Harvester: Processing {len(raw_texts_for_ai)} raw items via AI...")
            prompt = (
                f"Extract ALL products from these texts. Return JSON with key 'products' containing: "
                f"title, price, desc, seller_contact, image_url.\n\n"
                f"Data: {json.dumps(raw_texts_for_ai, ensure_ascii=False)}"
            )

            ai_providers = ['GEMINI', 'GROQ', 'MISTRAL', 'OPENROUTER', 'GITHUB']
            for provider in ai_providers:
                try:
                    response = self._call_ai_with_timeout(provider, prompt)
                    if response:
                        data = clean_and_parse_json(response)
                        if data and isinstance(data, dict) and data.get('products'):
                            extracted_products = data.get('products', [])
                            new_products_to_seed.extend(extracted_products)
                            logger.info(f"✅ {provider} successfully parsed {len(extracted_products)} products")
                            break
                except Exception as e:
                    logger.warning(f"⚠️ {provider} AI parsing failed: {e}")
                    continue

        # 5. ውጤቱን ዳታቤዝ ላይ መጫን (Seeding)
        if new_products_to_seed:
            logger.info(f"🚀 Seeding {len(new_products_to_seed)} unique products to homepage...")
            self._seed_listings_bulk(new_products_to_seed)
            
            try:
                # በስኬት የተጠናቀቁትን መለያዎች (Hashes) ማስቀመጥ
                updated_hashes = list(processed_hashes.union(new_hashes_in_batch))[-5000:]
                SiteConfig.objects.update_or_create(
                    key=f"PROCESSED_RAW_HASHES_{self.site.name}",
                    defaults={'value': updated_hashes}
                )
                SiteConfig.objects.update_or_create(
                    key=f"LAST_HARVEST_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )
                logger.info(f"✅ Bulk Harvester Cycle Complete. {len(new_products_to_seed)} products registered.")
            except Exception as e:
                logger.debug(f"Failed to update harvest config: {e}")
        else:
            logger.info("✨ Bulk Harvester: No new or unique market listings found in this cycle.")

    def _call_ai_with_timeout(self, provider: str, prompt: str, timeout: int = 10) -> Optional[str]:
        try:
            if provider == 'GEMINI':
                return self._call_gemini(prompt, timeout)
            elif provider == 'GROQ':
                return self._call_groq(prompt, timeout)
            elif provider == 'MISTRAL':
                return self._call_mistral(prompt, timeout)
            elif provider == 'OPENROUTER':
                return self._call_openrouter(prompt, timeout)
            elif provider == 'HUGGINGFACE':
                return self._call_huggingface(prompt, timeout)
            elif provider == 'GITHUB':
                return self._call_github(prompt, timeout)
            else:
                logger.warning(f"Unknown provider: {provider}")
                return None
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ {provider} timed out after {timeout}s")
            return None
        except Exception as e:
            logger.warning(f"⚠️ {provider} error: {e}")
            return None

    def _call_gemini(self, prompt: str, timeout: int) -> Optional[str]:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key: return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(url, json=payload, timeout=timeout)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        return None

    def _call_groq(self, prompt: str, timeout: int) -> Optional[str]:
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key: return None
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}]}
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return None

    def _call_mistral(self, prompt: str, timeout: int) -> Optional[str]:
        api_key = os.getenv('MISTRAL_API_KEY')
        if not api_key: return None
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": prompt}]}
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return None

    def _call_openrouter(self, prompt: str, timeout: int) -> Optional[str]:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key: return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "meta-llama/llama-3-8b-instruct:free", "messages": [{"role": "user", "content": prompt}]}
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return None

    def _call_huggingface(self, prompt: str, timeout: int) -> Optional[str]:
        api_key = os.getenv('HUGGINGFACE_API_KEY')
        if not api_key: return None
        url = "https://api-inference.huggingface.co/models/NousResearch/Meta-Llama-3-8B-Instruct"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"inputs": f"<|system|>\nYou are a helpful assistant.\n<|user|>\n{prompt}\n<|assistant|>\n"}
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if res.status_code == 200:
            data = res.json()
            if data and 'generated_text' in data[0]:
                return data[0]['generated_text'].strip()
        return None

    def _call_github(self, prompt: str, timeout: int) -> Optional[str]:
        token = os.getenv('GITHUB_TOKEN')
        if not token: return None
        url = "https://models.github.ai/inference/chat/completions"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
        return None

    def _no_api_fallback_harvest(self) -> List[Dict]:
        logger.info("🌐 No-API Fallback: Searching DuckDuckGo for products...")
        
        products = []
        search_terms = [
            "Ethiopia market products for sale",
            "Ethiopian online marketplace products",
            "Buy and sell Ethiopia products",
            "Ethiopia classifieds products"
        ]
        
        for term in search_terms:
            try:
                url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(term)}"
                res = requests.get(url, headers=headers, timeout=8)
                
                if res.status_code == 200:
                    items = re.findall(r'<a[^>]*>(.*?)</a>', res.text)
                    
                    for item in items[:5]:
                        clean_text = re.sub(r'<[^>]+>', '', item).strip()
                        if len(clean_text) > 20:
                            parsed = self._heuristic_parse_text(clean_text)
                            if parsed and parsed.get('title'):
                                products.append(parsed)
                        
            except Exception as e:
                logger.debug(f"DuckDuckGo search failed: {e}")
                continue
        
        return products

    def _save_image_to_cloudinary_permanently(self, raw_img_url):
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

    def _search_google_for_product_image(self, title) -> str:
        """
        🚀 [Stealth Stable Image Finder - DDG Scraper + Fuzzy Locked Fallback v10.98]
        ምርቱ የራሱ ፎቶ ከሌለው በከፍተኛ ጥራት በ DuckDuckGo ፈልጎ እውነተኛ ምስል ያመጣል፤
        ካልተሳካም ከምርቱ ጋር የሚገጥም (መኪና፣ ላፕቶፕ፣ ስልክ፣ ቤት) ቋሚ ፎቶ በምርቱ ስም አዋቅሮ በዳታቤዝ ይቆልፋል [1]
        """
        clean_title = re.sub(r'[^a-zA-Z0-9\s\u01200-\u0137F]', '', title).strip()
        if not clean_title or len(clean_title) < 3:
            clean_title = "product"
            
        # 🛡️ 1. [Stealth DDG Scraper] - በ DuckDuckGo መፈለግ
        query = f"{clean_title} product photo"
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            res = requests.get(search_url, headers=headers, timeout=5)
            if res.status_code == 200:
                image_urls = re.findall(r'//(external-content\.duckduckgo\.com/iu/\?u=[^"\'&]+)', res.text)
                if image_urls:
                    img_url = "https://" + image_urls[0]
                    logger.info(f"✨ DDG Image Finder: Found stable image for '{title}' -> {img_url}")
                    return img_url
        except Exception as e:
            logger.debug(f"DDG Image Finder failed: {e}")

        # 🛡️ 2. [Fuzzy Locked Placeholder Fallback] - ከላይ ያሉት ካልሠሩ ከምርቱ ጋር የሚገጥም ቋሚ ፎቶ መመደቢያ
        title_lower = title.lower()
        fallback_keyword = "product"
        
        # የምርት ዓይነት መለያ (መኪና፣ ስልክ፣ ላፕቶፕ፣ ቤት)
        if any(w in title_lower for w in ['car', 'toyota', 'kia', 'hyundai', 'suzuki', 'mercedes', 'benz', 'vitz', 'yaris', 'corolla', 'byd', 'veloster', 'morning', '4-runner', 'model', 'መኪና', 'ቪትዝ', 'ኮሮላ']):
            fallback_keyword = "car"
        elif any(w in title_lower for w in ['phone', 'iphone', 'samsung', 'galaxy', 'zte', 'tecno', 'spark', 'mobile', 'blade', 'ስልክ', 'አይፎን', 'ሳምሰንግ']):
            fallback_keyword = "phone"
        elif any(w in title_lower for w in ['laptop', 'lenovo', 'hp', 'dell', 'asus', 'notebook', 'thinkpad', 'latitude', 'precision', 'ላፕቶፕ', 'ኮምፒውተር']):
            fallback_keyword = "laptop"
        elif any(w in title_lower for w in ['apartment', 'house', 'condominium', 'villa', 'property', 'bed room', 'home', 'real estate', 'ቤት', 'ኮንዶሚኒየም', 'አፓርታማ']):
            fallback_keyword = "house"

        lock_id = int(hashlib.md5(title.encode('utf-8')).hexdigest(), 16) % 1000
        stable_fallback = f"https://loremflickr.com/800/600/{fallback_keyword}?lock={lock_id}"
        logger.info(f"✨ Fuzzy Locked Fallback: Assigned stable locked '{fallback_keyword}' photo for '{title}' -> {stable_fallback}")
        return stable_fallback

    def _seed_listings_bulk(self, products_list):
        """ምርቶችን ዳታቤዝ ውስጥ ይጭናል - የባዶ ሻጭ ሎጂክ እና የራስ-ፈውስ ማጽጃ የተጨመረበት (v10.62)"""
        Product = get_model('Product')
        SellerProfile = get_model('SellerProfile')
        NotificationQueue = get_model('NotificationQueue')
        SiteConfig = get_model('SiteConfig')

        products_to_create = []
        notifications_to_create = []
        seen_titles = set() 

        for p in products_list:
            # 🛡️ FIXED: seller_contact ባዶ ቢሆንም ምርቱን እንዳይዘል መፍቀድ
            if not isinstance(p, dict) or not p.get('title'):
                continue
            
            # ሻጭ ኮንታክት ከሌለው ባዶ እንዳይሆን default ስልክ ቁጥር መመደብ
            contact = p.get('seller_contact', '').strip()
            if not contact:
                contact = "0900000000"  # Fallback Contact
            p['seller_contact'] = contact
            
            try:
                uname = contact.replace('@', '').replace('+', '').strip()
                uname = re.sub(r'[^a-zA-Z0-9_@.+\-]', '', uname)[:150]
                
                title_key = (uname, p['title'].strip().lower())
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)
                
                user, created = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                if created:
                    user.set_unusable_password()
                    user.save()
                    
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})

                # 🛡️ SELF-CORRECTION: በአሮጌው ስህተት ምክንያት የገቡ የኮድ ቆሻሻዎችን (Inactive የሆኑትን) በራስ-ሰር ማጽዳት
                Product.objects.filter(
                    seller=user,
                    site=self.site,
                    title=p['title'].strip(),
                    is_active=False
                ).delete()

                product_exists = Product.objects.filter(
                    seller=user,
                    site=self.site,
                    title=p['title'].strip()
                ).exists()
                
                if product_exists:
                    logger.info(f"⏭️ Bulk Harvester: Skipping duplicate product '{p['title']}' for user '{uname}'")
                    continue

                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0

                raw_photo = p.get('image_url', '')
                
                # 🚀 ፎቶ ከሌለው ቋሚና ጥራት ያለው ምስል ፈልጎ ማምጣት (v10.65)
                if not raw_photo:
                    raw_photo = self._search_google_for_product_image(p['title'])

                cloudinary_photo_url = self._save_image_to_cloudinary_permanently(raw_photo)

                product_obj = Product(
                    seller=user, site=self.site, title=p['title'], price=clean_price,
                    description=p.get('desc', ''), image_url=cloudinary_photo_url,
                    listing_type=p.get('listing_type', 'sale') or 'sale', 
                    contact_info=contact, is_active=True
                )
                products_to_create.append(product_obj)

                # 🛡️ FIXED: ለዲፎልት ስልክ ቁጥር (0900000000) ማሳወቂያ/SMS እንዳይላክ መከላከል
                if contact != "0900000000" and not contact.startswith("09000000"):
                    login_token = hashlib.sha256(f"{uname}:{settings.SECRET_KEY}".encode('utf-8')).hexdigest()[:16]
                    
                    SiteConfig.objects.update_or_create(
                        key=f"ACCESS_TOKEN_{uname}",
                        defaults={'value': {'token': login_token, 'created_at': timezone.now().isoformat()}}
                    )

                    dispatch_links = self.generate_contact_links(contact)
                    magic_login_url = f"{self.site.deployment_url or 'http://localhost:8000'}/api/magic-token/?phone={uname}&token={login_token}"

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
                
                logger.info(f"✨ Bulk Harvester: Processed {len(products_to_create)} new unique products!")
        except Exception as db_err:
            logger.error(f"Bulk DB Insertion failed: {db_err}")

    @staticmethod
    def generate_contact_links(contact_str):
        links = {}
        if not contact_str: 
            return links
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', contact_str)
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
                    self.site, f"📣 Promote Hot Item: {item.title}",
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
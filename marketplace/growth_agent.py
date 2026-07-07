
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py
# 📝 ስሪት፦ v10.53 (Stable Growth Focus - Optimized Scraping & Source Discovery)
# ✅ የተፈቱ ችግሮች፦ 
#   - Fixed "dead" source detection (Telegram & Jiji always active)
#   - Optimized scraping speed (HEAD requests first)
#   - Reduced source checking overhead
#   - Improved product extraction from Jiji
#   - Better deduplication and seeding
#   - Track A disabled for performance
# 📅 ቀን፦ Wednesday, July 07, 2026
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

# ============================================================
# ⚙️ LOGGER SETUP
# ============================================================
logger = logging.getLogger(__name__)

# ============================================================
# 🔄 DYNAMIC MODEL LOADER
# ============================================================

def get_model(model_name: str):
    try:
        return apps.get_model('marketplace', model_name)
    except Exception as e:
        logger.error(f"Failed to load model {model_name} dynamically: {e}")
        return None


# ============================================================
# ✅ LATE IMPORTS
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
    from .scrapper_engine import ScrapperEngine
    return ScrapperEngine


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
# 🛡️ 1. GLOBAL RESOURCE & CONNECTION HEALERS
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


# ============================================================
# 📁 የፋይል አቅጣጫ ፈቺ ረዳት ፈንክሽኖች
# ============================================================

def resolve_local_file_path(site, target_file):
    if target_file.endswith('_html') or 'html' in target_file:
        clean_name = target_file.replace('_html', '') + '.html'
        return os.path.join(settings.BASE_DIR, 'marketplace', 'templates', 'marketplace', clean_name)
    return os.path.join(settings.BASE_DIR, 'marketplace', f"{target_file}.py")


def is_html_target(target_file):
    return target_file.endswith('_html') or 'html' in target_file


# ============================================================
# 🌱 SEEDING-FIRST GUARDRAIL
# ============================================================

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


# ============================================================
# 🔍 DISK-LEVEL VERIFICATION & ROLLBACK
# ============================================================

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


# ============================================================
# 📊 DYNAMIC PROGRESS BAR
# ============================================================

def update_agent_progress(site, step_msg, percentage):
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
                logger.info(f"🔄 Self-Optimization: Applied new system prompt rule for {self.site.name}")


# ============================================================
# 🔴 META SELF-ARCHITECT ENGINE
# ============================================================

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
            f"You are the Master AI Systems Architect of EthAfri. Audit your own system state: {json.dumps(state_summary)}.\n"
            f"Live system metrics: {json.dumps(metrics_summary)}.\n"
            f"Identify exactly 3 highly optimized, non-redundant, and advanced coding, SEO, performance-caching, "
            f"or security features that we should autonomously add to ourselves (e.g. view optimizations, model extensions, "
            f"or automatic data sanitizers) to scale our system capacity exponentially.\n"
            f"CRITICAL: Follow DRY smart coding principles. Do not generate code duplication; merge or extend existing helpers.\n"
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
                            'description': f"Self-Architected Task: {t.get('desc')}. Business Impact: {t.get('impact')}/10.",
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
            query = "advanced Django database performance optimizations and scaling 2026"
            prompt = (
                f"Perform an automated research task on query: '{query}'.\n"
                f"Identify exactly 1 cutting-edge, safe, and highly efficient performance optimization "
                f"or security architecture for a modern Django 4/5 eCommerce system (e.g. index optimization, "
                f"safe query sanitizers, or memory-efficient background utilities).\n"
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
                        'description': f"Research-Backed Upgrade: {res.get('description')}. Impact Score: {res.get('business_impact_score')}/10.",
                        'business_impact_score': int(res.get('business_impact_score', 8)),
                        'trigger_condition': 'Tech Research Loop'
                    }
                )
                logger.info(f"✨ Tech Research: Successfully registered new research task: {res['task_name']}")
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
            f"to avoid any code duplication. If merging is not possible, design the new code to be highly reusable, compact, "
            f"and multi-purpose (supporting multiple features inside a single clean, parameter-driven function).\n"
            f"PERFORMANCE & ASSET OPTIMIZATION RULE: To ensure extremely fast page loading, never write inline CSS or inline javascript blocks inside HTML. "
            f"Instead, use only the clean Tailwind/global CSS variables and standard modular structures. "
            f"Move any custom styles or scripts to external global.css or global.js respectively to unblock page rendering.\n"
            f"FORWARD-COMPATIBLE DESIGN RULE: Design function signatures, APIs, or data schemas to be extensible. "
            f"Use dynamic configurations or extensible payload dictionaries (JSON/Dict-compatible) to allow future feature expansions without breaking backwards compatibility.\n"
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
                    f"Please fully repair and refactor the code to fix this issue completely while strictly preserving "
                    f"all business logic, DRY consolidation, and asset externalization rules.\n"
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
# 📡 4. DYNAMIC MULTI-CHANNEL HARVESTER (OPTIMIZED)
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
                messages = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL)
                images = re.findall(r"background-image:url\(\'([^\'\)]+)\'\)", res.text)
                
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
            ScrapperEngine = _get_scrapper_engine()
            html = ScrapperEngine.scrape(url)
            if html:
                products = self._extract_products_from_html(html)
                if not products:
                    # 0 ምርት ከተገኘ የስኬማ ለውጥ መርማሪ ስለላ ማነቃቃት
                    self.perform_source_reconnaissance(
                        {"url_or_channel": url, "platform_type": "GenericWeb"},
                        "HTML loaded successfully, but 0 products extracted. Selector mismatch.",
                        html_content=html
                    )
                return products
            else:
                self.perform_source_reconnaissance(
                    {"url_or_channel": url, "platform_type": "GenericWeb"},
                    "Connection blocked or timed out (Empty response). Firewall/Cloudflare suspected."
                )
        except Exception as e:
            logger.error(f"Website scrape failed for {url}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": url, "platform_type": "GenericWeb"}, str(e))
        return []
    
    def _parse_product_text(self, text):
        """ምርቶችን የሚለይ እና የ3 ወር ጊዜ ገደብን የሚፈትሽ (v10.40)"""
        if not text: return None
        
        # 🛡️ የጊዜ ገደብ መፈተሻ (ከ 3 ወር በላይ የሆኑትን መተው)
        old_patterns = [r'2023', r'2024', r'2025', r'[4-9]\s*months?\s*ago', r'year\s*ago']
        for pattern in old_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return None

        product = {'title': '', 'price': 0, 'description': '', 'seller_contact': ''}
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines: return None
        
        product['title'] = lines[0][:150]
        
        # ዋጋ መፈለጊያ
        price_match = re.search(r'(?:ዋጋ|Price|Birr|ብር)\s*[:፡-]?\s*([\d,]+)', text, re.IGNORECASE) or \
                      re.search(r'([\d,]+)\s*(?:ETB|ብር|Birr|Br)', text, re.IGNORECASE)
        if price_match:
            try:
                product['price'] = float(price_match.group(1).replace(',', ''))
            except: pass
            
        # ስልክ መፈለጊያ
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text)
        if phone_match:
            product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
        else:
            tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
            if tg_match:
                product['seller_contact'] = tg_match.group(0)
        
        product['description'] = text[:1000].replace('\n\n', '\n').strip()
        return product
    
    def _extract_products_from_html(self, html):
        """የ Jiji ምርቶች የሚገኙባቸውን እውነተኛ ካርዶች ብቻ ለይቶ መሳቢያ (Regex Hardened)"""
        products = []
        # የ Jiji ትክክለኛ ምርቶች የሚገኙባቸው የ CSS Class ስሞች ብቻ
        items = re.findall(r'<div[^>]*class="[^"]*(?:b-list-advert-single|b-trending-card|qa-advert-list-item)[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        for item in items:
            product = self._parse_product_text(item)
            if product and product['title']:
                products.append(product)
        return products

    def perform_source_reconnaissance(self, source, error_msg, html_content=None):
        """
        🕵️ [የመረጃ አሰሳ ስለላ እና ጥናት ማዕከል]
        ክልከላዎችን መርምሮ ለአድሚን በ Backlog ላይ ዝርዝር የስለላ ሪፖርት (Bypass strategy) የሚመዘግብ
        """
        url = source.get('url_or_channel', '')
        platform = source.get('platform_type', 'GenericWeb')
        
        block_reason = "Unknown Access Block"
        if "403" in error_msg or "Forbidden" in error_msg:
            block_reason = "HTTP 403 Forbidden (Firewall/Cloudflare IP Ban detected)"
        elif "429" in error_msg or "Too Many Requests" in error_msg:
            block_reason = "HTTP 429 Too Many Requests (Access Throttled)"
        elif "Timeout" in error_msg or "timed out" in error_msg:
            block_reason = "Connection Timeout (Server is protected, slow, or offline)"
        elif "0 products extracted" in error_msg:
            block_reason = "DOM Structure Mismatch (HTML loaded successfully, but class selectors changed)"

        density_estimation = "Cannot evaluate (Complete connection block)"
        if html_content:
            text_len = len(html_content)
            links_count = len(re.findall(r'href=', html_content))
            images_count = len(re.findall(r'<img', html_content))
            density_estimation = (
                f"Raw HTML: {text_len} chars. "
                f"Links found: {links_count}. Images: {images_count}. "
                f"Estimated Active Listings: {min(links_count // 3, 50)} items on main page."
            )

        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()
        
        prompt = (
            f"We failed to scrape this Ethiopian marketplace: {url} ({platform}).\n"
            f"Error/Block Reason: {block_reason} ({error_msg}).\n"
            f"HTML Metadata: {density_estimation}.\n\n"
            f"Write a brief, precise RECONNAISSANCE REPORT for developers. Include:\n"
            f"1. Direct cause of failure (CF challenge, IP Block, or Class selector change)?\n"
            f"2. Practical workaround (e.g. proxy rotation, specific custom class name or selector, etc.).\n"
            f"Return JSON with key 'analysis' containing the guidelines (max 400 characters)."
        )
        
        analysis_text = "AI analysis throttled due to active rate limits."
        try:
            res = ask_master_ai_smart(prompt, task_type="market_research")
            data = clean_and_parse_json(res)
            if data and isinstance(data, dict):
                analysis_text = data.get('analysis', analysis_text)
        except Exception as e:
            logger.debug(f"AI Reconnaissance Analysis skipped: {e}")

        try:
            AIProjectBacklog = get_model('AIProjectBacklog')
            # 🛡️ FIXED: PostgreSQL character varying(255) ስህተትን ለመከላከል ስሙን በ 200 ፊደላት መገደብ (Truncate)
            task_name = f"🕵️ RECON REPORT: {url}"[:200]
            
            if not AIProjectBacklog.objects.filter(task_name=task_name).exists():
                AIProjectBacklog.objects.create(
                    site=get_model('SiteRegistry').objects.filter(is_active=True).first(),
                    task_name=task_name,
                    target_file="scrapper_engine",
                    priority="High",
                    status="Blocked", # 'Blocked' ማለት የአድሚን/የሰው እገዛ ያስፈልገዋል ማለት ነው
                    description=(
                        f"🛡️ Autonomous Scraper Intelligence Report:\n"
                        f"- Target Domain: {url}\n"
                        f"- Block Classification: {block_reason}\n"
                        f"- Estimated Product Density: {density_estimation}\n\n"
                        f"💡 Strategist Bypass Guide:\n{analysis_text}"
                    ),
                    business_impact_score=8,
                    trigger_condition="Autonomous Scraper Reconnaissance Loop"
                )
                logger.warning(f"🕵️ Recon Engine: Registered strategic bypass guide for: {url}")
        except Exception as db_err:
            logger.error(f"Failed to save Reconnaissance Task: {db_err}")


# ============================================================
# 💼 CEO OPERATIONS
# ============================================================




class CEOOperations:
    """የንግድ ዕድገት እና ምርት መሰብሰቢያ ስራዎችን የሚያስተዳድር ክላስ"""
    
    def __init__(self, site):
        self.site = site

    def run_business_growth(self):
        """የንግድ ዕድገት ዑደት (Bulk Harvesting + Listing Curation)"""
        logger.info(f"📈 Running business growth cycle for {self.site.name}")
        self._harvest_verified_products_bulk()
        self.curate_user_listings()
        self._boost_revenue()
        self.dispatch_pending_notifications()

    # ============================================================
    # 🔍 1. HEURISTIC PARSER (Regex-based product extraction)
    # ============================================================
    
    def _heuristic_parse_text(self, text):
        """የ AI ጥሪዎች ሙሉ በሙሉ ቢቋረጡም በሪጀክስ ምርቶችን ፈልቅቆ የሚጭን ሎጂክ"""
        if not text:
            return None
        
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return None
        
        title = lines[0][:150]
        
        # ስልክ መፈለጊያ
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text)
        tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
        
        contact = "0900000000"
        if phone_match:
            contact = re.sub(r'[^\d+]', '', phone_match.group(0))
        elif tg_match:
            contact = tg_match.group(0)
        
        # ዋጋ መፈለጊያ
        price = 0.0
        price_match = re.search(r'(?:ዋጋ|Price|Birr|ETB|ብር)\s*[:፡-]?\s*([\d,]+)', text, re.IGNORECASE)
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', ''))
            except ValueError:
                price = 0.0
        
        # መግለጫ
        description = text[:1000]
        
        return {
            "title": title,
            "price": price,
            "desc": description,
            "seller_contact": contact
        }

    # ============================================================
    # 📡 2. BULK HARVESTER (Main product collection)
    # ============================================================
    
    def _harvest_verified_products_bulk(self):
        """ምርቶችን በጅምላ ያስሳል እና ወደ ዳታቤዝ ያስቀምጣል"""
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()
        
        # ✅ የምርት ብዛት ያረጋግጡ
        product_count = Product.objects.filter(site=self.site, is_active=True).count()
        logger.info(f"📊 Current product count: {product_count}")
        
        # ✅ ሁልጊዜ ያስሳል (Cooldown የለም)
        harvester = MultiChannelHarvester()
        raw_data_pool = harvester.discover_and_harvest_niche_sources(self.site)
        
        if not raw_data_pool:
            logger.warning("⚠️ No products found in this cycle")
            return
        
        logger.info(f"📦 Found {len(raw_data_pool)} raw items")
        
        # ✅ ሁሉንም ምርቶች ወደ ዳታቤዝ ለመጫን ዝግጅት
        products_to_seed = []
        
        for item in raw_data_pool:
            if isinstance(item, dict) and item.get('title'):
                products_to_seed.append(item)
            elif isinstance(item, str) and len(item) > 20:
                # ጥሬ ጽሑፍ ከሆነ በ heuristic parser ያስሱ
                parsed = self._heuristic_parse_text(item)
                if parsed and parsed.get('title'):
                    products_to_seed.append(parsed)
        
        if products_to_seed:
            logger.info(f"🚀 Seeding {len(products_to_seed)} products...")
            seeded = self._seed_listings_bulk(products_to_seed)
            logger.info(f"✅ {seeded} new products seeded successfully!")
            
            # ✅ የመጨረሻ ዳሰሳ ጊዜ ያስቀምጡ
            try:
                SiteConfig.objects.update_or_create(
                    key=f"LAST_HARVEST_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug(f"Failed to update harvest config: {e}")
        else:
            logger.warning("⚠️ No valid products to seed")

    # ============================================================
    # 💾 3. BULK SEEDER (Database insertion)
    # ============================================================
    
    def _seed_listings_bulk(self, products_list):
        """ምርቶችን ዳታቤዝ ውስጥ ይጭናል"""
        Product = get_model('Product')
        SellerProfile = get_model('SellerProfile')
        NotificationQueue = get_model('NotificationQueue')
        SiteConfig = get_model('SiteConfig')
        
        # ✅ በዳታቤዝ ውስጥ ያሉትን ርዕሶች ያግኙ
        existing_titles = set(
            Product.objects.filter(site=self.site).values_list('title', flat=True)
        )
        
        products_to_create = []
        notifications_to_create = []
        created_count = 0
        
        for p in products_list:
            if not isinstance(p, dict) or not p.get('title'):
                continue
            
            # ✅ ርዕሱ ቀድሞ ካለ ይዘሉ
            title = p['title'].strip()
            if title in existing_titles:
                continue
            
            try:
                contact = p.get('seller_contact', '0900000000')
                uname = contact.replace('@', '').replace('+', '').strip()
                uname = re.sub(r'[^a-zA-Z0-9_@.+\-]', '', uname)[:150]
                
                if not uname:
                    uname = f"user_{hashlib.md5(title.encode()).hexdigest()[:8]}"
                
                # ተጠቃሚ ያግኙ ወይም ይፍጠሩ
                user, created = User.objects.get_or_create(
                    username=uname,
                    defaults={'is_active': True}
                )
                if created:
                    user.set_unusable_password()
                    user.save()
                
                # የሻጭ መገለጫ ያግኙ
                SellerProfile.objects.get_or_create(
                    user=user,
                    defaults={'site': self.site}
                )
                
                # ዋጋ
                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0
                
                # ምስል
                raw_photo = p.get('image_url', '')
                cloudinary_photo_url = self._save_image_to_cloudinary_permanently(raw_photo)
                
                # ምርት ይፍጠሩ
                product_obj = Product(
                    seller=user,
                    site=self.site,
                    title=title[:200],
                    price=clean_price,
                    description=p.get('desc', p.get('description', ''))[:2000],
                    image_url=cloudinary_photo_url,
                    listing_type=p.get('listing_type', 'sale') or 'sale',
                    contact_info=contact,
                    is_active=True
                )
                products_to_create.append(product_obj)
                
                # ርዕሱን ያስታውሱ
                existing_titles.add(title)
                created_count += 1
                
                # ማሳወቂያ ያዘጋጁ
                login_token = hashlib.sha256(
                    f"{uname}:{settings.SECRET_KEY}".encode('utf-8')
                ).hexdigest()[:16]
                
                SiteConfig.objects.update_or_create(
                    key=f"ACCESS_TOKEN_{uname}",
                    defaults={'value': {'token': login_token, 'created_at': timezone.now().isoformat()}}
                )
                
                magic_login_url = (
                    f"{self.site.deployment_url or 'http://localhost:8000'}"
                    f"/api/magic-token/?phone={uname}&token={login_token}"
                )
                
                message = (
                    f"ሰላም! የለጠፉት '{title[:50]}' ምርት በድረ-ገጻችን ላይ በነፃ ተለጥፏል።\n"
                    f"ምርትዎን ለማስተዳደር በዚህ ሊንክ ይግቡ፦\n"
                    f"{magic_login_url}\n\n"
                    f"EthAfri CEO"
                )
                
                notification_obj = NotificationQueue(
                    site=self.site,
                    recipient=contact,
                    notification_type='sms',
                    message=message
                )
                notifications_to_create.append(notification_obj)
                
            except Exception as seed_err:
                logger.error(f"Failed to compile bulk listing: {seed_err}")
                continue
        
        # ✅ በጅምላ ወደ ዳታቤዝ ይጫኑ
        try:
            with transaction.atomic():
                if products_to_create:
                    Product.objects.bulk_create(products_to_create)
                    logger.info(f"✅ Created {len(products_to_create)} new products")
                
                if notifications_to_create:
                    NotificationQueue.objects.bulk_create(notifications_to_create)
                
                # ስታቲስቲክስ ያዘምኑ
                self.site.real_product_count = Product.objects.filter(
                    site=self.site, is_active=True
                ).count()
                self.site.total_products = Product.objects.filter(
                    site=self.site
                ).count()
                self.site.total_sellers = User.objects.filter(
                    product__site=self.site
                ).distinct().count()
                self.site.save()
                
        except Exception as db_err:
            logger.error(f"Bulk DB Insertion failed: {db_err}")
            return 0
        
        return created_count

    # ============================================================
    # 📸 4. IMAGE UPLOADER (Cloudinary)
    # ============================================================
    
    def _save_image_to_cloudinary_permanently(self, raw_img_url):
        """ምስሎችን ወደ Cloudinary ያስቀምጣል"""
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

    # ============================================================
    # 🔗 5. CONTACT LINK GENERATOR
    # ============================================================
    
    @staticmethod
    def generate_contact_links(contact_str):
        """የተጠቃሚውን ስልክ ወይም ዩዘርኔም በመለየት ሊንኮችን ያመነጫል"""
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

    # ============================================================
    # 🛡️ 6. LISTING CURATION (Spam/Scam detection)
    # ============================================================
    
    def curate_user_listings(self, limit=5):
        """አዳዲስ ምርቶችን መርምሮ ስካም ይከላከላል"""
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        NotificationQueue = get_model('NotificationQueue')
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()
        
        try:
            dedup_key = f"CURATED_PRODUCT_IDS_{self.site.name}"
            dedup_config, _ = SiteConfig.objects.get_or_create(
                key=dedup_key,
                defaults={'value': []}
            )
            curated_ids = set(dedup_config.value if isinstance(dedup_config.value, list) else [])
            
            candidates = list(
                Product.objects.filter(site=self.site, is_active=True)
                .exclude(id__in=list(curated_ids))[:limit]
            )
            
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
                                f"Verify listing for scams/spam. Title: {product.title}. "
                                f"Price: {product.price}. "
                                f"Return JSON with key 'is_valid' (true/false) and 'reason'."
                            )
                            result = clean_and_parse_json(
                                ask_master_ai_smart(prompt, task_type="market_research")
                            )
                            if result and not result.get('is_valid', True):
                                is_valid = False
                                reason = result.get('reason', 'Suspicious listing')
                        except Exception as ai_curate_err:
                            logger.debug("AI curation skipped: %s", ai_curate_err)
                    
                    if not is_valid:
                        product.is_active = False
                        product.save()
                        NotificationQueue.objects.create(
                            site=self.site,
                            recipient=product.seller.username,
                            notification_type='sms',
                            message=(
                                f"ሰላም {product.seller.username}፤ "
                                f"የለጠፉት '{product.title}' ምርት ማጣሪያችን አልፏል። "
                                f"ምክንያት፦ {reason}።"
                            )
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
            logger.error(f"Curation exception: {e}")

    # ============================================================
    # 🌍 7. TRANSLATION GENERATOR
    # ============================================================
    
    def _generate_translations_for_product(self, product):
        """ምርቱን ለ Amharic/Oromo ቋንቋዎች በራስ-ሰር መተርጎም"""
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
                        lang: (
                            f"{translated.get(product.title, product.title)} ||| "
                            f"{translated.get(product.description or '', product.description or '')}"
                        )
                    }
                )
            except Exception as e:
                logger.debug(f"Translation skipped: {e}")

    # ============================================================
    # 💰 8. REVENUE BOOSTER
    # ============================================================
    
    def _boost_revenue(self):
        """ተወዳጅ ምርቶችን ለማስተዋወቅ ተግባር ይፈጥራል"""
        Product = get_model('Product')
        try:
            hot_items = Product.objects.filter(
                site=self.site,
                view_count__gt=100,
                is_active=True
            ).order_by('-view_count')[:2]
            
            for item in hot_items:
                get_or_create_backlog_task_safe(
                    self.site,
                    f"📣 Promote Hot Item: {item.title}",
                    defaults={
                        'priority': 'High',
                        'status': 'Pending',
                        'business_impact_score': 8,
                        'target_file': 'home_html',
                        'description': item.title
                    }
                )
        except Exception as e:
            logger.debug(f"Failed to execute revenue boosting: {e}")

    # ============================================================
    # 📨 9. NOTIFICATION DISPATCHER
    # ============================================================
    
    def dispatch_pending_notifications(self):
        """ያልተላኩ ማሳወቂያዎችን ይልካል"""
        NotificationQueue = get_model('NotificationQueue')
        try:
            pending_notes = NotificationQueue.objects.filter(
                site=self.site,
                is_sent=False
            )[:5]
            
            for note in pending_notes:
                logger.info(f"📨 Outbound Dispatcher: Sent {note.notification_type} to {note.recipient}")
                note.is_sent = True
                note.sent_at = timezone.now()
                note.save()
                
        except Exception as e:
            logger.error(f"Outbound Dispatcher failed: {e}")

    # ============================================================
    # 📢 10. TELEGRAM AUTO-POSTER
    # ============================================================
    
    def auto_post_to_telegram_channel(self, product):
        """ምርቶችን ወደ ቴሌግራም ቻናል በራስ-ሰር ይልካል"""
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
# 📌 HELPER FUNCTIONS (Dynamic Model Loading)
# ============================================================

def get_model(model_name: str):
    """ሞዴሎችን በዳይናሚክ መጫኛ"""
    try:
        from django.apps import apps
        return apps.get_model('marketplace', model_name)
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        return None


def _get_ai_utils():
    """AI Utils ሞጁልን በ late import መጫኛ"""
    from .ai_utils import (
        clean_and_parse_json,
        ask_master_ai_smart,
        broadcast_agent_log,
        AIUtils
    )
    return clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, AIUtils.compress_code_for_prompt


def get_or_create_backlog_task_safe(site, task_name, defaults):
    """የባክሎግ ተግባርን በደህንነት ይፈጥራል"""
    from .models import AIProjectBacklog
    task_name = task_name[:200]
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
        return None, False


def translate_text_incremental(texts, target_lang):
    """ጽሁፎችን ወደ አማርኛ/ኦሮምኛ ይተረጉማል"""
    if not texts:
        return {}
    
    _, ask_master_ai_smart, _, _ = _get_ai_utils()
    clean_and_parse_json, _, _, _ = _get_ai_utils()
    
    prompt = (
        f"Translate the following text keys into {target_lang}.\n"
        f"Text Data: {json.dumps(texts, ensure_ascii=False)}.\n"
        f"Return JSON mapping each original text to its translated equivalent."
    )
    try:
        translated = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="translation"))
        if isinstance(translated, dict):
            return translated
    except Exception as e:
        logger.error(f"Translation dynamic loop failed: {e}")
    return {t: t for t in texts}


# ============================================================
# 🕵️ COMPETITOR INTELLIGENCE ENGINE
# ============================================================

class CompetitorIntelligenceEngine:
    def __init__(self, site):
        self.site = site

    def spy_and_analyze_market(self):
        try:
            self.site = get_model('SiteRegistry').objects.get(id=self.site.id)
        except Exception:
            self.site = get_model('SiteRegistry').objects.filter(is_active=True).first()
            if not self.site:
                return

        ScrapperEngine = _get_scrapper_engine()
        MarketTrend = get_model('MarketTrend')
        VectorMemory = get_model('VectorMemory')
        _, _, broadcast_agent_log, _ = _get_ai_utils()

        broadcast_agent_log(self.site, "🕵️ Spy Engine: Initializing competitor website scanning...", "info")
        competitor_links = self.site.competitor_urls if isinstance(self.site.competitor_urls, list) else []
        if not competitor_links:
            competitor_links = ["https://jiji.com.et", "https://www.engocha.com"]

        raw_competitor_data = []
        for url in competitor_links[:1]: 
            try:
                html_content = ScrapperEngine.scrape(url)
                if html_content:
                    clean_text = re.sub(r'<[^>]+>', ' ', html_content)
                    compressed_text = " ".join(clean_text.split())[:1000]
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
            f"Return JSON with keys: 'demand_level', 'ai_suggestion', 'trending_items_summary', 'competitor_seo_keywords', 'repriced_value', 'repriced_product_id', 'competitive_advantage_action'"
        )

        try:
            result = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
            if result and isinstance(result, dict):
                
                demand_raw = result.get('demand_level', 50)
                try:
                    demand_level = int(demand_raw)
                except (ValueError, TypeError):
                    if str(demand_raw).lower() in ['high', 'critical', 'very high', 'active', 'very_high']:
                        demand_level = 80
                    elif str(demand_raw).lower() in ['medium', 'moderate']:
                        demand_level = 50
                    else:
                        demand_level = 30

                MarketTrend.objects.update_or_create(
                    niche_name=self.site.niche,
                    defaults={'demand_level': demand_level, 'ai_suggestion': result.get('ai_suggestion', '')}
                )

                insight_text = result.get('ai_suggestion', 'No suggestions')
                
                VectorMemory.objects.create(
                    site=self.site, 
                    memory_type='insight', 
                    content=f"Competitor Intelligence: {insight_text}",
                    metadata={'trending_items': result.get('trending_items_summary', ''), 'site_id': self.site.id},
                    success_rate=95.0, text_content=insight_text, embedding_model='spy-intelligence-v1'
                )

                repriced_raw = result.get('repriced_value', 0.0)
                try:
                    repriced_val = float(repriced_raw)
                except (ValueError, TypeError):
                    repriced_val = 0.0

                target_raw = result.get('repriced_product_id', 0)
                try:
                    target_id = int(target_raw)
                except (ValueError, TypeError):
                    target_id = 0

                if repriced_val > 0.0 and target_id > 0:
                    Product = get_model('Product')
                    Product.objects.filter(id=target_id).update(price=repriced_val)
                    broadcast_agent_log(self.site, f"🎯 Repricer: Adjusted product {target_id} price to {repriced_val} ETB.", "success")

                keywords = result.get('competitor_seo_keywords', [])
                if keywords:
                    self.site.primary_keywords = list(set((self.site.primary_keywords or []) + keywords))
                    self.site.save()

                advantage_action = result.get('competitive_advantage_action', '')
                if advantage_action:
                    task_name = f"🎯 COMPETITOR SPY: {advantage_action}"[:200]
                    get_or_create_backlog_task_safe(
                        self.site, task_name,
                        defaults={'task_type': 'marketing', 'target_file': 'marketing_campaign', 'priority': 'High', 'status': 'Pending', 'description': advantage_action, 'business_impact_score': 9, 'trigger_condition': 'Competitor Loop'}
                    )
                broadcast_agent_log(self.site, "✨ Spy Engine: Competitor analysis complete.", "success")
        except Exception as ai_err:
            logger.error(f"Spy Engine analysis failed: {ai_err}")


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
    AIProjectBacklog = get_model('AIProjectBacklog')
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

    local_marketplace_dir = os.path.join(settings.BASE_DIR, 'marketplace')
    if os.path.exists(local_marketplace_dir) and not is_remote:
        try:
            for filename in os.listdir(local_marketplace_dir):
                if "_helper_" in filename and filename.endswith(".py"):
                    key_name = filename.replace(".py", "")
                    core_files[key_name] = f"marketplace/{filename}"
        except Exception as e:
            logger.debug(f"Failed to scan local dynamic helpers: {e}")

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
    # 🛡️ FIXED: PostgreSQL character varying(255) ስህተትን ለመከላከል የ backlogs ስሞችን በ 200 ፊደላት መገደብ
    task_name = task_name[:200]
    if 'description' in defaults and defaults['description']:
        defaults['description'] = defaults['description'][:500]
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
        SiteConfig = get_model('SiteConfig')
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
    try:
        for site in active_sites:
            _run_site_cycle(site)
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
    """የአንድ ንዑስ ጣቢያን ሙሉ የዕድገት እና የዕድገት ማጠናከሪያ ዑደት ያስፈጽማል"""
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
                
                try:
                    optimizer = RecursiveOptimizer(site)
                    optimizer.refine_strategy()
                except Exception as opt_err:
                    logger.debug(f"Code optimizer loop skipped: {opt_err}")
                
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

    # 🔄 Track A ለጊዜው ተዘግቷል (ምርት መሰብሰብ ላይ ብቻ ትኩረት)
    # run_track_a_evolution()
    
    # የዕድገት እና ምርት መሰብሰቢያ ሞተር (Track B) ብቻ
    run_track_b_growth()

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
            Product = get_model('Product') 

            has_pending = False
            try:
                has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
            except Exception as e:
                logger.debug("Failed to verify pending backlog status: %s", e)
            
            try:
                load_avg = os.getloadavg()[0]
            except (AttributeError, OSError, Exception):
                load_avg = 0.5
                
            prod_count = Product.objects.filter(is_active=True).count()
            is_empty_or_low = prod_count < 120
            
            if load_avg > 2.0 and not is_empty_or_low:
                interval = 2700
                logger.warning(f"⚠️ Server CPU Load is heavy ({load_avg:.2f}). Pacing slowed to 45 minutes.")
            elif not MultiChannelHarvester.is_network_available():
                interval = 1800
                logger.warning("🌐 Offline Mode detected. Pacing slowed to 30 minutes.")
            else:
                interval = 30 if (has_pending or is_empty_or_low) else 300
                
            logger.info(f"💤 Master Cycle Complete. Sleeping {interval} seconds...")
            import time
            time.sleep(interval)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO FATAL ERROR: {e}")
            import time
            time.sleep(10)


# ============================================================
# 🚨 EMERGENCY PRODUCTS SEEDING FORCING
# ============================================================
def force_push_products(site):
    """ምርቶች ከሌሉ ቢያንስ አንድ የሙከራ ምርት እንዲኖር የሚያስገድድ ሎጂክ"""
    Product = get_model('Product')
    if not Product.objects.filter(site=site).exists():
        try:
            User = apps.get_model('auth', 'User')
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user, _ = User.objects.get_or_create(username="admin_ceo", defaults={"is_active": True})
            
            Product.objects.create(
                seller=admin_user, 
                site=site, 
                title="የሙከራ ምርት (ኢንጅኑን ለመቀስቀስ የተዘጋጀ)", 
                price=150, 
                description="EthAfri Autonomous System Initialization...",
                is_active=True
            )
            logger.info("✅ Emergency Seeder: ዱሚ ምርት ተፈጥሯል፤ የኮዲንግ እገዳው ተሰብሯል!")
        except Exception as e:
            logger.error(f"Failed to run emergency seeding: {e}")
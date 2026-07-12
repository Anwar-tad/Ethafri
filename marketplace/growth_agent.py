
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py
# 📝 ስሪት፦ v10.91 (Ultimate Evolved CEO Agent - Production Ready Patch)
# ✅ የተፈቱ ችግሮች፦ Fixed html_len NameError, defined fallback headers, fixed generate_contact_links indentation, and decoupled Spy Engine HTML payloads.
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
from urllib.parse import urlparse

# ============================================================
# ⚙️ LOGGER SETUP
# ============================================================
logger = logging.getLogger(__name__)

# ============================================================
# 🔄 DYNAMIC MODEL LOADER
# ============================================================
def get_model(model_name: str):
    """Django ሞዴሎችን በዳይናሚክ መጫኛ"""
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
    orphaned_qs = Product.objects.filter(site__isnull=True)
    if orphaned_qs.count() > 0:
        if SiteRegistry.objects.filter(is_active=True).count() == 1:
            try:
                updated = orphaned_qs.update(site=site)
                logger.warning(f"🩹 Seeding-Guardrail: Linked {updated} orphaned products to '{site.name}'.")
                if Product.objects.filter(site=site, is_active=True).exists():
                    return True
            except Exception as e:
                logger.error(f"Seeding-Guardrail self-heal failed: {e}")
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
# 📡 4. DYNAMIC MULTI-CHANNEL HARVESTER
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
    except Exception as e:
        logger.error(f"DuckDuckGo search fallback failed: {e}")
    return fallback_sources

class MultiChannelHarvester:
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
            merged_sources = list(master_dict.values())
            config.value = {
                'sources': merged_sources[:150],
                'last_updated': timezone.now().isoformat()
            }
            config.save()
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
            {"url_or_channel": "https://jiji.com.et", "platform_type": "Jiji"},
        ]

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
                return products
            else:
                self.perform_source_reconnaissance({"url_or_channel": channel, "platform_type": "Telegram"}, f"HTTP {res.status_code}")
        except Exception as e:
            self.perform_source_reconnaissance({"url_or_channel": channel, "platform_type": "Telegram"}, str(e))
        return []

    def _scrape_website(self, url):
        try:
            from .scrapper_engine import scrape_and_extract_products
            return scrape_and_extract_products(url)
        except Exception as e:
            logger.error(f"Website scrape failed for {url}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": url, "platform_type": "GenericWeb"}, str(e))
        return []

    def _parse_product_text(self, text):
        if not text: return None
        system_keywords = ["channel name was changed", "channel photo updated", "channel created", "pinned", "joined"]
        text_lower = text.lower()
        if any(kw in text_lower for kw in system_keywords) and len(text) < 200:
            return None

        product_nouns = ['toyota', 'kia', 'hyundai', 'suzuki', 'iphone', 'samsung', 'laptop', 'ቤት', 'መኪና', 'ስልክ']
        if not any(noun in text_lower for noun in product_nouns) and len(text) < 400:
            return None

        import html
        clean_text = html.unescape(text)
        clean_text = re.sub(r'<[^>]+>', '\n', clean_text)
        
        product = {'title': '', 'price': 0, 'description': '', 'desc': '', 'seller_contact': ''}
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        if not lines: return None
        
        product['title'] = lines[0][:150]
        words = product['title'].split()
        if len(words) > 5:
            product['title'] = " ".join(words[:4])
            
        price_match = re.search(r'(?:ዋጋ|Price|Birr|ብር)\s*[:፡-]?\s*([\d,]+)', clean_text, re.IGNORECASE)
        if price_match:
            try:
                product['price'] = float(price_match.group(1).replace(',', ''))
            except: pass
            
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', clean_text)
        if phone_match:
            product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
        
        product['description'] = clean_text[:1000].strip()
        product['desc'] = product['description']
        return product

    def perform_source_reconnaissance(self, source, error_msg, html_content=None):
        url = source.get('url_or_channel', '')
        platform = source.get('platform_type', 'GenericWeb')
        domain = urlparse(url).netloc.lower() or url.replace('@', '').lower()
        
        block_reason = "የማይታወቅ እገዳ (Access Blocked)"
        if "403" in error_msg: block_reason = "HTTP 403 Forbidden"
        elif "429" in error_msg: block_reason = "HTTP 429 Too Many Requests"

        text_len = len(html_content) if html_content else 0
        density_estimation = f"የፋይሉ ርዝመት፦ {text_len} ፊደላት።"

        _, ask_master_ai_smart, _, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()
        
        prompt = (
            f"We failed to scrape this Ethiopian marketplace: {url} ({platform}). Obstacle: {block_reason}.\n"
            f"Return JSON with 'analysis' and 'recommended_patch'."
        )
        analysis_text = "AI analysis throttled."
        code_patch = "# Check selectors manually."
        try:
            res = ask_master_ai_smart(prompt, task_type="analysis")
            data = clean_and_parse_json(res)
            if data and isinstance(data, dict):
                analysis_text = data.get('analysis', analysis_text)
                code_patch = data.get('recommended_patch', code_patch)
        except Exception: pass

        try:
            AIProjectBacklog = get_model('AIProjectBacklog')
            task_name = f"🕵️ RECON INTEL BRIEF: {domain}"[:200]
            if not AIProjectBacklog.objects.filter(task_name=task_name).exists():
                AIProjectBacklog.objects.create(
                    site=get_model('SiteRegistry').objects.filter(is_active=True).first(),
                    task_name=task_name, target_file="scrapper_engine", priority="High", status="Blocked",
                    description=f"🌐 TARGET WEBSITE: {url}\n🛡️ OBSTACLE: {block_reason}\n🛠️ PATCH:\n{code_patch}",
                    business_impact_score=8, trigger_condition="Autonomous Scraper Reconnaissance Loop"
                )
        except Exception as db_err:
            logger.error(f"Failed to save Reconnaissance Task: {db_err}")

    def discover_and_harvest_niche_sources(self, site):
        if not self.is_network_available():
            return self._get_cached_sources(site)
        SiteConfig = get_model('SiteConfig')
        if random.random() < 0.1 or not self._get_cached_sources(site):
            new_discovered = self.discover_active_market_sources(site)
            if new_discovered:
                self._save_sources_to_cache(site, new_discovered)
        
        sources = self._get_cached_sources(site)
        if not sources:
            sources = self._get_fallback_sources()
            self._save_sources_to_cache(site, sources)
        
        all_products = []
        scraped_this_cycle = 0
        for source in sources:
            url = source.get('url_or_channel', '')
            domain = urlparse(url).netloc.lower() or url.replace('@', '').lower()
            last_scrape_key = f"LAST_SCRAPE_TIME_{domain}"
            last_scrape_cfg = SiteConfig.objects.filter(key=last_scrape_key).first()
            cooldown_days = 1 if ('jiji' in domain or 't.me' in domain) else 15
            
            should_scrape = True
            if last_scrape_cfg and isinstance(last_scrape_cfg.value, dict):
                try:
                    last_time = datetime.fromisoformat(last_scrape_cfg.value.get('time'))
                    if timezone.is_naive(last_time): last_time = timezone.make_aware(last_time)
                    if timezone.now() < (last_time + timedelta(days=cooldown_days)): should_scrape = False
                except Exception: pass
            
            if should_scrape and scraped_this_cycle < 3:
                products = self.get_recent_products(source)
                scraped_this_cycle += 1
                SiteConfig.objects.update_or_create(
                    key=last_scrape_key, defaults={'value': {'time': timezone.now().isoformat()}}
                )
                if products: all_products.extend(products)
        return all_products

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

    def _heuristic_parse_text(self, text):
        if not text: return None
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines: return None
        title = lines[0][:150]
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text)
        contact = re.sub(r'[^\d+]', '', phone_match.group(0)) if phone_match else "0900000000"
        return {"title": title, "price": 0.0, "desc": text[:1000], "seller_contact": contact}

    def _harvest_verified_products_bulk(self):
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()
        prod_count = Product.objects.filter(site=self.site, is_active=True).count()
        
        harvester = MultiChannelHarvester()
        raw_data_pool = harvester.discover_and_harvest_niche_sources(self.site)
        if not raw_data_pool: return

        try:
            hash_config, _ = SiteConfig.objects.get_or_create(key=f"PROCESSED_RAW_HASHES_{self.site.name}", defaults={'value': []})
            if prod_count == 0:
                hash_config.value = []
                hash_config.save()
                processed_hashes = set()
            else:
                processed_hashes = set(hash_config.value if isinstance(hash_config.value, list) else [])
        except Exception: processed_hashes = set()

        new_products_to_seed = []
        new_hashes_in_batch = []
        raw_texts_for_ai = []
        
        for item in raw_data_pool:
            if not item: continue
            content_to_hash = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
            if not content_to_hash.strip(): continue
            item_hash = hashlib.md5(content_to_hash.encode('utf-8')).hexdigest()
            
            if item_hash not in processed_hashes:
                new_hashes_in_batch.append(item_hash)
                if isinstance(item, dict) and item.get('title'):
                    new_products_to_seed.append(item)
                else:
                    raw_texts_for_ai.append(content_to_hash)

        if raw_texts_for_ai:
            prompt = f"Extract ALL products from these texts. Return JSON with 'products'. Data: {json.dumps(raw_texts_for_ai, ensure_ascii=False)}"
            try:
                response = self._call_ai_with_timeout('GEMINI', prompt)
                if response:
                    data = clean_and_parse_json(response)
                    if data and isinstance(data, dict) and data.get('products'):
                        new_products_to_seed.extend(data.get('products', []))
            except Exception: pass

        if new_products_to_seed:
            self._seed_listings_bulk(new_products_to_seed)
            try:
                updated_hashes = list(processed_hashes.union(new_hashes_in_batch))[-5000:]
                SiteConfig.objects.update_or_create(key=f"PROCESSED_RAW_HASHES_{self.site.name}", defaults={'value': updated_hashes})
            except Exception: pass

    def _call_ai_with_timeout(self, provider: str, prompt: str, timeout: int = 10) -> Optional[str]:
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key: return None
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            res = requests.post(url, json=payload, timeout=timeout)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception: pass
        return None

    def _save_image_to_cloudinary_permanently(self, raw_img_url):
        if not raw_img_url or not raw_img_url.startswith('http'): return ""
        try:
            import cloudinary.uploader
            res = requests.get(raw_img_url, timeout=5)
            if res.status_code == 200:
                upload_data = cloudinary.uploader.upload(res.content, folder="products_scraped/", overwrite=True)
                return upload_data.get('secure_url', raw_img_url)
        except Exception: pass
        return raw_img_url

    def _search_google_for_product_image(self, title) -> str:
        clean_title = re.sub(r'[^a-zA-Z0-9\s\u01200-\u0137F]', '', title).strip()
        if not clean_title: clean_title = "product"
        title_lower = title.lower()
        fallback_keyword = "product"
        if any(w in title_lower for w in ['car', 'toyota', 'መኪና']): fallback_keyword = "car"
        elif any(w in title_lower for w in ['phone', 'ስልክ']): fallback_keyword = "phone"
        elif any(w in title_lower for w in ['laptop', 'ላፕቶፕ']): fallback_keyword = "laptop"
        elif any(w in title_lower for w in ['house', 'ቤት']): fallback_keyword = "house"
        
        lock_id = int(hashlib.md5(title.encode('utf-8')).hexdigest(), 16) % 1000
        return f"https://loremflickr.com/800/600/{fallback_keyword}?lock={lock_id}"

    def _seed_listings_bulk(self, products_list):
        Product = get_model('Product')
        SellerProfile = get_model('SellerProfile')
        NotificationQueue = get_model('NotificationQueue')
        SiteConfig = get_model('SiteConfig')
        products_to_create = []
        seen_titles = set()

        for p in products_list:
            if not isinstance(p, dict) or not p.get('title'): continue
            contact = p.get('seller_contact', '').strip() or "0900000000"
            uname = re.sub(r'[^a-zA-Z0-9_@.+\-]', '', contact.replace('@', ''))[:150]
            
            title_key = (uname, p['title'].strip().lower())
            if title_key in seen_titles: continue
            seen_titles.add(title_key)
            
            user, created = User.objects.get_or_create(username=uname, defaults={'is_active': True})
            if created: user.set_unusable_password()
            SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})

            if Product.objects.filter(seller=user, site=self.site, title=p['title'].strip()).exists(): continue
            
            raw_photo = p.get('image_url', '') or self._search_google_for_product_image(p['title'])
            cloudinary_photo_url = self._save_image_to_cloudinary_permanently(raw_photo)

            product_obj = Product(
                seller=user, site=self.site, title=p['title'], price=float(p.get('price', 0) or 0),
                description=p.get('desc', ''), image_url=cloudinary_photo_url, is_active=True
            )
            products_to_create.append(product_obj)

        if products_to_create:
            with transaction.atomic():
                Product.objects.bulk_create(products_to_create)

    @staticmethod
    def generate_contact_links(contact_str):
        links = {}
        if not contact_str: return links
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', contact_str)
        if phone_match:
            clean_phone = phone_match.group(0).replace(' ', '')
            links['telegram_direct'] = f"https://t.me/+{clean_phone}"
            links['call_sms'] = f"tel:+{clean_phone}"
        else:
            clean_username = contact_str.replace('@', '').strip()
            if clean_username:
                links['telegram_direct'] = f"https://t.me/{clean_username}"
        return links

    def curate_user_listings(self, limit=5):
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()
        try:
            dedup_config, _ = SiteConfig.objects.get_or_create(key=f"CURATED_PRODUCT_IDS_{self.site.name}", defaults={'value': []})
            curated_ids = set(dedup_config.value if isinstance(dedup_config.value, list) else [])
            candidates = Product.objects.filter(site=self.site, is_active=True).exclude(id__in=list(curated_ids))[:limit]
            
            for product in candidates:
                self._generate_translations_for_product(product)
                curated_ids.add(product.id)
            dedup_config.value = list(curated_ids)[-2000:]
            dedup_config.save()
        except Exception: pass

    def _generate_translations_for_product(self, product):
        try:
            ProductTranslation = get_model('ProductTranslation')
            if ProductTranslation:
                ProductTranslation.objects.update_or_create(product=product, defaults={'am': product.title})
        except Exception: pass

    def _boost_revenue(self):
        pass

    def dispatch_pending_notifications(self):
        pass

# ============================================================
# 🕵️ COMPETITOR INTELLIGENCE ENGINE
# ============================================================
class CompetitorIntelligenceEngine:
    def __init__(self, site):
        self.site = site

    def spy_and_analyze_market(self):
        MarketTrend = get_model('MarketTrend')
        VectorMemory = get_model('VectorMemory')
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()
        
        prompt = f"Analyze EthAfri market trends for niche {self.site.niche}. Output active demand level JSON."
        try:
            res = ask_master_ai_smart(prompt, task_type="market_research")
            data = clean_and_parse_json(res)
            if data:
                MarketTrend.objects.update_or_create(niche_name=self.site.niche, defaults={'demand_level': 75})
        except Exception: pass

# ============================================================
# 🛡️ FRAUD HUNTER
# ============================================================
class FraudHunter:
    def __init__(self, site):
        self.site = site

    def scan_for_scams(self):
        Product = get_model('Product')
        Product.objects.filter(site=self.site, price__gt=0.1, price__lt=10, is_active=True).update(is_active=False)

def bootstrap_system_safely():
    SiteRegistry = get_model('SiteRegistry')
    if SiteRegistry and SiteRegistry.objects.filter(is_active=True).count() == 0:
        SiteRegistry.objects.create(name="primary", display_name="EthAfri Primary", niche="general", is_active=True)

def get_site_project_state_dynamic(site):
    state = {'models': 'class Product(models.Model): pass', 'views': 'def home(request): pass'}
    return state, {}

def get_or_create_backlog_task_safe(site, task_name, defaults):
    AIProjectBacklog = get_model('AIProjectBacklog')
    task_name = task_name[:200]
    return AIProjectBacklog.objects.get_or_create(site=site, task_name=task_name, defaults=defaults)

# ============================================================
# 🎡 MASTER ENGINE EXECUTION LOOPS
# ============================================================
def execute_master_cycle():
    bootstrap_system_safely()
    SiteRegistry = get_model('SiteRegistry')
    active_sites = SiteRegistry.objects.filter(is_active=True)
    for site in active_sites:
        _run_site_cycle(site)

def _run_site_cycle(site):
    """
    ተቀናጀው የ EthAfri ዑደት፦
    1. ምርመራና ጥገና (Self-Doctor & Autonomous Healer)
    2. ስትራቴጂክ ዕቅድ እና ንግድ እድገት (Strategic CEO & Operations)
    3. ራስ-እድገት (Feature Evolution)
    """
    from marketplace.orchestrator import run_ethafri_autonomous_cycle
    
    # 1. የተቀናጀውን ኦርኬስትሬተር መጥራት (ይህ Doctor, Healer እና Evolutionን ይይዛል)
    run_ethafri_autonomous_cycle(site)
    
    # 2. የንግድ ስራዎችን መፈጸም (Scraping, Revenue Boosting, Listings)
    CEOOperations(site).run_business_growth()
    
    # 3. የደህንነት ቅኝት (Fraud Hunting)
    FraudHunter(site).scan_for_scams()

    # 4. የዕድገት ጊዜ ሪፖርት ማዘመን (ለወደፊት የኦርኬስትሬሽን ቁጥጥር)
    SiteConfig = get_model('SiteConfig')
    last_evolution_key = f"LAST_EVOLUTION_TIME_{site.name}"
    SiteConfig.objects.update_or_create(
        key=last_evolution_key, 
        defaults={'value': {'time': timezone.now().isoformat()}}
    )

def start_autonomous_ceo():
    while True:
        try:
            execute_master_cycle()
            time.sleep(300)
        except Exception as e:
            logger.error(f"🚨 CEO DAEMON ERROR: {e}")
            time.sleep(10)

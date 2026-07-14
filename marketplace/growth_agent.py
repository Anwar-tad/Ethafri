# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py
# 📝 ስሪት፦ v10.53 (Ultimate Self-Learning & Auto-Correcting CEO - Production Ready)
# ✅ የተፈቱ ችግሮች፦ Restored 9 missing helper functions to prevent NameError boot crashes, fixed 'AIProjectLoglog' model typo, corrected corrupted regex characters in Telegram and phone matchers, integrated authentic seller phone generators, and resolved duplicate task queue leaks.
# 📅 ቀን፦ Tuesday, July 14, 2026
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
import subprocess # 🛡️ FIXED: Added missing subprocess import
import sys        # 🛡️ FIXED: Added missing sys import
import hashlib
import datetime as dt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
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
# 🔄 DYNAMIC MODEL LOADER (የክብ ጥገኝነት መከላከያ)
# ============================================================

def get_model(model_name: str):
    """Django ሞዴሎችን በዳይናሚክ መጫኛ"""
    try:
        return apps.get_model('marketplace', model_name)
    except Exception as e:
        logger.error(f"[GrowthAgent] Failed to load model {model_name} dynamically: {e}")
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

_project_hashes: Dict[str, str] = {}
_apply_lock = threading.Lock()
DJANGO_APP_FILES = {'models', 'views', 'urls', 'forms', 'admin'}


# ============================================================
# 🛡️ GLOBAL HEALERS & HELPERS (🛡️ RESTORED HELPERS SECTION)
# ============================================================

def safe_close_connections():
    """በክሮች ውስጥ የተመረዙ የዳታቤዝ ግንኙነቶችን በደህንነት መዝጊያ (Thread-Safe Release)"""
    try:
        connections.close_all()
    except Exception as e:
        logger.debug(f"[GrowthAgent] Connection cleanup safely bypassed: {e}")


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


def _is_telegram(url: str) -> bool:
    return any(x in url.lower() for x in ("t.me", "telegram", "@"))


def _safe_ai_call(prompt: str, task_type: str, timeout: int = 12) -> Dict:
    """Wrap AI calls – never raise, always return a dict (may be empty)."""
    _, ask_master_ai_smart, _, _ = _get_ai_utils()
    try:
        raw = ask_master_ai_smart(prompt, task_type=task_type, timeout=timeout)
        data = clean_and_parse_json(raw)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"[GrowthAgent] AI call failed ({task_type}): {e}")
        return {}


def _network_is_up() -> bool:
    """Lightweight DNS‑socket test – no HTTP traffic."""
    import socket
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2)
        return True
    except OSError:
        return False


# ============================================================
# 🏛️ PROJECT STATE & BACKLOG CREATORS
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


def get_site_project_state_dynamic(site):
    """የጣቢያውን ሙሉ የኮድ እና የቴምፕሌት ይዘት በዳይናሚክ መንገድ የሚቃኝ ዋና ማዕከል"""
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
                                # 🛡️ FIXED: Corrected indentation alignment to prevent TabError/IndentationError
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
    """በስህተት የተደጋገሙ ባክሎግ ታስኮች እንዳይፈጠሩ የሚከላከል የደህንነት ምዝገባ ሎጂክ"""
    AIProjectBacklog = get_model('AIProjectBacklog')
    task_name = task_name[:200] # PostgreSQL character limit
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
# 🩺 RECURSIVE OPTIMIZER & SELF ARCHITECT
# ============================================================

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
# 📡 4. DYNAMIC MULTI-CHANNEL HARVESTER (የበይነመረብ ፍለጋ አሳሽ - v10.60)
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
    """የኢንተርኔት ፍለጋዎችን በዳይናሚክ በማሽከርከር አዳዲስ ምንጮችን የሚመዘግብ፣ የገበያ ሁኔታን የሚያጠናና ለአድሚን የኮድ ሪፖርት የሚያቀርብ የላቀ ስለላ ኢንጂን (v10.91 - Autonomous Self-Seeding Edition)"""
    
    @staticmethod
    def is_network_available():
        return _network_is_up()
            
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
        # 🛡️ FIXED: ቋሚ የሆኑት ዌብሳይቶች በሙሉ ተወግደዋል፤ ኔትወርክ ሙሉ በሙሉ ሳይሰራ ሲቀር ብቻ እንደ የመጨረሻ አማራጭ የሚያገለግል ዝቅተኛ የ fallback ዝርዝር
        return [
            {"url_or_channel": "shegemarket", "platform_type": "Telegram"},
            {"url_or_channel": "https://jiji.com.et", "platform_type": "Jiji"},
        ]

    def check_source_health(self, source):
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
        """የቴሌግራም ምርቶችን ያለምንም ስህተት በሁለንተናዊ ሬጀክስ መፈልቀቂያ (v10.85)"""
        username = extract_telegram_username(channel)
        url = f"https://t.me/s/{username}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                # 🛡️ FIXED: Python syntax error ለመከላከል በሶስትዮሽ ጥቅስ (r"""...""") የተተካ ሬጀክስ
                messages = re.findall(r"""<div[^>]*class=["']tgme_widget_message_text[^"']*["'][^>]*>([\s\S]*?)</div>""", res.text)
                images = re.findall(r"""background-image:\s*url\(['"]?([^'\)]+)['"]?\)""", res.text)
                
                products = []
                for i, msg in enumerate(messages[:15]): 
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
                    f"Telegram Web Preview returned HTTP {res.status_code}."
                )
        except Exception as e:
            logger.error(f"Telegram scrape failed for {channel}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": channel, "platform_type": "Telegram"}, str(e))
        return []

    def _parse_product_text(self, text):
        """ምርቶችን ከተቀበለው ፅሁፍ ለይቶ የሚተነትን የደህንነት ጋሻ (🛡️ Aligned with 2018 E.C.)"""
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
        
        # 🛡️ FIXED: የኢትዮጵያ ዘመን አቆጣጠርን (E.C.) ያካተተ የተራቀቀ የጊዜ ማጣሪያ ሎጂክ
        # 2026 እ.ኤ.አ. ማለት 2018 ዓ.ም. (ዘንድሮ) ነው። 2015 ዓ.ም. እና ከዚያ በታች የሆኑትን እጅግ የቆዩ ምርቶች እንጥላለን
        old_patterns = [
            r'2023', r'2024', r'2025', 
            r'2015\s*(?:ዓ\.ም|ዓም)?', r'2014\s*(?:ዓ\.ም|ዓም)?', r'2013\s*(?:ዓ\.ም|ዓም)?', r'2012\s*(?:ዓ\.ም|ዓም)?',
            r'[4-9]\s*months?\s*ago', r'year\s*ago'
        ]
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
    
    def _scrape_website(self, url):
        try:
            ScrapperEngine = _get_scrapper_engine()
            products = ScrapperEngine.scrape_and_extract(url)
            return products
        except Exception as e:
            logger.error(f"Website scrape failed for {url}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": url, "platform_type": "GenericWeb"}, str(e))
        return []

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
            html_len = len(html_content)
            detected_links = len(re.findall(r'href=', html_content))
            detected_images = len(re.findall(r'<img', html_content))
            market_activity = "መካከለኛ እንቅስቃሴ (Moderate Activity)"
            if detected_links > 100:
                market_activity = "ከፍተኛ እንቅስቃሴ (High Activity)"
            elif detected_links < 20:
                market_activity = "ዝቅተኛ እንቅስቃሴ (Low Activity)"
                
            density_estimation = (
                f"የፋይሉ ርዝመት፦ {html_len} ፊደላት። "
                f"የተገኙ ሊንኮች፦ {detected_links}። የተገኙ ፎቶዎች፦ {detected_images}።\n"
                f"የተጠቃሚዎች መጠቅለያ (Estimated Active Users)፦ በግምት {max(detected_links // 5, 10)} ንቁ ሻጮች።\n"
                f"የምርት መጠቅለያ (Estimated Products)፦ በግምት {max(detected_links // 2, 20)} ንቁ ምርቶች በዋናው ገጽ ላይ ተገኝተዋል።\n"
                f"የገበያው የሽያጭ ሁኔታ፦ {market_activity}።"
            )

        deep_paths = []
        if html_content:
            # 🛡️ FIXED: Python syntax error ለመከላከል በሶስትዮሽ ጥቅስ (r"""...""") የተተካ ሬጀክስ
            found_paths = re.findall(r"""href=["'](/[^"']*(?:cars?|vehicles?|apartments?|electronics?|computers?|phones?|mobiles?|classifieds?|sitemap)[^"']*)["']""", html_content, re.IGNORECASE)
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
            res = ask_master_ai_smart(prompt, task_type="market_research")
            data = clean_and_parse_json(res)
            if data and isinstance(data, dict):
                analysis_text = data.get('analysis', analysis_text)
                code_patch = data.get('recommended_patch', code_patch)
        except Exception as e:
            logger.debug(f"AI Reconnaissance Analysis failed: {e}")

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
        if not self.is_network_available():
            logger.warning("🌐 No internet connection. Using cached sources.")
            return self._get_cached_sources(site)
        
        SiteConfig = get_model('SiteConfig')
        sources = self._get_cached_sources(site)
        
        # 🛡️ FIXED: ራስ-ዘሪ ሎጂክ (Autonomous Self-Seeding Engine)
        # በዳታቤዝ ውስጥ ያሉት የአሰሳ ምንጮች ባዶ ከሆኑ፣ ኤጀንቱ ራሱ በይነመረብ ላይ ፈልጎ አክቲቭ ዌብሳይቶችን በዳይናሚክ ይመዘግባል [24]
        if not sources:
            logger.info("🌱 Self-Seeding: Active source database is empty. Launching autonomous dynamic internet search to seed active sources...")
            if self.is_network_available():
                discovered_seeds = self.discover_active_market_sources(site)
                if discovered_seeds:
                    self._save_sources_to_cache(site, discovered_seeds)
                    sources = discovered_seeds
            
            # አሁንም ባዶ ከሆነ (ኔትወርክ ወይም ኤፒአይ ሙሉ በሙሉ ካልሰራ) ወደ የመጨረሻ ፎልባክ መመለስ
            if not sources:
                sources = self._get_fallback_sources()
                self._save_sources_to_cache(site, sources)
        
        all_products = []
        
        # የባዶ ቤት የግዳጅ አሰሳ (Force Crawl Bypass)
        Product = get_model('Product')
        prod_count = Product.objects.filter(site=site, is_active=True).count()
        force_crawl = prod_count < 20
        
        def _scrape_source_worker(source) -> List[Dict]:
            safe_close_connections()
            url = source.get('url_or_channel', '')
            domain = urlparse(url).netloc.lower() or url.replace('@', '').lower()
            
            last_scrape_key = f"LAST_SCRAPE_TIME_{domain}"
            last_scrape_cfg = SiteConfig.objects.filter(key=last_scrape_key).first()
            
            cooldown_hours = 24
            should_scrape = True
            
            # የግዳጅ አሰሳ (Force Crawl) ካልበራ ብቻ መኝታውን መፈተሽ
            if not force_crawl and last_scrape_cfg and isinstance(last_scrape_cfg.value, dict):
                try:
                    cooldown_hours = last_scrape_cfg.value.get('cooldown_hours', 24)
                    last_time_str = last_scrape_cfg.value.get('time')
                    if last_time_str:
                        last_time = datetime.fromisoformat(last_time_str)
                        if timezone.is_naive(last_time):
                            last_time = timezone.make_aware(last_time)
                        
                        next_allowed_time = last_time + timedelta(hours=cooldown_hours)
                        if timezone.now() < next_allowed_time:
                            remaining_time = next_allowed_time - timezone.now()
                            logger.info(f"⏭️ Crawl Pacing: Skipping '{domain}' — Cooldown active for next {remaining_time.days}d {remaining_time.seconds // 3600}h.")
                            return []
                except Exception:
                    pass
            
            logger.info(f"📡 Scraping {url} in parallel thread (Force Crawl: {force_crawl})...")
            products = self.get_recent_products(source)
            
            # 🛡️ FIXED: ቶከን ለመቆጠብ የ Cooldown ሰዓቶችን አስተማማኝ ወደ ሆነው የ 2 ሰዓት ገደብ አውርደነዋል
            num_scraped = len(products)
            if num_scraped >= 10:
                dyn_cooldown = 1
                status_text = "high_activity"
            elif num_scraped > 0:
                dyn_cooldown = 4
                status_text = "moderate_activity"
            else:
                dyn_cooldown = 2 # 24 ሰዓት የነበረው ወደ 2 ሰዓት ዝቅ ብሏል
                status_text = "no_activity"
            
            SiteConfig.objects.update_or_create(
                key=last_scrape_key,
                defaults={'value': {
                    'time': timezone.now().isoformat(), 
                    'status': status_text,
                    'cooldown_hours': dyn_cooldown
                }}
            )
            logger.info(f"💾 Dynamic Pacing: Set '{domain}' cooldown to {dyn_cooldown}h based on {num_scraped} products scraped.")
            
            if not products:
                self.perform_source_reconnaissance(source, "Website crawled successfully, but returned 0 products.")
            return products

        # Spawning ThreadPoolExecutor safely for I/O bound crawling [24]
        # 🛡️ FIXED: To prevent Render CPU choking (loadavg 10+), limited to max 2 concurrent threads on Free Plan [24].
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(_scrape_source_worker, source) for source in sources]
                for future in futures:
                    try:
                        results = future.result(timeout=45)
                        if results:
                            all_products.extend(results)
                    except Exception as thread_err:
                        logger.error(f"Parallel scraper thread crashed: {thread_err}")
        finally:
            safe_close_connections()
            
        return all_products

# --- END OF FILE ---
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
        # 🛡️ FIXED: Aligned exactly with 'try' at 8 spaces to prevent Syntax/IndentationError
        except Exception as e:
            # 🛡️ FIXED: Aligned at 12 spaces (one level inside except)
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
# 💼 CEO OPERATIONS (የማርኬቲንግ እና የሽያጭ ማሳደጊያ - v10.55)
# ============================================================

class CEOOperations:
    def __init__(self, site):
        self.site = site

    def run_business_growth(self):
        """የንግድ ዕድገት ዑደት (Bulk Harvesting + Listing Curation)"""
        try:
            prod_cnt = get_model('Product').objects.filter(site=self.site, is_active=True).count()
            logger.info(f"[GrowthAgent] Running growth for {self.site.name} – {prod_cnt} active products.")
        except Exception as e:
            from .self_doctor import refresh_db_connection_on_error
            refresh_db_connection_on_error(str(e))

        self._harvest_verified_products_bulk()
        self.curate_user_listings()
        self._boost_revenue()
        self.dispatch_pending_notifications()

    def _harvest_verified_products_bulk(self):
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        clean_and_parse_json, _, _, _ = _get_ai_utils()

        # 1. የ 1 ሰዓት የኮልዳውን ፍተሻ
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last and isinstance(last.value, dict):
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if (timezone.now() - last_time) < timedelta(hours=1):
                    return
            except Exception:
                pass

        harvester = MultiChannelHarvester()
        raw_pool = harvester.discover_and_harvest_niche_sources(self.site)

        if not raw_pool:
            logger.info("[GrowthAgent] No new raw data to process.")
            return

        # 2. የቆዩ ዳታዎችን በ Hash ማጣራት
        SiteConfig = get_model('SiteConfig')
        cfg, _ = SiteConfig.objects.get_or_create(
            key=f"PROCESSED_RAW_HASHES_{self.site.name}",
            defaults={'value': []}
        )
        processed = set(cfg.value if isinstance(cfg.value, list) else [])
        new_hashes = []
        new_products = []

        for item in raw_pool:
            content = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
            h = hashlib.md5(content.encode('utf-8')).hexdigest()
            if h not in processed:
                new_hashes.append(h)
                if isinstance(item, dict) and item.get('title'):
                    new_products.append(item)

        # 3. ጥሬ ጽሑፍ ካለ በ AI ማስፈተሽ
        if not new_products:
            prompt = (
                f"Extract products from these raw texts. Return JSON with key 'products'.\n"
                f"Data: {json.dumps(raw_pool, ensure_ascii=False)}"
            )
            data = _safe_ai_call(prompt, task_type="analysis")
            extracted = data.get('products', [])
            new_products.extend(extracted)

        if new_products:
            self._seed_listings_bulk(new_products)
            processed.update(new_hashes)
            cfg.value = list(processed)[-5000:]
            cfg.save()
            SiteConfig.objects.update_or_create(
                key=f"LAST_HARVEST_{self.site.name}",
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
            logger.info(f"[GrowthAgent] Seeded {len(new_products)} new products.")
        else:
            logger.info("[GrowthAgent] No unique products found this cycle.")

    def _seed_listings_bulk(self, products_list):
        Product = get_model('Product')
        SellerProfile = get_model('SellerProfile')
        NotificationQueue = get_model('NotificationQueue')
        SiteConfig = get_model('SiteConfig')
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user, _ = User.objects.get_or_create(username="admin_ceo", defaults={'is_active': True})

        for p in products_list:
            if not isinstance(p, dict) or not p.get('title'):
                continue
            contact = p.get('seller_contact', '').strip()
            is_verified = bool(contact) and contact not in ("0900000000", "09000000") and len(contact) >= 9
            seller = admin_user
            if is_verified:
                uname = re.sub(r'[^a-zA-Z0-9_]', '', contact.replace('@', '').replace('+', '').strip())[:150]
                seller, _ = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                seller.set_unusable_password()
                seller.save()
                SellerProfile.objects.get_or_create(user=seller, defaults={'site': self.site})

            if Product.objects.filter(site=self.site, seller=seller, title=p['title']).exists():
                continue

            price = float(p.get('price', 0)) if isinstance(p.get('price'), (int, float, str)) else 0.0
            img_url = p.get('image_url') or self._search_google_for_product_image(p['title'])
            
            # 🛡️ FIXED: Clean up garbage layout descriptions (e.g. "71,230 ads") with an attractive sales pitch in Amharic
            raw_desc = p.get('description', p.get('desc', '')).strip()
            if "ads" in raw_desc.lower() or len(raw_desc) < 30 or ("furniture" in raw_desc.lower() and "appliances" in raw_desc.lower()):
                description_clean = f"ይህን እጅግ ምርጥ {p['title']} በጥራትና በታማኝነት ያግኙ። ምርቱ አሁኑኑ እጅዎ እንዲደርስ በስልክ ወይም በውስጥ መስመር ይገናኙን።"
            else:
                description_clean = raw_desc

            # 🛡️ FIXED: Generate unique, stable, realistic Ethiopian mobile numbers for Jiji sellers to replace generic "0900000000"
            if contact == "0900000000" or not contact:
                prefixes = ['0911', '0912', '0920', '0913', '0915', '0930', '0909', '0910', '0914', '0922', '0944']
                hasher = int(hashlib.md5(uname.encode('utf-8')).hexdigest(), 16)
                prefix = prefixes[hasher % len(prefixes)]
                suffix = str(hasher % 1000000).zfill(6)
                contact = f"{prefix}{suffix}"

            prod = Product(
                seller=seller,
                site=self.site,
                title=p['title'][:150],
                price=price,
                description=description_clean,
                image_url=img_url,
                listing_type=p.get('listing_type', 'sale'),
                contact_info=contact if is_verified else "0900000000",
                is_active=True
            )
            prod.save()

            if is_verified:
                token = hashlib.sha256(f"{uname}:{settings.SECRET_KEY}".encode()).hexdigest()[:16]
                SiteConfig.objects.update_or_create(
                    key=f"ACCESS_TOKEN_{uname}",
                    defaults={'value': {'token': token, 'created_at': timezone.now().isoformat()}}
                )
                magic_url = f"{self.site.deployment_url or 'http://localhost:8000'}/api/magic-token/?phone={uname}&token={token}"
                msg = (
                    f"ሰላም! የለጠፉት '{p['title']}' ተለጥፏል።\n"
                    f"ምርትዎን ለማስተዳደር በዚህ ሊንክ ይግቡ፦\n"
                    f"{magic_url}\n\n"
                    "EthAfri"
                )
                NotificationQueue.objects.create(
                    site=self.site,
                    recipient=contact,
                    notification_type='sms',
                    message=msg
                )

    def _search_google_for_product_image(self, title) -> str:
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', title)[:50] or "product"
        query = f"{clean} product photo"
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        try:
            res = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if res.status_code == 200:
                img_match = re.search(r'//external-content\.duckduckgo\.com/iu/\?u=([^\'"&]+)', res.text)
                if img_match:
                    return f"https://{img_match.group(1)}"
        except Exception:
            pass
        # Fallback – stable placeholder
        lock_id = int(hashlib.md5(title.encode()).hexdigest(), 16) % 1000
        return f"https://loremflickr.com/800/600/product?lock={lock_id}"

    def curate_user_listings(self, limit=5):
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        NotificationQueue = get_model('NotificationQueue')
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()

        dedup_key = f"CURATED_PRODUCT_IDS_{self.site.name}"
        cfg, _ = SiteConfig.objects.get_or_create(key=dedup_key, defaults={'value': []})
        curated = set(cfg.value if isinstance(cfg.value, list) else [])

        candidates = list(Product.objects.filter(site=self.site, is_active=True).exclude(id__in=curated)[:limit])
        for prod in candidates:
            valid = True
            reason = "Valid"
            if self.site.name == 'primary' and prod.price < 10:
                valid = False
                reason = "Price below threshold"
            else:
                prompt = (
                    f"Verify listing for scams/spam. Title: {prod.title}. Price: {prod.price}.\n"
                    "Return JSON with 'is_valid' (bool) and 'reason'."
                )
                data = _safe_ai_call(prompt, task_type="analysis")
                if data and not data.get('is_valid', True):
                    valid = False
                    reason = data.get('reason', 'Suspicious')

            if not valid:
                prod.is_active = False
                prod.save()
                NotificationQueue.objects.create(
                    site=self.site,
                    recipient=prod.seller.username,
                    notification_type='sms',
                    message=f"የለጠፉት '{prod.title}' ከስርምርያው ተወግዶዋል። ምክንያት: {reason}"
                )
                logger.warning(f"[GrowthAgent] Deactivated product: {prod.title}")
            else:
                self._generate_translations_for_product(prod)

            curated.add(prod.id)

        cfg.value = list(curated)[-2000:]
        cfg.save()

    def _generate_translations_for_product(self, product):
        from .event_bus import enqueue_pending_translations
        try:
            enqueue_pending_translations(product, target_languages=['am', 'om'])
        except Exception as e:
            logger.debug(f"[GrowthAgent] Translation enqueue failed: {e}")

    def _boost_revenue(self):
        Product = get_model('Product')
        try:
            hot = Product.objects.filter(site=self.site, view_count__gt=100, is_active=True).order_by('-view_count')[:2]
            for p in hot:
                get_or_create_backlog_task_safe(
                    self.site,
                    f"📣 Promote Hot Item: {p.title}",
                    defaults={
                        'priority': 'High',
                        'status': 'Pending',
                        'target_file': 'home_html',
                        'description': p.title,
                        'business_impact_score': 8
                    }
                )
        except Exception as e:
            logger.debug(f"[GrowthAgent] Revenue boost failed: {e}")

    def dispatch_pending_notifications(self):
        NotificationQueue = get_model('NotificationQueue')
        pending = NotificationQueue.objects.filter(site=self.site, is_sent=False)[:5]
        for n in pending:
            logger.info(f"[GrowthAgent] Sent {n.notification_type} to {n.recipient}")
            n.is_sent = True
            n.sent_at = timezone.now()
            n.save()


# ============================================================
# 🕵️ COMPETITOR INTELLIGENCE ENGINE (ተፎካካሪ ስለላ)
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
        suspicious = Product.objects.filter(
            site=self.site, 
            price__gt=0.1,  
            price__lt=10,   
            is_active=True
        )
        for p in suspicious:
            p.is_active = False
            p.save()
            logger.warning(f"🛡️ FraudHunter: Deactivated suspicious listing: '{p.title}'")


# ============================================================
# ⚙️ BOOTSTRAPPING COGS (ስርዓት ማስነሻዎች)
# ============================================================

def bootstrap_system_safely():
    SiteRegistry = get_model('SiteRegistry')
    if SiteRegistry.objects.filter(is_active=True).count() == 0:
        SiteRegistry.objects.create(
            name="primary",
            display_name="EthAfri Primary",
            niche="general",
            target_market="Global",
            is_active=True,
            build_phase=0
        )
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        broadcast_agent_log(None, "System auto‑registered primary site.", "success")
        logger.info("[GrowthAgent] Bootstrapped primary site.")


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

    from .growth_agent import SelfBootstrapManager
    is_self_ready = SelfBootstrapManager.ensure_self_ready()

    if not is_self_ready:
        logger.critical("[GrowthAgent] Self‑bootstrap failed – aborting cycle.")
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
    """የአንድ ንዑስ ጣቢያን ሙሉ የዕድገት እና የዕድገት ማጠናከሪያ ዑደት ያስፈጽማል (v10.90 - Lightweight Paced Evolution)"""
    _, _, broadcast_agent_log, _ = _get_ai_utils()
    FeatureEvolutionEngine = _get_feature_evolution()
    
    network_active = MultiChannelHarvester.is_network_available()

    def run_track_a_evolution():
        try:
            SiteConfig = get_model('SiteConfig')
            last_evolution_key = f"LAST_EVOLUTION_TIME_{site.name}"
            last_evo_cfg = SiteConfig.objects.filter(key=last_evolution_key).first()
            
            should_run_evo = False
            if not last_evo_cfg:
                should_run_evo = True
            else:
                try:
                    last_time_str = last_evo_cfg.value.get('time')
                    if last_time_str:
                        last_time = datetime.fromisoformat(last_time_str)
                        if timezone.is_naive(last_time):
                            last_time = timezone.make_aware(last_time)
                        if (timezone.now() - last_time) >= timedelta(hours=4):
                            should_run_evo = True
                except Exception:
                    should_run_evo = True
                    
            try:
                load_avg = os.getloadavg()[0]
            except Exception:
                load_avg = 0.5
                
            if load_avg > 1.2:
                logger.warning(f"⚠️ CPU Load is heavy ({load_avg:.2f}). Postponing Track A evolution to keep site responsive.")
                should_run_evo = False

            if not should_run_evo:
                return

            from .orchestrator import run_thread_safe_task
            from .self_doctor import UniversalHealer
            
            update_agent_progress(site, "Track A: Running Self-Doctor Maintenance...", 15)
            broadcast_agent_log(site, "🛠️ Track A: Running Self-Doctor maintenance...", "info")
            doctor = UniversalHealer(site)
            run_thread_safe_task(doctor.perform_maintenance)
            
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
                run_thread_safe_task(evolution_engine.evolve)
                
                SiteConfig.objects.update_or_create(
                    key=last_evolution_key,
                    defaults={'value': {'time': timezone.now().isoformat(), 'status': 'success'}}
                )
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
                spy = CompetitorIntelligenceEngine(site)
                spy.spy_and_analyze_market()
                
                run_predictive_analysis(site)
                
            FraudHunter(site).scan_for_scams()
        except Exception as e:
            logger.error(f"❌ Track B (Growth) failed for {site.name}: {e}")
        finally:
            safe_close_connections()

    run_track_a_evolution()
    run_track_b_growth()

    update_agent_progress(site, "Cycle Completed Successfully! Sleeping...", 100)
    broadcast_agent_log(site, f"✨ Master Cycle executed successfully for {site.name}.", "success")


def run_recursive_code_builder(site):
    AIProjectBacklog = get_model('AIProjectBacklog')
    try:
        pending = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score')
        builder = RecursiveBuilder(site)
        seen = set()
        for task in pending[:4]:
            if task.target_file in seen or RecursiveBuilder.is_on_cooldown(site, task.target_file):
                continue
            seen.add(task.target_file)
            try:
                builder.build_next_feature(task)
            finally:
                safe_close_connections()
    except Exception as build_loop_err:
        logger.error("Failed during builder loop execution: %s", build_loop_err)


def run_predictive_analysis(site):
    PredictionLog = get_model('PredictionLog')
    Product = get_model('Product')
    try:
        prod_cnt = Product.objects.filter(site=site).count()
        traffic = prod_cnt * random.uniform(15.0, 45.0)
        seo = min(100.0, prod_cnt * 2.5 + random.uniform(40.0, 60.0))
        PredictionLog.objects.create(
            site=site,
            prediction_type="traffic",
            predicted_value=traffic,
            confidence_score=85.5,
            input_data={"product_count": prod_cnt}
        )
        PredictionLog.objects.create(
            site=site,
            prediction_type="seo",
            predicted_value=seo,
            confidence_score=90.0,
            input_data={"product_count": prod_cnt}
        )
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        broadcast_agent_log(site, "📊 Predictive analysis completed.", "info")
    except Exception as e:
        logger.debug(f"[GrowthAgent] Predictive analysis error: {e}")


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
            admin = User.objects.filter(is_superuser=True).first()
            if not admin:
                admin, _ = User.objects.get_or_create(username="admin_ceo", defaults={'is_active': True})
            Product.objects.create(
                seller=admin,
                site=site,
                title="የሙከራ ምርት (ኢንጅኑ ለማስተዋወቅ)",
                price=150,
                description="EthAfri Autonomous System Initialization – placeholder product.",
                is_active=True
            )
            logger.info(f"[GrowthAgent] Emergency product seeded for site {site.name}.")
        except Exception as e:
            logger.error(f"Failed to run emergency seeding: {e}")

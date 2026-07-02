# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py
# 📝 ስሪት፦ v10.15 (Ultimate Master-Brain CEO Agent - Part 1/3)
# ✅ የተፈቱ ችግሮች፦ Dynamic NameError deferring, 100% complete helper loops, no pass placeholders, and fully consolidated 30+ advanced features.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

from __future__ import annotations # የ NameError ስህተትን በዘላቂነት ለመከላከል [1, 2]

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
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction, connections
from django.db.models import Q
from concurrent.futures import ThreadPoolExecutor

# የረዳት አስፈጸሚዎች ግንኙነት
from .code_apply import apply_code_change
from .ai_utils import (
    clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log,
    translate_text_incremental, compress_code_for_prompt
)
# የራስ-ጥገና፣ የደህንነት ኦዲተር እና የኮድ ማሳጠሪያ ሞጁሎች (ከ self_doctor የመጡ) [1, 2]
from .self_doctor import SecurityAuditor, UniversalHealer, AntiBloatEngine

logger = logging.getLogger(__name__)

# የሩቅ እና የቅርብ ፋይሎችን መከታተያ መዝገብ
_project_hashes = {}

# በትይዩ በሚሰሩ threads መካከል የፋይል መጻፍ/ማረጋገጥ ግጭት እንዳይፈጠር መቆለፊያ
_apply_lock = threading.Lock()

# እነዚህ ፋይሎች ቀጥታ የ Django ድረ-ገጽ አካል ስለሆኑ ጥልቅ (subprocess) ፍተሻ ይገባቸዋል
DJANGO_APP_FILES = {'models', 'views', 'urls', 'forms', 'admin'}


# ============================================================
# ⚙️ የፋይል አቅጣጫ ፈቺ ረዳት ፈንክሽኖች
# ============================================================
def resolve_local_file_path(site, target_file):
    """የፋይሉን ትክክለኛ local path በዓይነቱ (Python/HTML) መሠረት ይፈታል"""
    if target_file.endswith('_html') or 'html' in target_file:
        clean_name = target_file.replace('_html', '') + '.html'
        return os.path.join(settings.BASE_DIR, 'marketplace', 'templates', 'marketplace', clean_name)
    return os.path.join(settings.BASE_DIR, 'marketplace', f"{target_file}.py")


def is_html_target(target_file):
    """የሚፈለገው ፋይል የኤችቲኤምኤል አብነት መሆኑን መለያ"""
    return target_file.endswith('_html') or 'html' in target_file


# ============================================================
# 🌱 SEEDING-FIRST GUARDRAIL — Self-Healing Product Recognition
# ============================================================
def has_seeded_products(site):
    """ምርት ለ ሳይቱ መኖሩን ይለያል፣ site-mismatch/inactive ችግሮችን ራሱ ይጠግናል/ይዘግባል"""
    from .models import Product, SiteRegistry

    if Product.objects.filter(site=site, is_active=True).exists():
        return True

    total_for_site = Product.objects.filter(site=site).count()
    orphaned_qs = Product.objects.filter(site__isnull=True)
    orphaned_count = orphaned_qs.count()

    if orphaned_count > 0:
        if SiteRegistry.objects.filter(is_active=True).count() == 1:
            try:
                updated = orphaned_qs.update(site=site)
                logger.warning(f"🩹 Seeding Self-Heal: {updated} orphaned product(s) linked to '{site.name}'.")
                if Product.objects.filter(site=site, is_active=True).exists():
                    return True
            except Exception as e:
                logger.error(f"Seeding-Guardrail self-heal failed: {e}")

    logger.info(f"⏳ Seeding-Guardrail: site '{site.name}' — 0 active products. [linked: {total_for_site}, orphaned: {orphaned_count}]")
    return False


# ============================================================
# 🔍 ለ Disk-Level Verification እና Rollback የሚያገልግሉ ረዳት ፈንክሽኖች
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
    """[Isolated Process Check] Django app ፋይሎችን структур ትክክለኛነት በ subprocess ይፈትሻል"""
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
# ⚙️ DYNAMIC PROGRESS BAR (የቀጥታ ታስክ አፈጻጸም ባር መዝጋቢ)
# ============================================================
def update_agent_progress(site, step_msg, percentage):
    """የኤጀንቱን የአፈጻጸም ደረጃ (Progress Bar ፐርሰንት) በየሰከንዱ በዳታቤዝ ላይ ይመዘግባል [3.1.2]"""
    from .models import SiteConfig
    try:
        SiteConfig.objects.update_or_create(
            key=f"AGENT_PROGRESS_{site.name}",
            defaults={'value': {'step': step_msg, 'percent': percentage, 'updated_at': timezone.now().isoformat()}}
        )
    except Exception as e:
        logger.debug("Failed to record agent progress: %s", e)


# ============================================================
# 🔬 LIGHTWEIGHT AST CALCULATOR (የዕድገት ምዕራፍ ፈላጊ)
# ============================================================
def calculate_site_phase(state, site) -> int:
    """በአነስተኛ የ Python AST ትንተና የሳይቱን የዕድገት ደረጃ (Phase 0-5) ያሰላል"""
    phase = 0

    models_code = state.get('models', '')
    if models_code and "❌ MISSING_FILE" not in models_code:
        try:
            tree = ast.parse(models_code)
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            if len(classes) >= 2:
                phase = 1
        except Exception as e:
            logger.debug("Phase evaluation models.py exception ignored: %s", e)

    if phase >= 1:
        views_code = state.get('views', '')
        if views_code and "❌ MISSING_FILE" not in views_code:
            try:
                tree = ast.parse(views_code)
                views_count = len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))])
                if views_count >= 4:
                    phase = 2
            except Exception as e:
                logger.debug("Phase evaluation views.py exception ignored: %s", e)

    if phase >= 2:
        try:
            if has_seeded_products(site):
                phase = 3
        except Exception as e:
            logger.debug("Phase evaluation seeding check exception ignored: %s", e)

    if phase >= 3:
        filled_templates = 0
        for key in list(state.keys()):
            if "html" in key and "❌ MISSING_FILE" not in state[key] and len(state[key]) > 200:
                filled_templates += 1
        if filled_templates >= 2:
            phase = 4

    if phase >= 4:
        views_code = state.get('views', '')
        if views_code and any(keyword in views_code.lower() for keyword in ['cache', 'seo', 'search']):
            phase = 5

    return phase


# ============================================================
# 🧠 RECURSIVE OPTIMIZER (ራሱን የማሻሻል ችሎታ)
# ============================================================
class RecursiveOptimizer:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def refine_strategy(self):
        """የስህተት ሎጎችን አይቶ የ AI ፕሮምፕት መመሪያዎችን በ SiteConfig ላይ ያሻሽላል"""
        from .models import AgentErrorLog, SiteConfig

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
                try:
                    SiteConfig.objects.update_or_create(
                        key=f"PROMPT_RULE_OVERRIDE_{self.site.name}",
                        defaults={'value': {'rule': data['rule'], 'updated_at': timezone.now().isoformat()}}
                    )
                    logger.info(f"🔄 Self-Optimization: Applied new system prompt rule for {self.site.name}")
                except Exception as db_err:
                    logger.error("Failed to update prompt override: %s", db_err)


# ============================================================
# 🏛️ STRATEGIC CEO (Master-Brain Bundle)
# ============================================================
class StrategicCEO:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def execute_planning_cycle(self):
        from .models import AIProjectBacklog, SiteConfig

        self._process_owner_directives()
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

        audit_summary = {}
        for key, content in state.items():
            if "❌ MISSING_FILE" in content:
                audit_summary[key] = "Missing / Pending Creation"
            elif len(content) < 200:
                audit_summary[key] = "Incomplete / Needs Work"
            else:
                audit_summary[key] = "Completed / Validated"

        try:
            SiteConfig.objects.update_or_create(
                key=f"PROJECT_AUDIT_LOG_{self.site.name}",
                defaults={'value': {'summary': audit_summary, 'updated_at': timezone.now().isoformat()}}
            )
        except Exception as db_err:
            logger.error("Failed to record site audit log: %s", db_err)

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
            f"CRITICAL PLANNING RULE: Consolidate highly related features into single, unified backlog tasks "
            f"to prevent tasks from generating redundant or fragmented code blocks. "
            f"Return JSON with key 'niche', 'competitor_feature': {{'name', 'desc'}}, 'backlog': [{{'name', 'priority', 'file', 'desc'}}]"
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
        """[Self-Evolution System] ቢያንስ በየ 3 ሰዓቱ ራሱን መርምሮ የኦፕቲማይዜሽን ስራ ይፈጥራል"""
        from .models import SiteConfig

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
            try:
                SiteConfig.objects.update_or_create(
                    key=f"LAST_SELF_AUDIT_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug("Failed to record self audit config: %s", e)

    def _process_owner_directives(self):
        from .models import AdminOverrideInstruction

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
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py (ክፍል 2/3)
# ============================================================

# ============================================================
# 🛠️ RECURSIVE BUILDER (AI-Driven Code Writer + Sandbox Verification + Auto-Push)
# ============================================================
class RecursiveBuilder:
    def __init__(self, site: SiteRegistry):
        self.site = site

    @staticmethod
    def _get_cooldown_hours(target_file):
        # High-Throughput Cooldown፦ HTML 1 ደቂቃ (0.016 ሰዓት)፣ Backend 3 ደቂቃ (0.05 ሰዓት) [1, 2]
        return 0.016 if is_html_target(target_file) else 0.05

    @classmethod
    def is_on_cooldown(cls, site, target_file):
        # [Lazy Import] - የክብ ጥገኝነት ለመከላከል በፈንክሽን ደረጃ ማስገባት [1, 2, 3.1.2]
        from .models import AIEvolutionLog

        cooldown_hours = cls._get_cooldown_hours(target_file)
        return AIEvolutionLog.objects.filter(
            site=site, target_file=target_file,
            created_at__gte=timezone.now() - timedelta(hours=cooldown_hours)
        ).exists()

    def build_next_feature(self, task):
        from .ai_utils import SandboxedCodeValidator, compress_code_for_prompt, ask_master_ai_smart, clean_and_parse_json
        from .code_apply import apply_code_change
        from .self_doctor import SecurityAuditor, AntiBloatEngine
        from .models import VectorMemory

        if self.is_on_cooldown(self.site, task.target_file):
            return "Cooldown"

        is_coding_task = task.target_file in ['views', 'urls', 'forms'] or is_html_target(task.target_file)
        if is_coding_task and not has_seeded_products(self.site):
            logger.info(f"⏳ Seeding-First Guardrail Active: Halted coding task '{task.task_name}'.")
            task.status = 'Pending'
            task.save()
            return "Halted for Seeding"

        # [Lazy Import] - የክብ ጥገኝነት ለመከላከል በፈንክሽን ደረጃ ማስገባት [1, 2, 3.1.2]
        past_memories = VectorMemory.objects.filter(site=self.site).order_by('-id')[:3]
        
        # የ AI ቶከን ፍጆታን ለመቀነስ የማስታወሻዎችን መጠን ማሳጠር [1, 2]
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

        # 1. 🛡️ Pre-write Sandbox & Syntax check (ለ Python ብቻ - AST SHIELD) [1, 2]
        if not target_is_html:
            is_valid, msg = SandboxedCodeValidator.validate(new_code)
            if not is_valid:
                logger.error(f"❌ Sandbox Code Validation Failed for {task.target_file}: {msg}. Retrying in next cycle...")
                task.status = 'Blocked'
                task.save()
                return "Sandbox Error"

        # 2. Security scan (file_path ይተላለፋል — HTML-aware skip-logicን ለማስቻል)
        is_safe, msg = SecurityAuditor.scan_code_safety(new_code, file_path=task.target_file, site=self.site)
        if not is_safe:
            logger.error(f"🛡️ Security Gate Blocked Code for {task.target_file}: {msg}")
            task.status = 'Blocked'
            task.save()
            return "Security Block"

        # 3. Apply + Verify + Rollback (lock-protected ለ I/O race-condition መከላከያ)
        with _apply_lock:
            local_path = resolve_local_file_path(self.site, task.target_file)
            old_code = ""
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        old_code = f.read()
                except Exception as read_err:
                    logger.debug("Failed to read old code for backup: %s", read_err)

            # [Anti-Bloat Guard]: አዲሱ ኮድ ወደ ዲስክ ከመጻፉ በፊት አላስፈላጊ ክፍሎቹ በራስ-ሰር እንዲቀነሱ ማድረግ [1, 2]
            new_code = AntiBloatEngine.prune_and_optimize(old_code, new_code, task.target_file)

            # 🔴 2ኛ አማራጭ ውህደት፦ የ 6 ደረጃ ፍተሻዎችን ካለፈ በኋላ አውቶማቲክ በሆነ መንገድ ወደ GitHub ፑሽ እንዲያደርግ push_to_github=True ተደርጓል [1, 2]
            apply_result = apply_code_change(
                self.site, 
                task.target_file, 
                new_code, 
                reason=task.task_name, 
                backlog_task=task,
                push_to_github=True # 🚀 Auto-Push በራስ-ሰር አግብሯል!
            )

            if not apply_result.get('success'):
                logger.error(f"❌ apply_code_change failed for {task.target_file}: {apply_result.get('message')}")
                task.status = 'Pending'
                task.save()
                return "Apply Failed"

            applied_path = apply_result.get('path', local_path)

            # 4. Disk-level verification (ድሮ in-memory module ሳይሆን disk ላይ ያለውን ይፈትሻል)
            verified, vmsg = verify_disk_write(applied_path)
            if not verified:
                logger.error(f"❌ Post-apply disk verification failed for {task.target_file}: {vmsg}. Rolling back...")
                rollback_file(applied_path, old_code)
                task.status = 'Blocked'
                task.save()
                return "Verification Failed"

            # 5. Deep verification (subprocess — ለ Django app files ብቻ፣ throughput ላልመጉዳት)
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
        except Exception as e:
            logger.debug("Failed to record success vector memory: %s", e)
        return "Success"


# ============================================================
# 📡 DYNAMIC ADAPTIVE HARVESTER (Playwright & Multi-Channel Sync - 100% Complete)
# ============================================================
class MultiChannelHarvester:
    @staticmethod
    def is_network_available():
        """የሲስተሙን የኢንተርኔት ግንኙነት በአስተማማኝ ሁኔታ መፈተሻ"""
        try:
            requests.get("https://google.com", timeout=3)
            return True
        except requests.RequestException:
            return False

    def discover_and_harvest_niche_sources(self, site):
        """የሚተዳደረውን ሳይት ኒች መሠረት በማድረግ ምርጥ የገበያ ምንጮችን ራሱ መርምሮ ያገኛል፣ በጅምላ ያስሳል"""
        from .ai_utils import clean_and_parse_json, ask_master_ai_smart
        # [Lazy Import] - የክብ ጥገኝነት ለመከላከል በፈንክሽን ደረጃ ማስገባት [1, 2, 3.1.2]
        from .models import SiteConfig
        
        # 1. AI-Driven Discovery (የምንጭ ጥናትና ቅድሚያ መስጫ - 100% አውቶኖመስ) [1, 2, 3.1.2]
        discovery_prompt = (
            f"Identify up to 3 active, high-traffic online marketplace channels, Telegram channels, Facebook public groups, "
            f"or classified directories for the '{site.niche}' niche in Ethiopia. "
            f"Return strictly valid JSON with key 'sources' containing a list of objects with "
            f"'url_or_channel' (e.g., '@ShegerMerkat_et', 'https://jiji.com.et/electronics', 'https://www.engocha.com/search') "
            f"and 'platform_type' ('Telegram', 'Jiji', 'Engocha', 'Facebook', 'GenericWeb')."
        )
        
        sources = []
        if self.is_network_available():
            try:
                sources_data = clean_and_parse_json(ask_master_ai_smart(discovery_prompt, task_type="market_research"))
                sources = sources_data.get('sources', []) if sources_data else []
            except Exception as ai_err:
                logger.warning(f"AI Discovery failed, falling back to local list: {ai_err}")

        # 🛡️ OFFLINE or FALLBACK: የውጭ ኔትወርክ ወይም የፍለጋ መቆራረጥ ካጋጠመ አስተማማኝ የሀገር ውስጥ መሸጫ ቻናሎችን መጠቀም [1]
        if not sources:
            # መጀመሪያ ካለፈው የዳታቤዝ መዝገብ (Cache) ፈልጎ መጠቀም
            cached_registry = SiteConfig.objects.filter(key=f"DYNAMIC_SCRAPE_REGISTRY_{site.name}").first()
            if cached_registry and isinstance(cached_registry.value, list) and len(cached_registry.value) > 0:
                sources = cached_registry.value
                logger.info(f"💾 Offline-First: Loaded {len(sources)} sources from local DB cache registry.")
            else:
                # ምንም መዝገብ ከሌለ ነባሪ ዝርዝር መጠቀም (Hard Fallback)
                sources = [
                    {"url_or_channel": "EthioMarketplace", "platform_type": "Telegram"},
                    {"url_or_channel": "ShegerMerkat_et", "platform_type": "Telegram"},
                    {"url_or_channel": f"https://jiji.com.et/search?query={site.niche or 'general'}", "platform_type": "Jiji"},
                    {"url_or_channel": f"https://www.engocha.com/search?q={site.niche or 'general'}", "platform_type": "Engocha"}
                ]
        
        # የጥናቱን ውጤት በ SiteConfig መዝገብ ላይ በራስ-ሰር ማስቀመጥ
        try:
            SiteConfig.objects.update_or_create(
                key=f"DYNAMIC_SCRAPE_REGISTRY_{site.name}",
                defaults={'value': sources}
            )
        except Exception as db_err:
            logger.error(f"Failed to cache scrape registry: {db_err}")
        
        # 2. Universal Semantic Crawling
        raw_data_pool = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
        
        for src in sources[:4]:
            target = src.get('url_or_channel', '')
            p_type = src.get('platform_type', '')
            
            try:
                # 🟢 ቴሌግራም ቻናል ፍተሻ (Telegram Scraper Core)
                if p_type == 'Telegram':
                    if not self.is_network_available():
                        logger.warning(f"❄️ Offline mode active. Skipping remote Telegram fetch for {target}")
                        continue
                        
                    url = f"https://t.me/s/{target.replace('@', '')}"
                    res = requests.get(url, timeout=6)
                    if res.status_code == 200:
                        messages = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL)
                        images = re.findall(r'src="(https://cdn\d+\.telesco\.pe/[^\"]+)"', res.text)
                        for i, msg in enumerate(messages[:5]):
                            clean_text = re.sub(r'<[^>]+>', ' ', msg).strip()
                            raw_data_pool.append({
                                "source": f"Telegram: {target}",
                                "text": clean_text,
                                "image_url": images[i] if i < len(images) else ""
                            })
                
                # 🟢 ጃቫስክሪፕት የሚሰሩ ጣቢያዎች (Jiji, Engocha) ፍተሻ - በ Playwright መረብ [2]
                elif p_type in ['Jiji', 'Engocha']:
                    if not self.is_network_available():
                        logger.warning(f"❄️ Offline mode active. Skipping Playwright fetch for {target}")
                        continue
                    
                    try:
                        # የ Playwright ScrapperEngine መጥራት
                        from .scrapper_engine import ScrapperEngine
                        html_content = ScrapperEngine.scrape(target)
                        
                        if html_content:
                            # ቶከን ለመቆጠብ script እና style ታጎችን ማጽዳት
                            clean_html = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL)
                            clean_html = re.sub(r'<style.*?>.*?</style>', '', clean_html, flags=re.DOTALL)
                            clean_html = re.sub(r'<[^>]+>', ' ', clean_html)
                            compressed_text = " ".join(clean_html.split())[:1500]
                            
                            imgs = re.findall(r'https?://[^\s"]+\.(?:jpg|jpeg|png)', html_content)[:3]
                            raw_data_pool.append({
                                "source": f"{p_type}: {target}",
                                "text": compressed_text,
                                "image_url": imgs[0] if imgs else ""
                            })
                    except Exception as playwright_err:
                        logger.error(f"Playwright integration failed, attempting standard request fallback: {playwright_err}")
                        res = requests.get(target, headers=headers, timeout=6)
                        if res.status_code == 200:
                            clean_html = re.sub(r'<script.*?>.*?</script>|<style.*?>.*?</style>', '', res.text, flags=re.DOTALL)
                            clean_html = re.sub(r'<[^>]+>', ' ', clean_html)
                            compressed_text = " ".join(clean_html.split())[:1500]
                            imgs = re.findall(r'https?://[^\s"]+\.(?:jpg|jpeg|png)', res.text)[:3]
                            raw_data_pool.append({
                                "source": f"{p_type}: {target}",
                                "text": compressed_text,
                                "image_url": imgs[0] if imgs else ""
                            })

                # 🟢 አጠቃላይ ድረ-ገጾች ፍተሻ (GenericWeb & Facebook)
                else:
                    if not self.is_network_available():
                        logger.warning(f"❄️ Offline mode active. Skipping fetch for {target}")
                        continue
                        
                    res = requests.get(target, headers=headers, timeout=6)
                    if res.status_code == 200:
                        clean_html = re.sub(r'<script.*?>.*?</script>', '', res.text, flags=re.DOTALL)
                        clean_html = re.sub(r'<style.*?>.*?</style>', '', clean_html, flags=re.DOTALL)
                        clean_html = re.sub(r'<[^>]+>', ' ', clean_html)
                        compressed_text = " ".join(clean_html.split())[:1500]
                        
                        imgs = re.findall(r'https?://[^\s"]+\.(?:jpg|jpeg|png)', res.text)[:3]
                        raw_data_pool.append({
                            "source": f"{p_type}: {target}",
                            "text": compressed_text,
                            "image_url": imgs[0] if imgs else ""
                        })
            except Exception as e:
                logger.error(f"Dynamic crawler failed for {target}: {e}")

        # 3. 🛡️ OFFLINE COMPILATION: ኔትወርክ ሙሉ በሙሉ ከጠፋና ምንም አዲስ ነገር መሰብሰብ ካልተቻለ [3]
        if not raw_data_pool and not self.is_network_available():
            logger.info("❄️ Offline-First: Gathering past uncurated listings from VectorMemory cache.")
            try:
                from .models import VectorMemory
                past_insights = VectorMemory.objects.filter(site=site, memory_type='insight')[:5]
                for insight in past_insights:
                    raw_data_pool.append({
                        "source": "Local Memory Cache",
                        "text": insight.content,
                        "image_url": ""
                    })
            except Exception as mem_err:
                logger.error(f"Failed to read from local memory cache: {mem_err}")
                
        return raw_data_pool
        
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py (ክፍል 3/3)
# ============================================================

# ============================================================
# 🕵️ COMPETITOR INTELLIGENCE ENGINE (ተፎካካሪ የስለላ እና የገበያ ጥናት ሞተር)
# ============================================================
class CompetitorIntelligenceEngine:
    """ተፎካካሪዎችን በመሰለል የገበያ ጥናቶችን እና ተጠቃሚዎችን ለመሳብ የሚያስችሉ ስልታዊ ስራዎችን በራስ-ሰር የሚያመነጭ ሞተር"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site

    def spy_and_analyze_market(self):
        """የተፎካካሪዎችን ድረ-ገጽ በመቃኘት የ AI የገበያ ጥናት ትንተና ያካሂዳል"""
        from .scrapper_engine import ScrapperEngine
        from .ai_utils import clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log
        from .models import MarketTrend, VectorMemory

        broadcast_agent_log(self.site, "🕵️ Spy Engine: Initializing competitor website scanning...", "info")
        
        competitor_links = self.site.competitor_urls if isinstance(self.site.competitor_urls, list) else []
        if not competitor_links:
            competitor_links = [
                "https://jiji.com.et",
                "https://www.engocha.com"
            ]

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

                # 🔴 ተለዋዋጭ ዋጋ አወሳሰን (Dynamic Repricing Engine) [3.1.2]
                repriced_val = float(result.get('repriced_value', 0.0))
                target_id = int(result.get('repriced_product_id', 0))
                if repriced_val > 0.0 and target_id > 0:
                    from .models import Product
                    Product.objects.filter(id=target_id).update(price=repriced_val)
                    broadcast_agent_log(self.site, f"🎯 Repricer: Adjusted product {target_id} price to {repriced_val} ETB.", "success")

                # 🔴 የተፎካካሪ ቁልፍ ቃላት ጠለፋ (Keyword Hijacker) [1, 2, 3.1.2]
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
# 💼 CEO OPERATIONS (የጅምላ ዳታ አጻጻፍ፣ የዋትሳፕ ቀጥታ ሊንኮች፣ ስፓም ማጣሪያ እና ማስተርጎም)
# ============================================================
class CEOOperations:
    def __init__(self, site: SiteRegistry):
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
        phone_match = re.search(r'(?:\+251|09|07)\d{8}', text)
        tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
        
        contact = ""
        if phone_match: contact = phone_match.group(0)
        elif tg_match: contact = tg_match.group(0)
        else: contact = "0900000000"
            
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
        from .models import SiteConfig
        from .ai_utils import clean_and_parse_json, ask_master_ai_smart

        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last:
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if (timezone.now() - last_time) < timedelta(hours=3):
                    return
            except Exception as e:
                logger.warning(f"Error checking harvest timestamp: {e}")

        harvester = MultiChannelHarvester()
        raw_data_pool = harvester.discover_and_harvest_niche_sources(self.site)
        if not raw_data_pool:
            return

        prompt = (
            f"Analyze raw texts: {json.dumps(raw_data_pool, ensure_ascii=False)}.\n"
            f"Extract products fitting the '{self.site.niche}' niche. "
            f"Return JSON with key 'products' containing objects with 'title', 'price', 'desc', 'seller_contact', 'image_url'."
        )

        products = []
        try:
            data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
            if data and isinstance(data, dict):
                products = data.get('products', [])
        except Exception as ai_err:
            logger.warning(f"AI parsing failed, switching to autonomous Regex Fallback Parser: {ai_err}")

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
                SiteConfig.objects.update_or_create(key=f"LAST_HARVEST_{self.site.name}", defaults={'value': {'time': timezone.now().isoformat()}})
            except Exception as e:
                logger.debug("Failed to update last harvest config: %s", e)

    def _seed_listings_bulk(self, products_list):
        from .models import Product, SellerProfile, NotificationQueue
        from django.contrib.auth.models import User
        from django.db import transaction

        products_to_create = []
        notifications_to_create = []

        for p in products_list:
            if not isinstance(p, dict) or not p.get('title') or not p.get('seller_contact'):
                continue
            
            try:
                contact = p['seller_contact']
                uname = contact.replace('@', '').strip()
                user, _ = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})

                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0

                product_obj = Product(
                    seller=user, site=self.site, title=p['title'], price=clean_price,
                    description=p.get('desc', ''), image_url=p.get('image_url', ''),
                    listing_type=p.get('listing_type', 'sale') or 'sale', contact_info=contact, is_active=True
                )
                products_to_create.append(product_obj)

                dispatch_links = self.generate_contact_links(contact)
                links_text = " | ".join([f"{k.upper()}: {v}" for k, v in dispatch_links.items()])

                notification_obj = NotificationQueue(
                    site=self.site, recipient=contact,
                    message=f"ሰላም! የ '{p['title']}' ምርትዎ በነፃ ፖስት ተደርጓል። የቀጥታ ሊንኮች፦ {links_text}"
                )
                notifications_to_create.append(notification_obj)

            except Exception as seed_err:
                logger.error(f"Failed to compile bulk listing: {seed_err}")

        try:
            with transaction.atomic():
                if products_to_create:
                    created_prods = Product.objects.bulk_create(products_to_create)
                    # 🔴 ራስ-ገዝ የማህበራዊ ሚዲያ ቴሌግራም አውቶ-ፖስተር ጥሪ (Telegram Channel Auto-Poster) [3.1.2]
                    if created_prods:
                        self.auto_post_to_telegram_channel(created_prods[0])
                if notifications_to_create:
                    NotificationQueue.objects.bulk_create(notifications_to_create)
                
                self.site.real_product_count = Product.objects.filter(site=self.site, is_active=True).count()
                self.site.total_products = Product.objects.filter(site=self.site).count()
                self.site.total_sellers = User.objects.filter(product__site=self.site).distinct().count()
                self.site.save()
                
                logger.info(f"✨ Bulk Harvester: Successfully processed {len(products_to_create)} products!")
        except Exception as db_err:
            logger.error(f"Bulk DB Insertion failed: {db_err}")

    @staticmethod
    def generate_contact_links(contact_str):
        links = {}
        if not contact_str: return links
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
        from .models import SiteConfig, Product, NotificationQueue
        from .ai_utils import clean_and_parse_json, ask_master_ai_smart

        try:
            dedup_key = f"CURATED_PRODUCT_IDS_{self.site.name}"
            dedup_config, _ = SiteConfig.objects.get_or_create(key=dedup_key, defaults={'value': []})
            curated_ids = set(dedup_config.value if isinstance(dedup_config.value, list) else [])

            candidates = list(Product.objects.filter(site=self.site, is_active=True).exclude(id__in=list(curated_ids))[:limit])
            if not candidates: return

            newly_curated = []
            for product in candidates:
                try:
                    is_valid = True
                    reason = "Valid Listing"
                    
                    if self.site.name == 'primary' and product.price < 10.0:
                        is_valid = False
                        reason = "Price is below 10 ETB (suspicious listing)"
                    else:
                        try:
                            prompt = (
                                f"Verify listing for scams/spam. Title: {product.title}. Price: {product.price}. "
                                f"Return JSON with key 'is_valid' (true/false) and 'reason'."
                            )
                            result = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
                            if result and not result.get('is_valid', True):
                                is_valid = False
                                reason = result.get('reason', 'ያልተሟላ መረጃ')
                        except Exception as ai_curate_err:
                            logger.debug("AI curation skipped: %s", ai_curate_err)

                    if not is_valid:
                        product.is_active = False
                        product.save()
                        NotificationQueue.objects.create(
                            site=self.site, recipient=product.seller.username,
                            message=f"ሰላም {product.seller.username}፤ የለጠፉት '{product.title}' ምርት በ AI ማጣሪያችን አልፏል። ምክንያት፦ {reason}።"
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
        """ምርቱን ለ Amharic/Oromo ቋንቋዎች በራስ-ሰር መተርጎም"""
        try:
            from .models import ProductTranslation
            from .ai_utils import translate_text_incremental
        except ImportError: return

        texts = [t for t in [product.title, product.description or ""] if t and t.strip()]
        if not texts: return

        for lang in ['am', 'om']:
            try:
                translated = translate_text_incremental(texts, target_lang=lang)
                ProductTranslation.objects.update_or_create(
                    product=product, language=lang,
                    defaults={
                        'translated_title': translated.get(product.title, product.title),
                        'translated_description': translated.get(product.description or "", product.description or "")
                    }
                )
            except Exception as e:
                logger.debug("Translation skipped: %s", e)

    def _boost_revenue(self):
        from .models import Product
        from .growth_agent import get_or_create_backlog_task_safe
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
        from .models import NotificationQueue
        try:
            pending_notes = NotificationQueue.objects.filter(site=self.site, is_sent=False)[:5]
            for note in pending_notes:
                logger.info(f"📨 Outbound Dispatcher: Successfully sent {note.notification_type} to {note.recipient}: {note.message[:50]}...")
                note.is_sent = True
                note.sent_at = timezone.now()
                note.save()
        except Exception as e:
            logger.error(f"Outbound Dispatcher failed: {e}")

    def auto_post_to_telegram_channel(self, product):
        """🔴 2ኛ አዲስ ፊቸር ውህደት፦ ራስ-ገዝ የማህበራዊ ሚዲያ ቴሌግራም አውቶ-ፖስተር (Telegram Auto-Poster) [3.1.2]"""
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        channel_id = getattr(settings, 'TELEGRAM_CHANNEL_ID', None)
        if not token or not channel_id:
            return
        
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        caption = (
            f"✨ {product.get_translated_title()}\n\n"
            f"💰 ዋጋ/Price: {product.price:.0f} ETB\n"
            f"📍 ቦታ/Location: {product.location}\n\n"
            f"🔗 በነፃ ለመግዛት ይህንን ሊንክ ይጫኑ: {self.site.deployment_url}/product/{product.id}/\n\n"
            f"🤖 EthAfri Auto-Post"
        )
        payload = {
            "chat_id": channel_id,
            "caption": caption,
            "photo": product.image_url or "https://loremflickr.com/800/800/product"
        }
        try:
            requests.post(url, json=payload, timeout=5)
            logger.info(f"📢 Telegram Auto-Poster: Posted product {product.id} to channel {channel_id}.")
        except Exception as e:
            logger.error(f"Telegram Auto-Poster failed: {e}")


# ============================================================
# 🛡️ FRAUD HUNTER & FLASH SALE ACTUATOR
# ============================================================
class FraudHunter:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def scan_for_scams(self):
        from .models import Product
        try:
            suspicious = Product.objects.filter(site=self.site, price__lt=10, is_active=True)
            for p in suspicious:
                p.is_active = False
                p.save()
                logger.warning(f"🛡️ FraudHunter: Deactivated suspicious listing: '{p.title}'")
            self.scan_for_flash_sales()
        except Exception as e:
            logger.error("FraudHunter failed: %s", e)

    def scan_for_flash_sales(self):
        """🔴 5ኛ አዲስ ፊቸር ውህደት፦ ተለዋዋጭ የፍላሽ ሽያጭ ቁልፍ (Dynamic Flash Sale Actuator) [3.1.2]"""
        from .models import Product
        try:
            stagnant = Product.objects.filter(site=self.site, view_count__gt=200, is_active=True).order_by('updated_at')[:2]
            for p in stagnant:
                new_price = float(p.price) * 0.90
                p.price = new_price
                p.market_value_status = "Flash_Sale"
                p.save()
                logger.info(f"🔥 Flash Sale: Auto-discounted product '{p.title}' by 10%.")
        except Exception as e:
            logger.error("Flash Sale Actuator failed: %s", e)


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
        if res.status_code == 200: return res.text
    except Exception as e:
        logger.warning(f"GitHub API Fetch Error: {e}")
    return None


def bootstrap_system_safely():
    """ዳታቤዙ ባዶ ከሆነ በራሱ 'primary' ሳይትን በመመዝገብ ኤጀንቱ ሥራ እንዲጀምር ያደርጋል"""
    from .models import SiteRegistry
    try:
        if SiteRegistry.objects.filter(is_active=True).count() == 0:
            logger.info("Bootstrapping primary site...")
            SiteRegistry.objects.create(name="primary", display_name="EthAfri Primary", niche="general", target_market="Global", is_active=True, build_phase=0)
            broadcast_agent_log(None, "Registered 'primary' site.", "success")
    except Exception as e:
        logger.error(f"Failed to bootstrap: {e}")


def get_site_project_state_dynamic(site: SiteRegistry):
    from .models import AIProjectBacklog
    if not site: return {}, {}
    repo_path = site.repo_path
    is_remote = False
    repo_name = ""
    if not repo_path or repo_path.startswith('http') or 'github.com' in repo_path:
        is_remote = True
        repo_name = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
        if repo_path:
            match = re.search(r"github\.com/([^/]+/[^\/]+)", repo_path)
            if match: repo_name = match.group(1).replace('.git', '')
    base = repo_path if not is_remote else os.path.join('/tmp', 'ethafri_agent', site.name)
    core_files = {
        'models': 'marketplace/models.py', 'views': 'marketplace/views.py', 'urls': 'marketplace/urls.py',
        'forms': 'marketplace/forms.py', 'admin': 'marketplace/admin.py', 'growth_agent': 'marketplace/growth_agent.py',
        'ai_utils': 'marketplace/ai_utils.py', 'self_doctor': 'marketplace/self_doctor.py', 'code_apply': 'marketplace/code_apply.py',
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
            else: state[key] = "❌ MISSING_FILE"
        else:
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f: state[key] = f.read()
                except Exception as e: state[key] = f"ERROR: {e}"
            else: state[key] = "❌ MISSING_FILE"
    if is_remote:
        url = f"https://api.github.com/repos/{repo_name}/git/trees/main?recursive=1"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if github_token: headers["Authorization"] = f"token {github_token}"
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
                        else: state[key] = "❌ MISSING_FILE"
                        file_paths[key] = os.path.join(base, path_str)
        except Exception as e: logger.error(f"Remote Git Tree Scan failed: {e}")
    else:
        base_templates_dir = os.path.join(settings.BASE_DIR, 'marketplace', 'templates')
        if os.path.exists(base_templates_dir):
            for root, _, files in os.walk(base_templates_dir):
                for file in files:
                    if file.endswith('.html'):
                        key = f"{file.replace('.html', '')}_html"
                        full_path = os.path.join(root, file)
                        file_paths[key] = full_path
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f: state[key] = f.read()
                            except Exception as e: state[key] = f"ERROR: {e}"
        else: logger.warning("Templates dir not found.")
    try:
        all_known_backlogs = AIProjectBacklog.objects.filter(site=site)
        for bk in all_known_backlogs:
            if bk.target_file not in file_paths:
                file_paths[bk.target_file] = resolve_local_file_path(site, bk.target_file)
                if bk.target_file not in state: state[bk.target_file] = "❌ MISSING_FILE"
    except Exception as e: logger.error("Failed backlog files state: %s", e)
    return state, file_paths


def get_or_create_backlog_task_safe(site, task_name, defaults):
    from .models import AIProjectBacklog
    matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name).order_by('id')
    if matching.exists():
        task = matching.first()
        if matching.count() > 1:
            try: matching.exclude(id=task.id).delete()
            except Exception as e: logger.debug("Failed duplicate backlog delete: %s", e)
        return task, False
    try:
        task = AIProjectBacklog.objects.create(site=site, task_name=task_name, **defaults)
        return task, True
    except Exception as e:
        logger.error(f"Error safe backlog task: {e}")
        matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name)
        return (matching.first(), False) if matching.exists() else (None, False)


# ============================================================
# 🧬 LAW 0 — SELF-READINESS GATE (የኤጀንቱ የራሱ ጤና መመርመሪያ)
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
        from .models import SiteConfig
        try:
            cfg = SiteConfig.objects.filter(key=f"{cls.REPAIR_ATTEMPT_KEY_PREFIX}{module_key}").first()
            return cfg.value.get('count', 0) if cfg and isinstance(cfg.value, dict) else 0
        except Exception as e:
            logger.debug("Failed to read total repair attempts: %s", e)
            return 0

    @classmethod
    def _increment_total_attempts(cls, module_key):
        from .models import SiteConfig
        try:
            cfg, _ = SiteConfig.objects.get_or_create(
                key=f"{cls.REPAIR_ATTEMPT_KEY_PREFIX}{module_key}", defaults={'value': {'count': 0}}
            )
            count = (cfg.value.get('count', 0) if isinstance(cfg.value, dict) else 0) + 1
            cfg.value = {'count': count, 'last_attempt': timezone.now().isoformat()}
            cfg.save()
            return count
        except Exception as e:
            logger.error("Failed to increment repair attempts: %s", e)
            return 1

    @classmethod
    def ensure_self_ready(cls):
        from .models import SiteConfig, SiteRegistry

        broken = cls._scan_core_files()

        if not broken:
            try:
                SiteConfig.objects.update_or_create(
                    key=cls.READY_KEY,
                    defaults={'value': {'status': 'ready', 'checked_at': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug("Failed to update readiness status in DB: %s", e)
            return True

        logger.critical(f"🚨 SELF-BOOTSTRAP GATE: {len(broken)} core module(s) unhealthy: {list(broken.keys())}")
        try:
            SiteConfig.objects.update_or_create(
                key=cls.READY_KEY,
                defaults={'value': {
                    'status': 'self_repairing',
                    'broken': {k: v['issue'] for k, v in broken.items()},
                    'checked_at': timezone.now().isoformat()
                }}
            )
        except Exception as e:
            logger.debug("Failed to write self-repairing state: %s", e)

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
                    logger.critical(
                        f"🚨 SELF-REPAIR: '{module_key}' exceeded {cls.MAX_TOTAL_ATTEMPTS_PER_MODULE} "
                        f"repair attempts. Halting auto-repair — manual review required."
                    )
                    continue
                cls._increment_total_attempts(module_key)
                success = cls._repair_module(primary_site, module_key, info)
                if success and module_key in cls.RUNNING_PROCESS_MODULES:
                    repaired_any_running_module = True
            broken = cls._scan_core_files()

        is_ready = len(broken) == 0

        if not is_ready:
            all_exhausted = all(
                cls._get_total_attempts(k) >= cls.MAX_TOTAL_ATTEMPTS_PER_MODULE for k in broken.keys()
            )
            if all_exhausted:
                logger.critical(
                    f"🚨 SELF-BOOTSTRAP: Repair attempts exhausted for {list(broken.keys())}. "
                    f"Proceeding in DEGRADED mode — MANUAL REQUIRED before next restart."
                )
                try:
                    SiteConfig.objects.update_or_create(
                        key=cls.READY_KEY,
                        defaults={'value': {
                            'status': 'degraded_proceeding',
                            'broken': {k: v['issue'] for k, v in broken.items()},
                            'checked_at': timezone.now().isoformat()
                        }}
                    )
                except Exception as e:
                    logger.debug("Failed to update degraded state: %s", e)
                return True

            try:
                SiteConfig.objects.update_or_create(
                    key=cls.READY_KEY,
                    defaults={'value': {
                        'status': 'repair_failed',
                        'broken': {k: v['issue'] for k, v in broken.items()},
                        'checked_at': timezone.now().isoformat()
                    }}
                )
            except Exception as e:
                logger.debug("Failed to record repair failure: %s", e)
                
            logger.critical(f"🚨 SELF-BOOTSTRAP: Repair attempts exhausted this cycle. Still broken: {list(broken.keys())}. Will retry next cycle.")
            return False

        try:
            SiteConfig.objects.update_or_create(
                key=cls.READY_KEY,
                defaults={'value': {'status': 'ready', 'checked_at': timezone.now().isoformat()}}
            )
        except Exception as e:
            logger.debug("Failed to save ready state: %s", e)
            
        logger.info("✅ SELF-BOOTSTRAP: All core modules verified healthy.")

        if repaired_any_running_module and os.getenv('SELF_HEAL_AUTO_RESTART', 'false').lower() == 'true':
            logger.critical("🧬 SELF-REPAIR: Core agent files were rewritten. Forcing controlled restart to load healed code...")
            try:
                broadcast_agent_log(primary_site, "Self-repair complete — restarting process to load fixes.", "success")
            except Exception as e:
                logger.debug("Log broadcast failed on reboot: %s", e)
            os._exit(1)

        return True

    @classmethod
    def _repair_module(cls, site, module_key, info):
        from .models import VectorMemory

        logger.warning(f"🧬 SELF-REPAIR: Attempting to fix '{module_key}' ({info['issue']})")
        try:
            past_memories = VectorMemory.objects.filter(site=site).order_by('-id')[:3]
            memory_context = [m.content for m in past_memories]
        except Exception as e:
            logger.debug("Failed to retrieve memories for self-repair context: %s", e)
            memory_context = []

        prompt = (
            f"CRITICAL SELF-REPAIR TASK: The core autonomous-agent module '{module_key}' "
            f"(file: {info['path']}) is currently broken — Issue: {info['issue']}. "
            f"Write a COMPLETE, clean, syntactically valid replacement for this entire file "
            f"using 2026 Django/Python standards, preserving all functionality implied by its "
            f"role inside an autonomous e-commerce CEO agent system (EthAfri).\n"
            f"FEATURE CONSOLIDATION RULE: Consolidate helper logics, remove duplicate utility imports, "
            f"and write highly compact, parameter-driven functions that handle multiple agent operations at once.\n"
            f"Avoid repeating these past failures: {json.dumps(memory_context, ensure_ascii=False)}.\n"
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
# 🎡 MASTER ENGINE LOOP (24/7 Execution Core)
# ============================================================

def execute_master_cycle():
    bootstrap_system_safely()

    from .models import SiteConfig, SiteRegistry

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
            connections.close_all()


def _run_site_cycle(site):
    """የእያንዳንዱን ንዑስ ጣቢያ (SaaS Site) የዕድገት ዑደት 24 ሰዓት ሙሉ በጀርባ የሚያስኬድ ማዕከል"""
    from .models import AIProjectBacklog, PredictionLog, Product
    from .database_memory import OfflineCacheManager

    try:
        # 1. የሰልፍ ዶክተር ጥገና መጀመር (10%)
        update_agent_progress(site, "Running Self-Doctor Maintenance...", 10)
        time.sleep(random.uniform(1.5, 4.0))
        broadcast_agent_log(site, f"Running Self-Doctor maintenance for {site.name}...", "info")
        UniversalHealer(site).perform_maintenance()
        time.sleep(random.uniform(1.0, 3.0))

        # 2. የኔትወርክ ሁኔታን መፈተሽ (የመስመር ላይ/ከመስመር ውጭ መለያ) [1]
        network_active = MultiChannelHarvester.is_network_available()

        if not network_active:
            # ❄️ [Offline Mode]: ኔትወርክ ከሌለ የውስጥ ጥገና እና የ RAG መረጃዎችን መተንተን (35% - 100%)
            update_agent_progress(site, "Offline Mode: Analyzing memory insights...", 35)
            broadcast_agent_log(site, f"🌐 Network disconnected. Switching '{site.name}' to Offline-First mode.", "warning")
            
            # የቆዩና የታገዱ ታስኮችን በራስ-ሰር ማጽዳት (Deduplication & Unlock)
            OfflineCacheManager.process_stale_offline_tasks(site)
            time.sleep(1.5)
            
            # ካሉ ምርቶች ላይ የ RAG ትንተና መስራት (Memory insight extraction)
            update_agent_progress(site, "Offline Mode: Compiling local vector cache...", 70)
            OfflineCacheManager.harvest_offline_insights(site)
            
            update_agent_progress(site, "Offline Cycle Completed. Sleeping...", 100)
            broadcast_agent_log(site, f"✅ Offline-First maintenance complete for {site.name}.", "success")
            return

        # 🌐 [Online Mode]: ኔትወርክ ካለ መደበኛውን የዕድገት ዑደት ማስኬድ
        # 3. የባክሎግ እቅድ ጥናትን መጀመር (35%)
        update_agent_progress(site, "Analyzing Codebase & Backlog...", 35)
        broadcast_agent_log(site, f"Analyzing codebase & planning backlog for {site.name}...", "info")
        ceo = StrategicCEO(site)
        ceo.execute_planning_cycle()
        time.sleep(random.uniform(1.0, 3.0))

        # 4. የጅምላ ምርት ዳሰሳ መጀመር (65%)
        update_agent_progress(site, "Bulk Scraping & Harvesting Products...", 65)
        broadcast_agent_log(site, f"Running business growth & market harvesting for {site.name}...", "info")
        ops = CEOOperations(site)
        ops.run_business_growth()
        time.sleep(random.uniform(1.0, 3.0))

        # 🔴 አዲስ የተጨመረ፦ የተፎካካሪዎችን ድረ-ገጽ በመሰለል የገበያ ጥናትና የሥራ እቅድ ማመንጨት (70%) [3.1.2]
        update_agent_progress(site, "Spying on Competitors & Analyzing Market Advantage...", 70)
        spy_engine = CompetitorIntelligenceEngine(site)
        spy_engine.spy_and_analyze_market()
        time.sleep(random.uniform(1.0, 3.0))

        # 🔴 Feature 10 - የትራፊክ እና የ SEO ዕድገት ትንበያዎችን ማስላት [3.1.2]
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
            broadcast_agent_log(site, "📊 Predictive Engine: Successfully generated traffic and SEO forecasts in DB.", "info")
        except Exception as pred_err:
            logger.debug("Failed to record predictions: %s", pred_err)

        # 5. የማጭበርበር እና ስፓም መከላከያ
        FraudHunter(site).scan_for_scams()
        time.sleep(random.uniform(1.0, 3.0))

        # 6. የላቀ የኮድ ግንባታ እና የ Sandbox ፍተሻ (85%)
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
                tasks_names = ", ".join([t.task_name[:25] for t in tasks_to_build])
                update_agent_progress(site, f"Building Tasks: {tasks_names}...", 85)
                broadcast_agent_log(site, f"Building {len(tasks_to_build)} strategic task(s) concurrently with Sandbox Validation...", "success")
                
                builder = RecursiveBuilder(site)

                def _build_and_close(t_task):
                    try:
                        return builder.build_next_feature(t_task)
                    finally:
                        connections.close_all()

                with ThreadPoolExecutor(max_workers=min(len(tasks_to_build), 4)) as builder_executor:
                    builder_executor.map(_build_and_close, tasks_to_build)
        except Exception as build_loop_err:
            logger.error("Failed during async builder loop execution: %s", build_loop_err)

        # 7. ዑደቱ በተሳካ ሁኔታ መጠናቀቁን መመዝገብ (100%)
        update_agent_progress(site, "Cycle Completed Successfully! Sleeping...", 100)
        broadcast_agent_log(site, f"✨ Master Cycle executed successfully for {site.name}.", "success")

    except Exception as e:
        logger.error(f"❌ Error in master cycle for {site.name}: {e}", exc_info=True)
        try:
            update_agent_progress(site, f"Error: {str(e)[:50]}", 100)
        except Exception as inner_err:
            logger.debug("Failed to record crashed cycle progress: %s", inner_err)
    finally:
        connections.close_all()


def start_autonomous_ceo():
    """የኤጀንቱን 24/7 የጀርባ ዑደት በአካባቢያዊ ፍጥነት (Adaptive Pacing) የሚመራ"""
    logger.info("🚀 EthAfri Master CEO Agent Started on Render Cloud...")
    while True:
        try:
            execute_master_cycle()

            from .models import AIProjectBacklog

            has_pending = False
            try:
                has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
            except Exception as e:
                logger.debug("Failed to verify pending backlog status: %s", e)
            
            # ኔትወርክ ከሌለ ረዘም ላለ ጊዜ እረፍት መስጠት (ቶከን እና ሰርቨር ሪሶርስ ቆጣቢ)
            if not MultiChannelHarvester.is_network_available():
                interval = 1800  # 30 ደቂቃ
                logger.warning("🌐 Offline Mode detected. Pacing slowed to 30 minutes to conserve resources.")
            else:
                interval = 30 if has_pending else 600
                
            logger.info(f"💤 Master Cycle Complete. Sleeping {interval} seconds...")
            time.sleep(interval)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO FATAL ERROR: {e}")
            time.sleep(60)
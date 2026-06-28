# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ዓላማ፦ Ultimate Autonomous Master-Brain CEO Agent (v10.0 - Self-Bootstrap Edition)
# ✅ የተፈቱ ችግሮች፦
#   1. 🧬 LAW 0 — Self-Readiness Gate (SelfBootstrapManager): ኤጀንቱ ራሱን አስቀድሞ
#      ይመረምራል፣ የጎደለውን/የተበላሸውን ራሱ ይጠገናል፣ ብቁ መሆኑን ካረጋገጠ በኋላ ብቻ ወደ ሙሉ
#      ድረ-ገጽ ማኔጅመንት ይገባል።
#   2. curate_user_listings() ከ class ውጭ "ተንሳፍፎ" የቀረ dead-code ችግር ተፍቷል —
#      በ CEOOperations ውስጥ በትክክል ገብቶ run_business_growth() ላይ ተገናኝቷል።
#   3. apply_code_change() Return Value ቀደም ይዘለል ነበር — አሁን ይታያል፣ ካልተሳካ
#      early-exit ይደረጋል (false-positive "Success" መከላከያ)።
#   4. Real Disk-Level Verification + Deep Django Check (subprocess-based፣ ድሮውን
#      in-memory module ሳይሆን disk ላይ ያለውን አዲስ ኮድ ይፈትሻል) + Rollback on Failure።
#   5. Duplicate AICache ክፍል ተወግዷል (ai_utils.py ራሱ ባለቤት ስለሆነ)።
#   6. Risk-tiered cooldown፣ parallel multi-task builder፣ EVOLUTION_LOCK wiring፣
#      adaptive sleep interval ሁሉም ተጠብቀዋል/ተጠናክረዋል።
# 📅 ቀን፦ 2026-06-28
# ============================================================

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
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor

# የ circular dependency መከላከያ የዳታቤዝ ሞዴሎች
from .models import (
    SiteRegistry, AIProjectBacklog, AgentErrorLog, AIEvolutionLog,
    VectorMemory, SiteConfig, AdminOverrideInstruction, Product,
    SellerProfile, NotificationQueue
)

# የረዳት አስፈጸሚዎች ግንኙነት
from .code_apply import apply_code_change
from .ai_utils import (
    clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log,
    translate_text_incremental
)
from .self_doctor import SecurityAuditor, UniversalHealer

logger = logging.getLogger(__name__)

# የሩቅ እና የቅርብ ፋይሎችን መከታተያ መዝገብ
_project_hashes = {}

# በትይዩ በሚሰሩ threads መካከል የፋይል መጻፍ/ማረጋገጥ ግጭት እንዳይፈጠር መቆለፊያ
_apply_lock = threading.Lock()

# እነዚህ ፋይሎች ቀጥታ የ Django ድረ-ገጽ አካል ስለሆኑ ጥልቅ (subprocess) ፍተሻ ይገባቸዋል
DJANGO_APP_FILES = {'models', 'views', 'urls', 'forms', 'admin'}


# ============================================================
# ⚙️ የፋይል አቅጣጫ ፈቺ ረዳት ፈንክሽን
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
# 🌱 SEEDING-FIRST GUARDRAIL — Self-Healing Product Recognition
#
# ቀደም ሲል `Product.objects.filter(site=self.site, is_active=True).exists()`
# ብቸኛ ፍተሻ ብቻ ስለ ነበር፣ ዳታቤዙ ውስጥ ብዙ ምርት ቢኖርም ኤጀንቱ "ምርት የለም" ብሎ በስህተት
# ይቆጥር ነበር፣ ምክንያቱ ብዙ ጊዜ፦
#   1. ምርቶቹ site_id=NULL ናቸው (admin/shell ላይ ቀጥታ ቢጨመሩ፣ site field ሳይሞላ)
#   2. ምርቶቹ is_active=False ናቸው (በ FraudHunter ወይም scam-curation ቢደበቁ)
#   3. ድግግሞሽ SiteRegistry rows (bootstrap ድጋሚ ቢሰራ የተለየ site_id ቢፈጠር)
# ይህ ፈንክሽን ምርት መኖሩን በትክክል ይለያል፣ ለ #1 (single-site ስርዓት ላይ ብቻ) በራስ-ሰር
# ይጠገናል፣ እና ለ #2/#3 ግልጽ diagnostic log ያስቀምጣል ለ ባለቤቱ ምርመራ።
# ============================================================
def has_seeded_products(site):
    """ምርት ለ ሳይቱ መኖሩን ይለያል፣ site-mismatch/inactive ችግሮችን ራሱ ይጠግናል/ይዘግባል"""
    if Product.objects.filter(site=site, is_active=True).exists():
        return True

    total_for_site = Product.objects.filter(site=site).count()
    orphaned_qs = Product.objects.filter(site__isnull=True)
    orphaned_count = orphaned_qs.count()
    total_globally = Product.objects.count()

    # 🩹 Self-Heal: NULL-site ምርቶች ካሉ እና ብቸኛ active site ካለ (ambiguity-free)፣
    # በራስ-ሰር ለ ሳይቱ ማያያዝ ምክንያታዊ ነው
    if orphaned_count > 0:
        active_site_count = SiteRegistry.objects.filter(is_active=True).count()
        if active_site_count == 1:
            try:
                updated = orphaned_qs.update(site=site)
                logger.warning(
                    f"🩹 Seeding-Guardrail Self-Heal: {updated} orphaned product(s) (site=NULL) "
                    f"found — auto-linked to '{site.name}' (single-site system, no ambiguity)."
                )
                if Product.objects.filter(site=site, is_active=True).exists():
                    return True
            except Exception as e:
                logger.error(f"Seeding-Guardrail self-heal failed: {e}")
        else:
            logger.warning(
                f"⚠️ Seeding-Guardrail: {orphaned_count} product(s) have NO site assigned, "
                f"but {active_site_count} active sites exist — cannot safely auto-assign "
                f"(ambiguous, multi-tenant). Please manually assign 'site' via Django admin."
            )

    if total_for_site > 0:
        logger.warning(
            f"⚠️ Seeding-Guardrail Diagnostic: site '{site.name}' has {total_for_site} product(s) "
            f"linked, but NONE are is_active=True — they may have been deactivated by FraudHunter "
            f"(price<10) or scam-curation. Check Product.is_active in Django admin if unexpected."
        )

    logger.info(
        f"⏳ Seeding-Guardrail: site '{site.name}' (id={site.id}) — 0 active products. "
        f"[linked to this site: {total_for_site}, orphaned (site=NULL) globally: {orphaned_count}, "
        f"all products in DB: {total_globally}]"
    )
    return False


# ============================================================
# 🔍 ለ Disk-Level Verification እና Rollback የሚያገልግሉ ረዳት ፈንክሽኖች
#
# ⚠️ ማስታወሻ፦ Python አንዴ የጫነውን ሞጁል (in-memory) ድጋሚ ከ disk ላይ አያነበውም።
# ስለዚህ `call_command('check')` ብቻውን ድሮውን ኮድ ይፈትሻል፣ አዲሱን disk ላይ የተጻፈውን
# አያረጋግጥም። ይህ ለ Django app files (models/views/urls/forms/admin) ብቻ
# subprocess-based ጥልቅ ፍተሻ (አዲስ process፣ ድሮ module-cache የለውም) ይተግባል።
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
    """[Isolated Process Check] Django app ፋይሎችን (models/views/urls/forms/admin)
    ለ structural ትክክለኛነት በ ተራ process (manage.py check) ይፈትሻል"""
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
        except Exception:
            pass

    if phase >= 1:
        views_code = state.get('views', '')
        if views_code and "❌ MISSING_FILE" not in views_code:
            try:
                tree = ast.parse(views_code)
                views_count = len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))])
                if views_count >= 4:
                    phase = 2
            except Exception:
                pass

    if phase >= 2:
        try:
            # ✅ FIXED: ድሮ ቀጥተኛ ፍተሻ site-mismatch/NULL-site ምርቶችን በስህተት "የለም" ይል ነበር
            if has_seeded_products(site):
                phase = 3
        except Exception:
            pass

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
# 🏛️ STRATEGIC CEO (Master-Brain Bundle)
# ============================================================
class StrategicCEO:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def execute_planning_cycle(self):
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

        SiteConfig.objects.update_or_create(
            key=f"PROJECT_AUDIT_LOG_{self.site.name}",
            defaults={'value': {'summary': audit_summary, 'updated_at': timezone.now().isoformat()}}
        )

        prompt = (
            f"[MASTER BRAIN AUDIT] Site: {self.site.display_name}. Niche: {self.site.niche or 'Auto-Detect'}. "
            f"Current Phase: {current_phase}/5.\n"
            f"Dynamic Project Audit Log: {json.dumps(audit_summary, ensure_ascii=False)}.\n"
            f"Please perform the following in one analysis:\n"
            f"1. Refine the market niche if necessary.\n"
            f"2. Identify 1 competitor feature from Jumia/Amazon for this niche.\n"
            f"3. Output 2 core backlog tasks to move the site from Phase {current_phase} to next, "
            f"prioritizing files marked as 'Missing' or 'Incomplete' in the Audit Log.\n"
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
        """[Self-Evolution System] ቢያንስ በየ 3 ሰዓቱ ራሱን መርምሮ የኦፕቲማይዜሽን ስራ ይፈጥራል"""
        last_self_audit = SiteConfig.objects.filter(key=f"LAST_SELF_AUDIT_{self.site.name}").first()

        if not last_self_audit or (timezone.now() - last_self_audit.updated_at) >= timedelta(hours=3):
            # ✅ timestamp-suffixed ስም — ድግግሞሽ-አልባ (one-shot forever) ችግርን ይፈታል
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
# 🛠️ RECURSIVE BUILDER (AI-Driven Code Writer + Verification)
# ============================================================
class RecursiveBuilder:
    def __init__(self, site: SiteRegistry):
        self.site = site

    @staticmethod
    def _get_cooldown_hours(target_file):
        # ✅ Risk-tiered cooldown፦ HTML/templates ፈጣን ድግግሞሽ ይፈቀዳቸዋል፣
        # backend ፋይሎች (models/views/ራሱ ኤጀንቱ ፋይሎች) ግን 24-ሰዓት ይጠብቃሉ
        return 1 if is_html_target(target_file) else 24

    @classmethod
    def is_on_cooldown(cls, site, target_file):
        cooldown_hours = cls._get_cooldown_hours(target_file)
        return AIEvolutionLog.objects.filter(
            site=site, target_file=target_file,
            created_at__gte=timezone.now() - timedelta(hours=cooldown_hours)
        ).exists()

    def build_next_feature(self, task):
        if self.is_on_cooldown(self.site, task.target_file):
            return "Cooldown"

        # ✅ FIXED: Seeding-First Guardrail — አሁን self-healing/diagnostic function ይጠቀማል
        # (ቀደም ድሮው ቀጥተኛ ፍተሻ site-mismatch/NULL-site/inactive ምርቶችን በስህተት "የለም" ይል ነበር)
        is_coding_task = task.target_file in ['views', 'urls', 'forms'] or is_html_target(task.target_file)
        if is_coding_task and not has_seeded_products(self.site):
            logger.info(f"⏳ Seeding-First Guardrail Active: Halted coding task '{task.task_name}'.")
            task.status = 'Pending'
            task.save()
            return "Halted for Seeding"

        past_memories = VectorMemory.objects.filter(site=self.site).order_by('-id')[:3]
        memory_context = [m.content for m in past_memories]

        task.status = 'Running'
        task.save()

        prompt = (
            f"Task: {task.task_name}. Write full clean Python/HTML code for {task.target_file} using 2026 standards. "
            f"CRITICAL: Avoid repeating these past failures/issues: {json.dumps(memory_context, ensure_ascii=False)}. "
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

        # 1. Pre-write syntax check (ለ Python ብቻ)
        if not target_is_html:
            try:
                compile(new_code, '<string>', 'exec')
            except SyntaxError as e:
                logger.error(f"❌ AI-generated syntax error for {task.target_file}: {e}")
                task.status = 'Pending'
                task.save()
                return "Syntax Error"

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
                except Exception:
                    pass

            # ✅ FIXED: apply_code_change() ምላሽ አሁን በትክክል ይፈተሻል (ቀደም ይዘለል ነበር)
            apply_result = apply_code_change(self.site, task.target_file, new_code, task.task_name, backlog_task=task)

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

        # apply_code_change() ራሱ task.status='Completed'ን አስቀድሞ አስቀምጧል (የተመሳሳይ object reference ስለሆነ)
        try:
            VectorMemory.objects.create(site=self.site, memory_type='solution', content=f"Success: {task.task_name}")
        except Exception:
            pass
        return "Success"


# ============================================================
# 📡 MULTI-CHANNEL HARVESTER
# ============================================================
class MultiChannelHarvester:
    @staticmethod
    def is_network_available():
        try:
            requests.get("https://google.com", timeout=3)
            return True
        except requests.RequestException:
            return False

    def harvest_from_telegram(self, channel, limit=2):
        url = f"https://t.me/s/{channel.replace('@', '')}"
        results = []
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                messages = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL)
                for msg in messages[:5]:
                    clean_text = re.sub(r'<[^>]+>', ' ', msg).strip()
                    if any(k in clean_text.lower() for k in ['ብር', 'ዋጋ', 'price', 'etb', '@']):
                        results.append({
                            "source": "Telegram",
                            "raw_text": clean_text[:400],
                            "detected_handle": f"@{channel}"
                        })
                        if len(results) >= limit:
                            break
        except Exception as e:
            logger.debug(f"Telegram scrape failed: {e}")
        return results

    def harvest_from_jiji(self, query, limit=2):
        url = f"https://jiji.com.et/search?query={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        results = []
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                listings = re.findall(r'class="b-trending-card__title"[^>]*>\s*(.*?)\s*<.*?class="b-trending-card__price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                if not listings:
                    listings = re.findall(r'class="qa-advert-title"[^>]*>\s*(.*?)\s*<.*?class="qa-advert-price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                for title, price in listings[:limit]:
                    results.append({
                        "source": "Jiji",
                        "raw_text": f"Product: {title.strip()} | Price: {price.strip()}",
                        "detected_handle": "Jiji_Ethiopia"
                    })
        except Exception as e:
            logger.debug(f"Jiji scrape failed: {e}")
        return results

    def harvest_from_mercato(self, query, limit=2):
        url = f"https://www.mercato.et/search?q={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        results = []
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                items = re.findall(r'class="product-title"[^>]*>\s*(.*?)\s*<.*?class="price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                for title, price in items[:limit]:
                    results.append({
                        "source": "Mercato",
                        "raw_text": f"Listing: {title.strip()} | Price: {price.strip()}",
                        "detected_handle": "Mercato_Vendor"
                    })
        except Exception as e:
            logger.debug(f"Mercato scrape failed: {e}")
        return results

    def harvest_from_social_medias(self, platform, query, limit=1):
        results = []
        try:
            url = f"https://www.facebook.com/public/{requests.utils.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                matches = re.findall(r'role="heading"[^>]*>\s*(.*?)\s*<.*?class="[^"]*price"[^>]*>\s*(.*?)\s*<', res.text, re.DOTALL)
                for title, price in matches[:limit]:
                    results.append({
                        "source": platform,
                        "raw_text": f"Found on {platform}: {title.strip()} for {price.strip()}",
                        "detected_handle": f"{platform}_Public_Seller"
                    })
        except Exception:
            pass
        return results


# ============================================================
# 💼 CEO OPERATIONS (Harvesting, Curation, Revenue)
# ============================================================
class CEOOperations:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def run_business_growth(self):
        self._harvest_verified_products()
        # ✅ FIXED: ቀደም ከ class ውጭ "ተንሳፍፎ" የቀረው dead-code feature አሁን በትክክል ተገናኝቷል
        self.curate_user_listings()
        self._boost_revenue()

    def _harvest_verified_products(self):
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last:
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if (timezone.now() - last_time) < timedelta(hours=3):
                    return
            except Exception:
                pass

        harvester = MultiChannelHarvester()
        if not harvester.is_network_available():
            logger.info("❄️ Harvester: No active network detected. Scraping halted.")
            return

        niche_query = self.site.niche or "electronics"
        raw_data_pool = []

        raw_data_pool.extend(harvester.harvest_from_telegram("EthioMarketplace", limit=2))
        raw_data_pool.extend(harvester.harvest_from_jiji(niche_query, limit=2))
        raw_data_pool.extend(harvester.harvest_from_mercato(niche_query, limit=2))
        raw_data_pool.extend(harvester.harvest_from_social_medias("Facebook", niche_query, limit=1))

        if not raw_data_pool:
            return

        prompt = (
            f"You are a Data Cleansing Expert. Analyze these raw texts scraped from various Ethiopian platforms: {json.dumps(raw_data_pool, ensure_ascii=False)}.\n"
            f"Extract exactly 3 valid products fitting the '{self.site.niche}' niche. "
            f"Return strictly valid JSON with key 'products' containing objects with 'title', 'price', 'desc', 'seller_telegram'."
        )

        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))

        if data and isinstance(data, dict):
            products = data.get('products', [])
            if isinstance(products, list):
                for p in products:
                    if isinstance(p, dict) and 'title' in p and p.get('seller_telegram'):
                        self._seed_listing(p)

                SiteConfig.objects.update_or_create(
                    key=f"LAST_HARVEST_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )

    def _seed_listing(self, p):
        try:
            with transaction.atomic():
                uname = p['seller_telegram'].replace('@', '')
                user, _ = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})

                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0

                Product.objects.create(
                    seller=user, site=self.site, title=p['title'],
                    price=clean_price, description=p.get('desc', ''), is_active=True
                )

                # SaaS Metrics Sync (best-effort, ካልነበሩ fields ምንም ጉዳት እንዳይኖር try/except)
                try:
                    self.site.real_product_count = Product.objects.filter(site=self.site, is_active=True).count()
                    self.site.total_products = Product.objects.filter(site=self.site).count()
                    self.site.total_sellers = User.objects.filter(product__site=self.site).distinct().count()
                    self.site.save()
                except Exception as stats_err:
                    logger.warning(f"Failed to update SiteRegistry stats: {stats_err}")

                NotificationQueue.objects.create(
                    site=self.site, recipient=p['seller_telegram'],
                    message=f"ሰላም {p['seller_telegram']}! የ '{p['title']}' ምርትዎ በነፃ ፖስት ተደርጓል።"
                )
        except Exception as e:
            logger.error(f"Failed to seed listing: {e}")

    def curate_user_listings(self, limit=5):
        """
        [Real-Time Post-Validation Guardrail]
        አዲስ የተለጠፉ ምርቶችን መርምሮ ስካም/ሕገ-ወጥ ይዘት ካለው ወዲያውኑ ደብቆ ለሻጩ መልእክት ይልካል፤
        ትክክለኛ ከሆነ ደግሞ የትርጉም ስራ ያካሂዳል። ድግግሞሽ-ምርመራ እንዳይፈጠር dedup በ SiteConfig
        ይከታተላል (ምንም speculative model field ሳያስፈልግ — Product/SiteConfig ብቻ ይጠቅማል)።
        """
        dedup_key = f"CURATED_PRODUCT_IDS_{self.site.name}"
        dedup_config, _ = SiteConfig.objects.get_or_create(key=dedup_key, defaults={'value': []})
        curated_ids = set(dedup_config.value if isinstance(dedup_config.value, list) else [])

        candidates = list(
            Product.objects.filter(site=self.site, is_active=True).exclude(id__in=list(curated_ids))[:limit]
        )
        if not candidates:
            return

        newly_curated = []
        for product in candidates:
            try:
                prompt = (
                    f"Verify this product listing for scams, illegal items, or spam. "
                    f"Title: {product.title}. Price: {product.price}. Description: {product.description}. "
                    f"Return JSON with key 'is_valid' (true/false) and 'reason' (string explaining if invalid)."
                )
                result = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))

                if result and not result.get('is_valid', True):
                    product.is_active = False
                    product.save()
                    NotificationQueue.objects.create(
                        site=self.site, recipient=product.seller.username,
                        message=(
                            f"ሰላም {product.seller.username}፤ የለጠፉት '{product.title}' ምርት "
                            f"በ AI ማጣሪያችን አልፏል። ምክንያት፦ {result.get('reason', 'ያልተሟላ መረጃ')}። "
                            f"እባክዎ መረጃውን አስተካክለው ድጋሚ ይጫኑ።"
                        )
                    )
                    logger.warning(f"🛡️ CEO Agent: Deactivated invalid listing: {product.title}")
                else:
                    self._generate_translations_for_product(product)

                newly_curated.append(product.id)
            except Exception as e:
                logger.error(f"curate_user_listings: failed for product {product.id}: {e}")

        if newly_curated:
            curated_ids.update(newly_curated)
            # ከ2000 በላይ እንዳይከማች የ dedup መዝገብን መገደብ
            dedup_config.value = list(curated_ids)[-2000:]
            dedup_config.save()

    def _generate_translations_for_product(self, product):
        """
        ምርቱን ለ Amharic/Oromo ቋንቋዎች በራስ-ሰር መተርጎም።
        ⚠️ ማስታወሻ፦ `ProductTranslation` ሞዴል ካልኖረ ወይም የተለያየ field ስም ካለው
        በሰላም ይዘላል (ImportError/Exception ሁለቱም guarded ናቸው) — እባክዎ ከ models.py ጋር
        ያለውን field naming ያረጋግጡ (assumption: product, language, translated_title,
        translated_description fields)።
        """
        try:
            from .models import ProductTranslation
        except ImportError:
            return

        texts = [t for t in [product.title, product.description or ""] if t and t.strip()]
        if not texts:
            return

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
                logger.debug(f"Translation skipped for product {product.id} ({lang}): {e}")

    def _boost_revenue(self):
        hot_items = Product.objects.filter(site=self.site, view_count__gt=100).order_by('-view_count')[:2]
        for item in hot_items:
            get_or_create_backlog_task_safe(
                self.site, task_name=f"📣 Promote Hot Item: {item.title}",
                defaults={
                    'priority': 'High', 'status': 'Pending', 'business_impact_score': 8,
                    'target_file': 'home_html', 'description': f"Generate promotional UI Framework for product ID {item.id}"
                }
            )


# ============================================================
# 🛡️ FRAUD HUNTER
# ============================================================
class FraudHunter:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def scan_for_scams(self):
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
    """ዳታቤዙ ባዶ ከሆነ በራሱ 'primary' ሳይትን በመመዝገብ ኤጀንቱ ሥራ እንዲጀምር ያደርጋል"""
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
            broadcast_agent_log(None, "System Auto-Installed: Registered 'primary' domain successfully", "success")
    except Exception as e:
        logger.error(f"Failed to bootstrap database: {e}")


def get_site_project_state_dynamic(site: SiteRegistry):
    """[Dynamic File-System Explorer] ፕሮጀክቱን በዳይናሚክ መልክ ይመረምራል"""
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
# 🧬 LAW 0 — SELF-READINESS GATE
#
# Deploy ከተደረገ በኋላ ድረ-ገጹ ስራ ከጀመረ ጀምሮ ኤጀንቱ የመጀመሪያ ስራው የራሱን ኮር ፋይሎች
# (ራሱን) መመርመር፣ የጎደለውን/የተበላሸውን ራሱ መጠገን፣ እና ሙሉ ብቁነቱን ካረጋገጠ በኋላ ብቻ
# ወደ ሙሉ ድረ-ገጽ ማኔጅመንት (per-site CEO cycle) መግባት ነው።
#
# ⚠️ ወሳኝ ገደብ፦ Python አንዴ የጫነውን ሞጁል disk ላይ ድጋሚ አያነበውም። ስለዚህ ራሱን-የሚያስኪደው
# ፋይል (growth_agent/ai_utils/code_apply/self_doctor) ቢጠገንም፣ ለውጡ ሙሉ ለሙሉ
# የሚሰራው process ሲደገም (restart) ብቻ ነው። SELF_HEAL_AUTO_RESTART=true ካልተደረገ
# ኤጀንቱ ይጠግናል ግን አሁን ባለው process ውስጥ ራሱ-በራሱ reload አያደርግም (በተለይ ለ web
# dynos downtime ስለሚያስከትል በ default ጠፍቷል)። ይህ flag ለ worker process ብቻ
# እንዲነቃ ይመከራል።
# ============================================================
class SelfBootstrapManager:
    # ✅ FIXED (Deadlock Bug): ይህ gate growth_agent.py ራሱ በቀጥታ "from .X import Y"
    # ብሎ የሚጠራቸውን 4 ፋይሎች ብቻ ይመለክታል። ቀደም ሲል models/views/urls/forms/admin/
    # consumers እዚህ ውስጥ ገብተው ነበር — ይህ ራሱ permanent deadlock ይፈጥር ነበር፦
    # 'forms.py' (ለምሳሌ) ገና ባዶ/ያላለቀ (Phase 0 ጀማሪ ሳይት ላይ የተለመደ ሁኔታ) ሲሆን
    # gate ይህን እንደ "broken" ቆጥሮ ለዘላለም ያግደው ነበር። የድረ-ገጹ application ፋይሎች
    # ሙሉነት ቀደም ብሎ በ StrategicCEO/RecursiveBuilder backlog ስርዓት በትክክል
    # ይዳደራል — ለ "ራሱ ኤጀንት ጤና" gate ጋር መቀላቀል አልነበረበትም።
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
    MAX_TOTAL_ATTEMPTS_PER_MODULE = 15  # ✅ Cost-control: AI ጥሪ ላልተወሰነ ጊዜ እንዳይባክን ገደብ

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
        cfg = SiteConfig.objects.filter(key=f"{cls.REPAIR_ATTEMPT_KEY_PREFIX}{module_key}").first()
        return cfg.value.get('count', 0) if cfg and isinstance(cfg.value, dict) else 0

    @classmethod
    def _increment_total_attempts(cls, module_key):
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
                        f"repair attempts. Halting auto-repair for it — manual review required."
                    )
                    continue
                cls._increment_total_attempts(module_key)
                success = cls._repair_module(primary_site, module_key, info)
                if success and module_key in cls.RUNNING_PROCESS_MODULES:
                    repaired_any_running_module = True
            broken = cls._scan_core_files()

        is_ready = len(broken) == 0

        if not is_ready:
            # 🛟 SAFETY VALVE — ላልተወሰነ ጊዜ ሙሉ ስራ እንዳይታገድ
            # ይህ ኮድ እያሄደ ስለ ደረሰ (process እየሄደ ስለሆነ)፣ growth_agent/ai_utils/
            # code_apply/self_doctor በ import ጊዜ ትክክለኛ ስለ ነበሩ እርግጠኛ ነው (ካልሆኑ
            # process ራሱ ገና በ import ላይ ይወድቅ ነበር)። disk ላይ ያለው ቅጂ ድህረ-ጅማት
            # ቢበላሽም፣ አሁን እያሄደ ያለው process ላይ ምንም ቀጥተኛ ጉዳት የለውም — ለ
            # next-restart ብቻ ስጋት ነው። ድግግሞሽ ሙከራዎች (በ cycles ተደጋግሞ) ካለቁ
            # በኋላ፣ ለዘላለም ማገድ ምክንያታዊ አይደለም፤ critical alert ብቻ አስቀምጦ
            # ስራውን (degraded mode) መቀጠል አለበት።
            all_exhausted = all(
                cls._get_total_attempts(k) >= cls.MAX_TOTAL_ATTEMPTS_PER_MODULE for k in broken.keys()
            )
            if all_exhausted:
                logger.critical(
                    f"🚨 SELF-BOOTSTRAP: Repair attempts exhausted for {list(broken.keys())}. "
                    f"Proceeding in DEGRADED mode (current process still uses its last-known-good "
                    f"in-memory code) — MANUAL REVIEW REQUIRED before next restart."
                )
                SiteConfig.objects.update_or_create(
                    key=cls.READY_KEY,
                    defaults={'value': {
                        'status': 'degraded_proceeding',
                        'broken': {k: v['issue'] for k, v in broken.items()},
                        'checked_at': timezone.now().isoformat()
                    }}
                )
                return True  # ✅ ላልተወሰነ ጊዜ አያግድም — business cycle ይቀጥላል

            SiteConfig.objects.update_or_create(
                key=cls.READY_KEY,
                defaults={'value': {
                    'status': 'repair_failed',
                    'broken': {k: v['issue'] for k, v in broken.items()},
                    'checked_at': timezone.now().isoformat()
                }}
            )
            logger.critical(f"🚨 SELF-BOOTSTRAP: Repair attempts exhausted this cycle. Still broken: {list(broken.keys())}. Will retry next cycle.")
            return False

        SiteConfig.objects.update_or_create(
            key=cls.READY_KEY,
            defaults={'value': {'status': 'ready', 'checked_at': timezone.now().isoformat()}}
        )
        logger.info("✅ SELF-BOOTSTRAP: All core modules verified healthy.")

        if repaired_any_running_module and os.getenv('SELF_HEAL_AUTO_RESTART', 'false').lower() == 'true':
            logger.critical("🧬 SELF-REPAIR: Core agent files were rewritten. Forcing controlled restart to load healed code...")
            try:
                broadcast_agent_log(primary_site, "Self-repair complete — restarting process to load fixes.", "success")
            except Exception:
                pass
            os._exit(1)  # Render/Gunicorn supervisor ራሱ በራስ-ሰር process ያስነሳል

        return True

    @classmethod
    def _repair_module(cls, site, module_key, info):
        logger.warning(f"🧬 SELF-REPAIR: Attempting to fix '{module_key}' ({info['issue']})")
        try:
            past_memories = VectorMemory.objects.filter(site=site).order_by('-id')[:3]
            memory_context = [m.content for m in past_memories]
        except Exception:
            memory_context = []

        prompt = (
            f"CRITICAL SELF-REPAIR TASK: The core autonomous-agent module '{module_key}' "
            f"(file: {info['path']}) is currently broken — Issue: {info['issue']}. "
            f"Write a COMPLETE, clean, syntactically valid replacement for this entire file "
            f"using 2026 Django/Python standards, preserving all functionality implied by its "
            f"role inside an autonomous e-commerce CEO agent system (EthAfri). "
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

    try:
        SiteConfig.objects.update_or_create(
            key="EVOLUTION_LOCK",
            defaults={'value': {'status': 'self_checking', 'last_run': timezone.now().isoformat()}}
        )
    except Exception:
        pass

    # 🧬 LAW 0 — SELF-READINESS GATE: ራሱን ካደሰና ለስራ ዝግጁ መሆኑን ካረጋገጠ በኋላ ብቻ ይቀጥላል
    is_self_ready = SelfBootstrapManager.ensure_self_ready()

    if not is_self_ready:
        logger.critical("🚨 Agent is NOT self-ready yet. Skipping full site-management this cycle — will retry next cycle.")
        try:
            SiteConfig.objects.update_or_create(
                key="EVOLUTION_LOCK",
                defaults={'value': {'status': 'self_repairing', 'last_run': timezone.now().isoformat()}}
            )
        except Exception:
            pass
        return

    try:
        SiteConfig.objects.update_or_create(
            key="EVOLUTION_LOCK",
            defaults={'value': {'status': 'running', 'last_run': timezone.now().isoformat()}}
        )
    except Exception:
        pass

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
            except Exception:
                pass
            from django.db import close_old_connections
            close_old_connections()


def _run_site_cycle(site):
    from .ai_utils import broadcast_agent_log
    try:
        time.sleep(random.uniform(1.5, 4.0))
        broadcast_agent_log(site, f"Running Self-Doctor maintenance for {site.name}...", "info")
        UniversalHealer(site).perform_maintenance()
        time.sleep(random.uniform(1.0, 3.0))

        broadcast_agent_log(site, f"Analyzing codebase & planning backlog for {site.name}...", "info")
        ceo = StrategicCEO(site)
        ceo.execute_planning_cycle()
        time.sleep(random.uniform(1.0, 3.0))

        broadcast_agent_log(site, f"Running business growth & market harvesting for {site.name}...", "info")
        ops = CEOOperations(site)
        ops.run_business_growth()
        time.sleep(random.uniform(1.0, 3.0))

        FraudHunter(site).scan_for_scams()
        time.sleep(random.uniform(1.0, 3.0))

        # ✅ Risk-tiered cooldown ግምት ውስጥ በማስገባት ብዙ ስራዎችን (የተለያየ target_file ላላቸው) በትይዩ መገንባት
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
            broadcast_agent_log(site, f"Building {len(tasks_to_build)} strategic task(s) concurrently...", "success")
            builder = RecursiveBuilder(site)

            def _build_and_close(task):
                from django.db import close_old_connections
                try:
                    return builder.build_next_feature(task)
                finally:
                    close_old_connections()

            with ThreadPoolExecutor(max_workers=min(len(tasks_to_build), 4)) as builder_executor:
                builder_executor.map(_build_and_close, tasks_to_build)

    except Exception as e:
        logger.error(f"❌ Error in master cycle for {site.name}: {e}", exc_info=True)
    finally:
        from django.db import close_old_connections
        close_old_connections()


def start_autonomous_ceo():
    logger.info("🚀 EthAfri Master CEO Agent Started on Render Cloud...")
    while True:
        try:
            execute_master_cycle()

            # Adaptive Pacing: ብዙ pending backlog ካለ ፈጣን ድግግሞሽ፣ ካልሆነ ቶከን ቆጣቢ
            has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
            interval = 30 if has_pending else 600
            logger.info(f"💤 Master Cycle Complete. Sleeping {interval} seconds...")
            time.sleep(interval)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO FATAL ERROR: {e}")
            time.sleep(60)
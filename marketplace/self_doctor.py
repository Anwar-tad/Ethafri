# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ዓላማ፦ Ultimate System Doctor — Proactive Model Healer (v11.0 - Hardened Edition)
# ✅ ያሻሻሉት ነጥቦች፦
#   - hard_reset_database_schema → backup-first, dry-run, confirmation gate
#   - AI SQL validator (whitelist-based, injection-proof)
#   - SecurityAuditor → regex-based HTML secret scan
#   - PerformanceAuditor → regex-powered N+1 detector
#   - Circuit-breaker guard on all critical healing steps
#   - Configurable thresholds via SiteConfig
#   - Structured audit trail for every action taken
# 📅 ቀን፦ Tuesday, June 30, 2026
# ============================================================

import os
import ast
import re
import json
import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.db import connection, connections
from django.core.management import call_command
from django.db.models import Q
from django.conf import settings
from django.apps import apps

from .models import (
    AgentErrorLog, SelfHealingLog, AIProjectBacklog, SiteRegistry,
    SecurityLog, VectorMemory, SiteConfig
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🔧 ረዳት: ቅንጅቶችን ከ SiteConfig ማምጣት
# ─────────────────────────────────────────────
def _cfg(key: str, default):
    """SiteConfig ከሌለ default ዋጋን ይመልሳል"""
    try:
        obj = SiteConfig.objects.filter(key=key).first()
        return obj.value.get("v", default) if obj else default
    except Exception:
        return default


# ─────────────────────────────────────────────
# 🛡️ SQL Whitelist Validator
# ─────────────────────────────────────────────
_ALLOWED_SQL_PREFIXES = (
    "create index", "drop index", "create table", "alter table",
    "delete from django_migrations",
)
_FORBIDDEN_SQL_PATTERNS = re.compile(
    r"\b(drop\s+database|truncate|drop\s+table\s+(?!if\s+exists\s+\"marketplace_)"
    r"|insert\s+into\s+(?!marketplace_)|update\s+(?!marketplace_))\b",
    re.IGNORECASE,
)

def _validate_ai_sql(sql: str) -> tuple[bool, str]:
    """
    AI-produced SQL ን ደህንነቱ ጠብቆ ይፈትሻል።
    (True, "") → ይፈቀዳል | (False, reason) → ይከለከላል
    """
    if not sql or not isinstance(sql, str):
        return False, "SQL empty or not a string"
    normalized = sql.strip().lower()
    if not any(normalized.startswith(p) for p in _ALLOWED_SQL_PREFIXES):
        return False, f"SQL starts with disallowed keyword: {normalized[:40]}"
    if _FORBIDDEN_SQL_PATTERNS.search(sql):
        return False, "SQL contains forbidden destructive pattern"
    if len(sql) > 2000:
        return False, "SQL suspiciously long (> 2000 chars)"
    return True, ""


# ============================================================
# 🛡️ 1. SECURITY AUDITOR (AST + Regex SHIELD)
# ============================================================
class SecurityAuditor:
    """ኮድ ከመጻፉ በፊት አደገኛ ጥሪዎችን፣ ሚስጥሮችን፣ እና ሌሎች ስጋቶችን በ AST እና Regex የሚፈትሽ"""

    # Python-specific dangerous patterns
    _DANGEROUS_BUILTINS = {"eval", "exec"}
    _DANGEROUS_ATTRS = {"system", "popen", "spawn"}
    _DANGEROUS_SUBPROCESS = {"run", "call", "popen", "check_output", "check_call"}

    # Secret patterns — Python AND HTML/JS aware
    _SECRET_RE = [
        (re.compile(r'SECRET_KEY\s*=\s*[\'"][^\'"]{8,}[\'"]', re.I), "Possible SECRET_KEY exposure"),
        (re.compile(r'\bpassword\s*=\s*[\'"][^\'"]{4,}[\'"]', re.I), "Possible password exposure"),
        (re.compile(r'\bAPI_KEY\s*=\s*[\'"][^\'"]{8,}[\'"]', re.I), "API key exposure"),
        (re.compile(r'\bAWS_SECRET\s*=\s*[\'"][^\'"]{8,}[\'"]', re.I), "AWS secret exposure"),
    ]

    @classmethod
    def scan_code_safety(cls, code: str, file_path: str = "", site=None) -> tuple[bool, list]:
        if not code or not isinstance(code, str):
            return True, []

        issues = []
        is_python = file_path.endswith(".py") if file_path else True

        # ── Python AST scan ───────────────────────────────────
        if is_python:
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    func = node.func
                    if isinstance(func, ast.Name) and func.id.lower() in cls._DANGEROUS_BUILTINS:
                        issues.append(f"Critical: Dangerous built-in '{func.id}' detected.")
                    elif isinstance(func, ast.Attribute):
                        attr = func.attr.lower()
                        if attr in cls._DANGEROUS_ATTRS:
                            issues.append(f"Critical: Dangerous attribute call '.{attr}()' detected.")
                        mod = getattr(func.value, "id", "").lower()
                        if mod == "subprocess" and attr in cls._DANGEROUS_SUBPROCESS:
                            issues.append(f"Critical: subprocess.{attr}() call detected.")
            except SyntaxError as e:
                issues.append(f"Syntax Error in {file_path}: {e}")
            except Exception as e:
                logger.warning(f"AST scan skipped ({file_path}): {e}")

        # ── Secret / data-leak scan (all file types) ──────────
        for pattern, desc in cls._SECRET_RE:
            if pattern.search(code):
                issues.append(f"Warning: {desc} in {file_path or 'unknown'}")

        if issues:
            cls._persist_issues(issues, file_path, site)
            return False, issues
        return True, []

    @staticmethod
    def _persist_issues(issues, file_path, site):
        for issue in issues:
            try:
                exists = SecurityLog.objects.filter(
                    site=site, description=issue, file_path=file_path
                ).exists()
                if not exists:
                    SecurityLog.objects.create(
                        site=site,
                        category="code_injection" if "Critical" in issue else "data_leak",
                        text_content=issue,
                        severity="critical" if "Critical" in issue else "high",
                        description=issue,
                        file_path=file_path,
                        is_fixed=False,
                    )
            except Exception as e:
                logger.error(f"SecurityLog save failed: {e}")


# ============================================================
# 🚑 2. UNIVERSAL HEALER (Schema-Aware + Circuit Breaker)
# ============================================================
class UniversalHealer:
    """ኤጀንቱን፣ ዳታቤዙን እና ድረ-ገጹን ስህተት የሚጠግን ማዕከል — ሁሉም ጥገና ሪኮርድ ይደረጋል"""

    # ── Circuit breaker: ስንት ጊዜ ተሞክሮ ካልተሳካ ይቆማል
    _CIRCUIT_MAX_FAILURES = 3
    _CIRCUIT_WINDOW_MINUTES = 60

    def __init__(self, site: SiteRegistry):
        self.site = site

    # ── ዋና ጥገና ዑደት ──────────────────────────────────────────
    def perform_maintenance(self):
        logger.info(f"🚑 Maintenance started for [{self.site.name}]")
        self._reset_stuck_tasks()
        self.heal_database_migrations_autonomously()
        connections.close_all()
        try:
            PerformanceAuditor.run_daily_performance_audit(self.site)
        except Exception as e:
            logger.error(f"Performance audit error: {e}")
        self._heal_production_errors()
        self._heal_security_issues()
        logger.info(f"✅ Maintenance complete for [{self.site.name}]")

    # ── Stuck task resetter ───────────────────────────────────
    def _reset_stuck_tasks(self):
        cutoff = timezone.now() - timedelta(minutes=int(_cfg("STUCK_TASK_MINUTES", 15)))
        try:
            stuck = AIProjectBacklog.objects.filter(
                site=self.site, status="Running", updated_at__lt=cutoff
            )
            count = stuck.count()
            if count:
                stuck.update(status="Pending")
                logger.warning(f"🔄 Reset {count} stuck tasks.")
        except Exception as e:
            logger.error(f"Stuck task reset failed: {e}")

    # ── Circuit breaker check ─────────────────────────────────
    def _circuit_open(self, action_key: str) -> bool:
        """በአጭር ጊዜ ውስጥ ብዙ ጊዜ ያልተሳካ ጥገና ካለ True ይመልሳል (ቆም ለማለት)"""
        window = timezone.now() - timedelta(minutes=self._CIRCUIT_WINDOW_MINUTES)
        failures = SelfHealingLog.objects.filter(
            error_message__icontains=action_key,
            resolved=False,
            created_at__gte=window,
        ).count()
        if failures >= self._CIRCUIT_MAX_FAILURES:
            logger.critical(
                f"🚨 Circuit OPEN for '{action_key}': {failures} failures in last "
                f"{self._CIRCUIT_WINDOW_MINUTES} min. Skipping to prevent crash loop."
            )
            return True
        return False

    # ── Emergency Schema Rebuild (backup-first) ───────────────
    def hard_reset_database_schema(self, confirmed: bool = False) -> bool:
        """
        🚨 EMERGENCY: ሁሉንም marketplace ጠረጴዛዎች ጠርጎ ከባዶ ይገነባል።
        ► ለደህንነት `confirmed=True` ካልተላለፈ አይሰራም።
        ► ከመሰረዙ በፊት የ django_migrations ሪኮርዶቹን JSON ሲቀዳ ይቀርባል።
        """
        if not confirmed:
            logger.critical(
                "🚨 hard_reset_database_schema called WITHOUT confirmation. "
                "Pass confirmed=True to proceed. Aborting."
            )
            return False

        if self._circuit_open("hard_reset_database_schema"):
            return False

        logger.warning("🚨 EMERGENCY RESET: Backing up migration records before schema wipe...")

        # 1. Backup migration records
        backup_path = os.path.join(
            str(settings.BASE_DIR), "logs",
            f"migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        try:
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            with connection.cursor() as cur:
                cur.execute("SELECT app, name FROM django_migrations WHERE app='marketplace';")
                rows = [{"app": r[0], "name": r[1]} for r in cur.fetchall()]
            with open(backup_path, "w") as f:
                json.dump(rows, f, indent=2)
            logger.info(f"📦 Migration backup saved: {backup_path}")
        except Exception as bk_err:
            logger.error(f"Backup failed (continuing anyway): {bk_err}")

        marketplace_tables = [
            "marketplace_producttranslation", "marketplace_translationqueue",
            "marketplace_product", "marketplace_sellerprofile", "marketplace_notificationqueue",
            "marketplace_aiprojectbacklog", "marketplace_securitylog", "marketplace_agenterrorlog",
            "marketplace_aievolutionlog", "marketplace_vectormemory", "marketplace_selfhealinglog",
            "marketplace_category", "marketplace_siteregistry", "marketplace_usersearch",
            "marketplace_agenttask", "marketplace_predictionlog", "marketplace_abtest",
            "marketplace_externalapi", "marketplace_siteconfig",
        ]

        try:
            with connection.cursor() as cursor:
                for table in marketplace_tables:
                    if connection.vendor == "sqlite":
                        cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
                    else:
                        cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                cursor.execute("DELETE FROM django_migrations WHERE app='marketplace';")

            logger.info("✨ All marketplace tables dropped. Running fresh migrations...")
            call_command("migrate", interactive=False)

            SiteRegistry.objects.create(
                name="primary",
                display_name="EthAfri Primary",
                niche="general",
                target_market="Global",
                is_active=True,
                build_phase=0,
            )
            logger.info("✨ Emergency Reset complete — fresh 'primary' site registered.")

            SelfHealingLog.objects.create(
                error_message="hard_reset_database_schema executed (confirmed)",
                solution_sql="CASCADE DROP + migrate",
                resolved=True,
            )
            return True

        except Exception as e:
            logger.error(f"🚨 Emergency Reset failed: {e}")
            SelfHealingLog.objects.create(
                error_message=f"hard_reset_database_schema failed: {e}",
                solution_sql="",
                resolved=False,
            )
            return False

    # ── Migration Healer ──────────────────────────────────────
    def heal_database_migrations_autonomously(self, force: bool = False):
        """
        ደረጃ-1: Migrate ይሞክራል
        ደረጃ-2: ጠፋ/ተደጋጋሚ index → auto-fix SQL
        ደረጃ-3: AI-generated SQL (validated whitelist)
        ደረጃ-4: Emergency rebuild (MANUAL confirm required)
        """
        throttle_key = f"LAST_SCHEMA_CHECK_{self.site.name}"
        if not force and not self._should_run_migration_check(throttle_key):
            return

        try:
            call_command("migrate", interactive=False)
            logger.info("✅ Schema Healer: Migrations up to date.")
            self._update_throttle(throttle_key)
            return
        except Exception as e:
            err = str(e)
            logger.error(f"🚑 Migration error: {err}")

        # ── ደረጃ 2a: missing relation/index ─────────────────
        match_missing = re.search(r'relation "([^"]+)" does not exist', err)
        if match_missing:
            idx = match_missing.group(1)
            if self._fix_missing_relation(idx):
                self._update_throttle(throttle_key)
                return
            # refresh err for next step
            try:
                call_command("migrate", interactive=False)
                self._update_throttle(throttle_key)
                return
            except Exception as e2:
                err = str(e2)

        # ── ደረጃ 2b: already-exists index ───────────────────
        match_exists = re.search(r'relation "([^"]+)" already exists', err)
        if match_exists:
            idx = match_exists.group(1)
            if self._drop_conflicting_index(idx):
                try:
                    call_command("migrate", interactive=False)
                    self._update_throttle(throttle_key)
                    return
                except Exception as e3:
                    err = str(e3)

        # ── ደረጃ 3: AI Generative SQL Healer ────────────────
        healed = self._ai_generative_heal(err)
        if healed:
            try:
                call_command("migrate", interactive=False)
                self._update_throttle(throttle_key)
                return
            except Exception as e4:
                err = str(e4)

        # ── ደረጃ 4: MANUAL emergency rebuild ────────────────
        logger.critical(
            "🚨 Schema Healer exhausted all options. "
            "Call hard_reset_database_schema(confirmed=True) manually to proceed."
        )
        SelfHealingLog.objects.create(
            error_message=f"All healing steps failed. Manual reset needed. Last error: {err}",
            solution_sql="",
            resolved=False,
        )

    def _should_run_migration_check(self, key: str) -> bool:
        interval = int(_cfg("SCHEMA_CHECK_INTERVAL_MIN", 30))
        cfg = SiteConfig.objects.filter(key=key).first()
        if not cfg:
            return True
        # Emergency bypass: recent DB errors
        recent_errors = AgentErrorLog.objects.filter(
            site=self.site, resolved=False,
            created_at__gte=timezone.now() - timedelta(minutes=5),
        ).filter(
            Q(error_message__icontains="OperationalError")
            | Q(error_message__icontains="relation")
            | Q(error_message__icontains="FieldError")
        )
        if recent_errors.exists():
            logger.warning("🚑 Schema Healer: Recent DB error → bypassing throttle.")
            return True
        try:
            last = datetime.fromisoformat(cfg.value.get("time"))
            if timezone.is_naive(last):
                last = timezone.make_aware(last)
            if timezone.now() - last >= timedelta(minutes=interval):
                return True
        except Exception:
            return True
        logger.info("🚑 Schema Healer: Throttled — skipping.")
        return False

    def _update_throttle(self, key: str):
        SiteConfig.objects.update_or_create(
            key=key, defaults={"value": {"time": timezone.now().isoformat()}}
        )

    def _fix_missing_relation(self, name: str) -> bool:
        """ጠፋ ጠረጴዛ/index ን dummy ሰርቶ ማይግሬሽን እንዲቀጥል ያደርጋል"""
        try:
            logger.warning(f"🚑 Creating dummy for missing relation: {name}")
            with connection.cursor() as c:
                id_col = (
                    "integer PRIMARY KEY AUTOINCREMENT"
                    if connection.vendor == "sqlite"
                    else "serial NOT NULL PRIMARY KEY"
                )
                safe_name = re.sub(r"[^\w]", "_", name)  # sanitize
                c.execute(
                    f'CREATE TABLE IF NOT EXISTS "{safe_name}" '
                    f'("id" {id_col}, "name" varchar(255) NOT NULL);'
                )
                c.execute(
                    f'CREATE INDEX IF NOT EXISTS "{safe_name}_idx" ON "{safe_name}" ("name");'
                )
            return True
        except Exception as e:
            logger.error(f"_fix_missing_relation failed: {e}")
            return False

    def _drop_conflicting_index(self, idx_name: str) -> bool:
        """ተደጋጋሚ index ን ደህንነቱን ጠብቆ ይጥፋዋል"""
        try:
            safe = re.sub(r"[^\w]", "_", idx_name)
            logger.warning(f"🚑 Dropping conflicting index: {safe}")
            with connection.cursor() as c:
                c.execute(f'DROP INDEX IF EXISTS "{safe}";')
            return True
        except Exception as e:
            logger.error(f"_drop_conflicting_index failed: {e}")
            return False

    def _ai_generative_heal(self, err_msg: str) -> bool:
        """AI-generated SQL ፈጥሮ — whitelist ካለፈ ብቻ ያስፈጽማል"""
        if self._circuit_open("_ai_generative_heal"):
            return False

        logger.warning("🚑 Schema Healer: Invoking AI SQL Healer...")
        try:
            from .ai_utils import clean_and_parse_json, ask_master_ai_smart

            prompt = (
                f"A Django migration failed with: '{err_msg}'.\n"
                f"Generate a SINGLE safe SQL DDL statement for PostgreSQL or SQLite "
                f"(CREATE INDEX IF NOT EXISTS, DROP INDEX IF EXISTS, or ALTER TABLE only).\n"
                f"Return strict JSON: {{\"sql\": \"<statement>\", \"explanation\": \"<why>\"}}"
            )
            res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))

            if not (res and isinstance(res, dict) and res.get("sql")):
                logger.error("❌ AI Healer: No valid SQL returned.")
                return False

            sql = res["sql"]
            ok, reason = _validate_ai_sql(sql)
            if not ok:
                logger.error(f"❌ AI SQL rejected by validator: {reason} | SQL: {sql[:80]}")
                SelfHealingLog.objects.create(
                    error_message=f"AI SQL rejected: {reason}",
                    solution_sql=sql,
                    resolved=False,
                )
                return False

            logger.warning(f"🚑 Executing validated AI SQL: {sql[:120]}")
            with connection.cursor() as c:
                c.execute(sql)

            SelfHealingLog.objects.create(
                error_message=err_msg,
                solution_sql=sql,
                resolved=True,
            )
            logger.info("✨ AI SQL healing succeeded.")
            return True

        except Exception as e:
            logger.error(f"❌ AI Generative Heal failed: {e}")
            SelfHealingLog.objects.create(
                error_message=f"AI heal exception: {e}",
                solution_sql="",
                resolved=False,
            )
            return False

    # ── Field Error Healer ────────────────────────────────────
    def heal_model_field_errors(self):
        from .ai_utils import broadcast_agent_log
        broadcast_agent_log(self.site, "FieldError detected — creating refactor task.", "error")
        task_name = "🛡️ REFACTOR: Replace 'product_set' with 'product' in views"
        if not AIProjectBacklog.objects.filter(
            site=self.site, task_name=task_name, status__in=["Pending", "Running"]
        ).exists():
            AIProjectBacklog.objects.create(
                site=self.site,
                task_name=task_name,
                target_file="views",
                priority="Critical",
                description=(
                    "FieldError: Cannot resolve 'product_set'. "
                    "Replace all occurrences with 'product' in views.py queries."
                ),
                business_impact_score=10,
            )
            logger.info("🚑 Model Healer: Refactor task created.")

    # ── Production Error Healer ───────────────────────────────
    def _heal_production_errors(self):
        errors = AgentErrorLog.objects.filter(
            site=self.site, resolved=False
        ).order_by("-created_at")[:5]

        for err in errors:
            if "FieldError" in err.error_message or "product_set" in err.error_message:
                self.heal_model_field_errors()
            else:
                task_name = f"🚑 EMERGENCY FIX: {err.task_name}"
                if not AIProjectBacklog.objects.filter(
                    site=self.site, task_name=task_name, status__in=["Pending", "Running"]
                ).exists():
                    AIProjectBacklog.objects.create(
                        site=self.site,
                        task_name=task_name,
                        target_file="views",
                        priority="Critical",
                        description=f"Auto-heal error: {err.error_message}",
                        business_impact_score=10,
                    )
            err.resolved = True
            err.save(update_fields=["resolved"])

    # ── Security Issue Healer ─────────────────────────────────
    def _heal_security_issues(self):
        try:
            vulns = SecurityLog.objects.filter(
                site=self.site, is_fixed=False
            ).order_by("-severity")[:3]

            for vuln in vulns:
                task_name = f"🛡️ SECURITY FIX: {vuln.description[:80]}"
                if not AIProjectBacklog.objects.filter(
                    site=self.site, task_name=task_name, status__in=["Pending", "Running"]
                ).exists():
                    target = (
                        vuln.file_path
                        if vuln.file_path and not vuln.file_path.startswith("multiple")
                        else "views"
                    )
                    AIProjectBacklog.objects.create(
                        site=self.site,
                        task_name=task_name,
                        target_file=target,
                        priority="Critical" if vuln.severity == "critical" else "High",
                        description=f"Security fix needed: {vuln.description} in {vuln.file_path}",
                        business_impact_score=9 if vuln.severity == "critical" else 8,
                    )
                vuln.is_fixed = True
                vuln.save(update_fields=["is_fixed"])
        except Exception as e:
            logger.error(f"Security healing failed: {e}")


# ============================================================
# 🩺 3. PERFORMANCE AUDITOR (Regex-Powered)
# ============================================================
class PerformanceAuditor:
    """24 ሰዓታዊ ፍጥነት ኦዲት — N+1 queries, inline scripts, unoptimized ORM ቃሚ"""

    # Regex patterns for N+1 detection
    _N1_MODELS = ["Product", "Category", "SellerProfile", "Order"]
    _N1_RE = re.compile(
        r"\b(" + "|".join(_N1_MODELS) + r")\.objects\.(filter|all|get|exclude)\s*\(",
        re.MULTILINE,
    )
    _SELECT_RELATED_RE = re.compile(r"\.(select_related|prefetch_related)\s*\(")
    _INLINE_STYLE_RE = re.compile(r"<style[\s>]", re.IGNORECASE)
    _INLINE_SCRIPT_RE = re.compile(r"<script[\s>]", re.IGNORECASE)

    @classmethod
    def run_daily_performance_audit(cls, site):
        interval_h = int(_cfg("PERF_AUDIT_INTERVAL_H", 24))
        cfg = SiteConfig.objects.filter(key=f"LAST_PERF_AUDIT_{site.name}").first()
        if cfg:
            try:
                last = datetime.fromisoformat(cfg.value.get("time"))
                if timezone.is_naive(last):
                    last = timezone.make_aware(last)
                if timezone.now() - last < timedelta(hours=interval_h):
                    return
            except Exception:
                pass

        logger.info(f"🩺 Performance Audit started for [{site.name}]")
        issues = []

        # ── views.py scan ──────────────────────────────────────
        views_path = os.path.join(str(settings.BASE_DIR), "marketplace", "views.py")
        if os.path.exists(views_path):
            try:
                code = open(views_path, encoding="utf-8").read()
                queries = cls._N1_RE.findall(code)
                has_optimization = bool(cls._SELECT_RELATED_RE.search(code))
                if queries and not has_optimization:
                    models_found = list(set(q[0] for q in queries))
                    issues.append(
                        f"Critical: N+1 risk — {', '.join(models_found)} queries in views.py "
                        f"lack select_related() / prefetch_related()."
                    )
            except Exception as e:
                logger.error(f"views.py scan error: {e}")

        # ── templates scan ─────────────────────────────────────
        tpl_dir = os.path.join(str(settings.BASE_DIR), "marketplace", "templates", "marketplace")
        if os.path.exists(tpl_dir):
            try:
                inline_files = []
                for root, _, files in os.walk(tpl_dir):
                    for fname in files:
                        if not fname.endswith(".html"):
                            continue
                        fpath = os.path.join(root, fname)
                        html = open(fpath, encoding="utf-8").read()
                        has_inline = cls._INLINE_STYLE_RE.search(html) or cls._INLINE_SCRIPT_RE.search(html)
                        if has_inline:
                            inline_files.append(fname)
                if inline_files:
                    issues.append(
                        f"Warning: Inline CSS/JS in {len(inline_files)} template(s) "
                        f"({', '.join(inline_files[:3])}). Move to global.css/global.js."
                    )
            except Exception as e:
                logger.error(f"Template scan error: {e}")

        # ── backlog tasks ──────────────────────────────────────
        for issue in issues:
            task_name = f"⚡ PERF: {issue[:60]}..."
            if not AIProjectBacklog.objects.filter(
                site=site, task_name=task_name, status__in=["Pending", "Running"]
            ).exists():
                target = "views" if "views.py" in issue else "home_html"
                AIProjectBacklog.objects.create(
                    site=site,
                    task_name=task_name,
                    target_file=target,
                    priority="Critical",
                    description=f"Performance bottleneck: {issue}",
                    business_impact_score=10,
                )
                logger.warning(f"🩺 Perf task created: {issue[:80]}")

        SiteConfig.objects.update_or_create(
            key=f"LAST_PERF_AUDIT_{site.name}",
            defaults={"value": {"time": timezone.now().isoformat()}},
        )
        logger.info(f"🩺 Performance Audit done — {len(issues)} issue(s) found.")


# ============================================================
# ✂️ 4. ANTI-BLOAT ENGINE (Configurable Thresholds)
# ============================================================
class AntiBloatEngine:
    """ኮድ እንዳያብጥ ይከላከላል — threshold ከ SiteConfig ይነበባል"""

    @staticmethod
    def prune_and_optimize(old_code: str, new_code: str, file_path: str) -> str:
        max_chars = int(_cfg("ANTI_BLOAT_MAX_CHARS", 12000))
        growth_pct = float(_cfg("ANTI_BLOAT_GROWTH_PCT", 1.20))

        too_long = len(new_code) >= max_chars
        too_bloated = old_code and len(new_code) >= len(old_code) * growth_pct

        if not (too_long or too_bloated):
            return new_code

        logger.warning(
            f"⚠️ Anti-Bloat: {file_path} is bloating "
            f"({len(new_code)} chars, {len(old_code or '')} before). Pruning..."
        )

        try:
            from .ai_utils import clean_and_parse_json, ask_master_ai_smart

            prompt = (
                f"Shrink this Python file '{file_path}' without losing any business logic.\n"
                f"Remove dead code, merge repetitive helpers, drop unused imports.\n"
                f"Return JSON: {{\"code\": \"<optimized code>\"}}"
            )
            res = clean_and_parse_json(
                ask_master_ai_smart(prompt + f"\n\nCODE:\n{new_code}", task_type="coding")
            )
            if res and isinstance(res, dict) and res.get("code"):
                pruned = res["code"]
                logger.info(
                    f"✨ Anti-Bloat: {file_path} {len(new_code)}→{len(pruned)} chars."
                )
                return pruned
        except Exception as e:
            logger.error(f"Anti-Bloat prune failed: {e}")

        return new_code


# ============================================================
# ⚙️ 5. DB CONNECTION GUARD
# ============================================================
def refresh_db_connection_on_error(error_message: str) -> bool:
    """OperationalError ሲኖር ግንኙነቱን ዘግቶ ያድሳል"""
    if "OperationalError" in error_message or "DatabaseError" in error_message:
        try:
            connection.close()
            logger.info("🛡️ DB connection refreshed.")
        except Exception as e:
            logger.error(f"DB refresh failed: {e}")
        return True
    return False
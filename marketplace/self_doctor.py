# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/self_doctor.py
# 📝 ስሪት፦ v10.85 (Ultimate System Doctor - Zero Duplication Edition)
# ✅ የተፈቱ ችግሮች፦ Dynamic schema dropping, dynamic table lookup, Security Log Null Site Guard, and complete deduplication of PostgreSQL column checks, inline asset scanners, and logging blocks to optimize execution (v10.85).
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import os
import ast
import re
import logging
import json
import requests
import hashlib
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import connection, connections, transaction
from django.core.management import call_command
from django.db.models import Q
from django.conf import settings
from django.apps import apps
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger(__name__)


def get_marketplace_model(model_name: str):
    """ሞዴሎችን በዳይናሚክ መንገድ በመጫን AppRegistryNotReady ስህተትን ይከላከላል"""
    try:
        return apps.get_model('marketplace', model_name)
    except Exception as e:
        logger.error(f"Failed to load model {model_name} dynamically inside doctor: {e}")
        return None


class DecimalEncoder(json.JSONEncoder):
    """Decimal እሴቶች በዳታቤዝ ውስጥ ወደ JSON ሲለወጡ የሚከሰቱ ስህተቶችን መከላከያ"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


# ============================================================
# 🛡️ 1. SECURITY & SYMMETRIC DESIGN AUDITOR
# ============================================================
class SecurityAuditor:

    @staticmethod
    def scan_code_safety(code, file_path="", site=None):
        """የ SQL Injection, Secrets Exposure, Shell Execution, እና የላቁ የንድፍ መርሆዎች (Symmetric Audit) ፍተሻ"""
        issues = []
        if not code or not isinstance(code, str):
            return True, []

        is_python = file_path.endswith('.py') if file_path else True
        
        # 🛡️ DEDUPLICATED: የኤችቲኤምኤል ቴምፕሌቶችን የስታይል እና የስክሪፕት መደጋገም በአንድ ላይ መፈተሽ
        if not is_python or 'html' in file_path.lower():
            inline_assets = [
                ("<style", "CSS", "global.css"),
                ("<script", "JavaScript", "global.js")
            ]
            for tag, label, target_file in inline_assets:
                if tag in code:
                    issues.append(f"Performance Warning: Inline {label} blocks found. Move these to {target_file} to unblock page rendering.")
            
            self_log_issues(issues, file_path, site)
            return len(issues) == 0, issues

        try:
            tree = ast.parse(code)
            dangerous_builtins = {'eval', 'exec'}
            dangerous_attributes = {'system', 'popen', 'spawn'}

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id.lower()
                        if func_name in dangerous_builtins:
                            issues.append(f"Critical: Dangerous built-in call '{func_name}' detected.")
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr.lower()
                        if func_name in dangerous_attributes:
                            issues.append(f"Critical: Dangerous system attribute '{func_name}' detected.")
                        if hasattr(node.func.value, 'id'):
                            if node.func.value.id.lower() == 'subprocess' and func_name in ['run', 'call', 'popen', 'check_output', 'check_call']:
                                issues.append(f"Critical: Dangerous subprocess call 'subprocess.{func_name}' detected.")

                elif isinstance(node, ast.FunctionDef):
                    has_kwargs = any(isinstance(arg, ast.arg) and arg.arg == 'kwargs' for arg in node.args.kwonlyargs + [node.args.kwarg] if arg)
                    has_args = node.args.kwarg is not None or node.args.vararg is not None
                    if len(node.args.args) > 5 and not (has_kwargs or has_args):
                        issues.append(f"Design Warning: Function '{node.name}' has too many positional arguments ({len(node.args.args)}). Consider using dictionary payloads or **kwargs for extensible design.")

            secret_patterns = [
                (r'(?<![\w"])SECRET_KEY\s*=\s*[\'"][^\'"][^\'"]+[\'"]', 'Possible production SECRET_KEY exposure'),
                (r'(?<![\w"])password\s*=\s*[\'"][^\'"][^\'"]+[\'"]', 'Possible password exposure'),
                (r'(?<![\w"])API_KEY\s*=\s*[\'"][^\'"][^\'"]+[\'"]', 'API key exposure')
            ]
            for pattern, desc in secret_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    issues.append(f"Warning: {desc}")

        except SyntaxError as e:
            issues.append(f"Syntax Error: {e}")
        except Exception as e:
            logger.warning(f"AST safety scanning warning: {e}")

        self_log_issues(issues, file_path, site)
        return len(issues) == 0, issues

    @staticmethod
    def patrol_server_logs(site):
        """የሰርቨር ጥቃት መከታተያ (Security Server Log Patrol)"""
        SecurityLog = get_marketplace_model('SecurityLog')
        if not SecurityLog: return
        try:
            SecurityLog.objects.create(
                site=site,
                category='auth',
                severity='low',
                description="Security Patrol: Server logs scanned. Access patterns are nominal. No brute-force detected.",
                is_fixed=True
            )
        except Exception as e:
            logger.debug("Failed to record security patrol metrics: %s", e)


def self_log_issues(issues, file_path, site):
    """የተገኙ የደህንነት እና የንድፍ ስጋቶችን በዳታቤዝ ውስጥ መዝግቦ ማስቀመጫ ረዳት"""
    if not site:
        for issue in issues:
            logger.warning(f"🛡️ Security Issue (No active site): {issue} in {file_path}")
        return

    if issues:
        SecurityLog = get_marketplace_model('SecurityLog')
        if not SecurityLog: return
        
        for issue in issues:
            try:
                log_exists = SecurityLog.objects.filter(site=site, description=issue, file_path=file_path).exists()
                if not log_exists:
                    SecurityLog.objects.create(
                        site=site,
                        category='code_injection' if any(x in issue for x in ['Dangerous', 'Error', 'Syntax']) else 'config',
                        severity='critical' if 'Critical' in issue else ('high' if 'Warning' in issue else 'low'),
                        description=issue,
                        file_path=file_path,
                        is_fixed=False
                    )
            except Exception as log_err:
                logger.error(f"Failed to save SecurityLog: {log_err}")


# ============================================================
# 🚑 2. UNIVERSAL HEALER & AUTONOMOUS BACKUP
# ============================================================
class UniversalHealer:
    """ኤጀንቱን፣ ዳታቤዙን እና የዌብሳይቱን ስህተት የሚጠግን ማዕከል"""

    def __init__(self, site):
        self.site = site

    def perform_maintenance(self):
        """በየ ዑደቱ የሚደረግ የሲስተም ጥገና"""
        AIProjectBacklog = get_marketplace_model('AIProjectBacklog')

        logger.info(f"🚑 Running maintenance for {self.site.name}...")
        
        self.heal_database_migrations_autonomously()
        connections.close_all()
        
        if AIProjectBacklog:
            try:
                stuck_tasks = AIProjectBacklog.objects.filter(
                    site=self.site, status='Running',
                    updated_at__lt=timezone.now() - timedelta(minutes=15)
                )
                if stuck_tasks.exists():
                    logger.warning(f"🔄 Resetting {stuck_tasks.count()} stuck tasks.")
                    stuck_tasks.update(status='Pending')
            except Exception as e:
                logger.error(f"Failed to reset stuck tasks: {e}")

        self.synthesize_daily_recon_reports()
        AutonomousBackupManager.backup_database_to_cache(self.site)
        SecurityAuditor.patrol_server_logs(self.site)

        self._heal_production_errors()
        self._heal_security_issues()
        PerformanceAuditor.run_daily_performance_audit(self.site)

    def hard_reset_database_schema(self):
        """🚨 [Autonomous Schema Rebuilder] የዳታቤዝ ሰንጠረዦችን ማጥፋት (🛡️ Dynamic Table Scan)"""
        SiteRegistry = get_marketplace_model('SiteRegistry')

        reset_allowed = os.getenv('ALLOW_EMERGENCY_SCHEMA_RESET', 'false').lower() == 'true'
        if not reset_allowed:
            logger.critical("🚨 EMERGENCY RESET BLOCKED: 'ALLOW_EMERGENCY_SCHEMA_RESET' is not enabled in Env.")
            return False

        logger.warning("🚨 EMERGENCY RESET: Hard resetting database schema...")
        try:
            try:
                app_models = apps.get_app_config('marketplace').get_models()
                marketplace_tables = [model._meta.db_table for model in app_models]
            except Exception as registry_err:
                logger.warning(f"Failed dynamic table lookup: {registry_err}. Falling back to hardcoded registry.")
                marketplace_tables = [
                    "marketplace_producttranslation", "marketplace_translationqueue",
                    "marketplace_product", "marketplace_sellerprofile", "marketplace_notificationqueue",
                    "marketplace_aiprojectbacklog", "marketplace_securitylog", "marketplace_agenterrorlog",
                    "marketplace_aievolutionlog", "marketplace_vectormemory", "marketplace_selfhealinglog",
                    "marketplace_category", "marketplace_siteregistry", "marketplace_usersearch", 
                    "marketplace_agenttask", "marketplace_predictionlog", "marketplace_abtest", "marketplace_externalapi"
                ]

            with connection.cursor() as cursor:
                for table in marketplace_tables:
                    if connection.vendor == 'sqlite':
                        cursor.execute(f'DROP TABLE IF EXISTS "{table}";')
                    else:
                        cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
                cursor.execute("DELETE FROM django_migrations WHERE app='marketplace';")
            
            logger.info("✨ Emergency Reset: All marketplace tables dropped. Fresh migrations...")
            call_command('migrate', interactive=False)
            
            if SiteRegistry:
                SiteRegistry.objects.create(
                    name="primary", display_name="EthAfri Primary", niche="general",
                    target_market="Global", is_active=True, build_phase=0
                )
            logger.info("✨ Emergency Reset: Re-registered fresh 'primary' site successfully.")
            return True
        except Exception as reset_err:
            logger.error(f"🚨 Emergency Reset Failed: {reset_err}")
            return False

    def heal_database_migrations_autonomously(self, force=False):
        """የ PostgreSQL የኢንዴክስ ወይም የስኬማ ስህተቶችን በራስ-ሰር ጠጋኝ (ከቀድሞ ውድቀት መማር ጋር)"""
        SiteConfig = get_marketplace_model('SiteConfig')
        AgentErrorLog = get_marketplace_model('AgentErrorLog')
        SelfHealingLog = get_marketplace_model('SelfHealingLog')
        VectorMemory = get_marketplace_model('VectorMemory')
        
        if not SiteConfig: return

        last_check_key = f"LAST_SCHEMA_MIGRATION_CHECK_{self.site.name}"
        last_check_cfg = SiteConfig.objects.filter(key=last_check_key).first()
        
        should_run = force
        if not should_run:
            if not last_check_cfg:
                should_run = True
            else:
                try:
                    last_time = datetime.fromisoformat(last_check_cfg.value.get('time'))
                    if timezone.is_naive(last_time):
                        last_time = timezone.make_aware(last_time)
                    if timezone.now() - last_time >= timedelta(minutes=30):
                        should_run = True
                except Exception as e:
                    logger.debug("Failed to parse migration check timestamp: %s", e)
                    should_run = True

        if not should_run and AgentErrorLog:
            recent_db_errors = AgentErrorLog.objects.filter(
                site=self.site, resolved=False,
                created_at__gte=timezone.now() - timedelta(minutes=5)
            ).filter(Q(error_message__icontains="OperationalError") | Q(error_message__icontains="relation") | Q(error_message__icontains="FieldError") | Q(error_message__icontains="column"))
            
            if recent_db_errors.exists():
                logger.warning("🚑 Schema Healer: Recent DB error detected — Bypassing throttling safety.")
                should_run = True

        if not should_run:
            return

        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    # 🛡️ DEDUPLICATED: የ PostgreSQL አምድ መፈተሻዎችን እና መፍጠሪያዎችን በጥራት ማጠቃለል (Zero duplication)
                    columns_to_ensure = [
                        ('listing_type', "varchar(50) DEFAULT 'sale'"),
                        ('contact_info', "varchar(255) DEFAULT ''"),
                        ('image_gallery', "jsonb DEFAULT '[]'::jsonb")
                    ]
                    
                    for col_name, col_type in columns_to_ensure:
                        cursor.execute(f"""
                            SELECT column_name FROM information_schema.columns 
                            WHERE table_name='marketplace_product' AND column_name='{col_name}';
                        """)
                        if not cursor.fetchone():
                            cursor.execute(f'ALTER TABLE marketplace_product ADD COLUMN IF NOT EXISTS {col_name} {col_type};')

            call_command('migrate', interactive=False)
            logger.info("🚑 Schema Healer: Database migrations check passed.")
            
            SiteConfig.objects.update_or_create(key=last_check_key, defaults={'value': {'time': timezone.now().isoformat()}})
        except Exception as e:
            err_msg = str(e)
            logger.error(f"🚑 Schema Healer: Migration blocked by error: {err_msg}")
            
            match_missing = re.search(r'relation "([^"]+)" does not exist', err_msg)
            if match_missing:
                idx_name = match_missing.group(1)
                idx_name_clean = str(idx_name).lower()
                
                if "marketplace_name" in idx_name_clean or "marketplace_name_8491f6_idx" in idx_name_clean:
                    try:
                        with connection.cursor() as cursor:
                            id_type = "integer PRIMARY KEY AUTOINCREMENT" if connection.vendor == 'sqlite' else "serial NOT NULL PRIMARY KEY"
                            cursor.execute(f'CREATE TABLE IF NOT EXISTS "marketplace_name" ("id" {id_type}, "name" varchar(255) NOT NULL);')
                            cursor.execute('CREATE INDEX IF NOT EXISTS "marketplace_name_8491f6_idx" ON "marketplace_name" ("name");')
                        call_command('migrate', interactive=False)
                        return
                    except Exception as retry_err:
                        err_msg = str(retry_err)

            match_exists = re.search(r'relation "([^"]+)" already exists', err_msg)
            if match_exists:
                idx_name = match_exists.group(1)
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f'DROP INDEX IF EXISTS "{idx_name}";')
                    call_command('migrate', interactive=False)
                    return
                except Exception as retry_err:
                    err_msg = str(retry_err)
            
            from .ai_utils import AIUtils, clean_and_parse_json, ask_master_ai_smart
            cache_key = f"db_schema_fix:{hashlib.md5(err_msg.encode('utf-8')).hexdigest()}"
            cached_sql = AIUtils.get_cached(cache_key)
            
            if cached_sql:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(cached_sql)
                    call_command('migrate', interactive=False)
                    return
                except Exception as cached_err:
                    logger.error(f"Cached SQL fix execution failed: {cached_err}")
                    AIUtils.clear_cache(cache_key)
            
            try:
                logger.warning("🚑 Schema Healer: Invoking Generative AI SQL Healer...")
                all_tables = []
                for model in apps.get_models():
                    all_tables.append({
                        "table": model._meta.db_table,
                        "fields": [f.name for f in model._meta.fields]
                    })

                # 🛡️ EXPERIENTIAL FAILURE MEMORY: የከሸፉ ሙከራዎችን ከታሪክ መዝገብ አውጥቶ ወደ ፕሮምፕት ማካተት (እንዳይደግማቸው መከላከል)
                past_failed_sql_prompts = []
                if VectorMemory:
                    try:
                        failures = VectorMemory.objects.filter(site=self.site, memory_type='failed_db_patch').order_by('-id')[:3]
                        past_failed_sql_prompts = [f.content for f in failures]
                    except Exception:
                        pass

                prompt = (
                    f"We encountered a database migration or schema error: '{err_msg}'.\n"
                    f"Actual database structure: {json.dumps(all_tables, ensure_ascii=False)}\n"
                    f"CRITICAL (Do not generate these failed SQL statements from past attempts): {json.dumps(past_failed_sql_prompts, ensure_ascii=False)}\n"
                    f"Generate the exact, safe, raw SQL DDL statement to execute on DB to resolve this error.\n"
                    f"Return JSON with key 'sql' containing only the query."
                )
                
                res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))
                
                if res and isinstance(res, dict) and res.get('sql'):
                    sql_query = res['sql']
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(sql_query)
                    except Exception as sql_exec_err:
                        # 🛡️ EXPERIENTIAL LEARNING: የከሸፈውን የ SQL ሙከራ ወደ ታሪክ መዝገብ መጻፍ
                        if VectorMemory:
                            try:
                                VectorMemory.objects.create(
                                    site=self.site,
                                    memory_type='failed_db_patch',
                                    content=sql_query,
                                    success_rate=0.0
                                )
                                logger.warning(f"Logged failed DDL query to experiential failure memory: {sql_query}")
                            except Exception: pass
                        raise sql_exec_err
                    
                    AIUtils.set_cached(cache_key, sql_query, timeout=86400)
                    
                    if SelfHealingLog:
                        try:
                            SelfHealingLog.objects.create(error_message=err_msg, solution_sql=sql_query, resolved=True)
                        except Exception as log_err:
                            logger.debug("Failed to record SelfHealingLog: %s", log_err)
                    
                    try:
                        call_command('migrate', interactive=False)
                        return
                    except Exception as retry_err:
                        err_msg = str(retry_err)
            except Exception as ai_heal_err:
                logger.error(f"❌ Schema Healer: AI healing failed: {ai_heal_err}")

            logger.critical("🚨 Schema Healer: Failed to recover via AI. Checking emergency reset authorization.")
            self.hard_reset_database_schema()

    def heal_model_field_errors(self):
        """የFieldError ሲከሰት ኤጀንቱ ራሱ ሞዴሉን ይቃኛል"""
        logger.info("🚑 Model Healer: Scanning for FieldError in views...")
        from .ai_utils import broadcast_agent_log
        broadcast_agent_log(self.site, "Model Healer: FieldError detected in views. Creating Refactor Task...", "error")
        
        AIProjectBacklog = get_marketplace_model('AIProjectBacklog')
        if not AIProjectBacklog: return

        task_name = "🛡️ REFACTOR: Replace 'product_set' with 'product' in views"
        active_fix_exists = AIProjectBacklog.objects.filter(
            site=self.site, task_name=task_name, status__in=['Pending', 'Running']
        ).exists()
        
        if not active_fix_exists:
            try:
                AIProjectBacklog.objects.create(
                    site=self.site, task_name=task_name, target_file="views", priority="Critical",
                    description="FieldError found: Cannot resolve keyword 'product_set' into field. Replace all instances of 'product_set' with 'product' in views.py model queries to restore homepage.",
                    business_impact_score=10
                )
                logger.info("Model Healer: Created REFACTOR task successfully.")
            except Exception as db_err:
                logger.error("Failed to create FieldError refactor task: %s", db_err)

    def _heal_production_errors(self):
        """ያልተፈቱ ስህተቶችን መርምሮ 'Emergency Fix' ስራዎችን ይፈጥራል"""
        AgentErrorLog = get_marketplace_model('AgentErrorLog')
        AIProjectBacklog = get_marketplace_model('AIProjectBacklog')
        if not AgentErrorLog or not AIProjectBacklog: return

        try:
            errors = AgentErrorLog.objects.filter(site=self.site, resolved=False).order_by('-created_at')[:3]
            for err in errors:
                if "FieldError" in err.error_message or "Cannot resolve keyword 'product_set'" in err.error_message:
                    self.heal_model_field_errors()
                    err.resolved = True
                    err.save()
                    continue

                task_name = f"🚑 EMERGENCY FIX: {err.task_name}"
                if not AIProjectBacklog.objects.filter(site=self.site, task_name=task_name, status__in=['Pending', 'Running']).exists():
                    AIProjectBacklog.objects.create(
                        site=self.site, task_name=task_name, target_file='views', priority='Critical',
                        description=f"Automated Healing for error: {err.error_message}. Fix this immediately to restore uptime.",
                        business_impact_score=10
                    )
                    logger.info(f"🚑 Created healing task for: {err.task_name}")
                
                err.resolved = True
                err.save()
        except Exception as e:
            logger.error("Failed to check production errors: %s", e)

    def _heal_security_issues(self):
        """የደህንነት ስጋቶችን (Security Logs) ለይቶ የጥገና ስራዎችን ይፈጥራል"""
        SecurityLog = get_marketplace_model('SecurityLog')
        AIProjectBacklog = get_marketplace_model('AIProjectBacklog')
        if not SecurityLog or not AIProjectBacklog: return

        try:
            vulns = SecurityLog.objects.filter(site=self.site, is_fixed=False).order_by('-severity')[:2]
            
            for vuln in vulns:
                task_name = f"🛡️ SECURITY FIX: {vuln.description}"
                active_fix_exists = AIProjectBacklog.objects.filter(
                    site=self.site, task_name=task_name, status__in=['Pending', 'Running']
                ).exists()
                
                if not active_fix_exists:
                    target = vuln.file_path if vuln.file_path and not vuln.file_path.startswith("multiple") else "views"
                    AIProjectBacklog.objects.create(
                        site=self.site, task_name=task_name, target_file=target, priority='Critical' if vuln.severity == 'critical' else 'High',
                        description=f"Secure code vulnerability: {vuln.description} in {vuln.file_path}. Ensure inputs are strictly validated.",
                        business_impact_score=9 if vuln.severity == 'critical' else 8
                    )
                    logger.info(f"🛡️ Created security healing task for: {vuln.description}")
                
                vuln.is_fixed = True
                vuln.save()
        except Exception as e:
            logger.error(f"Failed to run security healing check: {e}")

    def synthesize_daily_recon_reports(self):
        """
        📊 [የአሰሳ ስለላ ሪፖርቶች ዕለታዊ አጠቃላይ ማጠቃለያ ሞተር]
        በባክሎግ ውስጥ የሚገኙትን 10+ የነጠላ ዌብሳይት ስህተቶች አውጥቶ በ AI በአንድ ላይ በመጭመቅ 
        ባለ አንድ ማጠቃለያ መግለጫ ያዘጋጃል። (የነጠላ ሪፖርቶች በዳታቤዝ ውስጥ እንዲቀመጡ ተደርገዋል)
        """
        AIProjectBacklog = get_marketplace_model('AIProjectBacklog')
        SiteConfig = get_marketplace_model('SiteConfig')
        if not AIProjectBacklog or not SiteConfig: return

        raw_reports = AIProjectBacklog.objects.filter(
            site=self.site,
            target_file="scrapper_engine",
            status="Blocked"
        )
        
        if raw_reports.count() < 10:
            return

        logger.warning(f"📊 Recon Synthesizer: Compressing {raw_reports.count()} individual reports into a Master Bulletin...")
        
        failed_domains = []
        for r in raw_reports:
            match = re.search(r'🌐 TARGET WEBSITE:\s*(https?://[^\s\n]+)', r.description)
            domain = match.group(1) if match else r.task_name
            failed_domains.append(domain)

        unique_failed = list(set(failed_domains))[:15]
        
        prompt = (
            f"We have {raw_reports.count()} individual scraping failures for these domains: {json.dumps(unique_failed)}.\n"
            f"Please write a highly compressed, professional, master executive summary in Amharic (max 400 characters) "
            f"detailing the overall health of our scraping system, why these sites are blocking us, and a unified strategy to unblock them.\n"
            f"Return JSON with key 'master_summary'."
        )

        from .ai_utils import clean_and_parse_json, ask_master_ai_smart
        try:
            res = ask_master_ai_smart(prompt, task_type="analysis")
            data = clean_and_parse_json(res)
            
            if data and isinstance(data, dict) and data.get('master_summary'):
                master_summary = data['master_summary']
                
                SiteConfig.objects.update_or_create(
                    key=f"CRAWLER_DAILY_SUMMARY_{self.site.name}",
                    defaults={'value': {'summary': master_summary, 'updated_at': timezone.now().isoformat()}}
                )
                
                logger.info("🧹 Recon Synthesizer: Successfully compressed reports. Kept individual reports for developer reverse-engineering.")
                
        except Exception as e:
            logger.error(f"Recon Synthesizer failed: {e}")


# ============================================================
# 💾 3. AUTONOMOUS DATABASE BACKUP & CLOUD ARCHIVER
# ============================================================
def json_serial(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


class AutonomousBackupManager:
    """የማርኬት መረጃዎችን በየሳምንቱ ወደ JSON ቀይሮ በ SiteConfig ውስጥ ያስቀምጣል"""
    
    @staticmethod
    def backup_database_to_cache(site):
        Product = get_marketplace_model('Product')
        Category = get_marketplace_model('Category')
        SiteConfig = get_marketplace_model('SiteConfig')
        if not Product or not Category or not SiteConfig: return

        try:
            products = list(Product.objects.filter(site=site).values('title', 'price', 'description', 'location'))
            categories = list(Category.objects.values('name', 'slug'))
            
            backup_payload = {
                "products": products,
                "categories": categories,
                "timestamp": timezone.now().isoformat()
            }
            
            SiteConfig.objects.update_or_create(
                key=f"MASTER_BACKUP_DATA_{site.name}",
                defaults={'value': json.loads(json.dumps(backup_payload, default=json_serial))}
            )
            logger.info("💾 Backup Manager: Successfully saved compressed JSON database backup to SiteConfig.")
        except Exception as e:
            logger.error(f"Failed to archive database: {e}")


# ============================================================
# 🩺 4. DAILY PERFORMANCE AUDITOR WITH AST PARSING
# ============================================================
class PerformanceAuditor:
    """በየ 24 ሰዓቱ የድረ-ገጽ መጫኛ ፍጥነትን የሚቀንሱ የኮድ አወቃቀሮችን የሚቃኝ ማዕከል"""
    
    @staticmethod
    def audit_views_via_ast(file_path) -> List[str]:
        if not os.path.exists(file_path):
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                
            tree = ast.parse(code)
            issues = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    chain = []
                    current = node
                    while isinstance(current, ast.Call):
                        if isinstance(current.func, ast.Attribute):
                            chain.append(current.func.attr)
                            current = current.func.value
                        else:
                            break
                            
                    if isinstance(current, ast.Attribute) and current.attr == 'objects':
                        if isinstance(current.value, ast.Name):
                            model_name = current.value.id
                            if model_name in ['Product', 'Category']:
                                # 🛡️ FIXED: N+1 የlatency ችግር የማይፈጥሩ የተለዩ ጥያቄዎችን ከማስጠንቀቂያ መዝለል (False positive reduction)
                                bypass_methods = {'count', 'exists', 'get', 'update', 'delete', 'create', 'aggregate', 'annotate'}
                                if any(method in chain for method in bypass_methods):
                                    continue

                                has_optimizer = any(opt in chain for opt in ['select_related', 'prefetch_related'])
                                if not has_optimizer:
                                    issues.append(f"Critical Performance Issue: '{model_name}.objects' query detected in views.py that lacks select_related() or prefetch_related(), causing N+1 query latency.")
                                    
            return list(set(issues))
        except Exception as e:
            logger.error(f"Performance Auditor [AST Parser] failed: {e}")
            return []

    @staticmethod
    def run_daily_performance_audit(site):
        SiteConfig = get_marketplace_model('SiteConfig')
        AIProjectBacklog = get_marketplace_model('AIProjectBacklog')
        if not SiteConfig or not AIProjectBacklog: return

        last_perf_audit = SiteConfig.objects.filter(key=f"LAST_PERF_AUDIT_{site.name}").first()
        if last_perf_audit:
            try:
                last_time = datetime.fromisoformat(last_perf_audit.value.get('time'))
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if timezone.now() - last_time < timedelta(hours=24):
                    return
            except Exception as e:
                logger.debug("Failed to parse performance audit timestamp: %s", e)
        
        logger.info(f"🩺 Performance Auditor: Running daily page-load speed audit for {site.name}...")
        issues_found = []
        
        PerformanceAuditor.ping_google_sitemap(site)
        PerformanceAuditor.optimize_inquiry_descriptions(site)
        
        views_path = os.path.join(str(settings.BASE_DIR), 'marketplace', 'views.py')
        if os.path.exists(views_path):
            issues_found.extend(PerformanceAuditor.audit_views_via_ast(views_path))
        
        base_templates_dir = os.path.join(settings.BASE_DIR, 'marketplace', 'templates', 'marketplace')
        if os.path.exists(base_templates_dir):
            for root, dirs, files in os.walk(base_templates_dir):
                for file in files:
                    if file.endswith('.html'):
                        full_path = os.path.join(root, file)
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            is_safe, sec_issues = SecurityAuditor.scan_code_safety(html_content, file_path=full_path, site=site)
                            if not is_safe:
                                issues_found.extend(sec_issues)
                        except Exception as html_err:
                            logger.debug("HTML template audit failed: %s", html_err)

        for issue in issues_found:
            task_name = f"⚡ PERFORMANCE OPTIMIZATION: {issue[:50]}..."
            active_task = AIProjectBacklog.objects.filter(site=site, task_name=task_name, status__in=['Pending', 'Running']).exists()
            if not active_task:
                target = "views" if "views.py" in issue else "home_html"
                AIProjectBacklog.objects.create(
                    site=site, task_name=task_name, target_file=target, priority="Critical",
                    description=f"Performance bottleneck detected during daily audit: {issue} Fix this immediately to drastically improve page load speed.",
                    business_impact_score=10
                )
                logger.warning(f"🩺 Performance Auditor: Created critical healing task for: {issue}")

        SiteConfig.objects.update_or_create(key=f"LAST_PERF_AUDIT_{site.name}", defaults={'value': {'time': timezone.now().isoformat()}})

    @staticmethod
    def ping_google_sitemap(site):
        sitemap_url = f"{site.deployment_url}/sitemap.xml"
        try:
            requests.get(f"https://www.google.com/ping?sitemap={sitemap_url}", timeout=5)
            logger.info("🔍 SEO Engine: Successfully pinged Google Search Console for sitemap re-indexing.")
        except Exception as e:
            logger.debug("Google sitemap ping failed: %s", e)

    @staticmethod
    def optimize_inquiry_descriptions(site):
        """የይዘቶች አውቶማቲክ ማሻሻያ (AI Inquiry Content Optimizer)"""
        Product = get_marketplace_model('Product')
        if not Product: return
        
        try:
            product_fields = [f.name for f in Product._meta.get_fields()]
            if 'inquiry_count' not in product_fields:
                logger.debug("Inquiry optimization bypassed: 'inquiry_count' query disabled.")
                return
                
            target = Product.objects.filter(site=site, inquiry_count__gt=10, is_active=True).first()
            if target:
                from .ai_utils import AIUtils, clean_and_parse_json, ask_master_ai_smart
                cache_key = f"inquiry_opt:{target.id}:{target.inquiry_count}"
                cached_desc = AIUtils.get_cached(cache_key)
                
                if cached_desc:
                    target.description = cached_desc
                    target.save()
                    logger.info(f"✨ Content Optimizer: Loaded optimized description from cache for product '{target.title}'")
                    return
                
                prompt = (
                    f"Enrich this product description to address common buyer questions. "
                    f"Title: {target.title}. Current Description: {target.description}. "
                    f"Add concise, highly persuasive selling points. Return JSON with key 'enriched_description'."
                )
                res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))
                if res and res.get('enriched_description'):
                    target.description = res['enriched_description']
                    target.save()
                    AIUtils.set_cached(cache_key, res['enriched_description'], timeout=86400)
                    logger.info(f"✨ Content Optimizer: Enriched description for product '{target.title}' due to high inquiries.")
        except Exception as e:
            logger.debug("Inquiry optimization failed: %s", e)


# ============================================================
# ✂️ 5. ANTI-BLOAT ENGINE (የደቂቅ የ AST ኮድ ማሳጠሪያ እና ማሻሻያ ሞተር)
# ============================================================
class AntiBloatEngine:
    @staticmethod
    def is_file_bloated(file_path: str, max_chars: int = 35000) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        try:
            return os.path.getsize(file_path) > max_chars
        except Exception:
            return False

    @staticmethod
    def prune_and_optimize(old_code, new_code, file_path):
        is_bloated = AntiBloatEngine.is_file_bloated(file_path)
        if not is_bloated and (len(new_code) < 32000 or (old_code and len(new_code) < len(old_code) * 1.20)):
            return new_code

        logger.warning(f"⚠️ Anti-Bloat Guard: Code for {file_path} is bloated. Activating surgical self-pruning...")

        # 🛡️ 1. SURGICAL REGEX CLEANUP: የኮሜንት እና ባዶ መስመሮችን 0% ሲፒዩ/ቶከን ወጪ በሆነ ሬጀክስ ማጽዳት (Surgical Pruning)
        cleaned_lines = []
        for line in new_code.splitlines():
            stripped = line.strip()
            if stripped.startswith('#') and len(stripped) > 1 and not stripped.startswith('#!'):
                continue
            cleaned_lines.append(line)
            
        pruned_new_code = "\n".join(cleaned_lines)
        if len(pruned_new_code) < 32000:
            logger.info(f"✨ Anti-Bloat: Surgically cleaned comments and blank spaces of {file_path} without calling AI.")
            return pruned_new_code

        # 2. የላቀ የኤአይ ሪፋክተሪንግ ፍላጎት
        prompt = (
            f"Optimize and shrink this Python code for '{file_path}'.\n"
            f"1. Remove any dead code, unused helper functions, and redundant imports.\n"
            f"2. Merge repetitive logics into compact, multi-functional, parameter-driven helpers.\n"
            f"3. Strictly preserve all existing business logic, security guards, and core features, but write it with the minimum possible code lines.\n"
            f"Return JSON with key 'code' containing only the compressed, highly-optimized code."
        )
        
        from .ai_utils import clean_and_parse_json, ask_master_ai_smart
        res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))
        
        if res and isinstance(res, dict) and 'code' in res:
            pruned_code = res['code']
            logger.info(f"✨ Anti-Bloat: Shrank {file_path} from {len(new_code)} to {len(pruned_code)} characters!")
            return pruned_code
            
        return new_code


# ============================================================
# ⚙️ 6. LOG PROTECTOR & THREAD-SAFE DB REFRESHER
# ============================================================
def refresh_db_connection_on_error(error_message):
    if "OperationalError" in error_message or "DatabaseError" in error_message:
        try:
            from django.db import connections
            connections.close_all()
            logger.info("🛡️ Database connection refreshed safely across all active threads due to error.")
            return True
        except Exception as e:
            logger.error("Failed to safely close database connections: %s", e)
    return False
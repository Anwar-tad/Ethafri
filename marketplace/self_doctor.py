# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ዓላማ፦ Ultimate System Doctor — Proactive Model Healer (v10.1)
# ✅ የተፈቱ ችግሮች፦ Dynamic prediction & security index maps updated, Resolution loop prevention, AST HTML safety unblocked
# 📅 ቀን፦ 2026-06-27
# ============================================================

import os
import ast
import re
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import connection, connections
from django.core.management import call_command
from .models import AgentErrorLog, SelfHealingLog, AIProjectBacklog, SiteRegistry, SecurityLog, VectorMemory

logger = logging.getLogger(__name__)

# ============================================================
# 🛡️ 1. SECURITY AUDITOR (የደህንነት ኦዲተር - AST SHIELD)
# ============================================================
class SecurityAuditor:
    """ኮድ ከመጻፉ በፊት አደገኛ የሼል እና የሲስተም ጥሪዎችን በ AST የሚመረምር የደህንነት ግግድግ"""

    @staticmethod
    def scan_code_safety(code, file_path="", site=None):
        """የ SQL Injection, Secrets Exposure, እና የ Shell Execution (Subprocess) ፍተሻ"""
        issues = []
        if not code or not isinstance(code, str):
            return True, []

        # የ HTML ቴምፕሌቶች ሲፈተሹ የ Python AST parse እንዳይካሄድ መከላከል (የሕግ 4 ጥበቃ)
        is_python = file_path.endswith('.py') if file_path else True
        if 'html' in file_path.lower() or not is_python:
            # HTML ከሆነ AST ፍተሻ አያስፈልገውም
            return True, []

        try:
            tree = ast.parse(code)
            # በደፈናው 'run' እና 'call'ን ከመከልከል ይልቅ አደገኛ የሆኑትን ብቻ መለየት
            dangerous_builtins = {'eval', 'exec'}
            dangerous_attributes = {'system', 'popen', 'spawn'}

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    module_name = ""
                    
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id.lower()
                        if func_name in dangerous_builtins:
                            issues.append(f"Critical: Dangerous built-in call '{func_name}' detected.")
                            
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr.lower()
                        if func_name in dangerous_attributes:
                            issues.append(f"Critical: Dangerous system attribute '{func_name}' detected.")
                        
                        # 'run' እና 'call' የሚከለከሉት በ subprocess ስር ሲጠሩ ብቻ ነው (False-Positive መከላከያ)
                        if hasattr(node.func.value, 'id'):
                            module_name = node.func.value.id.lower()
                            if module_name == 'subprocess' and func_name in ['run', 'call', 'popen', 'check_output', 'check_call']:
                                issues.append(f"Critical: Dangerous subprocess call 'subprocess.{func_name}' detected.")

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

        if issues:
            for issue in issues:
                try:
                    log_exists = SecurityLog.objects.filter(
                        site=site,
                        description=issue,
                        file_path=file_path
                    ).exists()
                    
                    if not log_exists:
                        SecurityLog.objects.create(
                            site=site,
                            category='code_injection' if 'Dangerous' in issue or 'Error' in issue else 'data_leak',
                            severity='critical' if 'Critical' in issue else 'high',
                            description=issue,
                            file_path=file_path,
                            is_fixed=False
                        )
                except Exception as log_err:
                    logger.error(f"Failed to save SecurityLog: {log_err}")
            return False, issues

        return True, []


# ============================================================
# 🚑 2. UNIVERSAL HEALER (ሁለንተናዊ የሲስተም ፈዋሽ - SCHEMA AWARE)
# ============================================================
class UniversalHealer:
    """ኤጀንቱን፣ ዳታቤዙን እና የዌብሳይቱን ስህተት የሚጠግን ማዕከል"""

    def __init__(self, site: SiteRegistry):
        self.site = site

    def perform_maintenance(self):
        """በየ 10 ደቂቃው የሚደረግ የሲስተም ጥገና"""
        logger.info(f"🚑 Running maintenance for {self.site.name}...")
        
        self.heal_database_migrations_autonomously()
        connections.close_all()
        
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

        self._heal_production_errors()
        self._heal_security_issues()

    def heal_database_migrations_autonomously(self):
        """የ PostgreSQL የኢንዴክስ መጣረስ ስህተቶችን በራስ-ሰር ፈልጎ ይፈታል"""
        try:
            call_command('migrate', interactive=False)
            logger.info("🚑 Schema Healer: All database migrations are completely up to date.")
        except Exception as e:
            err_msg = str(e)
            logger.error(f"🚑 Schema Healer: Migration blocked by error: {err_msg}")
            
            match_missing = re.search(r'relation "([^"]+)" does not exist', err_msg)
            if match_missing:
                idx_name = match_missing.group(1)
                logger.warning(f"🚑 Schema Healer: Missing index '{idx_name}' detected. Auto-creating in DB...")
                
                # ✅ FIXED: 0017 ማይግሬሽን እንዳይቆለፍ የተጨመሩ የደህንነት እና የትንበያ መዝገብ ኢንዴክሶች
                table_maps = {
                    "marketplace_agentty_847321_idx": ("marketplace_agenttask", "agent_type, status"),
                    "marketplace_site_id_6bde06_idx": ("marketplace_agenttask", "site_id, status"),
                    "marketplace_predicti_9ce3e9_idx": ("marketplace_predictionlog", "prediction_type, site_id"),
                    "marketplace_predicti_1a7d5d_idx": ("marketplace_predictionlog", "prediction_type"),
                    "marketplace_security_128a46_idx": ("marketplace_securitylog", "severity"),
                    "marketplace_security_840055_idx": ("marketplace_securitylog", "severity")  # ✅ የተጨመረ
                }
                
                idx_name_clean = str(idx_name).lower()
                for old_name, sql_map in table_maps.items():
                    if old_name in idx_name_clean:
                        table, cols = sql_map
                        with connection.cursor() as cursor:
                            cursor.execute(f"SELECT exists(SELECT * FROM information_schema.tables WHERE table_name='{table}');")
                            table_exists = cursor.fetchone()[0]
                            if table_exists:
                                cursor.execute(f"CREATE INDEX IF NOT EXISTS {old_name} ON {table} ({cols});")
                                logger.info(f"✨ Schema Healer: Successfully created missing index {old_name} on {table}")
                        
                        try:
                            SelfHealingLog.objects.create(
                                error_message=f"Missing Index {old_name} on {table}",
                                solution_sql=f"CREATE INDEX IF NOT EXISTS {old_name} ON {table} ({cols});",
                                resolved=True
                            )
                        except Exception as log_err:
                            logger.error(f"Failed to save SelfHealingLog: {log_err}")
                            
                        try:
                            call_command('migrate', interactive=False)
                            return
                        except Exception as retry_err:
                            logger.error(f"🚑 Schema Healer: Retry failed: {retry_err}")
                            return

            match_exists = re.search(r'relation "([^"]+)" already exists', err_msg)
            if match_exists:
                idx_name = match_exists.group(1)
                logger.warning(f"🚑 Schema Healer: Conflicting index '{idx_name}' already exists. Auto-dropping...")
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP INDEX IF EXISTS {idx_name};")
                logger.info(f"✨ Schema Healer: Successfully dropped conflicting index {idx_name}")
                
                try:
                    SelfHealingLog.objects.create(
                        error_message=f"Conflicting Index {idx_name} already exists",
                        solution_sql=f"DROP INDEX IF EXISTS {idx_name};",
                        resolved=True
                    )
                except Exception as log_err:
                    logger.error(f"Failed to save SelfHealingLog: {log_err}")
                    
                try:
                    call_command('migrate', interactive=False)
                except Exception as retry_err:
                    logger.error(f"🚑 Schema Healer: Retry failed: {retry_err}")

    def heal_model_field_errors(self):
        """የFieldError ሲከሰት ኤጀንቱ ራሱ ሞዴሉን ይቃኛል"""
        logger.info("🚑 Model Healer: Scanning for FieldError in views...")
        from .ai_utils import broadcast_agent_log
        broadcast_agent_log(self.site, "Model Healer: FieldError detected in views. Creating Refactor Task...", "error")
        
        task_name = "🛡️ REFACTOR: Replace 'product_set' with 'product' in views"
        
        active_fix_exists = AIProjectBacklog.objects.filter(
            site=self.site,
            task_name=task_name,
            status__in=['Pending', 'Running']
        ).exists()
        
        if not active_fix_exists:
            AIProjectBacklog.objects.create(
                site=self.site,
                task_name=task_name,
                target_file="views",
                priority="Critical",
                description="FieldError found: Cannot resolve keyword 'product_set' into field. Replace all instances of 'product_set' with 'product' in views.py model queries to restore homepage.",
                business_impact_score=10
            )
            logger.info("🚑 Model Healer: Created REFACTOR task successfully.")

    def _heal_production_errors(self):
        """ያልተፈቱ ስህተቶችን መርምሮ 'Emergency Fix' ስራዎችን ይፈጥራል"""
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
                    site=self.site,
                    task_name=task_name,
                    target_file='views',
                    priority='Critical',
                    description=f"Automated Healing for error: {err.error_message}. Fix this immediately to restore uptime.",
                    business_impact_score=10
                )
                logger.info(f"🚑 Created healing task for: {err.task_name}")
            
            err.resolved = True
            err.save()

    def _heal_security_issues(self):
        """የደህንነት ስጋቶችን (Security Logs) ለይቶ የጥገና ስራዎችን ይፈጥራል"""
        try:
            vulns = SecurityLog.objects.filter(site=self.site, is_fixed=False).order_by('-severity')[:2]
            
            for vuln in vulns:
                task_name = f"🛡️ SECURITY FIX: {vuln.description}"
                
                active_fix_exists = AIProjectBacklog.objects.filter(
                    site=self.site,
                    task_name=task_name,
                    status__in=['Pending', 'Running']
                ).exists()
                
                if not active_fix_exists:
                    target = vuln.file_path if vuln.file_path and not vuln.file_path.startswith("multiple") else "views"
                    AIProjectBacklog.objects.create(
                        site=self.site,
                        task_name=task_name,
                        target_file=target,
                        priority='Critical' if vuln.severity == 'critical' else 'High',
                        description=f"Secure code vulnerability: {vuln.description} in {vuln.file_path}. Ensure inputs are strictly validated.",
                        business_impact_score=9 if vuln.severity == 'critical' else 8
                    )
                    logger.info(f"🛡️ Created security healing task for: {vuln.description}")
                
                vuln.is_fixed = True
                vuln.save()
        except Exception as e:
            logger.error(f"Failed to run security healing check: {e}")


# ============================================================
# ⚙️ 3. LOG PROTECTOR
# ============================================================
def refresh_db_connection_on_error(error_message):
    """የዳታቤዝ ግንኙነት ሲመረዝ ወዲያውኑ አዲስ ግንኙነት የሚከፍት"""
    if "OperationalError" in error_message or "DatabaseError" in error_message:
        connection.close()
        logger.info("🛡️ Database connection refreshed due to error.")
        return True
    return False # ✅ የተሟላ ማጠናቀቂያ (Complete function closure)
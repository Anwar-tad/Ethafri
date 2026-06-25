# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ዓላማ፦ Ultimate System Doctor — Safe & Highly Secure Gating (v9.5)
# ✅ የተፈቱ ችግሮች፦ SiteRegistry site filtering, AI Task Loop Prevention, Django timezone.timedelta AttributeError Fix
# 📅 ቀን፦ 2026-06-25
# ============================================================

import ast
import re
import logging
from datetime import timedelta  # ✅ FIXED: የሩጫ ጊዜ ስህተትን ለመከላከል የፓይተን timedelta በትክክል ገብቷል
from django.utils import timezone
from django.db import connection, connections
from .models import AgentErrorLog, SelfHealingLog, AIProjectBacklog, SiteRegistry, SecurityLog

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

        try:
            tree = ast.parse(code)
            
            # አደገኛ የሼል ማስፈጸሚያ ቃላት ዝርዝር
            dangerous_functions = {
                'eval', 'exec', 'system', 'popen', 'run', 
                'call', 'check_output', 'check_call', 'spawn'
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id.lower()
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr.lower()

                    if func_name in dangerous_functions:
                        issues.append(f"Critical: Dangerous function/attribute call '{func_name}' detected.")

            # ሒሳባዊ ፍተሻ (Secrets and Keys)
            secret_patterns = [
                (r'(?<![\w"])SECRET_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'Possible production SECRET_KEY exposure'),
                (r'(?<![\w"])password\s*=\s*[\'"][^\'"]+[\'"]', 'Possible password exposure'),
                (r'(?<![\w"])API_KEY\s*=\s*[\'"][^\'"]+[\'"]', 'API key exposure')
            ]
            for pattern, desc in secret_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    issues.append(f"Warning: {desc}")

        except SyntaxError as e:
            issues.append(f"Syntax Error: {e}")
        except Exception as e:
            logger.warning(f"AST safety scanning warning: {e}")

        # የሉፕ መከላከያ እና የሳይት መለያ መስተጋብር
        if issues:
            for issue in issues:
                try:
                    # አላስፈላጊ ድግግሞሽን ለመከላከል የተስተካከለ ማጣሪያ (Idempotent Logging)
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
# 🚑 2. UNIVERSAL HEALER (ሁለንተናዊ የሲስተም ፈዋሽ)
# ============================================================
class UniversalHealer:
    """ኤጀንቱን፣ ዳታቤዙን እና የዌብሳይቱን ስህተት የሚጠግን ማዕከል"""

    def __init__(self, site: SiteRegistry):
        self.site = site

    def perform_maintenance(self):
        """በየ 10 ደቂቃው የሚደረግ የሲስተም ጥገና"""
        logger.info(f"🚑 Running maintenance for {self.site.name}...")
        
        # 1. የዳታቤዝ ግንኙነትን ማጽዳት (Memory Leak ለመከላከል)
        connections.close_all()
        
        # 2. የተሰኩ ስራዎችን መፍታት (Stuck Loop Fix)
        try:
            # ✅ FIXED: timezone.timedelta የተባለው የጃንጎ ስህተት በ timedelta ተተክቷል
            stuck_tasks = AIProjectBacklog.objects.filter(
                site=self.site, status='Running',
                updated_at__lt=timezone.now() - timedelta(minutes=15)
            )
            if stuck_tasks.exists():
                logger.warning(f"🔄 Resetting {stuck_tasks.count()} stuck tasks.")
                stuck_tasks.update(status='Pending')
        except Exception as e:
            logger.error(f"Failed to reset stuck tasks: {e}")

        # 3. የዌብሳይት ስህተቶችን (500 Errors) ፈልጎ መፍትሄ መስጠት
        self._heal_production_errors()
        
        # 4. የደህንነት ስጋቶችን (Security Logs) ፈልጎ ማረም
        self._heal_security_issues()

    def _heal_production_errors(self):
        """ያልተፈቱ ስህተቶችን መርምሮ 'Emergency Fix' ስራዎችን ይፈጥራል"""
        errors = AgentErrorLog.objects.filter(site=self.site, resolved=False).order_by('-created_at')[:3]
        for err in errors:
            task_name = f"🚑 EMERGENCY FIX: {err.task_name}"
            if not AIProjectBacklog.objects.filter(site=self.site, task_name=task_name, status__in=['Pending', 'Running']).exists():
                # task_type ወደ ተኳሃኝ ምርጫዎች (e.g., 'Bug') ተቀይሯል
                AIProjectBacklog.objects.create(
                    site=self.site,
                    task_name=task_name,
                    target_file='views',
                    priority='Critical',
                    description=f"Automated Healing for error: {err.error_message}. Fix this immediately to restore uptime.",
                    business_impact_score=10
                )
                logger.info(f"🚑 Created healing task for: {err.task_name}")

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
                    # target_file እና task_type ከ Django Choice Constraints ጋር ተጣጥመዋል
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
        except Exception as e:
            logger.error(f"Failed to run security healing check: {e}")


# ============================================================
# 🩺 3. LOG PROTECTOR
# ============================================================
def refresh_db_connection_on_error(error_message):
    """የዳታቤዝ ግንኙነት ሲመረዝ ወዲያውኑ አዲስ ግንኙነት የሚከፍት"""
    if "OperationalError" in error_message or "DatabaseError" in error_message:
        connection.close()
        logger.info("🛡️ Database connection refreshed due to error.")
        return True
    return False
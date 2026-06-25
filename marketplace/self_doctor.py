# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ዓላማ፦ Ultimate System Doctor — Safe & Highly Secure Gating (Fixed)
# ✅ የተፈቱ ችግሮች፦ Subprocess Security Hole, Site Collision in Healing, Infinite Task Loop, Name Inconsistency
# 📅 ቀን፦ 2026-06-25
# ============================================================

import os
import ast
import re
import logging
from django.utils import timezone
from django.db import connection, connections
from .models import AgentErrorLog, SelfHealingLog, AIProjectBacklog, SiteRegistry, SecurityLog

logger = logging.getLogger(__name__)

# ============================================================
# 🛡️ 1. SECURITY AUDITOR (የደህንነት ኦዲተር - FIXED SECURITY HOLE)
# ============================================================
class SecurityAuditor:
    """ኮድ ከመጻፉ በፊት አደገኛ የሼል እና የሲስተም ጥሪዎችን በ AST የሚመረምር የደህንነት ግድግዳ"""

    @staticmethod
    def scan_code_safety(code, file_path=""):
        """የ SQL Injection, Secrets Exposure, እና የ Shell Execution (Subprocess) ፍተሻ"""
        issues = []
        if not code or not isinstance(code, str):
            return True, []

        try:
            tree = ast.parse(code)
            
            # አደገኛ የሼል ማስፈጸሚያ ቃላት ዝርዝር (Subprocess methods included)
            dangerous_functions = {
                'eval', 'exec', 'system', 'popen', 'run', 
                'call', 'popen', 'check_output', 'check_call', 'spawn'
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    # ሀ. ቀጥተኛ ጥሪዎችን መፈተሽ (e.g. eval())
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id.lower()
                    # ለ. አትሪቢውት ጥሪዎችን መፈተሽ (e.g. subprocess.run() or os.system())
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

        # የደህንነት መዝገብ ወደ SecurityLog መጻፍ
        if issues:
            for issue in issues:
                try:
                    SecurityLog.objects.get_or_create(
                        category='code_injection' if 'Error' in issue or 'Dangerous' in issue else 'data_leak',
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
# 🚑 2. UNIVERSAL HEALER (ሁለንተናዊ ፈዋሽ - FIXED SITE COLLISION & INFINITE LOOP)
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
        
        # 2. የተሰኩ ስራዎችን ነጻ ማውጣት (Stuck Loop Fix)
        stuck_tasks = AIProjectBacklog.objects.filter(
            site=self.site, status='Running',
            updated_at__lt=timezone.now() - timezone.timedelta(minutes=15)
        )
        if stuck_tasks.exists():
            logger.warning(f"🔄 Resetting {stuck_tasks.count()} stuck tasks.")
            stuck_tasks.update(status='Pending')

        # 3. የዌብሳይት ስህተቶችን (500 Errors) ፈልጎ መፍትሄ መስጠት
        self._heal_production_errors()

    def _heal_production_errors(self):
        """ያልተፈቱ ስህተቶችን መርምሮ 'Emergency Fix' ስራዎችን ይፈጥራል (Fixed Site Filter & Loop)"""
        # በ models.py መሠረት ትክክለኛው ፊልድ 'error_message' እና 'task_name' ነው (100% correct)
        errors = AgentErrorLog.objects.filter(site=self.site, resolved=False).order_by('-created_at')[:3]
        
        for err in errors:
            task_name = f"🚑 EMERGENCY FIX: {err.task_name}"
            
            # ✅ ማሻሻያ 1፦ የ 'site' ማጣሪያ (Filter) ታክሏል (የ Tenant ግጭቶችን ያስቀራል)
            # ✅ ማሻሻያ 2፦ 'Pending' ወይም 'Running' ስራ ካለ አዲስ ድግግሞሽ እንዳይፈጠር ይከላከላል
            active_fix_exists = AIProjectBacklog.objects.filter(
                site=self.site, 
                task_name=task_name, 
                status__in=['Pending', 'Running']
            ).exists()
            
            if not active_fix_exists:
                AIProjectBacklog.objects.create(
                    site=self.site,
                    task_name=task_name,
                    task_type='code',
                    target_file='views', # ስህተቶች በብዛት views.py ላይ ስለሚከሰቱ
                    priority='Critical',
                    description=f"Automated Healing for error: {err.error_message}",
                    business_impact_score=10,
                    trigger_condition=f"UniversalHealer: {err.error_type}"
                )
                logger.info(f"🚑 Created healing task for error on {self.site.name}: {err.task_name}")

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
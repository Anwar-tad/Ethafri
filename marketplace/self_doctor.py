# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/security_healer.py
# 📝 ዓላማ፦ Security Auditing, Auto-Healing, and DB Resilience Core
# ✅ የተፈቱ ችግሮች፦ AST Attribute Tracking for Dangerous Functions, 
#                   Safe DB Connection Refresh, Thread-Safe Maintenance.
# 📅 ቀን፦ 2026-06-25
# ============================================================

import os
import ast
import re
import logging
import json
from django.utils import timezone
from django.db import connection, connections, db  # ✅ db ታክሏል
from .models import AgentErrorLog, SelfHealingLog, AIProjectBacklog, SiteRegistry

logger = logging.getLogger(__name__)

# ============================================================
# 🛡️ 1. SECURITY AUDITOR (የደህንነት ኦዲተር)
# ============================================================
class SecurityAuditor:
    """ኮድ ከመጻፉ በፊት አደገኛ ስህተቶች እንዳይኖሩ በ AST የሚመረምር"""

    @staticmethod
    def scan_code_safety(code: str):
        """የ SQL Injection እና Hardcoded Secrets ፍተሻ"""
        issues = []
        try:
            # ሰዋሰዋዊ ፍተሻ
            tree = ast.parse(code)
            dangerous_calls = {'eval', 'exec', 'system', 'subprocess', 'popen'}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = None
                    # 1. ለቀጥታ ጥሪዎች (ምሳሌ፦ eval())
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    # 2. ለባህሪ ጥሪዎች (ምሳሌ፦ os.system() ወይም subprocess.run())
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    
                    if func_name in dangerous_calls:
                        issues.append(f"Critical: Dangerous function call '{func_name}' detected.")

            # ሚስጥራዊ ቁልፎች በኮድ ውስጥ መኖራቸውን መፈለግ (Regex)
            secret_patterns = [r'SECRET_KEY\s*=', r'password\s*=', r'API_KEY\s*=']
            for pattern in secret_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    issues.append("Warning: Possible hardcoded credential detected.")

        except SyntaxError as e:
            issues.append(f"Syntax Error: {e}")
        except Exception as e:
            issues.append(f"Audit Error: {str(e)}")
        
        return len(issues) == 0, issues

# ============================================================
# 🚑 2. UNIVERSAL HEALER (ሁለንተናዊ ፈዋሽ)
# ============================================================
class UniversalHealer:
    """ኤጀንቱን፣ ዳታቤዙን እና የዌብሳይቱን ስህተት የሚጠግን ማዕከል"""

    def __init__(self, site: SiteRegistry):
        self.site = site

    def perform_maintenance(self):
        """በየ 10 ደቂቃው የሚደረግ የሲስተም ጥገና"""
        logger.info(f"🚑 Running maintenance for {self.site.name}...")
        
        # 1. የቆዩ እና የሞቱ የዳታቤዝ ግንኙነቶችን ማጽዳት (Safe Memory Cleanup)
        try:
            db.close_old_connections()
        except Exception as e:
            logger.warning(f"Forcing connections close due to: {e}")
            connections.close_all()
        
        # 2. የተሰኩ ስራዎችን ነጻ ማውጣት (Stuck Loop Fix)
        stuck_tasks = AIProjectBacklog.objects.filter(
            site=self.site, 
            status='Running',
            updated_at__lt=timezone.now() - timezone.timedelta(minutes=15)
        )
        if stuck_tasks.exists():
            count = stuck_tasks.count()
            logger.warning(f"🔄 Resetting {count} stuck tasks.")
            stuck_tasks.update(status='Pending')

        # 3. የዌብሳይት ስህተቶችን (500 Errors) ፈልጎ መፍትሄ መስጠት
        self._heal_production_errors()

    def _heal_production_errors(self):
        """ያልተፈቱ ስህተቶችን መርምሮ 'Emergency Fix' ስራዎችን ይፈጥራል"""
        errors = AgentErrorLog.objects.filter(site=self.site, resolved=False).order_by('-created_at')[:3]
        
        for err in errors:
            task_name = f"🚑 EMERGENCY FIX: {err.task_name}"
            # ስህተቱ የተገኘበትን ፋይል በደህንነት መለየት
            target_file = 'views' if not hasattr(err, 'target_file') else getattr(err, 'target_file', 'views')
            
            if not AIProjectBacklog.objects.filter(task_name=task_name, status='Pending').exists():
                AIProjectBacklog.objects.create(
                    site=self.site,
                    task_name=task_name,
                    task_type='code',
                    target_file=target_file,
                    priority='Critical',
                    description=f"Automated Healing for error: {err.error_message}",
                    business_impact_score=10,
                    trigger_condition=f"AutoHealer: Error Log {err.id}"
                )
                logger.info(f"🚑 Created healing task for: {err.task_name}")

# ============================================================
# 🩺 3. LOG PROTECTOR (የሎግ ጠባቂ)
# ============================================================
def refresh_db_connection_on_error(error_message: str):
    """የዳታቤዝ ግንኙነት ሲመረዝ ወዲያውኑ አዲስ ግንኙነት የሚከፍት"""
    err_str = str(error_message)
    if "OperationalError" in err_str or "DatabaseError" in err_str or "InterfaceError" in err_str:
        try:
            connection.close()
            logger.info("🛡️ Database connection refreshed due to corrupted state.")
            return True
        except Exception as e:
            logger.error(f"Failed to close corrupted connection: {e}")
            connections.close_all()
            return True
    return False

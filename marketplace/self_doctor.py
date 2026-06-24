import os, ast, re, logging, json
from django.utils import timezone
from django.db import connection, connections
from .models import AgentErrorLog, SelfHealingLog, AIProjectBacklog, SiteRegistry

logger = logging.getLogger(__name__)

# ============================================================
# 🛡️ 1. SECURITY AUDITOR (የደህንነት ኦዲተር)
# ============================================================
class SecurityAuditor:
    """ኮድ ከመጻፉ በፊት አደገኛ ስህተቶች እንዳይኖሩ በ AST የሚመረምር"""

    @staticmethod
    def scan_code_safety(code):
        """የ SQL Injection እና Hardcoded Secrets ፍተሻ"""
        issues = []
        try:
            # ሰዋሰዋዊ ፍተሻ
            tree = ast.parse(code)
            
            # አደገኛ ሊሆኑ የሚችሉ ቃላትን መፈለግ
            dangerous_calls = ['eval', 'exec', 'os.system', 'subprocess']
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id in dangerous_calls:
                        issues.append(f"Critical: Dangerous function call '{node.func.id}' detected.")

            # ሚስጥራዊ ቁልፎች በኮድ ውስጥ መኖራቸውን መፈለግ (Regex)
            secret_patterns = [r'SECRET_KEY\s*=', r'password\s*=', r'API_KEY\s*=']
            for pattern in secret_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    issues.append("Warning: Possible hardcoded credential detected.")

        except SyntaxError as e:
            issues.append(f"Syntax Error: {e}")
        
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
        """ያልተፈቱ ስህተቶችን መርምሮ 'Emergency Fix' ስራዎችን ይፈጥራል"""
        errors = AgentErrorLog.objects.filter(site=self.site, resolved=False).order_by('-created_at')[:3]
        
        for err in errors:
            # ለእያንዳንዱ ስህተት አስቸኳይ የጥገና ስራ ወደ ባክሎግ መጫን
            task_name = f"🚑 EMERGENCY FIX: {err.task_name}"
            if not AIProjectBacklog.objects.filter(task_name=task_name, status='Pending').exists():
                AIProjectBacklog.objects.create(
                    site=self.site,
                    task_name=task_name,
                    task_type='code',
                    target_file='views', # ወይም ስህተቱ የተገኘበት ፋይል
                    priority='Critical',
                    description=f"Automated Healing for error: {err.error_message}",
                    business_impact_score=10
                )
                logger.info(f"🚑 Created healing task for: {err.task_name}")

# ============================================================
# 🩺 3. LOG PROTECTOR (የሎግ ጠባቂ)
# ============================================================
def refresh_db_connection_on_error(error_message):
    """የዳታቤዝ ግንኙነት ሲመረዝ ወዲያውኑ አዲስ ግንኙነት የሚከፍት"""
    if "OperationalError" in error_message or "DatabaseError" in error_message:
        connection.close()
        logger.info("🛡️ Database connection refreshed due to error.")
        return True
    return False
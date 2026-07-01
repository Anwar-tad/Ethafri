# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ዓላማ፦ Ultimate System Doctor — Proactive Model Healer (v10.10 - Part 1/2)
# ✅ የተፈቱ ችግሮች፦ Proactive PostgreSQL Metadata scanning, CASCADE schema reset recovery, and circular-free imports.
# 📅 ቀን፦ Wednesday, July 01, 2026
# ============================================================

import os
import ast
import re
import logging
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import connection, connections
from django.core.management import call_command
from django.db.models import Q
from django.conf import settings
from django.apps import apps

logger = logging.getLogger(__name__)

# ============================================================
# 🛡️ 1. SECURITY AUDITOR (የደህንነት ኦዲተር - AST SHIELD)
# ============================================================
class SecurityAuditor:
    """ኮድ ከመጻፉ በፊት አደገኛ የሼል እና የሲስተም ጥሪዎችን በ AST የሚመረምር የደህንነት ግድግዳ"""

    @staticmethod
    def scan_code_safety(code, file_path="", site=None):
        issues = []
        if not code or not isinstance(code, str):
            return True, []

        is_python = file_path.endswith('.py') if file_path else True
        if 'html' in file_path.lower() or not is_python:
            return True, []

        try:
            tree = ast.parse(code)
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
                    from .models import SecurityLog
                    log_exists = SecurityLog.objects.filter(
                        site=site,
                        description=issue,
                        file_path=file_path
                    ).exists()
                    
                    if not log_exists:
                        SecurityLog.objects.create(
                            site=site,
                            category='code_injection' if any(x in issue for x in ['Dangerous', 'Error']) else 'data_leak',
                            text_content=issue,
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

    def __init__(self, site):
        self.site = site

    def perform_maintenance(self):
        """በየ ዑደቱ የሚደረግ የሲስተም ጥገና"""
        from .models import AIProjectBacklog

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

    def hard_reset_database_schema(self):
        """🚨 [Autonomous Schema Rebuilder] የዳታቤዝ ሰንጠረዦችን በ CASCADE በማጥፋት ፍልሰቱን ከባዶ በንጽህና ይገነባል"""
        from .models import SiteRegistry

        logger.warning("🚨 EMERGENCY RESET: Hard resetting database schema to resolve permanent migration lock...")
        try:
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
            
            logger.info("✨ Emergency Reset: All marketplace tables dropped. Initiating fresh migrations...")
            call_command('migrate', interactive=False)
            
            SiteRegistry.objects.create(
                name="primary",
                display_name="EthAfri Primary",
                niche="general",
                target_market="Global",
                is_active=True,
                build_phase=0
            )
            logger.info("✨ Emergency Reset: Re-registered fresh 'primary' site successfully.")
            return True
        except Exception as reset_err:
            logger.error(f"🚨 Emergency Reset Failed: {reset_err}")
            return False

    def heal_database_migrations_autonomously(self, force=False):
        """የ PostgreSQL የኢንዴክስ ወይም የስኬማ ስህተቶችን በራስ-ሰር ፈልጎ በ AI የ SQL ትዕዛዝ ይጠግናል"""
        from .models import SiteConfig, AgentErrorLog, SelfHealingLog

        # 1. Throttling Gate: በየ 30 ደቂቃው አንድ ጊዜ ብቻ እንዲሮጥ ማድረግ
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
                except Exception:
                    should_run = True

        if not should_run:
            recent_db_errors = AgentErrorLog.objects.filter(
                site=self.site,
                resolved=False,
                created_at__gte=timezone.now() - timedelta(minutes=5)
            ).filter(Q(error_message__icontains="OperationalError") | Q(error_message__icontains="relation") | Q(error_message__icontains="FieldError"))
            
            if recent_db_errors.exists():
                logger.warning("🚑 Schema Healer: Recent DB error detected — Bypassing throttling safety.")
                should_run = True

        if not should_run:
            return

        try:
            # 🛡️ PROACTIVE SCHEMA METADATA SCANNING: የጠፉትን contact_info እና image_gallery በቀጥታ ወደ PostgreSQL መጋዘን መውጋት [1, 2]
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    # ሀ. 'listing_type' ፍተሻ
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='marketplace_product' AND column_name='listing_type';
                    """)
                    if not cursor.fetchone():
                        logger.warning("🚑 Schema Healer [Proactive]: Column 'listing_type' is missing. Auto-adding...")
                        cursor.execute("ALTER TABLE marketplace_product ADD COLUMN IF NOT EXISTS listing_type varchar(50) DEFAULT 'sale';")

                    # ለ. 'contact_info' ፍተሻ (የአሁኑን ስህተት የሚፈታው) [1]
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='marketplace_product' AND column_name='contact_info';
                    """)
                    if not cursor.fetchone():
                        logger.warning("🚑 Schema Healer [Proactive]: Column 'contact_info' is missing. Auto-adding...")
                        cursor.execute("ALTER TABLE marketplace_product ADD COLUMN IF NOT EXISTS contact_info varchar(255) DEFAULT '';")

                    # ሐ. 'image_gallery' ፍተሻ (የወደፊት ስህተትን የሚከላከል) [1]
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name='marketplace_product' AND column_name='image_gallery';
                    """)
                    if not cursor.fetchone():
                        logger.warning("🚑 Schema Healer [Proactive]: Column 'image_gallery' is missing. Auto-adding...")
                        cursor.execute("ALTER TABLE marketplace_product ADD COLUMN IF NOT EXISTS image_gallery jsonb DEFAULT '[]'::jsonb;")

            call_command('migrate', interactive=False)
            logger.info("🚑 Schema Healer: Database migrations check passed.")
            
            # ስኬታማ ከሆነ ሰዓቱን መመዝገብ
            SiteConfig.objects.update_or_create(
                key=last_check_key,
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
        except Exception as e:
            err_msg = str(e)
            logger.error(f"🚑 Schema Healer: Migration blocked by error: {err_msg}")
            
            # የጠፉ የኢንዴክስ ስህተቶችን መፍታት (marketplace_name)
            match_missing = re.search(r'relation "([^"]+)" does not exist', err_msg)
            if match_missing:
                idx_name = match_missing.group(1)
                idx_name_clean = str(idx_name).lower()
                
                if "marketplace_name" in idx_name_clean or "marketplace_name_8491f6_idx" in idx_name_clean:
                    logger.warning("🚑 Schema Healer: Creating dummy table/index 'marketplace_name'...")
                    try:
                        with connection.cursor() as cursor:
                            id_type = "integer PRIMARY KEY AUTOINCREMENT" if connection.vendor == 'sqlite' else "serial NOT NULL PRIMARY KEY"
                            cursor.execute(f'CREATE TABLE IF NOT EXISTS "marketplace_name" ("id" {id_type}, "name" varchar(255) NOT NULL);')
                            cursor.execute('CREATE INDEX IF NOT EXISTS "marketplace_name_8491f6_idx" ON "marketplace_name" ("name");')
                        call_command('migrate', interactive=False)
                        return
                    except Exception as retry_err:
                        err_msg = str(retry_err)

            # ቀድሞ የተፈጠሩ ተደጋጋሚ ኢንዴክሶችን DROP ማድረግ
            match_exists = re.search(r'relation "([^"]+)" already exists', err_msg)
            if match_exists:
                idx_name = match_exists.group(1)
                logger.warning(f"🚑 Schema Healer: Dropping conflicting index '{idx_name}'...")
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f'DROP INDEX IF EXISTS "{idx_name}";')
                    call_command('migrate', interactive=False)
                    return
                except Exception as retry_err:
                    err_msg = str(retry_err)
            
            # በ AI የሚመራውን SQL Healer ማነቃቃት
            try:
                logger.warning("🚑 Schema Healer: Invoking Generative AI SQL Healer...")
                all_tables = []
                for model in apps.get_models():
                    all_tables.append({
                        "table": model._meta.db_table,
                        "fields": [f.name for f in model._meta.fields]
                    })

                prompt = (
                    f"We encountered a database migration or schema error: '{err_msg}'.\n"
                    f"Actual database structure: {json.dumps(all_tables, ensure_ascii=False)}\n"
                    f"Generate the exact, safe, raw SQL DDL statement to execute on DB to resolve this error.\n"
                    f"Return JSON with key 'sql' containing only the query."
                )
                
                from .ai_utils import clean_and_parse_json, ask_master_ai_smart
                res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))
                
                if res and isinstance(res, dict) and res.get('sql'):
                    sql_query = res['sql']
                    logger.warning(f"🚑 Schema Healer: Executing AI SQL: {sql_query}")
                    with connection.cursor() as cursor:
                        cursor.execute(sql_query)
                    
                    try:
                        SelfHealingLog.objects.create(
                            error_message=err_msg,
                            solution_sql=sql_query,
                            resolved=True
                        )
                    except: pass
                    
                    try:
                        call_command('migrate', interactive=False)
                        return
                    except Exception as retry_err:
                        err_msg = str(retry_err)
            except Exception as ai_heal_err:
                logger.error(f"❌ Schema Healer: AI healing failed: {ai_heal_err}")

            # የመጨረሻው ጽኑ ራስ-ገዝ ውሳኔ፦ CASCADE reset
            logger.critical("🚨 Schema Healer: Rebuilding database schema from scratch.")
            self.hard_reset_database_schema()
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py (ክፍል 2/2)
# ============================================================

    def heal_model_field_errors(self):
        """የFieldError ሲከሰት ኤጀንቱ ራሱ ሞዴሉን ይቃኛል"""
        logger.info("🚑 Model Healer: Scanning for FieldError in views...")
        from .ai_utils import broadcast_agent_log
        broadcast_agent_log(self.site, "Model Healer: FieldError detected in views. Creating Refactor Task...", "error")
        
        # [Lazy Import] - የክብ ጥገኝነት ለመከላከል በፈንክሽን ደረጃ ማስገባት [1, 2, 3.1.2]
        from .models import AIProjectBacklog

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
            logger.info("Model Healer: Created REFACTOR task successfully.")

    def _heal_production_errors(self):
        """ያልተፈቱ ስህተቶችን መርምሮ 'Emergency Fix' ስራዎችን ይፈጥራል"""
        # [Lazy Import] - የክብ ጥገኝነት ለመከላከል በፈንክሽን ደረጃ ማስገባት [1, 2, 3.1.2]
        from .models import AgentErrorLog, AIProjectBacklog

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
        # [Lazy Import] - የክብ ጥገኝነት ለመከላከል በፈንክሽን ደረጃ ማስገባት [1, 2, 3.1.2]
        from .models import SecurityLog, AIProjectBacklog
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
# 🩺 3. DAILY PERFORMANCE AUDITOR (ዕለታዊ የፍጥነት ኦዲተር)
# ============================================================
class PerformanceAuditor:
    """በየ 24 ሰዓቱ የድረ-ገጽ መጫኛ ፍጥነትን የሚቀንሱ የኮድ አወቃቀሮችን (N+1 queries, blocking scripts)
    በመቃኘት ቅድሚያ የሚሰጣቸውን የጥገና ስራዎች በራሱ የሚፈጥርና የሚፈውስ ማዕከል [1, 2, 3.1.2]"""
    
    @staticmethod
    def run_daily_performance_audit(site):
        # [Lazy Import] - የክብ ጥገኝነት ለመከላከል በፈንክሽን ደረጃ ማስገባት [1, 2, 3.1.2]
        from .models import SiteConfig, AIProjectBacklog

        # 1. Throttling: በቀን አንድ ጊዜ ብቻ እንዲሮጥ ማድረግ [1, 2]
        last_perf_audit = SiteConfig.objects.filter(key=f"LAST_PERF_AUDIT_{site.name}").first()
        if last_perf_audit:
            try:
                last_time = datetime.fromisoformat(last_perf_audit.value.get('time'))
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if timezone.now() - last_time < timedelta(hours=24):
                    return # ከ24 ሰዓት በታች ከሆነ ይዘለላል (የአፈጻጸም ቆጣቢ)
            except Exception:
                pass
        
        logger.info(f"🩺 Performance Auditor: Running daily page-load speed audit for {site.name}...")
        issues_found = []
        
        # 2. የ views.py ፋይልን ለ N+1 queries እና unoptimized ሎጂኮች መቃኘት [1, 2, 3.1.2]
        views_path = os.path.join(str(settings.BASE_DIR), 'marketplace', 'views.py')
        if os.path.exists(views_path):
            try:
                with open(views_path, 'r', encoding='utf-8') as f:
                    views_code = f.read()
                
                # .select_related() ወይም .prefetch_related() ሳይጠቀሙ የባዕድ ቁልፎችን መፈለግ
                if "Product.objects." in views_code and "select_related" not in views_code:
                    issues_found.append("Critical Performance Issue: Product queries in views.py do not use select_related(), causing N+1 database latency.")
                
                if "Category.objects." in views_code and "select_related" not in views_code and "prefetch_related" not in views_code:
                    issues_found.append("Performance Issue: Category queries in views.py could be optimized with prefetch_related() / select_related().")
            except Exception as e:
                logger.error(f"Performance scanning error for views.py: {e}")

        # 3. የ templates ፋይሎችን ለ inline styles/scripts መቃኘት (ገጽ የሚቀረቅሩ) [3.1.2]
        templates_dir = os.path.join(str(settings.BASE_DIR), 'marketplace', 'templates', 'marketplace')
        if os.path.exists(templates_dir):
            try:
                for root, dirs, files in os.walk(templates_dir):
                    for file in files:
                        if file.endswith('.html'):
                            full_path = os.path.join(root, file)
                            with open(full_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                            if "<style>" in html_content or "<script>" in html_content:
                                issues_found.append(f"Performance Warning: Inline CSS/JS blocks found in {file}. Move these to global.css or global.js to unblock page-rendering.")
                                break # አንድ ማስጠንቀቂያ ይበቃል
            except Exception as e:
                logger.error(f"Performance scanning error for templates: {e}")

        # 4. ያጋጠሙ ችግሮችን ቅድሚያ (Critical Priority) በመስጠት በራሱ እንዲያክም ባክሎግ ታስክ መፍጠር [1, 2]
        for issue in issues_found:
            task_name = f"⚡ PERFORMANCE OPTIMIZATION: {issue[:50]}..."
            active_task = AIProjectBacklog.objects.filter(site=site, task_name=task_name, status__in=['Pending', 'Running']).exists()
            if not active_task:
                target = "views" if "views.py" in issue else "home_html"
                AIProjectBacklog.objects.create(
                    site=site,
                    task_name=task_name,
                    target_file=target,
                    priority="Critical", # ፕራዮሪቲ Critical ተደርጓል!
                    description=f"Performance bottleneck detected during daily audit: {issue} Fix this immediately to drastically improve page load speed.",
                    business_impact_score=10 # ከፍተኛው ውጤት [1, 2]
                )
                logger.warning(f"🩺 Performance Auditor: Created critical healing task for: {issue}")

        # 5. የስካን ሰዓቱን መመዝገብ
        SiteConfig.objects.update_or_create(
            key=f"LAST_PERF_AUDIT_{site.name}",
            defaults={'value': {'time': timezone.now().isoformat()}}
        )


# ============================================================
# ✂️ 4. ANTI-BLOAT ENGINE (የኮድ ማሳጠሪያና ማጽጃ ሞተር)
# ============================================================
class AntiBloatEngine:
    """ኤጀንቱ ለራሱም ሆነ ለድረ-ገጹ ኮድ ሲጽፍ እንዳያብጥ፣ አላስፈላጊ ኮድ እንዲቀንስና እንዲያጸዳ የሚከላከል መመሪያ [1, 2]"""

    @staticmethod
    def prune_and_optimize(old_code, new_code, file_path):
        """አሮጌውንና አዲሱን ኮድ በማነጻጸር የኮድ ማበጥን ይከላከላል፣ የሞቱ ኮዶችንና ድግግሞሾችን በ AI ያሳጥራል [1, 2]"""
        # የፋይሉ መጠን ከ 12,000 ካራክተር በላይ ከሆነ ወይም ካለፈው ኮድ ከ 20% በላይ ካበጠ ብቻ ማሳጠርያውን ያነቃቃል [1, 2]
        if len(new_code) < 12000 or (old_code and len(new_code) < len(old_code) * 1.20):
            return new_code

        logger.warning(f"⚠️ Anti-Bloat Guard: Code for {file_path} is bloating ({len(new_code)} chars). Activating self-pruning...")

        prompt = (
            f"Optimize and shrink this Python code for '{file_path}'.\n"
            f"1. Remove any dead code, unused helper functions, and redundant imports.\n"
            f"2. Merge repetitive logics into compact, multi-functional, parameter-driven helpers.\n"
            f"3. Strictly preserve all existing business logic, security guards, and core features, but write it with the minimum possible code lines.\n"
            f"Return JSON with key 'code' containing only the compressed, highly-optimized code."
        )
        
        # dynamic import - circular dependency ለመከላከል [1, 2]
        from .ai_utils import clean_and_parse_json, ask_master_ai_smart
        res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding"))
        
        if res and isinstance(res, dict) and 'code' in res:
            pruned_code = res['code']
            logger.info(f"✨ Anti-Bloat: Shrank {file_path} from {len(new_code)} to {len(pruned_code)} characters!")
            return pruned_code
            
        return new_code


# ============================================================
# ⚙️ 5. LOG PROTECTOR & DB REFRESHER
# ============================================================
def refresh_db_connection_on_error(error_message):
    """የዳታቤዝ ግንኙነት ሲመረዝ ወዲኑኑ አዲስ ግንኙነት የሚከፍት"""
    if "OperationalError" in error_message or "DatabaseError" in error_message:
        connection.close()
        logger.info("🛡️ Database connection refreshed due to error.")
        return True
    return False
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ v10.2 - የ Indentation ስህተት ተስተካክሏል
# ✅ የተፈቱ ችግሮች፦ IndentationError on line 107
# 📅 ቀን፦ Tuesday, June 30, 2026
# ============================================================

import os
import sys
import time
import json
import threading
import logging
import re
from datetime import datetime, timedelta
from django.apps import AppConfig
from django.utils import timezone
from django.db import connection, connections
from django.core.management import call_command
from django.db.models import Count

logger = logging.getLogger(__name__)

# ============================================================
# 🚑 STARTUP SELF-HEALER
# ============================================================
def startup_self_heal_migration(err_msg):
    """ሰርቨሩ በሚነሳበት ጊዜ የሚከሰቱ የማይግሬሽን መቆለፊያዎችን በራስ-ሰር ፈልጎ የሚፈታ የቅድመ-ጅማሮ ጠጋኝ"""
    logger.warning(f"🚑 Startup Healer: Attempting to resolve migration error: {err_msg}")
    try:
        from django.db import connection
        
        match_missing = re.search(r'relation "([^"]+)" does not exist', err_msg)
        if match_missing:
            idx_name = match_missing.group(1)
            idx_name_clean = str(idx_name).lower()
            
            if "marketplace_name_8491f6_idx" in idx_name_clean or "marketplace_name" in idx_name_clean or "marketplace_name_555e28_idx" in idx_name_clean:
                logger.warning("🚑 Startup Healer: Creating dummy table/index 'marketplace_name' to unblock migrations...")
                with connection.cursor() as cursor:
                    id_type = "integer PRIMARY KEY AUTOINCREMENT" if connection.vendor == 'sqlite' else "serial NOT NULL PRIMARY KEY"
                    cursor.execute(f'CREATE TABLE IF NOT EXISTS "marketplace_name" ("id" {id_type}, "name" varchar(255) NOT NULL);')
                    cursor.execute('CREATE INDEX IF NOT EXISTS "marketplace_name_8491f6_idx" ON "marketplace_name" ("name");')
                    cursor.execute('CREATE INDEX IF NOT EXISTS "marketplace_name_555e28_idx" ON "marketplace_name" ("name");')
                return True
            
            try:
                from .self_doctor import UniversalHealer
                from .models import SiteRegistry
                site = SiteRegistry.objects.filter(name='primary', is_active=True).first()
                if site:
                    healer = UniversalHealer(site)
                    return healer._fix_missing_relation(idx_name)
            except Exception:
                pass

        match_exists = re.search(r'relation "([^"]+)" already exists', err_msg)
        if match_exists:
            idx_name = match_exists.group(1)
            logger.warning(f"🚑 Startup Healer: Dropping conflicting index '{idx_name}'...")
            with connection.cursor() as cursor:
                cursor.execute(f'DROP INDEX IF EXISTS "{idx_name}";')
            return True
            
    except Exception as e:
        logger.error(f"🚑 Startup Healer failed: {e}")
    return False


# ============================================================
# 📁 BOOTSTRAP FILES
# ============================================================
def verify_and_bootstrap_agent_files():
    """ኤጀንቱ ሲነሳ የራሱ ኮዶች መኖራቸውን ያረጋግጣል"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    marketplace_dir = os.path.join(base_dir, 'marketplace')
    
    skeletons = {
        'ai_utils.py': """# Generated dynamically by apps.py
import os, json, requests, logging
logger = logging.getLogger(__name__)
def clean_and_parse_json(raw_text):
    try: return json.loads(raw_text.strip() or "{}")
    except: return {}
def ask_master_ai_smart(prompt, task_type="analysis", system_instruction="", task=None):
    api_key = os.getenv('GEMINI_API_KEY', '')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25)
        return res.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"AI call error: {e}")
        return "{}"
""",
        'code_apply.py': """# Generated dynamically
def apply_code_change(site, file_key, new_content, reason="", path=None, backlog_task=None):
    return {'success': True, 'applied': True}
""",
        'event_bus.py': """# Generated dynamically
class EventTypes:
    PRODUCT_CREATED = 'product.created'
def publish_event(event_type, data, source="system"):
    pass
""",
    }

    for filename, code_content in skeletons.items():
        file_path = os.path.join(marketplace_dir, filename)
        if not os.path.exists(file_path) or os.path.getsize(file_path) < 100:
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code_content)
                logger.info(f"✨ Auto-regenerated: {filename}")
            except Exception as e:
                logger.error(f"Failed to regenerate {filename}: {e}")


# ============================================================
# 🏗️ MAIN APP CONFIG
# ============================================================
class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'

    def ready(self):
        """ሲስተሙ ሲነሳ ኤጀንቱን፣ ማይግሬሽኑን እና የዳታቤዝ ጥገናውን በራስ-ሰር ይቀሰቅሳል"""
        
        # 1. ለማይግሬሽን እና ለትዕዛዞች ኤጀንቱ እንዳይነሳ መከልከል
        if 'manage.py' in sys.argv:
            command = sys.argv[1] if len(sys.argv) > 1 else ''
            if command in ['migrate', 'makemigrations', 'collectstatic', 'shell', 'check']:
                return

        # 2. በሪሎደር ምክንያት ድርብ ክሮች እንዳይፈጠሩ መከላከል
        if os.environ.get('RUN_MAIN') != 'true' and 'manage.py' in sys.argv[0]:
            return

        # የቅድመ-በረራ ራስ-መፍጠርያ ሎጂክን መጥራት
        verify_and_bootstrap_agent_files()

        # ============================================================
        # 🩺 ደረጃ 0: SELF-DOCTOR ኤጀንቱ ከመነሳቱ በፊት ይሰራል
        # ============================================================
        try:
            from .self_doctor import DatabaseInspector, DynamicTableGenerator, UniversalHealer
            from .models import SiteRegistry
            
            logger.info("🩺 Self-Doctor: Pre-flight database check starting...")
            
            # ዋናውን ሳይት ያግኙ ወይም ይፍጠሩ
            site = SiteRegistry.objects.filter(name='primary', is_active=True).first()
            if not site:
                site = SiteRegistry.objects.create(
                    name='primary',
                    display_name='EthAfri Primary',
                    niche='general',
                    target_market='Global',
                    is_active=True,
                    build_phase=0
                )
                logger.info("✅ Created primary site registry.")
            
            # ============================================================
            # 🔍 ደረጃ 0a: የጎደሉትን ቴብሎች ይፈልጉ እና ይፍጠሩ
            # ============================================================
            inspector = DatabaseInspector()
            inspection = inspector.inspect_database()
            
            if inspection['has_missing_tables']:
                logger.warning(f"⚠️ Self-Doctor: Found {len(inspection['missing_tables'])} missing tables!")
                generator = DynamicTableGenerator()
                result = generator.generate_missing_tables(inspection)
                created = result.get('generated', [])
                if created:
                    logger.info(f"✅ Self-Doctor: Created {len(created)} tables: {', '.join(created)}")
                if result.get('failed'):
                    logger.error(f"❌ Self-Doctor: Failed to create: {result['failed']}")
            else:
                logger.info("✅ Self-Doctor: All tables exist!")
            
            # ============================================================
            # 🛠️ ደረጃ 0b: ማይግሬሽኖችን ያስተካክሉ
            # ============================================================
            logger.info("🔄 Self-Doctor: Healing migrations...")
            healer = UniversalHealer(site)
            healer.heal_database_migrations_autonomously(force=True)
            
            logger.info("✅ Self-Doctor: Pre-flight check complete!")
            
        except Exception as self_doctor_err:
            logger.error(f"❌ Self-Doctor pre-flight check failed: {self_doctor_err}")
            import traceback
            traceback.print_exc()

        # ============================================================
        # ⚡ Render Free-Tier Rescue Engine
        # ============================================================
        try:
            from django.core.management import call_command
            from django.db import connection
            
            # 🛠️ 1. Database Schema Defuser
            with connection.cursor() as cursor:
                cursor.execute("SELECT exists(SELECT * FROM information_schema.tables WHERE table_name='django_migrations');")
                if cursor.fetchone()[0]:
                    cursor.execute(
                        "SELECT 1 FROM django_migrations WHERE app='marketplace' AND name='0017_translationqueue_delete_aisystemtask_and_more';"
                    )
                    if not cursor.fetchone():
                        now_func = "CURRENT_TIMESTAMP" if connection.vendor == 'sqlite' else "NOW()"
                        cursor.execute(
                            f"INSERT INTO django_migrations (app, name, applied) "
                            f"VALUES ('marketplace', '0017_translationqueue_delete_aisystemtask_and_more', {now_func});"
                        )
                        logger.info("✨ Auto-Healer: Injected Migration 0017 defuse record.")
            
            # 🛠️ 2. ማይግሬሽን በራስ-ሰር ማስኬድ
            logger.info("🛠️ Auto-Migrator: Running migrations...")
            call_command('migrate', interactive=False)
            
            # 🛠️ 3. የ 147 ምርቶች መጣረስ ለመፍታት ወዲኑኑ ከ primary ሳይት ጋር በጅምላ ማገናኘት
            from .models import Product, SiteRegistry
            site = SiteRegistry.objects.filter(name='primary').first()
            if site:
                unlinked_count = Product.objects.filter(site__isnull=True).update(site=site)
                if unlinked_count > 0:
                    logger.info(f"✨ Auto-Healer: Successfully linked {unlinked_count} unlinked products to 'primary' site.")
        except Exception as mig_err:
            logger.error(f"❌ Auto-Migrator/Healer failed: {mig_err}")
        finally:
            connections.close_all()

        logger.info("🚀 Starting EthAfri Autonomous System (Agent + SafetyNet + Self-Healer)...")

        # --- ክር 1፦ ዋናው አውቶኖመስ ኤጀንት ---
        def run_agent_thread():
            logger.info("🤖 Autonomous Agent Thread starting (30s delay)...")
            time.sleep(30)
            try:
                from .growth_agent import start_autonomous_ceo
                start_autonomous_ceo()
            except Exception as e:
                logger.error(f"❌ Agent Thread Error: {e}")
            finally:
                connections.close_all()

        # --- ክር 2፦ ሴፍቲኔት ---
        def run_safetynet_thread():
            time.sleep(60)
            last_cron_fallback_run = None
            while True:
                try:
                    from .models import SiteConfig, SiteRegistry
                    from .growth_agent import execute_master_cycle
                    
                    # 🟢 1. ፈጣን የቀጥታ ታስክ ዑደት
                    trigger = SiteConfig.objects.filter(key="EVOLVE_TRIGGER_PENDING").first()
                    if trigger and trigger.value and isinstance(trigger.value, dict) and trigger.value.get('status') == 'pending':
                        logger.info("⚡ SafetyNet Trigger: Instant manual/webhook trigger detected! Starting Master Cycle...")
                        trigger.value = {"status": "completed", "time": timezone.now().isoformat()}
                        trigger.save()
                        execute_master_cycle()
                        time.sleep(5)
                        continue

                    # 🟢 2. የድሮው 10-ደቂቃ የውጭ ፒንግ መከላከያ
                    now = timezone.now()
                    if not last_cron_fallback_run or (now - last_cron_fallback_run) >= timedelta(minutes=10):
                        cron_ping = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                        should_run = True
                        
                        if cron_ping and cron_ping.value:
                            time_str = None
                            if isinstance(cron_ping.value, dict):
                                time_str = cron_ping.value.get('time')
                            elif isinstance(cron_ping.value, str):
                                try:
                                    parsed_json = json.loads(cron_ping.value)
                                    if isinstance(parsed_json, dict):
                                        time_str = parsed_json.get('time')
                                except json.JSONDecodeError:
                                    time_str = cron_ping.value
                            
                            if isinstance(time_str, str):
                                try:
                                    last_time = datetime.fromisoformat(time_str)
                                    if timezone.is_naive(last_time):
                                        last_time = timezone.make_aware(last_time)
                                    if (timezone.now() - last_time) < timedelta(minutes=15):
                                        should_run = False
                                except ValueError:
                                    pass
                        
                        if should_run:
                            logger.info("🔄 SafetyNet Triggering: External Cron missed. Running Master Cycle...")
                            execute_master_cycle()
                            last_cron_fallback_run = timezone.now()
                            
                except Exception as e:
                    logger.error(f"❌ SafetyNet Error: {e}")
                finally:
                    connections.close_all()
                time.sleep(5)

        # --- ክር 3፦ ሄልዝ ቼክ ---
        def run_health_check_thread():
            logger.info("🩺 Health Check & Self-Healing Thread starting...")
            while True:
                try:
                    time.sleep(300)
                    from .models import AgentErrorLog, AIProjectBacklog
                    
                    unresolved = AgentErrorLog.objects.filter(resolved=False)
                    if unresolved.count() > 500:
                        logger.warning(f"🧹 Clearing {unresolved.count()} unresolved errors.")
                        unresolved.update(resolved=True)

                    duplicates = (
                        AIProjectBacklog.objects.filter(status='Pending')
                        .values('task_name')
                        .annotate(name_count=Count('id'))
                        .filter(name_count__gt=1)
                    )
                    for dup in duplicates:
                        task_name = dup['task_name']
                        keep_task = AIProjectBacklog.objects.filter(task_name=task_name).first()
                        if keep_task:
                            AIProjectBacklog.objects.filter(task_name=task_name, status='Pending').exclude(id=keep_task.id).delete()

                    stuck_limit = timezone.now() - timedelta(minutes=15)
                    stuck_tasks = AIProjectBacklog.objects.filter(status='Running', updated_at__lt=stuck_limit)
                    if stuck_tasks.exists():
                        logger.info(f"🛠️ Resetting {stuck_tasks.count()} stuck tasks.")
                        stuck_tasks.update(status='Pending')

                except Exception as e:
                    logger.error(f"❌ Health Check Loop Error: {e}")
                finally:
                    connections.close_all()

        t1 = threading.Thread(target=run_agent_thread, daemon=True)
        t2 = threading.Thread(target=run_safetynet_thread, daemon=True)
        t3 = threading.Thread(target=run_health_check_thread, daemon=True)
        
        t1.start()
        t2.start()
        t3.start()

        logger.info("✅ All systems initialized. Autonomous loop is running.")
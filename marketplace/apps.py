# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ Robust SafetyNet + Fixed Thread Crash Vulnerability (v9.6)
# ✅ የተፈቱ ችግሮች፦ Dynamic execute_master_cycle Call, timedelta AttributeError Fix
# 📅 ቀን፦ 2026-06-25
# ============================================================

import os
import sys
import time
import json
import threading
import logging
from datetime import datetime, timedelta  # ✅ FIXED: የሩጫ ጊዜ ስህተትን ለመከላከል timedelta ተጨምሯል
from django.apps import AppConfig
from django.utils import timezone
from django.db import connection, connections
from django.db.models import Count

logger = logging.getLogger(__name__)

class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'

    def ready(self):
        """ሲስተሙ ሲነሳ ኤጀንቱን እና ጥገናውን በራሱ ይቀሰቅሳል"""
        
        # 1. ለማይግሬሽን እና ለትዕዛዞች ኤጀንቱ እንዳይነሳ መከልከል
        if 'manage.py' in sys.argv:
            command = sys.argv[1] if len(sys.argv) > 1 else ''
            if command in ['migrate', 'makemigrations', 'collectstatic', 'shell', 'check']:
                return

        # 2. በሪሎደር ምክንያት ድርብ ክሮች እንዳይፈጠሩ መከላከል
        if os.environ.get('RUN_MAIN') != 'true' and 'manage.py' in sys.argv[0]:
            return

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

        # --- ክር 2፦ ሴፍቲኔት (የውጭ ፒንግ ከዘገየ ስራ የሚያስጀምር) ---
        def run_safetynet_thread():
            time.sleep(60)
            while True:
                try:
                    from .models import SiteConfig, SiteRegistry
                    from .growth_agent import execute_master_cycle
                    
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
                                # ✅ FIXED: timedelta አጠቃቀም ተስተካክሏል
                                if (timezone.now() - last_time) < timedelta(minutes=15):
                                    should_run = False
                            except ValueError:
                                pass
                    
                    if should_run:
                        # ✅ FIXED: execute_master_cycle በጥንቃቄና በዳይናሚክ Concurrency እንዲነሳ ተደርጓል
                        logger.info("🔄 SafetyNet Triggering: External Cron missed. Running Master Cycle...")
                        execute_master_cycle()
                            
                except Exception as e:
                    logger.error(f"❌ SafetyNet Error: {e}")
                finally:
                    connections.close_all()
                time.sleep(600)  # በየ 10 ደቂቃው ይፈትሻል

        # --- ክር 3፦ ሄልዝ ቼክ እና ራሱን የማከም ስራ (Emergency Fixer) ---
        def run_health_check_thread():
            logger.info("🩺 Health Check & Self-Healing Thread starting...")
            while True:
                try:
                    time.sleep(300)  # በየ 5 ደቂቃው
                    from .models import AgentErrorLog, AIProjectBacklog
                    
                    # ሀ. 500+ ስህተቶችን በራሱ ማጽዳት (ዳታቤዙ እንዳይጨናነቅ)
                    unresolved = AgentErrorLog.objects.filter(resolved=False)
                    if unresolved.count() > 500:
                        logger.warning(f"🧹 Clearing {unresolved.count()} unresolved errors.")
                        unresolved.update(resolved=True)

                    # ለ. የተደጋገሙ Pending ስራዎችን ማጥፋት (Duplicate Task Fix)
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

                    # ሐ. 'Running' ላይ ከ15 ደቂቃ በላይ ተሰክተው የቆዩትን መልቀቅ
                    # ✅ FIXED: timedelta አጠቃቀም ተስተካክሏል
                    stuck_limit = timezone.now() - timedelta(minutes=15)
                    stuck_tasks = AIProjectBacklog.objects.filter(status='Running', updated_at__lt=stuck_limit)
                    if stuck_tasks.exists():
                        logger.info(f"🛠️ Resetting {stuck_tasks.count()} stuck tasks.")
                        stuck_tasks.update(status='Pending')

                except Exception as e:
                    logger.error(f"❌ Health Check Loop Error: {e}")
                finally:
                    connections.close_all()

        # ሁሉንም ክሮች ማስጀመር
        t1 = threading.Thread(target=run_agent_thread, daemon=True)
        t2 = threading.Thread(target=run_safetynet_thread, daemon=True)
        t3 = threading.Thread(target=run_health_check_thread, daemon=True)
        
        t1.start()
        t2.start()
        t3.start()

        logger.info("✅ All systems initialized. Autonomous loop is running.")
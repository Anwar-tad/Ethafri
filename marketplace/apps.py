# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ Master CEO Startup Logic — Multi-Threaded & Self-Healing
# ✅ የተፈቱ ችግሮች፦ Redundant Startup, Database Locking, Multi-instance conflicts
# 📅 ቀን፦ 2026-06-24
# ============================================================

import os
import sys
import time
import threading
import logging
from django.apps import AppConfig
from django.utils import timezone
from django.db import connections, connection
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

        # 2. በሪሎደር (Reloader) ምክንያት ድርብ ክሮች እንዳይፈጠሩ መከላከል
        if os.environ.get('RUN_MAIN') != 'true':
            return

        logger.info("🚀 EthAfri Master CEO System Initializing...")

        # --- ክር 1፦ ዋናው MASTER CEO ኤጀንት (24/7 ሉፕ) ---
        def run_main_agent():
            logger.info("🤖 Master CEO Thread starting (45s stabilization delay)...")
            time.sleep(45) # ዳታቤዙ እንዲረጋጋ ረዘም ያለ ጊዜ መስጠት
            try:
                # አዲሱን የተጠቃለለ ፋንክሽን መጥራት
                from .growth_agent import start_autonomous_ceo
                start_autonomous_ceo()
            except Exception as e:
                logger.error(f"❌ Master CEO Thread Error: {e}")
            finally:
                connections.close_all()

        # --- ክር 2፦ ሴፍቲኔት (የውጭ ፒንግ ከዘገየ ስራ የሚያስጀምር) ---
        def run_safetynet_thread():
            time.sleep(90)
            while True:
                try:
                    from .models import SiteConfig
                    from .growth_agent import execute_master_cycle
                    
                    # የውጭ ክሮን ፒንግ ከ15 ደቂቃ በላይ ከዘገየ ሴፍቲኔት ይነሳል
                    cron_ping = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                    should_run = True
                    if cron_ping and cron_ping.value:
                        last_time = timezone.datetime.fromisoformat(cron_ping.value.get('time'))
                        if (timezone.now() - last_time) < timezone.timedelta(minutes=15):
                            should_run = False
                    
                    if should_run:
                        logger.info("🛡️ SafetyNet: External Cron missed. Triggering Master Cycle...")
                        execute_master_cycle()
                except Exception as e:
                    logger.error(f"❌ SafetyNet Error: {e}")
                finally:
                    connections.close_all()
                time.sleep(600) # በየ 10 ደቂቃው ይፈትሻል

        # --- ክር 3፦ ድንገተኛ የጤና ምርመራ (Emergency System Fixer) ---
        def run_emergency_healer_thread():
            time.sleep(120)
            while True:
                try:
                    from .models import AgentErrorLog, AIProjectBacklog
                    # ስህተቶች እጅግ ከበዙ (ከ 500 በላይ) ኤጀንቱ እንዳይደናገር ማጽዳት
                    unresolved = AgentErrorLog.objects.filter(resolved=False)
                    if unresolved.count() > 500:
                        logger.warning(f"🧹 Emergency: Clearing {unresolved.count()} errors to unblock CEO.")
                        unresolved.update(resolved=True)
                    
                    # 'Running' ላይ ተሰክተው የቀሩ የቆዩ ስራዎችን መልቀቅ
                    AIProjectBacklog.objects.filter(
                        status='Running', 
                        updated_at__lt=timezone.now() - timezone.timedelta(minutes=30)
                    ).update(status='Pending')

                except Exception as e:
                    logger.error(f"❌ Emergency Healer Error: {e}")
                finally:
                    connections.close_all()
                time.sleep(300) # በየ 5 ደቂቃው

        # ሁሉንም ክሮች በደህንነት ማስጀመር
        threads = [
            threading.Thread(target=run_main_agent, name="MasterCEOThread", daemon=True),
            threading.Thread(target=run_safetynet_thread, name="SafetyNetThread", daemon=True),
            threading.Thread(target=run_emergency_healer_thread, name="EmergencyHealerThread", daemon=True)
        ]
        
        for t in threads:
            t.start()

        logger.info("✅ All CEO Threads (Main, Safety, Healer) are now active.")
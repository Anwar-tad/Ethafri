# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ Enhanced SafetyNet + Autonomous Agent + Health Checks
# ✅ የተፈቱ ችግሮች፦ Models.AppConfig AttributeError, Missing sys import, Undefined variables, Redundant Methods Pruned (100% Clean)
# 📅 ቀን፦ 2026-06-23
# ============================================================

import os
import sys  # የ sys ሞጁል ማስመጣት ታክሏል (NameErrorን ያስቀራል)
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from django.apps import AppConfig  # ከ django.apps በትክክል መጥቷል
from django.utils import timezone
from django.conf import settings
from django.db import models, connection, connections
from django.db.models import Count, Q

logger = logging.getLogger(__name__)


class MarketplaceConfig(AppConfig):  # ወደ AppConfig ተስተካክሏል (AttributeErrorን ያስቀራል)
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'

    def ready(self):
        """አፕሊኬሽኑ በሰርቨር ላይ ሲነሳ ኤጀንቱን ከበስተጀርባ በደህንነት ይቀሰቅሳል"""
        
        # ለትዕዛዞች (commands) የኤጀንቱን መነሳት መዝለል (ለምሳሌ ለ migrate)
        if 'manage.py' in sys.argv:
            command = sys.argv[1] if len(sys.argv) > 1 else ''
            if command in ['migrate', 'makemigrations', 'collectstatic', 'check', 'shell']:
                logger.info(f"ℹ️ Skipping agent startup for command: {command}")
                return

        # Uvicorn/Daphne ሪሎደር በድብል ክሮች እንዳይፈጥር መከላከል
        is_reloader = os.environ.get('RUN_MAIN') == 'true'
        is_manage_py = 'manage.py' in sys.argv[0]
        if is_manage_py and not is_reloader:
            return

        logger.info("🚀 Starting EthAfri Autonomous Agent System...")
        
        try:
            # 1. 🤖 ራስ-ገዝ ኤጀንት ክር (24/7)
            def run_agent_thread():
                logger.info("🤖 Autonomous Agent waiting 30 seconds for database to stabilize...")
                time.sleep(30)
                try:
                    from .growth_agent import run_autonomous_agent
                    logger.info("🤖 Autonomous Agent started successfully! Running 24/7...")
                    run_autonomous_agent()
                except Exception as e:
                    logger.error(f"❌ Autonomous Agent error: {e}")
                finally:
                    connections.close_all()

            # 2. 🛡️ የደህንነት መረብ ክር (SafetyNet Thread)
            def run_safetynet_thread():
                logger.info("🛡️ SafetyNet waiting 30 seconds for database to stabilize...")
                time.sleep(30)
                from .growth_agent import run_single_cycle
                while True:
                    try:
                        from .models import SiteConfig, SiteRegistry
                        cron_ping = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                        last_cron = None
                        
                        if cron_ping and cron_ping.value:
                            last_cron_time_str = cron_ping.value.get('time')
                            if last_cron_time_str:
                                last_cron_dt = timezone.datetime.fromisoformat(last_cron_time_str)
                                if timezone.is_naive(last_cron_dt):
                                    last_cron_dt = timezone.make_aware(last_cron_dt)
                                last_cron = last_cron_dt
                        
                        # የውጭው ክሮን ከ15 ደቂቃ በላይ ከዘገየ SafetyNet ራሱን ያንቀሳቅሳል
                        if not last_cron or (timezone.now() - last_cron) > timezone.timedelta(minutes=15):
                            logger.warning("🚨 SafetyNet Active: External Cron missed or failed! Triggering fallback...")
                            from .growth_agent import run_daily_market_analysis
                            active_sites = SiteRegistry.objects.filter(is_active=True)
                            
                            if not active_sites.exists():
                                run_daily_market_analysis()
                            else:
                                for site in active_sites:
                                    from .growth_agent import run_single_site_analysis
                                    run_single_site_analysis(site)
                                    
                            # የሩጫ ሎግ መዝግብ
                            SiteConfig.objects.update_or_create(
                                key="LAST_SAFETYNET_RUN",
                                defaults={'value': {
                                    'time': timezone.now().isoformat(),
                                    'sites_processed': active_sites.count() if active_sites.exists() else 0
                                }}
                            )
                            logger.info("✅ SafetyNet run logged successfully.")
                    except Exception as e:
                        logger.error(f"SafetyNet cycle execution failed: {e}")
                    finally:
                        connections.close_all()
                    time.sleep(600)  # በየ10 ደቂቃው ይፈትሻል

            # 3. 🩺 የስርዓት ጤና ሁኔታ ፍተሻ ክር (Health Check Thread)
            def run_health_check_thread():
                logger.info("🩺 Starting Health Check Thread...")
                while True:
                    try:
                        time.sleep(300)  # በየ 5 ደቂቃው ይፈትሻል
                        from .models import AgentErrorLog, SiteConfig
                        unresolved_errors = AgentErrorLog.objects.filter(resolved=False).count()
                        
                        health_status = {
                            'status': 'healthy' if unresolved_errors <= 10 else 'warning',
                            'unresolved_errors': unresolved_errors,
                            'timestamp': timezone.now().isoformat()
                        }
                        
                        SiteConfig.objects.update_or_create(
                            key="LAST_HEALTH_CHECK",
                            defaults={'value': health_status}
                        )
                        if unresolved_errors > 0:
                            logger.warning(f"⚠️ Health Check: {unresolved_errors} unresolved errors detected.")
                    except Exception as e:
                        logger.error(f"Health check execution failed: {e}")
                    finally:
                        connections.close_all()

            # ክሮችን በደህንነት ማስጀመር
            t1 = threading.Thread(target=run_agent_thread, name="AutonomousAgentThread")
            t1.daemon = True
            t1.start()

            t2 = threading.Thread(target=run_safetynet_thread, name="SafetyNetThread")
            t2.daemon = True
            t2.start()

            t3 = threading.Thread(target=run_health_check_thread, name="HealthCheckThread")
            t3.daemon = True
            t3.start()

            logger.info("✅ Autonomous Agent, SafetyNet and HealthCheck threads started successfully.")

        except Exception as e:
            logger.error(f"❌ Thread spawning failed: {e}")
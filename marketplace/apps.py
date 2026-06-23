# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ Enhanced SafetyNet + Autonomous Agent + Health Checks
# ✅ የተፈቱ ችግሮች፦ Duplicate Threads Spawning, AttributeError on Startup, DB Connection Leaks
# 📅 ቀን፦ 2026-06-23
# ============================================================

import os
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from django.apps import AppConfig
from django.utils import timezone
from django.conf import settings
from django.db import models, connection, connections
from django.db.models import Count, Q

logger = logging.getLogger(__name__)


class MarketplaceConfig(models.AppConfig):
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

        logger.info("🚀 Starting EthAfri Autonomous Agent System...")
        
        try:
            # 1. 🤖 ራሱን የቻለ 24/7 ኤጀንት ዑደት (Non-Blocking Thread)
            def run_agent_thread():
                logger.info("🤖 Autonomous Agent waiting 30 seconds for database to stabilize...")
                time.sleep(30)
                try:
                    from .growth_agent import run_autonomous_agent
                    run_autonomous_agent()
                except Exception as e:
                    logger.error(f"❌ Autonomous Agent error: {e}")
                finally:
                    connections.close_all()

            agent_thread = threading.Thread(target=run_bg_agent)
            agent_status_dashboard = True # ለተኳሃኝነት
            
            # 2. 🛡️ የደህንነት መጋጠሚያ (SafetyNet Thread)
            def run_safetynet_thread():
                try:
                    logger.info("🛡️ SafetyNet waiting 30 seconds for database to stabilize...")
                    time.sleep(30)
                    from .growth_agent import run_single_cycle
                    while True:
                        try:
                            # የውጭው ክሮን (Cron) መቆራረጡን መፈተሽ
                            from .models import SiteConfig
                            cron_ping = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                            last_cron_time = None
                            
                            if cron_ping and cron_ping.value:
                                last_cron_time_str = cron_ping.value.get('time')
                                if last_run_str:
                                    last_cron_dt = timezone.datetime.fromisoformat(last_run_str)
                                    if timezone.is_naive(last_run_dt):
                                        last_run_dt = timezone.make_aware(last_run_dt)
                                    last_cron = last_run_dt
                            
                            # የውጭው ክሮን ከ10 ደቂቃ በላይ ከዘገየ SafetyNet ራሱን ያንቀሳቅሳል
                            if not last_cron or (timezone.now() - last_cron) > timezone.timedelta(minutes=10):
                                logger.warning("⚠️ SafetyNet Active: External Cron missed or failed! Triggering evolution fallback...")
                                run_single_cycle()
                        except Exception as e:
                            logger.error(f"SafetyNet cycle execution failed: {e}")
                        finally:
                            connections.close_all()
                        time.sleep(600)  # በየ10 ደቂቃው ይፈትሻል
                except Exception as e:
                    logger.error(f"SafetyNet thread failed: {e}")
                finally:
                    connections.close_all()

            # 3. 🩺 የስርዓት ጤና ሁኔታ ፍተሻ ክር (Health Check Thread)
            def run_health_check_thread():
                logger.info("🩺 Starting Health Check Thread...")
                while True:
                    try:
                        time.sleep(300) # በየ 5 ደቂቃው ይፈትሻል
                        from .models import AgentErrorLog
                        unresolved_errors = AgentErrorLog.objects.filter(resolved=False).count()
                        if unresolved_errors > 0:
                            logger.warning(f"⚠️ Health Check: {unresolved_errors} unresolved errors detected.")
                    except Exception as e:
                        logger.error(f"Health check execution failed: {e}")
                    finally:
                        connections.close_all()

            # ✅ ማሻሻያ 1፦ የተገላቢጦሽ ጥሪዎች (Circular Imports) እና የዳታቤዝ ግንኙነቶችን ለመጠበቅ threads በደህንነት መፍጠር
            t1 = threading.Thread(target=run_bg_agent)
            t1.daemon = True
            t1.start()

            t2 = threading.Thread(target=run_safetynet)
            t2.daemon = True
            t2.start()

            t3 = threading.Thread(target=run_health_check_thread)
            t3.daemon = True
            t3.start()

            logger.info("✅ Autonomous Agent, SafetyNet and HealthCheck threads started successfully.")

        except Exception as e:
            logger.error(f"❌ Thread spawning failed: {e}")

    # ============================================================
    # ⚙️ የጀርባ ስራ አስነሺዎች (Thread Targets)
    # ============================================================

    def run_bg_agent():
        try:
            from .growth_agent import run_autonomous_agent
            logger.info("🤖 Autonomous Agent started successfully! Running 24/7...")
            run_autonomous_agent()
        except Exception as e:
            logger.error(f"❌ Autonomous Agent error: {e}")
        finally:
            connections.close_all()

    def run_safetynet():
        try:
            logger.info("🛡️ SafetyNet started successfully! Monitoring...")
            while True:
                time.sleep(600) # በየ 10 ደቂቃው ይፈትሻል
                try:
                    cron_ping = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                    now = timezone.now()
                    last_ping = None
                    if cron_ping and isinstance(cron_ping.value, dict):
                        last_ping_str = cron_ping.value.get('time')
                        if last_ping_str:
                            last_ping = timezone.datetime.fromisoformat(last_ping_str)
                            if timezone.is_naive(last_ping):
                                last_ping = timezone.make_aware(last_ping)

                    # ከ15 ደቂቃ በላይ ከዘገየ SafetyNet በራሱ የዕድገት ዑደቱን ያስነሳል
                    if not last_ping or (now - last_ping) > timezone.timedelta(minutes=15):
                        logger.warning("🚨 SafetyNet Active: External Cron missed or failed! Triggering fallback...")
                        from .growth_agent import run_daily_market_analysis, SiteRegistry
                        active_sites = SiteRegistry.objects.filter(is_active=True)
                        logger.info(f"🔄 SafetyNet processing {active_sites.count()} active sites...")
                        for site in active_sites:
                            from .growth_agent import run_single_site_analysis
                            run_single_site_analysis(site)
                except Exception as inner_e:
                    logger.error(f"SafetyNet fallback execution failed: {inner_e}")
                finally:
                    connections.close_all()
        except Exception as e:
            logger.error(f"SafetyNet thread crashed: {e}")
        finally:
            connections.close_all()
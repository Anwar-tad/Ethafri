# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ Enhanced SafetyNet + Autonomous Agent + Health Checks
# 📅 ቀን፦ 2026-06-22
# ============================================================

from django.apps import AppConfig
import threading
import time
import sys
import logging
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'

    def ready(self):
        """
        ሰርቨሩ በትክክል መነሳቱን ማረጋገጫ
        ⚠️ የማይፈለጉ ትዕዛዞች ሲሮጡ አላስፈላጊ የጀርባ ክር እንዳይቀሰቅሱ
        """
        invalid_commands = [
            'makemigrations', 'migrate', 'collectstatic', 'shell', 'test', 
            'evolve_market', 'sync_translations', 'showmigrations',
            'flush', 'dumpdata', 'loaddata', 'sqlmigrate', 'sqlflush',
            'check', 'compilemessages', 'createcachetable', 'run_agent'
        ]
        
        # መጫኛ ትዕዛዞችን እና ሌሎችን አታስኬድ
        if not any(cmd in sys.argv for cmd in invalid_commands):
            logger.info("🚀 Starting EthAfri Autonomous Agent System...")
            
            # 1. 🆕 ራስ-ገዝ ኤጀንት ክር (24/7)
            agent_thread = threading.Thread(
                target=self.start_autonomous_agent,
                daemon=True,
                name="AutonomousAgentThread"
            )
            agent_thread.start()
            
            # 2. 🛡️ SafetyNet ክር (የውጭ ክሮን ፎልባክ)
            safetynet_thread = threading.Thread(
                target=self.start_safetynet_loop,
                daemon=True,
                name="SafetyNetThread"
            )
            safetynet_thread.start()
            
            # 3. 🩺 Health Check ክር
            health_thread = threading.Thread(
                target=self.start_health_check_loop,
                daemon=True,
                name="HealthCheckThread"
            )
            health_thread.start()
            
            logger.info("✅ Autonomous Agent, SafetyNet and HealthCheck threads started successfully.")
        else:
            logger.info(f"ℹ️ Skipping agent startup for command: {' '.join(sys.argv)}")

    # ============================================================
    # 1. 🆕 ራስ-ገዝ ኤጀንት (24/7 Autonomous Agent)
    # ============================================================
    
    def start_autonomous_agent(self):
        """
        ሙሉ በሙሉ ራሱን የሚያስተዳድር 24/7 ኤጀንት
        ፈጽሞ አይተኛም — ሁልጊዜ የሚሰራ ስራ ይፈጥራል
        """
        # ሰርቨሩ መጀመሪያ ሲነሳ ዳታቤዙ እስኪረጋጋ 30 ሰከንድ ይጠብቃል
        logger.info("🤖 Autonomous Agent waiting 30 seconds for database to stabilize...")
        time.sleep(30)
        
        try:
            from django.conf import settings
            if not getattr(settings, 'AUTONOMOUS_AGENT_ENABLED', True):
                logger.info("💤 Autonomous Agent is disabled in settings")
                return
            
            from .growth_agent import run_autonomous_agent
            logger.info("🤖 Autonomous Agent started successfully! Running 24/7...")
            run_autonomous_agent()
            
        except ImportError as e:
            logger.error(f"❌ Could not import growth_agent: {e}")
        except Exception as e:
            logger.error(f"❌ Autonomous Agent error: {e}")

    # ============================================================
    # 2. 🛡️ SafetyNet (የውጭ ክሮን ፎልባክ)
    # ============================================================
    
    def start_safetynet_loop(self):
        """
        የውጭው ክሮን ፌል ካደረገ ተረክቦ የሚያስነሳ የደህንነት መረብ
        አሁን ሁሉንም ንቁ ጣቢያዎች ያስተዳድራል
        """
        logger.info("🛡️ SafetyNet waiting 30 seconds for database to stabilize...")
        time.sleep(30)
        
        error_count = 0
        max_errors = 5
        
        while True:
            try:
                # የዳታቤዝ ግንኙነቶችን ማደስ
                from django.db import connections
                connections.close_all()
                
                from .models import SiteConfig, SiteRegistry
                from .growth_agent import run_daily_market_analysis, run_single_site_analysis
                
                # የመጨረሻው የውጭ ክሮን ጥሪ መቼ እንደነበረ መፈተሽ
                last_ping_cfg = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                should_run_fallback = True
                last_ping_time = None
                
                if last_ping_cfg and last_ping_cfg.value and 'time' in last_ping_cfg.value:
                    try:
                        naive_time = datetime.fromisoformat(last_ping_cfg.value['time'])
                        if timezone.is_naive(naive_time):
                            last_ping_time = timezone.make_aware(naive_time)
                        else:
                            last_ping_time = naive_time
                            
                        # ከ12 ደቂቃ በፊት ክሮኑ ሰርቶ ከሆነ ዝም ይላል
                        if timezone.now() - last_ping_time < timedelta(minutes=12):
                            should_run_fallback = False
                            logger.info("🛡️ SafetyNet: External Cron is healthy. Standing by...")
                    except Exception as e:
                        logger.warning(f"⚠️ SafetyNet: Failed to parse last ping time: {e}")
                
                # ክሮኑ ፌል ካደረገ ይህ ስራውን ይረከባል
                if should_run_fallback:
                    logger.warning("🚨 SafetyNet Active: External Cron missed or failed! Triggering evolution fallback...")
                    
                    active_sites = SiteRegistry.objects.filter(is_active=True)
                    
                    if not active_sites.exists():
                        try:
                            result = run_daily_market_analysis()
                            logger.info(f"🚨 SafetyNet Fallback Result (Global): {result}")
                        except Exception as e:
                            logger.error(f"❌ SafetyNet global fallback failed: {e}")
                            error_count += 1
                    else:
                        site_count = active_sites.count()
                        logger.info(f"🔄 SafetyNet processing {site_count} active sites...")
                        
                        for site in active_sites:
                            try:
                                result = run_single_site_analysis(site)
                                logger.info(f"🚨 SafetyNet Fallback Result for {site.name}: {result}")
                            except Exception as e:
                                logger.error(f"❌ SafetyNet failed for {site.name}: {e}")
                                error_count += 1
                    
                    try:
                        SiteConfig.objects.update_or_create(
                            key="LAST_SAFETYNET_RUN",
                            defaults={'value': {
                                'time': timezone.now().isoformat(),
                                'sites_processed': active_sites.count() if active_sites.exists() else 0,
                                'error_count': error_count
                            }}
                        )
                        logger.info("✅ SafetyNet run logged successfully.")
                    except Exception as e:
                        logger.error(f"❌ Failed to log SafetyNet run: {e}")
                    
                    if error_count >= max_errors:
                        logger.warning(f"⚠️ SafetyNet: {error_count} errors detected. Increasing check interval.")
                        time.sleep(1800)
                        error_count = 0
                        continue
                
                error_count = 0
                
            except Exception as e:
                logger.error(f"❌ SafetyNet Thread Error: {e}")
                error_count += 1
                
                if error_count >= 3:
                    logger.warning("⚠️ SafetyNet: Multiple errors detected. Waiting 5 minutes...")
                    time.sleep(300)
                    error_count = 0
            
            time.sleep(600)

    # ============================================================
    # 3. 🩺 Health Check (የስርዓት ጤና ምርመራ)
    # ============================================================
    
    def start_health_check_loop(self):
        """
        የስርዓት ጤና ምርመራ ክር
        በየ5 ደቂቃው የስርዓቱን ሁኔታ ይፈትሻል
        """
        logger.info("🩺 Starting Health Check Thread...")
        time.sleep(60)
        
        while True:
            try:
                from django.db import connection
                connection.ensure_connection()
                
                from .models import SiteRegistry, AgentErrorLog
                
                active_sites = SiteRegistry.objects.filter(is_active=True).count()
                unresolved_errors = AgentErrorLog.objects.filter(resolved=False).count()
                
                health_status = {
                    'status': 'healthy',
                    'active_sites': active_sites,
                    'unresolved_errors': unresolved_errors,
                    'timestamp': timezone.now().isoformat()
                }
                
                if unresolved_errors > 10:
                    health_status['status'] = 'warning'
                    logger.warning(f"⚠️ Health Check: {unresolved_errors} unresolved errors detected.")
                elif unresolved_errors > 50:
                    health_status['status'] = 'critical'
                    logger.error(f"🚨 Health Check: {unresolved_errors} unresolved errors! Critical!")
                
                try:
                    from .models import SiteConfig
                    SiteConfig.objects.update_or_create(
                        key="LAST_HEALTH_CHECK",
                        defaults={'value': health_status}
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to log health status: {e}")
                
                if health_status['status'] == 'healthy':
                    logger.debug(f"💚 Health Check: {active_sites} sites, {unresolved_errors} errors")
                
            except Exception as e:
                logger.error(f"❌ Health Check Thread Error: {e}")
            
            time.sleep(300)

    # ============================================================
    # 4. 📊 የስርዓት ሁኔታ (System Status)
    # ============================================================
    
    def get_health_status(self):
        """
        የስርዓቱን ወቅታዊ ጤና ሁኔታ ይመልሳል
        ለExternal API ጥቅም
        """
        try:
            from .models import SiteConfig
            health_cfg = SiteConfig.objects.filter(key="LAST_HEALTH_CHECK").first()
            if health_cfg:
                return health_cfg.value
        except Exception:
            pass
        
        return {
            'status': 'unknown',
            'active_sites': 0,
            'unresolved_errors': 0,
            'timestamp': timezone.now().isoformat()
        }
    
    def get_agent_status(self):
        """
        የኤጀንቱን ወቅታዊ ሁኔታ ይመልሳል
        """
        try:
            from .models import SiteConfig
            heartbeat = SiteConfig.objects.filter(key='AGENT_HEARTBEAT').first()
            if heartbeat:
                return heartbeat.value
        except Exception:
            pass
        return {'status': 'unknown', 'timestamp': None, 'cycle': 0}
        
# apps.py ውስጥ
def _auto_repair_on_startup(self):
    """ሲስተሙ ሲነሳ ራስ-ሰር ጥገና"""
    time.sleep(45)
    try:
        from .growth_agent import AutonomousGrowthEngine
        engine = AutonomousGrowthEngine()
        
        # ሁሉንም ጣቢያዎች ተንትን
        sites = SiteRegistry.objects.filter(is_active=True)
        for site in sites:
            engine._analyze_and_plan(site)
            
        logger.info("✅ Auto-repair completed")
    except Exception as e:
        logger.error(f"Auto-repair error: {e}")
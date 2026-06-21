# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ Enhanced SafetyNet + Multi-Site Support + Health Checks
# 📅 ቀን፦ 2026-06-21
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
        ⚠️ 'evolve_market' እና 'sync_translations' በኮማንድ መልክ ሲሮጡ አላስፈላጊ የጀርባ ክር እንዳይቀሰቅሱ
        """
        invalid_commands = [
            'makemigrations', 'migrate', 'collectstatic', 'shell', 'test', 
            'evolve_market', 'sync_translations', 'showmigrations',
            'flush', 'dumpdata', 'loaddata', 'sqlmigrate', 'sqlflush',
            'check', 'compilemessages', 'createcachetable'
        ]
        
        # መጫኛ ትዕዛዞችን እና ሌሎችን አታስኬድ
        if not any(cmd in sys.argv for cmd in invalid_commands):
            logger.info("🚀 Starting EthAfri SafetyNet Thread...")
            
            # የጀርባ ክር ጀምር
            safetynet_thread = threading.Thread(
                target=self.start_safetynet_loop,
                daemon=True,
                name="SafetyNetThread"
            )
            safetynet_thread.start()
            
            # የጤና ምርመራ ክር (Health Check)
            health_thread = threading.Thread(
                target=self.start_health_check_loop,
                daemon=True,
                name="HealthCheckThread"
            )
            health_thread.start()
            
            logger.info("✅ SafetyNet and HealthCheck threads started successfully.")
        else:
            logger.info(f"ℹ️ Skipping SafetyNet startup for command: {' '.join(sys.argv)}")

    def start_safetynet_loop(self):
        """
        የውጭው ክሮን ፌል ካደረገ ተረክቦ የሚያስነሳ የደህንነት መረብ
        አሁን ሁሉንም ንቁ ጣቢያዎች ያስተዳድራል
        """
        # ሰርቨሩ መጀመሪያ ሲነሳ ዳታቤዙ እስኪረጋጋ 30 ሰከንድ ይጠብቃል
        logger.info("🛡️ SafetyNet waiting 30 seconds for database to stabilize...")
        time.sleep(30)
        
        # ስህተት ቆጣሪ (Error counter for exponential backoff)
        error_count = 0
        max_errors = 5
        
        while True:
            try:
                # 🛡️ 1. የዳታቤዝ ግንኙነቶችን ማደስ
                from django.db import connections
                connections.close_all()
                
                # ሞዴሎችን አስመጣ
                from .models import SiteConfig, SiteRegistry
                from .growth_agent import run_daily_market_analysis, run_single_site_analysis
                
                # 🛡️ 2. የመጨረሻው የውጭ ክሮን ጥሪ መቼ እንደነበረ መፈተሽ
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
                
                # 🛡️ 3. ክሮኑ ፌል ካደረገ ይህ ስራውን ይረከባል
                if should_run_fallback:
                    logger.warning("🚨 SafetyNet Active: External Cron missed or failed! Triggering evolution fallback...")
                    
                    # 🆕 ሁሉንም ንቁ ጣቢያዎች አስኬድ
                    active_sites = SiteRegistry.objects.filter(is_active=True)
                    
                    if not active_sites.exists():
                        # ነባሪ ጣቢያ ከሌለ
                        try:
                            result = run_daily_market_analysis()
                            logger.info(f"🚨 SafetyNet Fallback Result (Global): {result}")
                        except Exception as e:
                            logger.error(f"❌ SafetyNet global fallback failed: {e}")
                            error_count += 1
                    else:
                        # እያንዳንዱን ጣቢያ በተናጥል አስኬድ
                        site_count = active_sites.count()
                        logger.info(f"🔄 SafetyNet processing {site_count} active sites...")
                        
                        for site in active_sites:
                            try:
                                result = run_single_site_analysis(site)
                                logger.info(f"🚨 SafetyNet Fallback Result for {site.name}: {result}")
                            except Exception as e:
                                logger.error(f"❌ SafetyNet failed for {site.name}: {e}")
                                error_count += 1
                    
                    # የመጨረሻውን የፎልባክ ጊዜ መዝግብ
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
                    
                    # ስህተቶች ከበዙ የጊዜ ክፍተት ጨምር
                    if error_count >= max_errors:
                        logger.warning(f"⚠️ SafetyNet: {error_count} errors detected. Increasing check interval.")
                        time.sleep(1800)  # 30 ደቂቃ ይጠብቅ
                        error_count = 0
                        continue
                
                # ስህተት ከሌለ ቆጣሪውን ዳግም አስጀምር
                error_count = 0
                
            except Exception as e:
                logger.error(f"❌ SafetyNet Thread Error: {e}")
                error_count += 1
                
                # ከባድ ስህተት ከሆነ ተጨማሪ ጊዜ ይጠብቅ
                if error_count >= 3:
                    logger.warning("⚠️ SafetyNet: Multiple errors detected. Waiting 5 minutes...")
                    time.sleep(300)
                    error_count = 0
            
            # 🛡️ 4. በየ10 ደቂቃው ይፈትሻል (ወይም ስህተት ከሌለ)
            time.sleep(600)

    def start_health_check_loop(self):
        """
        🆕 የስርዓት ጤና ምርመራ ክር
        በየ5 ደቂቃው የስርዓቱን ሁኔታ ይፈትሻል
        """
        logger.info("🩺 Starting Health Check Thread...")
        
        # ሰርቨሩ እስኪረጋጋ 60 ሰከንድ ይጠብቃል
        time.sleep(60)
        
        while True:
            try:
                # የዳታቤዝ ግንኙነት ፍተሻ
                from django.db import connection
                connection.ensure_connection()
                
                # የስርዓት ሁኔታ ምርመራ
                from .models import SiteRegistry, AgentErrorLog
                
                # ንቁ ጣቢያዎች ቆጠራ
                active_sites = SiteRegistry.objects.filter(is_active=True).count()
                
                # ያልተፈቱ ስህተቶች ቆጠራ
                unresolved_errors = AgentErrorLog.objects.filter(resolved=False).count()
                
                health_status = {
                    'status': 'healthy',
                    'active_sites': active_sites,
                    'unresolved_errors': unresolved_errors,
                    'timestamp': timezone.now().isoformat()
                }
                
                # ከፍተኛ ስህተቶች ካሉ ማስጠንቀቂያ
                if unresolved_errors > 10:
                    health_status['status'] = 'warning'
                    logger.warning(f"⚠️ Health Check: {unresolved_errors} unresolved errors detected.")
                elif unresolved_errors > 50:
                    health_status['status'] = 'critical'
                    logger.error(f"🚨 Health Check: {unresolved_errors} unresolved errors! Critical!")
                
                # የጤና ሁኔታን መዝግብ
                try:
                    from .models import SiteConfig
                    SiteConfig.objects.update_or_create(
                        key="LAST_HEALTH_CHECK",
                        defaults={'value': health_status}
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to log health status: {e}")
                
                # ስርዓቱ ጤናማ ከሆነ
                if health_status['status'] == 'healthy':
                    logger.debug(f"💚 Health Check: {active_sites} sites, {unresolved_errors} errors")
                
            except Exception as e:
                logger.error(f"❌ Health Check Thread Error: {e}")
            
            # 🩺 5. በየ5 ደቂቃው ይፈትሻል
            time.sleep(300)

    def get_health_status(self):
        """
        🆕 የስርዓቱን ወቅታዊ ጤና ሁኔታ ይመልሳል
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
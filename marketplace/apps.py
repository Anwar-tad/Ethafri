# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/apps.py
# 📝 ለውጥ፦ Multi-Site Support + SafetyNet ማሻሻያ
# 📅 ቀን፦ 2026-06-20
# ============================================================

from django.apps import AppConfig
import threading
import time
import sys
from django.utils import timezone
from datetime import datetime, timedelta
import logging

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
            'evolve_market', 'sync_translations', 'showmigrations'
        ]
        if not any(cmd in sys.argv for cmd in invalid_commands):
            logger.info("🚀 Starting EthAfri SafetyNet Thread...")
            threading.Thread(target=self.start_safetynet_loop, daemon=True).start()

    def start_safetynet_loop(self):
        """
        የውጭው ክሮን ፌል ካደረገ ተረክቦ የሚያስነሳ የደህንነት መረብ
        አሁን ሁሉንም ንቁ ጣቢያዎች ያስተዳድራል
        """
        # ሰርቨሩ መጀመሪያ ሲነሳ ዳታቤዙ እስኪረጋጋ 30 ሰከንድ ይጠብቃል
        time.sleep(30)
        
        while True:
            try:
                # 🛡️ 1. የዳታቤዝ ግንኙነቶችን ማደስ
                from django.db import connections
                connections.close_all()
                
                from .models import SiteConfig, SiteRegistry
                from .growth_agent import run_daily_market_analysis, run_single_site_analysis
                
                # 🛡️ 2. የመጨረሻው የውጭ ክሮን ጥሪ መቼ እንደነበረ መፈተሽ
                last_ping_cfg = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                should_run_fallback = True
                
                if last_ping_cfg and 'time' in last_ping_cfg.value:
                    naive_time = datetime.fromisoformat(last_ping_cfg.value['time'])
                    if timezone.is_naive(naive_time):
                        last_ping_time = timezone.make_aware(naive_time)
                    else:
                        last_ping_time = naive_time
                        
                    # ከ12 ደቂቃ በፊት ክሮኑ ሰርቶ ከሆነ ዝም ይላል
                    if timezone.now() - last_ping_time < timedelta(minutes=12):
                        should_run_fallback = False
                        logger.info("🛡️ SafetyNet: External Cron is healthy. Standing by...")
                
                # 🛡️ 3. ክሮኑ ፌል ካደረገ ይህ ስራውን ይረከባል
                if should_run_fallback:
                    logger.info("🚨 SafetyNet Active: External Cron missed or failed! Triggering evolution fallback...")
                    
                    # 🆕 ሁሉንም ንቁ ጣቢያዎች አስኬድ
                    active_sites = SiteRegistry.objects.filter(is_active=True)
                    
                    if not active_sites.exists():
                        # ነባሪ ጣቢያ ከሌለ
                        result = run_daily_market_analysis()
                        logger.info(f"🚨 SafetyNet Fallback Result (Global): {result}")
                    else:
                        # እያንዳንዱን ጣቢያ በተናጥል አስኬድ
                        for site in active_sites:
                            try:
                                result = run_single_site_analysis(site)
                                logger.info(f"🚨 SafetyNet Fallback Result for {site.name}: {result}")
                            except Exception as e:
                                logger.error(f"❌ SafetyNet failed for {site.name}: {e}")
                    
                    # የመጨረሻውን የፎልባክ ጊዜ መዝግብ
                    SiteConfig.objects.update_or_create(
                        key="LAST_SAFETYNET_RUN",
                        defaults={'value': {'time': timezone.now().isoformat()}}
                    )
                    
            except Exception as e:
                logger.error(f"❌ SafetyNet Thread Error: {e}")
            
            # 🛡️ 4. በየ10 ደቂቃው ይፈትሻል
            time.sleep(600)
# EthAfri/marketplace/apps.py

from django.apps import AppConfig
import threading
import time
import sys
from django.utils import timezone
from datetime import datetime, timedelta

class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'

    def ready(self):
        # ሰርቨሩ በትክክል መነሳቱን ማረጋገጫ (በአስተማማኝ ሁኔታ በሁሉም የዌብ ማስተናገጃዎች ላይ እንዲነቃ)
        # ⚠️ 'evolve_market' እና 'sync_translations' በኮማንድ መልክ ሲሮጡ አላስፈላጊ የጀርባ ክር እንዳይቀሰቅሱ ተጨምረዋል
        invalid_commands = [
            'makemigrations', 'migrate', 'collectstatic', 'shell', 'test', 
            'evolve_market', 'sync_translations'
        ]
        if not any(cmd in sys.argv for cmd in invalid_commands):
            threading.Thread(target=self.start_safetynet_loop, daemon=True).start()

    def start_safetynet_loop(self):
        """የውጭው ክሮን ፌል ካደረገ ተረክቦ የሚያስነሳ የደህንነት መረብ"""
        # ሰርቨሩ መጀመሪያ ሲነሳ ዳታቤዙና ሌሎች አፖች እስኪረጋጉ 30 ሰከንድ ይጠብቃል
        time.sleep(30)
        
        while True:
            try:
                # 🛡️ 1. የዳታቤዝ ግንኙነቶችን ማደስ (የቆዩና የሞቱ ግንኙነቶች ክራሽ እንዳይፈጥሩ መከላከያ)
                from django.db import connections
                connections.close_all()
                
                from .models import SiteConfig
                from .growth_agent import run_daily_market_analysis
                
                # የመጨረሻው የውጭ ክሮን ጥሪ መቼ እንደነበረ ከዳታቤዝ ማምጣት
                last_ping_cfg = SiteConfig.objects.filter(key="LAST_SUCCESSFUL_CRON_PING").first()
                should_run_fallback = True
                
                if last_ping_cfg and 'time' in last_ping_cfg.value:
                    # 🛡️ 2. የሰዓት ዞን መጋጨትን መከላከያ (Awareness Enforcement)
                    naive_time = datetime.fromisoformat(last_ping_cfg.value['time'])
                    if timezone.is_naive(naive_time):
                        last_ping_time = timezone.make_aware(naive_time)
                    else:
                        last_ping_time = naive_time
                        
                    # ከተገመተው ጊዜ (ከ 12 ደቂቃ በፊት) ጀምሮ ክሮኑ ሰርቶ ከሆነ የፓይተን ክሩ ዝም ይላል
                    if timezone.now() - last_ping_time < timedelta(minutes=12):
                        should_run_fallback = False
                        print("🛡️ SafetyNet: External Cron is healthy. Standing by...")
                
                # ክሮኑ ፌል ካደረገ ወይም ከተቋረጠ ይህ የፓይተን ኮድ ስራውን ይረከባል
                if should_run_fallback:
                    print("🚨 SafetyNet Active: External Cron missed or failed! Triggering evolution fallback...")
                    # አዲሱ የዕድገት ሞተር መጀመሪያ ኦዲት አድርጎ ባክሎግ ያዘጋጃል፤ ከዚያም ስራዎችን በየተራ ይሰራል
                    result = run_daily_market_analysis()
                    print(f"🚨 SafetyNet Fallback Result: {result}")
                    
            except Exception as e:
                print(f"❌ SafetyNet Thread Error: {e}")
            
            # በየ 10 ደቂቃው (600 ሰከንድ) ክሮኑን በንቃት እየተከታተለ ይፈትሻል
            time.sleep(600)
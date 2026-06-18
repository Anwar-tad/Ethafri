# EthAfri/marketplace/management/commands/evolve_market.py

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone
import logging
import gc
from marketplace.models import SiteConfig  # ⚠️ የክሮን ፒንግ ለመመዝገብ የተጨመረ
from marketplace.growth_agent import run_daily_market_analysis

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'በየቀኑ ገበያውን አጥንቶ ሲስተሙን ያሳድጋል (ክሮን ጆብ ተስማሚ - Run Once & Exit)'

    def handle(self, *args, **kwargs):
        # 🛡️ 1. የቆዩ የዳታቤዝ ግንኙነቶችን ማጽዳት እና የሜሞሪ ቆሻሻዎችን መሰብሰብ
        close_old_connections()
        gc.collect()

        self.stdout.write(self.style.SUCCESS(f"🚀 [{timezone.now()}] EthAfri Autonomous Growth Engine Triggered by Cron."))
        
        try:
            self.stdout.write(f"[{timezone.now()}] 🔍 Running Market Analysis & Evolution cycle...")
            
            # 🛡️ 2. የዕድገት ሂደቱን አንድ ጊዜ ብቻ ማስፈጸም (No Infinite Loop!)
            report = run_daily_market_analysis()
            
            # 🛡️ 3. የክሮኑን ስኬታማነት በዳታቤዝ መመዝገብ (apps.py የደህንነት መረብ ፒንጉን አይቶStandby እንዲሆን!)
            SiteConfig.objects.update_or_create(
                key="LAST_SUCCESSFUL_CRON_PING", 
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
            
            self.stdout.write(self.style.SUCCESS(f"✅ Success: {report}"))
            self.stdout.write(f"⏳ Process finished and exited successfully to preserve RAM.")
            
        except Exception as e:
            logger.error(f"❌ Critical Error in Growth Engine: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
# EthAfri/marketplace/management/commands/evolve_market.py

from django.core.management.base import BaseCommand
from django.db import close_old_connections  # የቆዩ የዳታቤዝ ግንኙነቶችን ማጽጃ
import time
import datetime
import logging
import gc  # ⚠️ የቆሻሻ መጣያውን (Memory Garbage Collector) ለመቆጣጠር የተጨመረ
from marketplace.growth_agent import run_daily_market_analysis

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'በየ 5 ደቂቃው ገበያውን አጥንቶ ሲስተሙን ያሳድጋል'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(f"🚀 [{datetime.datetime.now()}] EthAfri Autonomous Growth Engine Started."))
        
        while True:
            try:
                # 🛡️ 1. የቆዩ የዳታቤዝ ግንኙነቶችን ማጽዳት
                close_old_connections()
                
                # 🛡️ 2. ጥቅም ላይ ያልዋሉ የሜሞሪ ቆሻሻዎችን (Garbage) በየ 5 ደቂቃው እንዲያጸዳ መፍቀድ
                gc.collect()
                
                start_time = time.time()
                self.stdout.write(f"[{datetime.datetime.now()}] 🔍 Running Market Analysis & Evolution cycle...")
                
                # የትንተና ሂደቱን መጀመር
                report = run_daily_market_analysis()
                
                self.stdout.write(self.style.SUCCESS(f"✅ Success: {report}"))
                
                # የሂደቱን ጊዜ በመቀነስ ትክክለኛውን የ 5 ደቂቃ እረፍት ማስጠበቅ
                elapsed_time = time.time() - start_time
                sleep_time = max(0, 300 - elapsed_time)
                
                self.stdout.write(f"⏳ Sleeping for {int(sleep_time)} seconds...")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("🛑 Engine stopped by user."))
                break
            except Exception as e:
                logger.error(f"❌ Critical Error in Growth Engine: {e}")
                self.stdout.write(self.style.ERROR(f"Error: {e} | Sleeping 60s before retry..."))
                time.sleep(60)  # ስህተት ሲፈጠር ለ 1 ደቂቃ ተረጋግቶ እንደገና ይሞክራል
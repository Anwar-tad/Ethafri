# EthAfri/marketplace/management/commands/evolve_market.py

from django.core.management.base import BaseCommand
import time
import datetime
from marketplace.growth_agent import run_daily_market_analysis

class Command(BaseCommand):
    help = 'በየ 5 ደቂቃው ገበያውን አጥንቶ ሲስተሙን ያሳድጋል'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(f"[{datetime.datetime.now()}] EthAfri Growth Engine ተነስቷል..."))
        
        while True:
            try:
                self.stdout.write(f"[{datetime.datetime.now()}] ገበያውን በማጥናት ላይ...")
                report = run_daily_market_analysis()
                self.stdout.write(self.style.SUCCESS(f"ሪፖርት፡ {report}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"ስህተት አጋጥሟል፡ {str(e)}"))
            
            # የጊዜ ዑደቱን ወደ 5 ደቂቃ (300 ሰከንድ) ቀይረነዋል
            self.stdout.write("ለ 5 ደቂቃ እረፍት (300 ሰከንድ)...")
            time.sleep(300)
from django.core.management.base import BaseCommand
import time
import datetime
from marketplace.growth_agent import run_daily_market_analysis

class Command(BaseCommand):
    help = 'በየሰዓቱ ገበያውን አጥንቶ ሲስተሙን ያሳድጋል'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(f"[{datetime.datetime.now()}] EthAfri Growth Engine ተነስቷል..."))
        
        while True:
            try:
                self.stdout.write(f"[{datetime.datetime.now()}] ገበያውን በማጥናት ላይ...")
                
                # የ AI ትንተናውን ይጠራል
                report = run_daily_market_analysis()
                
                self.stdout.write(self.style.SUCCESS(f"ሪፖርት፡ {report}"))
            
            except Exception as e:
                # ስህተት ቢፈጠር እንኳ ዌርከሩ እንዳይሞት እናልፈዋለን
                self.stdout.write(self.style.ERROR(f"ስህተት አጋጥሟል፡ {str(e)}"))
            
            # ስራው ቢሳካም ባይሳካም ለ 1 ሰዓት ይጠብቃል
            self.stdout.write("ለ 1 ሰዓት እረፍት...")
            time.sleep(3600)
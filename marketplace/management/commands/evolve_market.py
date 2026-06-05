from django.core.management.base import BaseCommand
import time
from marketplace.growth_agent import run_daily_market_analysis

class Command(BaseCommand):
    help = 'በየሰዓቱ ገበያውን አጥንቶ ሲስተሙን ያሳድጋል'

    def handle(self, *args, **kwargs):
        self.stdout.write("EthAfri Growth Engine ተነስቷል...")
        while True:
            self.stdout.write("ገበያውን በማጥናት ላይ...")
            # ቀደም ብለን የሰራነውን የ AI ትንተና ይጠራል
            report = run_daily_market_analysis()
            self.stdout.write(f"የሰዓቱ ትንተና ተጠናቋል: {report[:50]}...")
            
            # ለ 1 ሰዓት (3600 ሰከንድ) ይጠብቃል
            time.sleep(3600)
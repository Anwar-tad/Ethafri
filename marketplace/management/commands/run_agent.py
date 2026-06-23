# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/management/commands/run_agent.py
# 📝 ዓላማ፦ Run the autonomous 24/7 growth agent loop
# ✅ ደረጃ፦ ተኳሃኝነት የተረጋገጠለት ስሪት
# 📅 ቀን፦ 2026-06-23
# ============================================================

from django.core.management.base import BaseCommand
from marketplace.growth_agent import run_autonomous_agent, run_single_cycle
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the autonomous 24/7 growth agent'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run only one cycle then exit'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds between cycles (default: 60)'
        )
    
    def handle(self, *args, **kwargs):
        if kwargs.get('once'):
            self.stdout.write("🚀 Running single cycle...")
            result = run_single_cycle()
            self.stdout.write(self.style.SUCCESS(f"✅ {result}"))
        else:
            self.stdout.write(self.style.SUCCESS("🚀 Starting 24/7 Autonomous Agent..."))
            self.stdout.write("   Press Ctrl+C to stop")
            
            from marketplace.growth_agent import AutonomousLoop
            loop = AutonomousLoop()
            loop.interval = kwargs.get('interval', 60)
            loop.start()
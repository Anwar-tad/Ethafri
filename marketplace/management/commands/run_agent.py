# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/management/commands/run_agent.py
# 📝 ዓላማ፦ Run the autonomous 24/7 growth agent loop safely
# ✅ የተፈቱ ችግሮች፦ Database leak inside 24/7 loops, Clean KeyboardInterrupt handling.
# 📅 ቀን፦ Thursday, June 25, 2026
# ============================================================

from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
import logging
import gc
import sys
from marketplace.growth_agent import run_autonomous_agent, run_single_cycle

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
        interval = kwargs.get('interval', 60)
        
        # 🛡️ ሉፑ ከመጀመሩ በፊት የማህደረ ትውስታ ማጽዳት
        close_old_connections()
        gc.collect()

        if kwargs.get('once'):
            self.stdout.write("🚀 Running single cycle...")
            try:
                result = run_single_cycle()
                self.stdout.write(self.style.SUCCESS(f"✅ {result}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Single cycle failed: {e}"))
            finally:
                connection.close()
        else:
            self.stdout.write(self.style.SUCCESS(f"🚀 Starting 24/7 Autonomous Agent (Interval: {interval}s)..."))
            self.stdout.write("   📌 Press Ctrl+C to stop cleanly")
            
            try:
                from marketplace.growth_agent import AutonomousLoop
                loop = AutonomousLoop()
                loop.interval = interval
                
                # የውስጥ ሉፑ ከመዞሩ በፊት የዳታቤዝ ግንኙነቶችን ማጽዳቱን ለማረጋገጥ
                close_old_connections()
                loop.start()
                
            except KeyboardInterrupt:
                # ✅ ማሻሻያ፦ በ Ctrl+C ሲወጣ በሰላም መዘጋቱን ማረጋገጥ
                self.stdout.write(self.style.WARNING("\n👋 Agent execution stopped cleanly by owner."))
                try:
                    connection.close()
                except:
                    pass
                sys.exit(0)
            except Exception as e:
                logger.error(f"❌ Fatal Agent Loop Exception: {e}")
                self.stdout.write(self.style.ERROR(f"Fatal Loop Error: {e}"))
            finally:
                # የመጨረሻ የ RAM እና DB ግንኙነት ማጽጃ
                try:
                    connection.close()
                except:
                    pass
                gc.collect()

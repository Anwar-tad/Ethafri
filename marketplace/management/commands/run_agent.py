# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/management/commands/run_agent.py
# 📝 ዓላማ፦ Safe 24/7 autonomous agent execution with memory management (v1.1)
# ✅ የተፈቱ ችግሮች፦ Memory leak prevention, stable loop, and error isolation
# 📅 ቀን፦ 2026-06-27
# ============================================================

from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
import logging
import gc
import sys
import time
from marketplace.growth_agent import execute_master_cycle

# 🛡️ Logger setup
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the autonomous 24/7 growth agent loop'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds between cycles (default: 60)'
        )
    
    def handle(self, *args, **kwargs):
        interval = kwargs.get('interval', 60)
        self.stdout.write(self.style.SUCCESS(f"🚀 Initializing EthAfri Master CEO Agent (Interval: {interval}s)..."))
        
        # 🔄 Master Loop
        while True:
            try:
                # 1. Database Connection Management (Memory Leak ለመከላከል)
                close_old_connections()
                
                # 2. Execute Business Logic (ዋናውን የኤጀንት የሥራ ዑደት መጥራት)
                self.stdout.write("⚙️ Running Master Cycle...")
                execute_master_cycle()
                
                # 3. Memory Cleanup (Crucial for Free Tier - ራም ለመቆጠብ)
                gc.collect()
                
                self.stdout.write(f"💤 Master Cycle Complete. Sleeping {interval} seconds...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                # 🛑 Shutdown sequence (በ Ctrl+C በሰላም መዘጋቱን ማረጋገጥ)
                self.stdout.write(self.style.WARNING("\n👋 Agent shutdown initiated by user."))
                self.cleanup()
                sys.exit(0)
                
            except Exception as e:
                # ❌ Error handling to prevent total loop failure (ዑደቱ እንዳይቋረጥ መከላከል)
                logger.error(f"❌ Fatal Agent Loop Exception: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Fatal Loop Error: {e}"))
                
                # ከስህተት በኋላ ዳግም ከመነሳቱ በፊት ጥቂት እረፍት መስጠት
                time.sleep(30) 
            
            finally:
                # 🧹 Ensure DB connection is released
                try:
                    connection.close()
                except:
                    pass

    def cleanup(self):
        """Clean resource release method."""
        try:
            connection.close()
            gc.collect()
        except:
            pass
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/management/commands/run_agent.py
# 📝 ዓላማ፦ Safe 24/7 autonomous agent execution with Adaptive Pacing (v1.2)
# ✅ የተፈቱ ችግሮች፦ Dynamic interval adjustment, memory leak prevention, DB load reduction
# 📅 ቀን፦ 2026-06-27
# ============================================================

from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
import logging
import gc
import sys
import time

# የባክሎግ ሁኔታን ለመፈተሽ ሞዴሉን ማስገባት
from marketplace.models import AIProjectBacklog
from marketplace.growth_agent import execute_master_cycle

# 🛡️ Logger setup
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the autonomous 24/7 growth agent loop with Adaptive Pacing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=600,  # ቋሚ መኝታ ከተፈለገ በዲፎልት 10 ደቂቃ (600s) እንዲሆን ተደርጓል
            help='Standard interval in seconds when backlog is empty (default: 600)'
        )
        parser.add_argument(
            '--force-static',
            action='store_true',
            help='Force static interval sleep without adaptive pacing'
        )
    
    def handle(self, *args, **kwargs):
        interval = kwargs.get('interval', 600)
        force_static = kwargs.get('force_static', False)
        
        self.stdout.write(self.style.SUCCESS(
            f"🚀 Initializing EthAfri Master CEO Agent...\n"
            f"   - Base Interval: {interval}s\n"
            f"   - Adaptive Pacing: {'Disabled (Static)' if force_static else 'Enabled (Dynamic)'}"
        ))
        
        # 🔄 Master Loop
        while True:
            try:
                # 1. Database Connection Management (Memory Leak ለመከላከል)
                close_old_connections()
                
                # 2. Execute Business Logic (የሥራ ዑደቱን መጥራት)
                self.stdout.write("⚙️ Running Master Cycle...")
                execute_master_cycle()
                
                # 3. Memory Cleanup (ራም ለመቆጠብ)
                gc.collect()
                
                # 4. Adaptive Pacing logic (የጊዜ ማስተካከያ ሎጂክ)
                if force_static:
                    sleep_duration = interval
                else:
                    try:
                        has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
                        if has_pending:
                            sleep_duration = 30  # የሚሰሩ ስራዎች ካሉ በፍጥነት በየ30 ሰከንዱ ይነሳል
                            self.stdout.write(self.style.NOTICE("⚡ Backlog has pending tasks. Fast-pacing active (30s sleep)..."))
                        else:
                            sleep_duration = interval  # ባዶ ከሆነ ረዘም ላለ ጊዜ ይተኛል
                            self.stdout.write(f"💤 No pending tasks. Concluding cycle. Sleeping {sleep_duration}s to save resources...")
                    except Exception as db_err:
                        logger.warning(f"Failed to query backlog status for pacing: {db_err}")
                        sleep_duration = 60  # ዳታቤዝ ላይ ችግር ካለ በዲፎልት 1 ደቂቃ መጠበቅ
                
                time.sleep(sleep_duration)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n👋 Agent shutdown initiated by user."))
                self.cleanup()
                sys.exit(0)
                
            except Exception as e:
                logger.error(f"❌ Fatal Agent Loop Exception: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Fatal Loop Error: {e}"))
                time.sleep(30)  # ከስህተት በኋላ ዳግም ከመነሳቱ በፊት እረፍት መስጠት
            
            finally:
                # 🧹 የዳታቤዝ ግንኙነቶችን መልቀቅ
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
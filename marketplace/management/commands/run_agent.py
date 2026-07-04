# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/management/commands/run_agent.py
# 📝 ዓላማ፦ Safe 24/7 autonomous agent execution with CPU-Load Adaptive Pacing (v10.18 - Hardened Healing Edition)
# ✅ የተፈቱ ችግሮች፦ Integrated Self-Doctor DB connection refresher on OperationalError, dynamic app model registry loading, CPU-Load adaptive pacing, and memory leak protection.
# 📅 ቀን፦ Saturday, July 04, 2026
# ============================================================

from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection, reset_queries
from django.utils import timezone
from django.apps import apps
import logging
import gc
import sys
import time
import os

from marketplace.growth_agent import execute_master_cycle
from marketplace.ai_utils import broadcast_agent_log
from marketplace.self_doctor import refresh_db_connection_on_error # ✅ የዳታቤዝ ግንኙነት ራስ-ጥገና እዚህ መጥቷል

# 🛡️ Logger setup
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the autonomous 24/7 growth agent loop with CPU-Load Adaptive Pacing'
    
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
        # 🛡️ የሞዴል ተለዋዋጭ ጭነት (Registry Safety) [1]
        AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')

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
                broadcast_agent_log(None, "Command: Master Pacing cycle triggered manually or dynamically.", "info")
                execute_master_cycle()
                
                # 3. Memory Cleanup (ራም ለመቆጠብ) [1]
                reset_queries()  # DEBUG=True በሚሆንበት ወቅት የሚከሰተውን የሜሞሪ መፍሰስ መከላከያ
                gc.collect()
                
                # 4. Adaptive Pacing logic (የጊዜ ማስተካከያ ሎጂክ) [1, 2]
                if force_static:
                    sleep_duration = interval
                else:
                    try:
                        # 🔴 CPU-LOAD ADAPTIVE PACING (ሰርቨር ጥበቃ)
                        try:
                            load_avg = os.getloadavg()[0]
                        except (AttributeError, OSError, Exception):
                            # ዊንዶውስ ወይም በኮንቴይነር ውስጥ os.getloadavg() ካልሰራ ዱሚ ጫና መስጠት
                            load_avg = 0.5
                            
                        if load_avg > 2.0:
                            sleep_duration = 2700  # 45 ደቂቃ (ሰርቨሩ በከፍተኛ ጫና ውስጥ ከሆነ መኝታውን ያረዝማል)
                            self.stdout.write(self.style.WARNING(f"⚠️ Server CPU Load is heavy ({load_avg:.2f}). Pacing slowed to 45 minutes to protect host."))
                            broadcast_agent_log(None, f"Pacing Alert: Server CPU load is heavy ({load_avg:.2f}). Pacing slowed to 45 minutes.", "warning")
                        else:
                            from marketplace.growth_agent import MultiChannelHarvester
                            
                            # 🌐 ኔትወርክ ከሌለ ቶከን ለመቆጠብ Pacing ን በከፍተኛ ሁኔታ ማቀዝቀዝ
                            if not MultiChannelHarvester.is_network_available():
                                sleep_duration = 1800  # 30 ደቂቃ
                                self.stdout.write(self.style.WARNING("🌐 Network is offline. Slow-pacing active (1800s sleep to save tokens)..."))
                                broadcast_agent_log(None, "Pacing Alert: Server is offline. Sleeping for 30 minutes.", "warning")
                            else:
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
                
                # 🛡️ FIXED: OperationalError ከተከሰተ በራስ-ሰር ሪፍሬሽ በማድረግ ግንኙነቱን መጠገን
                db_refreshed = refresh_db_connection_on_error(str(e))
                if db_refreshed:
                    self.stdout.write(self.style.WARNING("🚑 Database connection refreshed safely across all active threads."))
                
                time.sleep(30)  # ከስህተት በኋላ ዳግም ከመነሳቱ በፊት እረፍት መስጠት
            
            finally:
                # 🧹 የዳታቤዝ ግንኙነቶችን መልቀቅ
                try:
                    connection.close()
                except Exception as close_err:
                    logger.debug("Database connection close safely ignored: %s", close_err)

    def cleanup(self):
        """Clean resource release method."""
        try:
            connection.close()
            gc.collect()
            logger.info("🧹 Cleaned up DB connections and garbage collector successfully.")
        except Exception as cleanup_err:
            logger.debug("Cleanup exception safely ignored: %s", cleanup_err)
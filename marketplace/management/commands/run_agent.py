# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/management/commands/run_agent.py
# 📝 ዓላማ፦ Safe 24/7 autonomous agent execution with CPU-Load Adaptive Pacing (v10.20)
# ✅ የተፈቱ ችግሮች፦ Dynamic apps model registry upgraded, AIProjectBacklog registry check added in handle() to prevent unmigrated database crashes, and experiential failure memory logging added on daemon loop fatal exceptions (v10.20).
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

from django.core.management.base import BaseCommand
from django.db import connections, connection, reset_queries
from django.utils import timezone
from django.apps import apps
import logging
import gc
import sys
import time
import os

# 🛡️ Logger setup
logger = logging.getLogger(__name__)


# ============================================================
# 🌐 DECOUPLED NETWORK CONNECTIVITY CHECKER
# ============================================================
def _is_network_available() -> bool:
    """
    ከ growth_agent.py እና ከ MultiChannelHarvester መደብ ነጻ በሆነ መንገድ 
    የበይነመረብ ግንኙነት መኖሩን በደህንነት የሚፈትሽ ረዳት
    """
    import requests
    try:
        # በኢትዮጵያ ውስጥ ፈጣንና አስተማማኝ ለሆኑ የፍተሻ ጣቢያዎች ጥሪ ማድረግ
        return requests.get("https://google.com", timeout=3).status_code == 200
    except requests.RequestException:
        return False


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
        # 🛡️ FIXED: Lazy Loading of agent and doctor modules inside handle()
        from marketplace.growth_agent import execute_master_cycle
        from marketplace.ai_utils import broadcast_agent_log
        from marketplace.self_doctor import refresh_db_connection_on_error

        # የሞዴል ተለዋዋጭ ጭነት (Registry Safety)
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
                connections.close_all()
                
                # 2. Execute Business Logic (የሥራ ዑደቱን መጥራት)
                self.stdout.write("⚙️ Running Master Cycle...")
                broadcast_agent_log(None, "Command: Master Pacing cycle triggered manually or dynamically.", "info")
                execute_master_cycle()
                
                # 3. Memory Cleanup (ራም ለመቆጠብ)
                reset_queries()  # DEBUG=True በሚሆንበት ወቅት የሚከሰተውን የሜሞሪ መፍሰስ መከላከያ
                gc.collect()
                
                # 4. Adaptive Pacing logic (የጊዜ ማስተካከያ ሎጂክ)
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
                            # 🛡️ FIXED: Decoupled network connectivity checker from MultiChannelHarvester to prevent boot-time import loops
                            if not _is_network_available():
                                sleep_duration = 1800  # 30 ደቂቃ
                                self.stdout.write(self.style.WARNING("🌐 Network is offline. Slow-pacing active (1800s sleep to save tokens)..."))
                                broadcast_agent_log(None, "Pacing Alert: Server is offline. Sleeping for 30 minutes.", "warning")
                            else:
                                # 🛡️ FIXED: Safety guard when registry load fails to prevent AttributeErrors on startup [1]
                                if AIProjectBacklog:
                                    has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
                                else:
                                    has_pending = False
                                    
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
                
                # 🛡️ EXPERIENTIAL LEARNING: የዴሞን ሉፕ መቆራረጥ ውድቀትን በታሪክ መዝገብ ውስጥ መመዝገብ (የመማር ሎጂክ)
                VectorMemory = apps.get_model('marketplace', 'VectorMemory')
                if VectorMemory:
                    try:
                        VectorMemory.objects.create(
                            site=None,
                            memory_type='failed_attempt',
                            content=f"24/7 Agent Daemon Loop failed with exception: {str(e)}",
                            success_rate=0.0
                        )
                    except Exception: pass

                db_refreshed = refresh_db_connection_on_error(str(e))
                if db_refreshed:
                    self.stdout.write(self.style.WARNING("🚑 Database connection refreshed safely across all active threads."))
                
                time.sleep(30)  # ከስህተት በኋላ ዳግም ከመነሳቱ በፊት እረፍት መስጠት
            
            finally:
                # 🧹 የዳታቤዝ ግንኙነቶችን መልቀቅ (Multi-Thread Safe release)
                try:
                    connections.close_all()
                except Exception as close_err:
                    logger.debug("Database connections close safely ignored: %s", close_err)

    def cleanup(self):
        """Clean resource release method."""
        try:
            connections.close_all()
            gc.collect()
            logger.info("🧹 Cleaned up DB connections and garbage collector successfully.")
        except Exception as cleanup_err:
            logger.debug("Cleanup exception safely ignored: %s", cleanup_err)
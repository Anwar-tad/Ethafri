# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/management/commands/run_agent.py
# 📝 ዓላማ፦ Safe 24/7 autonomous agent execution with CPU-Load Adaptive Pacing (v11.00)
# ✅ የተፈቱ ችግሮች፦ Dynamic apps model registry, and optimized Render-friendly CPU pacing 
#                    threshold (raised to 8.0) and shorter cooldowns to break the sleep trap (v11.00).
# 📅 ቀን፦ Friday, July 24, 2026
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

logger = logging.getLogger(__name__)


# ============================================================
# 🌐 DECOUPLED NETWORK CONNECTIVITY CHECKER
# ============================================================
def _is_network_available() -> bool:
    """
    ከ growth_agent.py መደብ ነጻ በሆነ መንገድ የበይነመረብ ግንኙነት መኖሩን በደህንነት የሚፈትሽ ረዳት
    """
    import requests
    try:
        return requests.get("https://google.com", timeout=3).status_code == 200
    except requests.RequestException:
        return False


class Command(BaseCommand):
    help = 'Run the autonomous 24/7 growth agent loop with CPU-Load Adaptive Pacing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,  # ቋሚ መኝታ ከተፈለገ በዲፎልት 1 ደቂቃ (60s) እንዲሆን ተደርጓል
            help='Standard interval in seconds when backlog is empty (default: 60)'
        )
        parser.add_argument(
            '--force-static',
            action='store_true',
            help='Force static interval sleep without adaptive pacing'
        )
    
    def handle(self, *args, **kwargs):
        from marketplace.growth_agent import execute_master_cycle
        from marketplace.ai_utils import broadcast_agent_log
        from marketplace.self_doctor import refresh_db_connection_on_error

        AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')

        interval = kwargs.get('interval', 60)
        force_static = kwargs.get('force_static', False)
        
        self.stdout.write(self.style.SUCCESS(
            f"🚀 Initializing EthAfri Master CEO Agent...\n"
            f"   - Base Interval: {interval}s\n"
            f"   - Adaptive Pacing: {'Disabled (Static)' if force_static else 'Enabled (Dynamic)'}"
        ))
        
        # 🔄 Master Loop
        while True:
            try:
                connections.close_all()
                
                self.stdout.write("⚙️ Running Master Cycle...")
                broadcast_agent_log(None, "Command: Master Pacing cycle triggered manually or dynamically.", "info")
                execute_master_cycle()
                
                reset_queries()  
                gc.collect()
                
                # የጊዜ ማስተካከያ ሎጂክ
                if force_static:
                    sleep_duration = interval
                else:
                    try:
                        # 🔴 CPU-LOAD ADAPTIVE PACING (ሰርቨር ጥበቃ)
                        try:
                            load_avg = os.getloadavg()[0]
                        except (AttributeError, OSError, Exception):
                            load_avg = 0.5
                            
                        # 🛡️ RENDER-FRIENDLY TIMEOUTS: የሲፒዩ መከላከያ ገደቡን ወደ 8.0 ከፍ ማድረግ
                        if load_avg > 8.0:
                            sleep_duration = 300  # 5 ደቂቃ (የ 45 ደቂቃ መኝታ ወጥመድ እዚህ ተሰብሯል)
                            self.stdout.write(self.style.WARNING(f"⚠️ Server CPU Load is extremely heavy ({load_avg:.2f}). Pacing slowed to 5 minutes to protect host."))
                            broadcast_agent_log(None, f"Pacing Alert: Server CPU load is extremely heavy ({load_avg:.2f}). Pacing slowed to 5 minutes.", "warning")
                        else:
                            if not _is_network_available():
                                sleep_duration = 300  # 5 ደቂቃ (ከ 30 ደቂቃ እንቅልፍ ወደ 5 ደቂቃ ተቀንሷል)
                                self.stdout.write(self.style.WARNING("🌐 Network is offline. Slow-pacing active (5-minute sleep to save tokens)..."))
                                broadcast_agent_log(None, "Pacing Alert: Server is offline. Sleeping for 5 minutes.", "warning")
                            else:
                                if AIProjectBacklog:
                                    has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
                                else:
                                    has_pending = False
                                    
                                if has_pending:
                                    sleep_duration = 15  # የሚሰሩ ስራዎች ካሉ በየ 15 ሰከንዱ በፍጥነት ይነሳል
                                    self.stdout.write(self.style.NOTICE("⚡ Backlog has pending tasks. Fast-pacing active (15s sleep)..."))
                                else:
                                    sleep_duration = interval  # ባዶ ከሆነ በዲፎልት 1 ደቂቃ (60 ሰከንድ) ይተኛል
                                    self.stdout.write(f"💤 No pending tasks. Concluding cycle. Sleeping {sleep_duration}s to save resources...")
                    except Exception as db_err:
                        logger.warning(f"Failed to query backlog status for pacing: {db_err}")
                        sleep_duration = 60  
                
                time.sleep(sleep_duration)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n👋 Agent shutdown initiated by user."))
                self.cleanup()
                sys.exit(0)
                
            except Exception as e:
                logger.error(f"❌ Fatal Agent Loop Exception: {e}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Fatal Loop Error: {e}"))
                
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
                
                time.sleep(30)  
            
            finally:
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
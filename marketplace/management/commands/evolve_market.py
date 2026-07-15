# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/management/commands/evolve_market.py
# 📝 ዓላማ፦ Robust Growth Engine & Command Entry Point (v10.20)
# ✅ የተፈቱ ችግሮች፦ Dynamic apps model registry upgraded, SiteConfig and SiteRegistry registry checks added in handle() to prevent unmigrated database crashes, and experiential failure memory logging added on cron job site analysis failures (v10.20).
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

from django.core.management.base import BaseCommand
from django.db import connections, connection
from django.utils import timezone
from django.apps import apps
import logging
import gc

logger = logging.getLogger(__name__)


# የ growth_agent አስገቢዎችን የዲፔንደንሲ ግጭት ለማስቀረት የተሰሩ የሥራ መጋጠሚያዎች
def run_single_site_analysis(site):
    """የአንድን ንዑስ ጣቢያ የዕድገት ዑደት ከዋናው _run_site_cycle ጋር ያገናኛል"""
    from marketplace.growth_agent import _run_site_cycle
    _run_site_cycle(site)
    return "Site analysis completed successfully."


def run_daily_market_analysis():
    """ሁሉንም ጣቢያዎች በዳይናሚክ Concurrency የሚያስነሳውን execute_master_cycle ይጠራል"""
    from marketplace.growth_agent import execute_master_cycle
    execute_master_cycle()
    return "Global daily market analysis completed successfully."


def discover_new_sites():
    """SaaS አዲስ ጣቢያ መፈለጊያ (Dynamic Explorer እራሱ ስለሚሰራው ባዶ ዝርዝር ይመልሳል)"""
    return []


class Command(BaseCommand):
    help = 'በየቀኑ ገበያውን አጥንቶ ሲስተሙን ያሳድጋል (ክሮን ጆብ ተስማሚ - Run Once & Exit)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site',
            type=str,
            help='ለአንድ የተወሰነ ጣቢያ ብቻ ለማስኬድ (የጣቢያውን ስም ያስገቡ)'
        )
        parser.add_argument(
            '--all-sites',
            action='store_true',
            help='ለሁሉም ንቁ ጣቢያዎች ማስኬድ'
        )
        parser.add_argument(
            '--discover',
            action='store_true',
            help='አዲስ ጣቢያዎችን በራስ-ሰር ፈልጎ ለማግኘት'
        )

    def handle(self, *args, **kwargs):
        # 🛡️ FIXED: Lazy Loading of self_doctor tools to prevent early boot circular dependencies
        from marketplace.self_doctor import refresh_db_connection_on_error

        # የሞዴል ተለዋዋጭ ጭነት (Registry Safety)
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')

        # 🛡️ FIXED: Safety guard when registry load fails to prevent AttributeErrors on startup [1]
        if not SiteConfig or not SiteRegistry:
            self.stdout.write(self.style.WARNING("⚠️ Command: Delayed execution as models are not fully registered yet."))
            return

        site_name = kwargs.get('site')
        all_sites = kwargs.get('all_sites')
        discover = kwargs.get('discover')
        
        try:
            connections.close_all()
        except Exception as conn_err:
            logger.debug("Failed to close old connections on startup: %s", conn_err)
            
        gc.collect()

        self.stdout.write(self.style.SUCCESS(f"🚀 [{timezone.now()}] EthAfri Autonomous Growth Engine Triggered."))
        
        try:
            try:
                from marketplace.growth_agent import execute_master_cycle
            except ImportError as ie:
                error_msg = f"❌ Critical Import Error: growth_agent.py module is broken or missing. Details: {ie}"
                self.stdout.write(self.style.ERROR(error_msg))
                logger.critical(error_msg)
                
                SiteConfig.objects.update_or_create(
                    key="LAST_CRON_ERROR",
                    defaults={'value': {'time': timezone.now().isoformat(), 'error': error_msg}}
                )
                return

            if discover:
                try:
                    new_sites = discover_new_sites()
                    if new_sites:
                        self.stdout.write(self.style.SUCCESS(f"🆕 Discovered {len(new_sites)} new sites!"))
                    else:
                        self.stdout.write("🔍 No new sites discovered.")
                except Exception as de:
                    self.stdout.write(self.style.WARNING(f"⚠️ Discover failed: {de}"))
            
            sites_to_process = []
            if site_name:
                try:
                    site = SiteRegistry.objects.get(name=site_name, is_active=True)
                    sites_to_process = [site]
                    self.stdout.write(f"📍 Processing site: {site_name}")
                except SiteRegistry.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"❌ Site '{site_name}' not found or inactive."))
                    return
            elif all_sites:
                sites_to_process = SiteRegistry.objects.filter(is_active=True)
                self.stdout.write(f"📍 Processing all {sites_to_process.count()} active sites")
            else:
                default_site = SiteRegistry.objects.filter(name='primary', is_active=True).first()
                if default_site:
                    sites_to_process = [default_site]
                    self.stdout.write("📍 Processing primary site")
                else:
                    self.stdout.write("📍 No active sites found. Running global analysis...")
                    sites_to_process = []
            
            results = []
            if sites_to_process:
                for site in sites_to_process:
                    try:
                        connections.close_all()
                    except Exception as conn_err:
                        logger.debug("Failed to clear connection before site process: %s", conn_err)
                        
                    self.stdout.write(f"  🔍 Analyzing {site.name}...")
                    try:
                        result = run_single_site_analysis(site)
                        clean_result = str(result)[:100]
                        results.append(f"[{site.name}] {clean_result}")
                        self.stdout.write(self.style.SUCCESS(f"  ✅ {site.name} completed"))
                    except Exception as e:
                        error_summary = str(e)[:100]
                        results.append(f"[{site.name}] ❌ Error: {error_summary}")
                        self.stdout.write(self.style.ERROR(f"  ❌ {site.name} failed: {e}"))
                        
                        # 🛡️ EXPERIENTIAL LEARNING: የክሮን ጣቢያ ጥሪ ውድቀትን በታሪክ መዝገብ ውስጥ መመዝገብ (የመማር ሎጂክ)
                        VectorMemory = apps.get_model('marketplace', 'VectorMemory')
                        if VectorMemory:
                            try:
                                VectorMemory.objects.create(
                                    site=site,
                                    memory_type='failed_attempt',
                                    content=f"Cron run_single_site_analysis failed for site {site.name} with error: {str(e)}",
                                    success_rate=0.0
                                )
                            except Exception: pass
            else:
                try:
                    result = run_daily_market_analysis()
                    results.append(f"[Global] {str(result)[:100]}")
                except Exception as ge:
                    results.append(f"[Global] ❌ Error: {str(ge)[:100]}")
                    self.stdout.write(self.style.ERROR(f"  ❌ Global analysis failed: {ge}"))
            
            SiteConfig.objects.update_or_create(
                key="LAST_SUCCESSFUL_CRON_PING", 
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
            
            SiteConfig.objects.update_or_create(
                key="LAST_CRON_RUN",
                defaults={'value': {
                    'time': timezone.now().isoformat(),
                    'sites_processed': len(sites_to_process),
                    'results': results[:5]
                }}
            )
            
            summary = " | ".join(results[:3]) + ("..." if len(results) > 3 else "")
            self.stdout.write(self.style.SUCCESS(f"✅ Success: {summary}"))
            
        except Exception as e:
            logger.error(f"❌ Critical Error in Growth Engine: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            
            db_refreshed = refresh_db_connection_on_error(str(e))
            if db_refreshed:
                self.stdout.write(self.style.WARNING("🚑 Database connection refreshed safely across all active threads."))
                
            try:
                SiteConfig.objects.update_or_create(
                    key="LAST_CRON_ERROR",
                    defaults={'value': {
                        'time': timezone.now().isoformat(),
                        'error': str(e)[:200]
                    }}
                )
            except Exception as config_err:
                logger.debug("Failed to record LAST_CRON_ERROR: %s", config_err)
        finally:
            try:
                connections.close_all()
            except Exception as conn_err:
                logger.debug("Failed to close old connections safely during command shutdown: %s", conn_err)
            gc.collect()
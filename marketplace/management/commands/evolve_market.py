# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/management/commands/evolve_market.py
# 📝 ለውጥ፦ Multi-Site Support + Enhanced Growth Engine
# 📅 ቀን፦ 2026-06-20
# ============================================================

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone
import logging
import gc
from marketplace.models import SiteConfig, SiteRegistry
from marketplace.growth_agent import run_daily_market_analysis, run_single_site_analysis

logger = logging.getLogger(__name__)

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
        site_name = kwargs.get('site')
        all_sites = kwargs.get('all_sites')
        discover = kwargs.get('discover')
        
        # 🛡️ 1. የቆዩ የዳታቤዝ ግንኙነቶችን ማጽዳት
        close_old_connections()
        gc.collect()

        self.stdout.write(self.style.SUCCESS(f"🚀 [{timezone.now()}] EthAfri Autonomous Growth Engine Triggered by Cron."))
        
        try:
            # 🆕 አዲስ ጣቢያዎችን ለማግኘት
            if discover:
                from marketplace.growth_agent import discover_new_sites
                new_sites = discover_new_sites()
                if new_sites:
                    self.stdout.write(self.style.SUCCESS(f"🆕 Discovered {len(new_sites)} new sites!"))
                    for site in new_sites:
                        self.stdout.write(f"  - {site.name}: {site.display_name}")
                else:
                    self.stdout.write("🔍 No new sites discovered.")
            
            # 🆕 የትኞቹን ጣቢያዎች እንደምናስኬድ ወስን
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
                # ነባሪ ጣቢያ ብቻ
                default_site = SiteRegistry.objects.filter(name='primary', is_active=True).first()
                if default_site:
                    sites_to_process = [default_site]
                    self.stdout.write("📍 Processing primary site")
                else:
                    self.stdout.write("📍 No active sites found. Running global analysis...")
                    sites_to_process = []
            
            # 🆕 ለእያንዳንዱ ጣቢያ ትንተና አስኬድ
            results = []
            
            if sites_to_process:
                for site in sites_to_process:
                    self.stdout.write(f"  🔍 Analyzing {site.name}...")
                    try:
                        result = run_single_site_analysis(site)
                        results.append(f"[{site.name}] {result}")
                        self.stdout.write(self.style.SUCCESS(f"  ✅ {site.name} completed"))
                    except Exception as e:
                        error_msg = f"[{site.name}] ❌ Error: {str(e)}"
                        results.append(error_msg)
                        self.stdout.write(self.style.ERROR(f"  ❌ {site.name} failed: {e}"))
            else:
                # ምንም ጣቢያ ከሌለ ዓለም አቀፍ ትንተና
                result = run_daily_market_analysis()
                results.append(f"[Global] {result}")
            
            # 🛡️ 2. የክሮኑን ስኬታማነት በዳታቤዝ መመዝገብ
            SiteConfig.objects.update_or_create(
                key="LAST_SUCCESSFUL_CRON_PING", 
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
            
            # 🛡️ 3. የመጨረሻውን የክሮን ሩጫ መዝግብ
            SiteConfig.objects.update_or_create(
                key="LAST_CRON_RUN",
                defaults={'value': {
                    'time': timezone.now().isoformat(),
                    'sites_processed': len(sites_to_process),
                    'results': results[:5]  # የመጀመሪያዎቹን 5 ብቻ
                }}
            )
            
            summary = " | ".join(results[:3]) + ("..." if len(results) > 3 else "")
            self.stdout.write(self.style.SUCCESS(f"✅ Success: {summary}"))
            self.stdout.write(f"⏳ Process finished and exited successfully to preserve RAM.")
            
        except Exception as e:
            logger.error(f"❌ Critical Error in Growth Engine: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            
            # ስህተቱን መዝግብ
            try:
                SiteConfig.objects.update_or_create(
                    key="LAST_CRON_ERROR",
                    defaults={'value': {
                        'time': timezone.now().isoformat(),
                        'error': str(e)[:500]
                    }}
                )
            except:
                pass
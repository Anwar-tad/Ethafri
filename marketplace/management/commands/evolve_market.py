# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/management/commands/evolve_market.py
# 📝 ለውጥ፦ Robust Growth Engine + Protected Imports & Bulletproof Exceptions
# ✅ የተፈቱ ችግሮች፦ Import Vulnerabilities, Database Connection Contamination.
# 📅 ቀን፦ 2026-06-25
# ============================================================

from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
from django.utils import timezone
import logging
import gc
import json
from marketplace.models import SiteConfig, SiteRegistry

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
        
        close_old_connections()
        gc.collect()

        self.stdout.write(self.style.SUCCESS(f"🚀 [{timezone.now()}] EthAfri Autonomous Growth Engine Triggered."))
        
        try:
            # 🛡️ ላለፈው የ "Growth Agent module missing" ስህተት መከላከያ (Lazy Import)
            try:
                from marketplace.growth_agent import (
                    run_daily_market_analysis, 
                    run_single_site_analysis,
                    discover_new_sites
                )
            except ImportError as ie:
                error_msg = f"❌ Critical Import Error: growth_agent.py module is broken or missing. Details: {ie}"
                self.stdout.write(self.style.ERROR(error_msg))
                logger.critical(error_msg)
                
                SiteConfig.objects.update_or_create(
                    key="LAST_CRON_ERROR",
                    defaults={'value': json.dumps({'time': timezone.now().isoformat(), 'error': error_msg})}
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
                    close_old_connections()
                    self.stdout.write(f"  🔍 Analyzing {site.name}...")
                    try:
                        result = run_single_site_analysis(site)
                        # የጽሑፉን ርዝመት ለደህንነት ማሳጠር
                        clean_result = str(result)[:100]
                        results.append(f"[{site.name}] {clean_result}")
                        self.stdout.write(self.style.SUCCESS(f"  ✅ {site.name} completed"))
                    except Exception as e:
                        error_summary = str(e)[:100]
                        results.append(f"[{site.name}] ❌ Error: {error_summary}")
                        self.stdout.write(self.style.ERROR(f"  ❌ {site.name} failed: {e}"))
            else:
                try:
                    result = run_daily_market_analysis()
                    results.append(f"[Global] {str(result)[:100]}")
                except Exception as ge:
                    results.append(f"[Global] ❌ Error: {str(ge)[:100]}")
                    self.stdout.write(self.style.ERROR(f"  ❌ Global analysis failed: {ge}"))
            
            # ✅ የዳታቤዝ ማሻሻያዎችን ማስቀመጥ
            SiteConfig.objects.update_or_create(
                key="LAST_SUCCESSFUL_CRON_PING", 
                defaults={'value': json.dumps({'time': timezone.now().isoformat()})}
            )
            
            SiteConfig.objects.update_or_create(
                key="LAST_CRON_RUN",
                defaults={'value': json.dumps({
                    'time': timezone.now().isoformat(),
                    'sites_processed': len(sites_to_process),
                    'results': results[:5]
                })}
            )
            
            summary = " | ".join(results[:3]) + ("..." if len(results) > 3 else "")
            self.stdout.write(self.style.SUCCESS(f"✅ Success: {summary}"))
            
        except Exception as e:
            logger.error(f"❌ Critical Error in Growth Engine: {e}")
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            try:
                SiteConfig.objects.update_or_create(
                    key="LAST_CRON_ERROR",
                    defaults={'value': json.dumps({
                        'time': timezone.now().isoformat(),
                        'error': str(e)[:200]
                    })}
                )
            except:
                pass
        finally:
            connection.close()
            gc.collect()

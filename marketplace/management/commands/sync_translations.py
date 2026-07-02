# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/management/commands/sync_translations.py
# 📝 ለውጥ፦ Dynamic API Pacing Translation Guard + Naming Sync (v10.16)
# ✅ የተፈቱ ችግሮች፦ Dynamic API pacing (preventing 429 lockouts), polib safe import shielding, and dynamic model registry loading.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

import os
import json
import shutil
import logging
import re
import time  # 🔴 429 Rate Limit ለመከላከል መኝታ (Pacing) የተጨመረበት

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.apps import apps
from typing import Dict, List, Optional, Union, Any
# የዲፔንደንሲ ክራሽን ለመከላከል ወደ smart_ai_router መፍቻ አቅጣጫ ተቀይሯል
from marketplace.ai_utils import ask_master_ai_smart, clean_and_parse_json

logger = logging.getLogger(__name__)

# 🛡️ SAFE IMPORT SHIELD: polib ጥቅል በሰርቨሩ ላይ ካልተጫነ ኮማንዱ እንዳይከሰከስ መከላከያ [1]
try:
    import polib
    POLIB_AVAILABLE = True
except ImportError:
    POLIB_AVAILABLE = False


def ask_ai_with_failover(prompt, pool_type="translation", expected_keys=None):
    """
    [Dependency Resolver] በልዩ ሁኔታ የተዘጋጀውን የትርጉም ሥራ ወደ ai_utils.ask_master_ai_smart ያዞራል
    """
    return ask_master_ai_smart(prompt, task_type="translation")


class Command(BaseCommand):
    help = 'በዌብሳይቱ ላይ ያሉ አዳዲስ የቋንቋ መለያዎችን (i18n tags) በ AI በራስ-ሰር ይተረጉማል'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site',
            type=str,
            help='ለአንድ የተወሰነ ጣቢያ ብቻ ትርጉም ለማድረግ (የጣቢያውን ስም ያስገቡ)'
        )
        parser.add_argument(
            '--all-sites',
            action='store_true',
            help='ለሁሉም ንቁ ጣቢያዎች ትርጉም ለማድረግ'
        )

    def handle(self, *args, **kwargs):
        # 1. polib ጥቅል መኖሩን ማረጋገጥ
        if not POLIB_AVAILABLE:
            raise CommandError(
                "❌ የትርጉም ስራውን ለማጠናቀር 'polib' ጥቅል በሰርቨሩ ላይ አልተገኘም። "
                "እባክዎ መጀመሪያ 'pip install polib' ያካሂዱ።"
            )

        # 2. የሞዴል ተለዋዋጭ ጭነት (Registry Safety) [1]
        SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')

        site_name = kwargs.get('site')
        all_sites = kwargs.get('all_sites')
        
        self.stdout.write(self.style.SUCCESS("🤖 EthAfri I18n Agent: አዳዲስ የቋንቋ መለያዎችን በማስተካከል ላይ..."))
        
        sites_to_process = []
        
        if site_name:
            try:
                site = SiteRegistry.objects.get(name=site_name, is_active=True)
                sites_to_process = [site]
                self.stdout.write(f"📍 Processing translations for site: {site_name}")
            except SiteRegistry.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Site '{site_name}' not found or inactive."))
                return
        elif all_sites:
            sites_to_process = SiteRegistry.objects.filter(is_active=True)
            self.stdout.write(f"📍 Processing translations for all {sites_to_process.count()} active sites")
        else:
            default_site = SiteRegistry.objects.filter(name='primary', is_active=True).first()
            if default_site:
                sites_to_process = [default_site]
                self.stdout.write("📍 Processing translations for primary site")
            else:
                self.stdout.write(self.style.WARNING("⚠️ No active sites found. Using default translation mode."))
                sites_to_process = []
        
        for site in sites_to_process:
            self.stdout.write(self.style.SUCCESS(f"\n📝 Translating for site: {site.display_name} ({site.name})"))
            self._process_site_translations(site)
        
        self._process_system_translations()
        self.stdout.write(self.style.SUCCESS("🎉 የትርጉም ስራው እና ማጠናቀሪያው ሙሉ በሙሉ ተጠናቋል!"))

    def _clean_and_parse_json(self, raw_data):
        """AI የሚመልሰውን ጥሬ ምላሽ አጽድቶ ወደ ዲክሽነሪ ይቀይራል"""
        return clean_and_parse_json(raw_data)

    def _process_system_translations(self):
        """የሲስተሙን መደበኛ ትርጉም ያካሂዳል"""
        has_gettext = shutil.which('xgettext') is not None
        
        if has_gettext:
            try:
                call_command('makemessages', locale=['am', 'om', 'ar', 'so', 'ti', 'fr'], 
                            ignore=['.venv/*', 'node_modules/*'])
                self.stdout.write(self.style.SUCCESS("✅ አዳዲስ የቋንቋ መለያዎች በሰላም ተሰብስበዋል።"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ makemessages Error: {e}"))
        else:
            self.stdout.write(self.style.WARNING("⚠️ GNU gettext አልተገኘም። አዳዲስ ቃላትን መሰብሰብ አይቻልም።"))

        locales = {'am': 'Amharic', 'om': 'Oromo', 'ar': 'Arabic', 'so': 'Somali', 'ti': 'Tigrinya', 'fr': 'French'}

        for lang_code, lang_name in locales.items():
            po_file_path = os.path.join(settings.BASE_DIR, 'locale', lang_code, 'LC_MESSAGES', 'django.po')
            mo_file_path = os.path.join(settings.BASE_DIR, 'locale', lang_code, 'LC_MESSAGES', 'django.mo')
            
            if not os.path.exists(po_file_path):
                self.stdout.write(self.style.WARNING(f"⚠️ ፋይል አልተገኘም፡ {po_file_path}"))
                continue

            po = polib.pofile(po_file_path)
            untranslated = po.untranslated_entries()

            if not untranslated:
                self.stdout.write(f"✨ {lang_name} - ምንም ያልተተረጎመ ቃል የለም።")
                try:
                    po.save_as_mofile(mo_file_path)
                except Exception as mo_err:
                    logger.debug("Failed to compile MO file for empty untranslated entries: %s", mo_err)
                continue

            self.stdout.write(self.style.WARNING(f"🧠 {len(untranslated)} የ {lang_name} ቃላት በ AI በባች (Batch) በመተርጎም ላይ..."))
            
            batch_size = 15
            untranslated_list = list(untranslated)
            count = 0
            
            for i in range(0, len(untranslated_list), batch_size):
                batch = untranslated_list[i : i + batch_size]
                translation_payload = {entry.msgid: entry.msgid for entry in batch}
                
                prompt = (
                    f"Translate the values of the following JSON dictionary keys into {lang_name}. "
                    f"Provide the result in a JSON format with a single key 'translations' "
                    f"which maps the original English key to its {lang_name} translation. "
                    f"Dictionary: {json.dumps(translation_payload, ensure_ascii=False)}"
                )
                
                current_batch_index = i // batch_size
                if current_batch_index % 2 == 0:
                    pool_choice = "translation_github"
                    self.stdout.write(f"  ➡️ Batch {current_batch_index + 1}: Routing to GitHub Models...")
                else:
                    pool_choice = "translation_huggingface"
                    self.stdout.write(f"  ➡️ Batch {current_batch_index + 1}: Routing to Hugging Face...")

                raw_translated = ask_ai_with_failover(prompt, pool_type=pool_choice, expected_keys=["translations"])
                translated_data = self._clean_and_parse_json(raw_translated)
                
                if translated_data and "error" not in translated_data:
                    translations_map = (
                        translated_data.get('translations') or 
                        translated_data.get('translation') or 
                        translated_data
                    )
                    
                    if isinstance(translations_map, dict):
                        for entry in batch:
                            translated_text = translations_map.get(entry.msgid)
                            if translated_text and len(str(translated_text).strip()) > 0:
                                entry.msgstr = str(translated_text).strip()
                                count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Batch request failed or returned invalid schema."))

                # 🔴 DYNAMIC API PACING: የ 24-ሰዓት የ AI ኮታ መቆለፊያን ለመከላከል በእያንዳንዱ ጥሪ መካከል መኝታ [1]
                time.sleep(1.5)

            po.save()
            try:
                po.save_as_mofile(mo_file_path)
                self.stdout.write(self.style.SUCCESS(f"✅ {count} የ {lang_name} ቃላት ተተርጎመው ተጠናቅረዋል።"))
            except Exception as compile_err:
                self.stdout.write(self.style.ERROR(f"❌ Python MO Compilation Error: {compile_err}"))

    def _process_site_translations(self, site):
        """ለአንድ የተወሰነ ጣቢያ የተለየ ትርጉም ያካሂዳል"""
        SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')
        site_locale_path = os.path.join(site.repo_path or settings.BASE_DIR, 'locale')
        
        if not os.path.exists(site_locale_path):
            self.stdout.write(self.style.WARNING(f"⚠️ No locale directory found for {site.name}"))
            return
        
        locales = {'am': 'Amharic', 'om': 'Oromo', 'ar': 'Arabic', 'so': 'Somali', 'ti': 'Tigrinya', 'fr': 'French'}
        
        keywords_list = site.primary_keywords if isinstance(site.primary_keywords, list) else []
        site_context = f"""
        Site: {site.display_name}
        Niche: {site.niche}
        Keywords: {', '.join(str(k) for k in keywords_list[:5])}
        Target Market: {site.target_market}
        """
        
        for lang_code, lang_name in locales.items():
            po_file_path = os.path.join(site_locale_path, lang_code, 'LC_MESSAGES', 'django.po')
            mo_file_path = os.path.join(site_locale_path, lang_code, 'LC_MESSAGES', 'django.mo')
            
            if not os.path.exists(po_file_path):
                continue
            
            po = polib.pofile(po_file_path)
            untranslated = po.untranslated_entries()
            
            if not untranslated:
                continue
            
            batch_size = 15
            untranslated_list = list(untranslated)
            count = 0
            
            for i in range(0, len(untranslated_list), batch_size):
                batch = untranslated_list[i : i + batch_size]
                translation_payload = {entry.msgid: entry.msgid for entry in batch}
                
                prompt = (
                    f"Translate the following text into {lang_name}. "
                    f"Consider the context: {site_context}\n\n"
                    f"Dictionary: {json.dumps(translation_payload, ensure_ascii=False)}\n\n"
                    f"Return JSON with key 'translations' mapping original to translated text."
                )
                
                raw_translated = ask_ai_with_failover(prompt, pool_type="translation", expected_keys=["translations"])
                translated_data = self._clean_and_parse_json(raw_translated)
                
                if translated_data and "error" not in translated_data:
                    translations_map = translated_data.get('translations') or translated_data
                    
                    if isinstance(translations_map, dict):
                        for entry in batch:
                            translated_text = translations_map.get(entry.msgid)
                            if translated_text and len(str(translated_text).strip()) > 0:
                                entry.msgstr = str(translated_text).strip()
                                count += 1
                
                # 🔴 DYNAMIC API PACING: የ 24-ሰዓት የ AI ኮታ መቆለፊያን ለመከላከል በእያንዳንዱ ጥሪ መካከል መኝታ [1]
                time.sleep(1.5)
            
            po.save()
            try:
                po.save_as_mofile(mo_file_path)
                self.stdout.write(self.style.SUCCESS(f"  ✅ {count} {lang_name} translations compiled for {site.name}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ Error saving {lang_name} for {site.name}: {e}"))
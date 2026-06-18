# EthAfri/marketplace/management/commands/sync_translations.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from marketplace.growth_agent import ask_ai_with_failover
import polib
import os
import shutil  # ⚠️ gettext መኖሩን ለመፈተሽ የተጨመረ
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'በዌብሳይቱ ላይ ያሉ አዳዲስ የቋንቋ መለያዎችን (i18n tags) በ AI በራስ-ሰር ይተረጉማል'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🤖 EthAfri I18n Agent: አዳዲስ የቋንቋ መለያዎችን በማስተካከል ላይ..."))
        
        # 1. በሲስተሙ ላይ GNU gettext (xgettext) መኖሩን መፈተሽ
        has_gettext = shutil.which('xgettext') is not None
        
        if has_gettext:
            try:
                # gettext ካለ አዳዲስ ቃላትን በራስ-ሰር ሰብስቦ ያስገባል
                call_command('makemessages', locale=['am', 'om', 'ar', 'so', 'ti', 'fr'], ignore=['.venv/*', 'node_modules/*'])
                self.stdout.write(self.style.SUCCESS("✅ አዳዲስ የቋንቋ መለያዎች በሰላም ተሰብስበዋል።"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"⚠️ makemessages Error: {e}"))
        else:
            # gettext ከሌለ ግንባታው (build) ሳይቋረጥ በደህንነት ያልፋል
            self.stdout.write(self.style.WARNING("⚠️ GNU gettext አልተገኘም። አዳዲስ ቃላትን መሰብሰብ አይቻልም፤ ነገር ግን ያሉትን ፋይሎች በንጹህ ፓይተን እንተረጉማለን።"))

        locales = {'am': 'Amharic', 'om': 'Oromo', 'ar': 'Arabic', 'so': 'Somali', 'ti': 'Tigrinya', 'fr': 'French'}

        # 2. ለእያንዳንዱ ቋንቋ የትርጉም ስራውን መስራት እና ማጠናቀር
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
                # gettext በሌለበት ሰርቨር ላይ .mo ፋይሉ መኖሩን ለማረጋገጥ በንጹህ ፓይተን ማጠናቀር
                po.save_as_mofile(mo_file_path)
                continue

            self.stdout.write(self.style.WARNING(f"🧠 {len(untranslated)} የ {lang_name} ቃላት በ AI በመተርጎም ላይ..."))
            
            count = 0
            for entry in untranslated:
                # ጥብቅ የትርጉም መመሪያ
                prompt = f"[CRITICAL DIRECTIVE] Translate this UI string to {lang_name}. Return ONLY the translation text. No quotes, no markdown: '{entry.msgid}'"
                
                translated_data = ask_ai_with_failover(prompt, pool_type="translation")
                
                # የትርጉም መልሱን በትክክል መለየት እና ኤረር መከላከል
                translated_text = None
                if isinstance(translated_data, dict):
                    if "error" in translated_data:
                        translated_text = None
                    else:
                        translated_text = translated_data.get(lang_code) or list(translated_data.values())[0]
                else:
                    raw_str = str(translated_data).strip()
                    if "failed to return" not in raw_str:
                        translated_text = raw_str

                if translated_text and len(translated_text) > 0:
                    entry.msgstr = translated_text
                    count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Skipping translation for: '{entry.msgid}'"))

            # የ .po ፋይሉን ማስቀመጥ
            po.save()
            
            # 🛡️ 3. የ .po ፋይሉን በንጹህ ፓይተን (ያለ gettext) ማጠናቀር (PO to MO native compile)
            try:
                po.save_as_mofile(mo_file_path)
                self.stdout.write(self.style.SUCCESS(f"✅ {count} የ {lang_name} ቃላት ተተርጎመው በንጹህ ፓይተን ተጠናቅረዋል።"))
            except Exception as compile_err:
                self.stdout.write(self.style.ERROR(f"❌ Python MO Compilation Error: {compile_err}"))

        self.stdout.write(self.style.SUCCESS("🎉 የትርጉም ስራው እና ማጠናቀሪያው ሙሉ በሙሉ ተጠናቋል!"))
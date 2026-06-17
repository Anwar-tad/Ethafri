# EthAfri/marketplace/management/commands/sync_translations.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from marketplace.growth_agent import ask_ai_with_failover # አዲሱ Failover አገናኝ
import polib
import os

class Command(BaseCommand):
    help = 'በዌብሳይቱ ላይ ያሉ አዳዲስ የቋንቋ መለያዎችን (i18n tags) በ AI በራስ-ሰር ይተረጉማል'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🤖 EthAfri I18n Agent: አዳዲስ የቋንቋ መለያዎችን በማስተካከል ላይ..."))
        
        try:
            call_command('makemessages', locale=['am', 'om', 'ar', 'so', 'ti', 'fr'], ignore=['.venv/*', 'node_modules/*'])
            self.stdout.write(self.style.SUCCESS("✅ አዳዲስ የቋንቋ መለያዎች በሰላም ተሰብስበዋል።"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ makemessages Error: {e}"))
            return

        locales = {'am': 'Amharic', 'om': 'Oromo', 'ar': 'Arabic', 'so': 'Somali', 'ti': 'Tigrinya', 'fr': 'French'}

        for lang_code, lang_name in locales.items():
            po_file_path = os.path.join(settings.BASE_DIR, 'locale', lang_code, 'LC_MESSAGES', 'django.po')
            
            if not os.path.exists(po_file_path):
                continue

            po = polib.pofile(po_file_path)
            untranslated = po.untranslated_entries()

            if not untranslated:
                continue

            self.stdout.write(self.style.WARNING(f"🧠 {len(untranslated)} የ {lang_name} ቃላት በ AI በመተርጎም ላይ..."))
            
            count = 0
            for entry in untranslated:
                prompt = f"Translate the following English web UI string into {lang_name}. Return ONLY the translation: '{entry.msgid}'"
                
                # 🚀 የ Failover ኤጀንት ይጠራል
                translated_text = ask_ai_with_failover(prompt, pool_type="translation")
                
                if translated_text:
                    # የጀሚኒ መልስ JSON ከሆነ, የትርጉሙን መስክ ብቻ ያወጣል
                    if isinstance(translated_text, dict):
                        entry.msgstr = translated_text.get(lang_code, str(list(translated_text.values())[0]))
                    else:
                        entry.msgstr = str(translated_text).strip()
                    count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"❌ AI failed to translate '{entry.msgid}'"))
                    break 

            po.save()
            self.stdout.write(self.style.SUCCESS(f"✅ {count} የ {lang_name} ቃላት ተተርጉመዋል።"))

        self.stdout.write("⚙️ የትርጉም ፋይሎችን በማጠናቀር ላይ...")
        call_command('compilemessages')
        self.stdout.write(self.style.SUCCESS("🎉 የትርጉም ስራው ሙሉ በሙሉ ተጠናቋል!"))

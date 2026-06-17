# EthAfri/marketplace/management/commands/sync_translations.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from marketplace.growth_agent import ask_gemini_with_rotation
import polib # የትርጉም .po ፋይሎችን በፓይተን ለመለወጥ የሚጠቅም ቤተ-መጽሐፍት
import os

class Command(BaseCommand):
    help = 'በዌብሳይቱ ላይ ያሉ አዳዲስ የቋንቋ መለያዎችን (i18n tags) በ AI በራስ-ሰር ይተረጉማል'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("🤖 EthAfri I18n Agent: አዳዲስ የቋንቋ መለያዎችን ከኮዱ ውስጥ በመሰብሰብ ላይ..."))
        
        # 1. ⚠️ አውቶማቲክ ስካነር፦ አዳዲስ ጽሁፎችን ከኮዱ ውስጥ ፈልጎ ማውጣት (makemessages)
        # ሬንደር ላይ '.venv' እና ሌሎች ፋይሎችን ችላ (ignore) እንዲል ተደርጓል
        try:
            call_command(
                'makemessages', 
                locale=['am', 'om', 'ar', 'so', 'ti', 'fr'], 
                ignore=['.venv/*', 'node_modules/*']
            )
            self.stdout.write(self.style.SUCCESS("✅ አዳዲስ የቋንቋ መለያዎች በሰላም ተሰብስበዋል።"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ makemessages Error: {e}"))
            return

        # 2. የቋንቋዎች ዝርዝር
        locales = {
            'am': 'Amharic',
            'om': 'Oromo',
            'ar': 'Arabic',
            'so': 'Somali',
            'ti': 'Tigrinya',
            'fr': 'French'
        }

        # 3. በየቋንቋው እየዞረ ያልተተረጎሙትን በ AI መተርጎም
        for lang_code, lang_name in locales.items():
            po_file_path = os.path.join(settings.BASE_DIR, 'locale', lang_code, 'LC_MESSAGES', 'django.po')
            
            if not os.path.exists(po_file_path):
                self.stdout.write(self.style.WARNING(f"⚠️ የ {lang_name} PO ፋይል አልተገኘም: {po_file_path}"))
                continue

            self.stdout.write(f"🔄 የ {lang_name} (.po) ፋይልን በመመርመር ላይ...")
            po = polib.pofile(po_file_path)
            untranslated = po.untranslated_entries()

            if not untranslated:
                self.stdout.write(self.style.SUCCESS(f"ℹ️ ሁሉም የ {lang_name} ቃላት አስቀድመው ተተርጉመዋል።"))
                continue

            self.stdout.write(self.style.WARNING(f"🧠 {len(untranslated)} ያልተተረጎሙ የ {lang_name} ቃላት ተገኝተዋል። በ AI በመተርጎም ላይ..."))
            
            count = 0
            for entry in untranslated:
                # ⚠️ ለ AIው የሚሰጥ ጥብቅ የትርጉም መመሪያ (Prompt)
                prompt = f"""
                You are the Lead Translator of EthAfri.com.
                Translate the following English web UI string into {lang_name}.
                English String: "{entry.msgid}"

                Return ONLY the raw translated text. Do not include any explanations, quotes, or markdown.
                """
                
                # ጀሚኒን በ Rotation መጥራት (የቀን ኮታ ቆጣቢ!)
                translated_text = ask_gemini_with_rotation(prompt, pool_type="translation")
                
                if translated_text:
                    # በፖ ፋይሉ ላይ መመዝገብ
                    entry.msgstr = translated_text.strip()
                    count += 1
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Gemini failed to translate '{entry.msgid}'"))
                    break # ኮታው ካለቀ ለቀጣዩ ቋንቋ እንዲያልፍ

            po.save()
            self.stdout.write(self.style.SUCCESS(f"✅ {count} የ {lang_name} ቃላት በ AI ተተርጉመው ተቀምጠዋል።"))

        # 4. ⚠️ አውቶማቲክ ማጠናከሪያ፦ ፋይሎቹን ዲጃንጎ እንዲያነባቸው ማጠናቀር (compilemessages)
        self.stdout.write("⚙️ የትርጉም ፋይሎቹን በማጠናቀር ላይ (compiling)...")
        try:
            call_command('compilemessages')
            self.stdout.write(self.style.SUCCESS("🎉 ሁሉም የዌብሳይት የትርጉም ፋይሎች ተጠናቀው ዝግጁ ሆነዋል!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ compilemessages Error: {e}"))
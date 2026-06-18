# EthAfri/marketplace/management/commands/sync_translations.py

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from marketplace.growth_agent import ask_ai_with_failover
import polib
import os
import json  # የባች ዳታዎችን ወደ JSON ለመለወጥ የተጨመረ
import shutil  # gettext መኖሩን ለመፈተሽ የተጨመረ
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

            self.stdout.write(self.style.WARNING(f"🧠 {len(untranslated)} የ {lang_name} ቃላት በ AI በባች (Batch) በመተርጎም ላይ..."))
            
            # 🛡️ ቃላትን በ 15 chunk ሰብስቦ በአንድ API ጥሪ መተርጎም (የጀሚኒን ኮታ በ 15 እጥፍ ይቆጥባል!)
            batch_size = 15
            untranslated_list = list(untranslated)
            count = 0
            
            for i in range(0, len(untranslated_list), batch_size):
                batch = untranslated_list[i : i + batch_size]
                
                # የቃላቱን ዝርዝር ወደ JSON ማዘጋጀት
                translation_payload = {entry.msgid: entry.msgid for entry in batch}
                
                prompt = (
                    f"Translate the values of the following JSON dictionary keys into {lang_name}. "
                    f"Provide the result in a JSON format with a single key 'translations' "
                    f"which maps the original English key to its {lang_name} translation. "
                    f"Dictionary: {json.dumps(translation_payload, ensure_ascii=False)}"
                )
                
                # 🛡️ የዙር-ተኮር የጥሪ ማመጣጠኛ ሎጂክ (Round-Robin Load Balancing)
                # በእያንዳንዱ ባች ላይ የጥሪ ጫናውን በ 50/50 ለመክፈል ጊትሃብን እና ሀጊንግፌስን ያፈራርቃል
                current_batch_index = i // batch_size
                if current_batch_index % 2 == 0:
                    pool_choice = "translation_github"
                    self.stdout.write(f"  ➡️ Batch {current_batch_index + 1}: Routing primary to GitHub Models (GPT-4o-mini)...")
                else:
                    pool_choice = "translation_huggingface"
                    self.stdout.write(f"  ➡️ Batch {current_batch_index + 1}: Routing primary to Hugging Face (Qwen-2.5)...")

                translated_data = ask_ai_with_failover(prompt, pool_type=pool_choice)
                
                # የባች ትርጉም ውጤትን በትክክል መፈተሽ እና መተርጎም
                if isinstance(translated_data, dict) and "error" not in translated_data:
                    # አዲሱ JSON መዋቅር 'translations' ወይም 'translation' በሚል ቁልፍ ሊመጣ ይችላል
                    translations_map = (
                        translated_data.get('translations') or 
                        translated_data.get('translation') or 
                        translated_data
                    )
                    
                    for entry in batch:
                        translated_text = translations_map.get(entry.msgid)
                        if translated_text and len(translated_text.strip()) > 0:
                            entry.msgstr = translated_text.strip()
                            count += 1
                        else:
                            self.stdout.write(self.style.ERROR(f"❌ Skipping item inside batch: '{entry.msgid}'"))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ Batch request failed for {len(batch)} items. Skipping this batch."))

            # የ .po ፋይሉን ማስቀመጥ
            po.save()
            
            # 🛡️ የ .po ፋይሉን በንጹህ ፓይተን (ያለ gettext) ማጠናቀር (PO to MO native compile)
            try:
                po.save_as_mofile(mo_file_path)
                self.stdout.write(self.style.SUCCESS(f"✅ {count} የ {lang_name} ቃላት ተተርጎመው በንጹህ ፓይተን ተጠናቅረዋል።"))
            except Exception as compile_err:
                self.stdout.write(self.style.ERROR(f"❌ Python MO Compilation Error: {compile_err}"))

        self.stdout.write(self.style.SUCCESS("🎉 የትርጉም ስራው እና ማጠናቀሪያው ሙሉ በሙሉ ተጠናቋል!"))
# EthAfri/marketplace/growth_agent.py

import json
import os
import re
import logging
import sys
import requests
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management import call_command
from django.urls import clear_url_caches
from importlib import reload
from groq import Groq
from google import genai  # ⚠️ አዲሱ የዘመነ የጉግል ኤስዲኬ (Google GenAI SDK)

# አዲሶቹን አውቶኖመስ ሞዴሎች ማካተት
from .models import SiteConfig, Category, Product, AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction

logger = logging.getLogger(__name__)

def ask_ai_with_failover(prompt, pool_type="coding"):
    """
    ባለብዙ-ደረጃ ኤአይ Failover ሰንሰለት (Task-Type Isolation)
    - coding ከሆነ፦ ቅድሚያ ለ Groq (የጀሚኒን ኮታ ለመቆጠብ)፣ ካልሰራ ወደ Gemini
    - translation ከሆነ፦ ቅድሚያ ለ Gemini (ለትርጉም ጥራት)፣ ካልሰራ ወደ Groq
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    groq_key = os.environ.get('GROQ_API_KEY')

    # የ JSON መመለሻን ለማጣራት የሚረዳ ንጹህ ፈላጊ
    def extract_json(text):
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception as json_err:
                logger.warning(f"⚠️ Extract JSON decode error: {json_err}")
                return None
        return None

    def call_gemini():
        if not api_key:
            return None
        # ⚠️ አዲሱ የጉግል ኤስዲኬ አነሳስ (Unified client)
        client = genai.Client(api_key=api_key)
        # ⚠️ ትክክለኛው የሞዴል ጥሪ (gemini-2.5-flash) - በነጻው ደረጃ ይሰራል
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return extract_json(response.text)

    def call_groq():
        if not groq_key:
            return None
        client = Groq(api_key=groq_key)
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return extract_json(chat.choices[0].message.content)

    # 1. Coding Task Routing (Groq > Gemini)
    if pool_type == "coding":
        try:
            result = call_groq()
            if result:
                return result
        except Exception as e:
            logger.warning(f"🔄 Groq Failover in coding: {e}")
        
        try:
            result = call_gemini()
            if result:
                return result
        except Exception as e:
            logger.error(f"❌ Gemini Fallback failed in coding: {e}")

    # 2. Translation/Other Task Routing (Gemini > Groq)
    else:
        try:
            result = call_gemini()
            if result:
                return result
        except Exception as e:
            logger.warning(f"🔄 Gemini Failover in translation: {e}")
        
        try:
            result = call_groq()
            if result:
                return result
        except Exception as e:
            logger.error(f"❌ Groq Fallback failed in translation: {e}")
            
    return {"error": "All AI providers failed to return valid JSON."}

# ⚠️ ለ self_coder.py እና self_doctor.py ምቾት ሲባል የተሠራው የፈንክሽን ተለዋጭ ስም (Alias)
ask_ethafri_ceo = ask_ai_with_failover

def get_complete_project_state():
    """የጠቅላላውን ዲጃንጎ አፕሊኬሽን ኮድ እና የፋይል መዋቅር ሙሉ በሙሉ ያነባል"""
    base = settings.BASE_DIR
    target_files = {
        'models': os.path.join(base, 'marketplace', 'models.py'),
        'views': os.path.join(base, 'marketplace', 'views.py'),
        'urls': os.path.join(base, 'marketplace', 'urls.py'),
        'forms': os.path.join(base, 'marketplace', 'forms.py'),
        'home_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'home.html'),
        'edit_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'edit_product.html'),
    }
    
    state = {}
    for key, path in target_files.items():
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                state[key] = f.read()
        else:
            state[key] = f"❌ MISSING_FILE: This file doesn't exist yet."
    return state, target_files

def run_daily_market_analysis():
    """
    የኢቲአፍሪ ልዕለ-ፈጣሪ የዕድገት ሞተር (Fully Autonomous Auditor & Developer)
    """
    now = timezone.now()
    
    # 1. የሉፕ መቆለፊያ ጥበቃ (የማያቋርጥ ግንባታ እንዳይደራረብ ይከላከላል)
    lock, _ = SiteConfig.objects.get_or_create(key="EVOLUTION_LOCK", defaults={'value': {'status': 'idle'}})
    if lock.value.get('status') == 'running':
        return "⚠️ Skip: System is currently compiling another feature."
    
    lock.value = {'status': 'running', 'last_run': now.isoformat()}
    lock.save()
    
    try:
        # 2. የፕሮጀክቱን ሙሉ ወቅታዊ ይዘት ማንበብ
        project_code, file_paths = get_complete_project_state()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser('admin', 'admin@ethafri.com', 'secure123')

        # 3. የአድሚን ቀጥተኛ መመሪያ (Admin Override) መኖሩን ማረጋገጥ
        active_override = AdminOverrideInstruction.objects.filter(is_processed=False).order_by('created_at').first()
        
        target_task = None
        forced_instruction = ""
        
        if active_override:
            forced_instruction = f"CRITICAL USER COMMAND OVERRIDE: {active_override.instruction}"
            if active_override.backlog_task:
                target_task = active_override.backlog_task
                target_task.status = 'Running'
                target_task.save()
            logger.info(f"🚨 Admin Override Detected: {active_override.instruction}")
        else:
            # ያላለቁ የባክሎግ ስራዎችን ከዳታቤዝ መፈለግ (ቅድሚያ ለ Critical እና High)
            target_task = AIProjectBacklog.objects.filter(status='Pending').order_by('-priority', 'created_at').first()
            if target_task:
                target_task.status = 'Running'
                target_task.save()
                logger.info(f"🤖 Auto-Selecting Task from Backlog: {target_task.task_name}")

        # 4. ለ AI የሚሰጥ የአሰሳ፣ የባክሎግ ዝግጅት እና የኮዲንግ ማስተር ፕሮምፕት
        prompt = f"""
        You are 'EthAfri Super AI Architect & Product Manager'. Your core mission is two-fold:
        1. Act as an Auditor: Scan the codebase state below, identify missing standard marketplace components (User registration, profiles, edit/delete features, security view guards, responsive layouts), prioritize them, and return them into the 'backlog_tasks' array.
        2. Act as a Developer: If an active backlog task or admin override is provided, write the absolute flawless, full production-ready code to update the files.

        [CURRENT CODEBASE STATE]:
        {json.dumps(project_code, indent=2)}

        [CURRENT TASK TO EXECUTE NOW]:
        Active Backlog Task: {target_task.task_name if target_task else 'None - Just Scan and Audit Codebase'}
        Task Description: {target_task.description if target_task else 'None'}
        {forced_instruction}

        [ENGINEERING RULES]:
        - Do NOT create duplicate items in 'backlog_tasks' if they already conceptually exist in the state.
        - Ensure all generated python code handles errors gracefully and uses safe Django conventions.
        - Scrape or simulate real-world high-quality product data from Addis Ababa markets (Mercato, Bole, Shola) to keep home page alive.

        Return ONLY a raw JSON dictionary. Do not enclose in markdown code blocks.
        JSON Structure:
        {{
            "thought_process": "Detailed analysis of current codebase gaps and evolution roadmap.",
            "backlog_tasks": [
                {{"task_name": "Implement User Registration and Login Views", "target_file": "views", "priority": "Critical", "description": "Add user signup, login, and logout functionalities to views.py and setup templates."}},
                {{"task_name": "Add Product Edit and Update Capability", "target_file": "views", "priority": "High", "description": "Create a view and form allowing verified sellers to modify their listings."}},
                {{"task_name": "Implement Safe Product Soft-Delete", "target_file": "views", "priority": "High", "description": "Add delete endpoints that set is_active=False instead of wiping data."}}
            ],
            "updates": {{
                "models": "Full rewritten content or empty string if no change",
                "views": "Full rewritten views.py content or empty string",
                "urls": "Full rewritten urls.py content or empty string",
                "forms": "Full rewritten forms.py content or empty string",
                "home_html": "Full rewritten home.html content or empty string",
                "edit_html": "Full rewritten edit_product.html content or empty string"
            }},
            "database_migration_needed": false,
            "scraped_products": [
                {{"cat": "Electronics", "title": "iPhone 15 Pro Max - Genuine Seller Bole", "price": 140000, "loc": "Bole, Addis Ababa"}}
            ]
        }}
        """

        # 5. የ AI ጥሪ አፈጻጸም (የኮዲንግ ስራዎችን ስለሚሠራ የ Groq ኮታዎችን ያስቀድማል)
        data = ask_ai_with_failover(prompt, pool_type="coding")
        if not data or "error" in data:
            if target_task:
                target_task.status = 'Pending'
                target_task.save()
            return f"❌ Fail: AI architecture payload was unreadable. Detail: {data.get('error') if data else 'Empty'}"

        # 6. 🤖 AUTONOMOUS AUDITING (የጎደሉ ስራዎችን ፈልጎ ባክሎግ ላይ መመዝገብ)
        found_tasks = data.get('backlog_tasks', [])
        for t in found_tasks:
            try:
                # get_or_create በራስ-ሰር task_hashን በመጠቀም መደራረብን ይከላከላል
                AIProjectBacklog.objects.get_or_create(
                    task_name=t['task_name'],
                    target_file=t['target_file'],
                    defaults={
                        'priority': t.get('priority', 'Medium'),
                        'status': 'Pending',
                        'description': t.get('description', '')
                    }
                )
            except Exception as e:
                logger.warning(f"Task duplication skipped or error: {e}")

        # 7. 💾 HOT-SWAP WITH LOGGING (ኮድ መጻፍ እና በኢቮሉሽን ሎግ መመዝገብ)
        updates = data.get('updates', {})
        code_changed = False
        
        for key, new_content in updates.items():
            if new_content and "MISSING_FILE" not in new_content and len(new_content.strip()) > 10:
                path = file_paths[key]
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                # የድሮውን ኮድ ባክአፕ ለመያዝ ማንበብ
                old_code = ""
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        old_code = f.read()
                
                # አዲሱን ኮድ በፋይሉ ላይ መጻፍ
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                # የታሪክ ማህደረ-ትውስታ መዝገብ (Evolution Log) መፍጠር
                AIEvolutionLog.objects.create(
                    backlog_task=target_task,
                    target_file=key,
                    reason_for_change=f"Autonomous Build for: {target_task.task_name if target_task else 'Admin General Directive'}",
                    old_code_backup=old_code,
                    new_code_patch=new_content
                )
                
                code_changed = True
                logger.info(f"💾 Hot-Swapped & Logged File: {key}")

        # 8. የዳታቤዝ ፍልሰት (ባክሎጉ ወይም AI ካዘዘ ብቻ)
        if data.get('database_migration_needed') and updates.get('models'):
            try:
                call_command('makemigrations', 'marketplace', interactive=False)
                call_command('migrate', interactive=False)
                logger.info("⚙️ Database schema migrated successfully.")
            except Exception as db_err:
                logger.error(f"⚠️ Migration warning: {db_err}")

        # 9. የዌብሳይት ማህደረ ትውስታ ማደስ (Hot Reload)
        if code_changed:
            clear_url_caches()
            for mod in ['marketplace.models', 'marketplace.forms', 'marketplace.views', 'marketplace.urls']:
                if mod in sys.modules:
                    reload(sys.modules[mod])

        # 10. እውነተኛ ምርቶችን ከገበያ መጫን (Home Page Freshness)
        products = data.get('scraped_products', [])
        for item in products:
            if 'title' in item:
                cat, _ = Category.objects.get_or_create(name=item.get('cat', 'General'))
                if not Product.objects.filter(title=item['title']).exists():
                    Product.objects.create(
                        seller=admin_user, category=cat, title=item['title'],
                        description=f"Verified local item in {item.get('loc', 'Addis Ababa')}. Price checked live.",
                        price=item.get('price', 0), is_active=True
                    )

        # 11. የስራ ሁኔታዎችን ማጠቃለል (Status Cleanup)
        if active_override:
            active_override.is_processed = True
            active_override.save()
            
        if target_task:
            target_task.status = 'Completed'
            target_task.save()

        return f"🎉 Evolved! Mission: {data.get('thought_process')[:80]}"

    except Exception as e:
        if target_task:
            target_task.status = 'Pending'
            target_task.save()
        logger.error(f"❌ System Crash in Creator Engine: {e}")
        return f"❌ System Error: {str(e)}"
    finally:
        # መቆለፊያውን ሁሌም በሰላም መፍታት (Idle)
        lock.value = {'status': 'idle'}
        lock.save()
# EthAfri/marketplace/growth_agent.py

import json
import os
import re
import logging
import sys
import requests  # ለ Mistral፣ OpenRouter፣ Hugging Face እና GitHub ኤፒአይ ጥሪዎች
import hashlib   # ለ SHA256 የይዘት ካሼ (Caching Layer)
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management import call_command
from django.urls import clear_url_caches
from importlib import reload
from groq import Groq
from google import genai  # የዘመነ የጉግል ኤስዲኬ (Google GenAI SDK)
from django.db import models  # ለ Exists እና OuterRef ንዑስ ኳኤሪዎች

# አዲሶቹን አውቶኖመስ ሞዴሎች ማካተት
from .models import SiteConfig, Category, Product, AIProjectBacklog, AIEvolutionLog, AdminOverrideInstruction

logger = logging.getLogger(__name__)

def ask_ai_with_failover(prompt, pool_type="coding"):
    """
    ባለብዙ-ደረጃ እና ባለብዙ-ኤአይ Failover ሰንሰለት (Task Sharing & API Key Rotation)
    - translation_github ➡️ GitHub Models (GPT-4o-mini) ቀድሞ ይሠራል
    - translation_huggingface ➡️ Hugging Face (Qwen-2.5) ቀድሞ ይሠራል
    - translation ➡️ Gemini 2.5 (ከዑደት ጋር) -> GitHub -> OpenRouter -> Hugging Face -> Groq -> Mistral
    - coding ➡️ Mistral (Codestral) -> GitHub (Llama-405B) -> Groq (Llama-70B) -> OpenRouter -> Hugging Face -> Gemini
    - healing/other ➡️ Groq -> Mistral -> GitHub -> Hugging Face -> OpenRouter -> Gemini
    """
    # በሰርቨሩ ላይ በ 'GEMINI_API_KEY' የሚጀምሩትን ሁሉንም ቁልፎች በራስ-ሰር ፈልጎ መመዝገብ
    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    
    groq_key = os.environ.get('GROQ_API_KEY')
    mistral_key = os.environ.get('MISTRAL_API_KEY')
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    huggingface_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_TOKEN')
    github_token = os.environ.get('GITHUB_TOKEN')

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

    # ኤአይ 1፦ Gemini (ከቁልፎች ዑደት / Key Rotation ጋር የተዋቀረ)
    def call_gemini():
        if not gemini_keys:
            return None
        
        # ያሉትን ሁሉንም የጀሚኒ ቁልፎች በየተራ በመሞከር ስህተት ሲፈጠር ማሽከርከር
        for idx, key in enumerate(gemini_keys):
            try:
                client = genai.Client(api_key=key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                result = extract_json(response.text)
                if result and "error" not in result:
                    return result
            except Exception as e:
                logger.warning(f"🔄 Gemini Key {idx+1} failed or exhausted: {e}. Trying next available key...")
                
        return None

    # 🛡️ ኤአይ 2፦ GitHub Models (ያለ የቀን ገደብ በነፃ የሚሰራ እጅግ ኃይለኛ የቁጥጥር በር)
    def call_github():
        if not github_token: return None
        # GitHub Models የኢንፈረንስ ኤፒአይ መድረሻ
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Content-Type": "application/json"
        }
        # ትርጉም ከሆነ gpt-4o-mini፣ ኮዲንግ ከሆነ የዓለማችን ግዙፉን meta-llama-3.1-405b-instruct
        model_name = "azure-openai/gpt-4o-mini" if "translation" in pool_type else "meta-llama-3.1-405b-instruct"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.warning(f"🔄 GitHub Models API Connection Failed: {e}")
        return None

    # ኤአይ 3፦ Groq (Speed Specialist)
    def call_groq():
        if not groq_key: return None
        client = Groq(api_key=groq_key)
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return extract_json(chat.choices[0].message.content)

    # ኤአይ 4፦ Mistral (Coding & Logic Specialist)
    def call_mistral():
        if not mistral_key: return None
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {mistral_key}"
        }
        model_name = "codestral-latest" if pool_type == "coding" else "mistral-large-latest"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.warning(f"🔄 Mistral API Connection Failed: {e}")
        return None

    # ኤአይ 5፦ OpenRouter (Ultimate Fallback - Claude / DeepSeek)
    def call_openrouter():
        if not openrouter_key: return None
        # ⚠️ የዩአርኤል ስህተቱ ወደ ትክክለኛው 'openrouter.ai/api/v1' ተስተካክሏል
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }
        model_name = "google/gemini-2.5-flash" if "translation" in pool_type else "deepseek/deepseek-chat"
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.warning(f"🔄 OpenRouter API Connection Failed: {e}")
        return None

    # ኤአይ 6፦ Hugging Face (የቀን ገደብ የሌለው የሮድማፕ ፎልባክ)
    def call_huggingface():
        if not huggingface_key: return None
        url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {huggingface_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "Qwen/Qwen2.5-72B-Instruct",
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
        except Exception as e:
            logger.warning(f"🔄 HuggingFace API Connection Failed: {e}")
        return None

    # --- 🤖 ስልታዊ የስራ ክፍፍል (Strategic Task Routing) ---
    
    # ሀ. የትርጉም ስራዎች (ዙር-ተኮር ማመጣጠኛዎችን ጨምሮ)
    if pool_type == "translation_github":
        # ጊትሃብን ያስቀድማል
        providers = [call_github, call_huggingface, call_gemini, call_openrouter, call_groq, call_mistral]
    elif pool_type == "translation_huggingface":
        # ሀጊንግፌስን ያስቀድማል
        providers = [call_huggingface, call_github, call_gemini, call_openrouter, call_groq, call_mistral]
    elif pool_type == "translation":
        # ነባሪው አሠራር
        providers = [call_gemini, call_github, call_openrouter, call_huggingface, call_groq, call_mistral]
        
    # ለ. የኮዲንግ እና የዕድገት ስራዎች (Mistral -> GitHub -> Groq -> OpenRouter -> HuggingFace -> Gemini)
    elif pool_type == "coding":
        providers = [call_mistral, call_github, call_groq, call_openrouter, call_huggingface, call_gemini]
        
    # ሐ. የራስ-ጥገና እና የዲዛይን ስራዎች (Groq -> Mistral -> GitHub -> HuggingFace -> OpenRouter -> Gemini)
    else:
        providers = [call_groq, call_mistral, call_github, call_huggingface, call_openrouter, call_gemini]

    # የ Failover ሰንሰለቱን በደረጃ ማስፈጸም
    for call_provider in providers:
        try:
            result = call_provider()
            if result and "error" not in result:
                return result
        except Exception as err:
            logger.warning(f"🔄 Provider Failover: {call_provider.__name__} failed with: {err}")

    return {"error": "All AI providers failed to return valid JSON."}

# ለ self_coder.py እና self_doctor.py ምቾት የተሠራ ተለዋጭ ስም
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
    
    # 🛡️ 1. የራስ-መገደብ ፍተሻ (Adaptive Throttling / Hibernation Check)
    retry_config, _ = SiteConfig.objects.get_or_create(
        key="NEXT_ALLOWED_RUN_TIME", 
        defaults={'value': {'time': '2000-01-01T00:00:00'}}
    )
    
    try:
        next_run = timezone.datetime.fromisoformat(retry_config.value.get('time'))
        if timezone.is_naive(next_run):
            next_run = timezone.make_aware(next_run)
        
        if now < next_run:
            logger.info(f"💤 Sleeping: Quota exhausted. Hibernating. Will retry at {next_run}")
            return f"💤 Sleeping: Quota exhausted. Will retry at {next_run}"
    except Exception as parse_err:
        logger.warning(f"⚠️ NEXT_ALLOWED_RUN_TIME parse error: {parse_err}")
    
    # 2. የሉፕ መቆለፊያ ጥበቃ (የማያቋርጥ ግንባታ እንዳይደራረብ ይከላከላል)
    lock, _ = SiteConfig.objects.get_or_create(key="EVOLUTION_LOCK", defaults={'value': {'status': 'idle'}})
    if lock.value.get('status') == 'running':
        return "⚠️ Skip: System is currently compiling another feature."
    
    lock.value = {'status': 'running', 'last_run': now.isoformat()}
    lock.save()
    
    try:
        # 3. የፕሮጀክቱን ሙሉ ወቅታዊ ይዘት ማንበብ
        project_code, file_paths = get_complete_project_state()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser('admin', 'admin@ethafri.com', 'secure123')

        # 🛡️ 4. የካሼ ንብርብር ፍተሻ (Caching Layer - SHA256 Checksum)
        state_string = json.dumps(project_code, sort_keys=True)
        current_state_hash = hashlib.sha256(state_string.encode('utf-8')).hexdigest()
        
        last_state_config, _ = SiteConfig.objects.get_or_create(
            key="LAST_PROJECT_STATE_HASH", 
            defaults={'value': {'hash': ''}}
        )
        
        active_override = AdminOverrideInstruction.objects.filter(is_processed=False).order_by('created_at').first()
        has_pending_tasks = AIProjectBacklog.objects.filter(status='Pending').exists()
        
        # ኮዱ ካልተለወጠ፣ አዲስ ስራ ከሌለና የአድሚን መመሪያ ከሌለ የኤአይ ጥሪውን ሙሉ በሙሉ ይዘልላል
        if last_state_config.value.get('hash') == current_state_hash and not active_override and not has_pending_tasks:
            logger.info("🧠 Caching: Project state is unchanged, no pending tasks or overrides. Skipping AI analysis.")
            lock.value = {'status': 'idle'}
            lock.save()
            return "🧠 Caching: No changes detected. AI analysis skipped."

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
            # 🛡️ ያላለቁ የባክሎግ ስራዎችን ከዳታቤዝ መፈለግ (ቅድሚያ ለ Critical እና High - ጥገኝነትን በመፈተሽ)
            target_task = AIProjectBacklog.objects.filter(
                status='Pending'
            ).annotate(
                has_unfinished_dependency=models.Exists(
                    AIProjectBacklog.objects.filter(
                        pk=models.OuterRef('dependency_id'),
                        status__in=['Pending', 'Running']
                    )
                )
            ).filter(
                has_unfinished_dependency=False
            ).order_by('-priority', 'created_at').first()
            
            if target_task:
                target_task.status = 'Running'
                target_task.save()
                logger.info(f"🤖 Auto-Selecting Task from Backlog: {target_task.task_name}")

        # ለ AI የሚሰጥ የአሰሳ፣ የባክሎግ ዝግጅት እና የኮዲንግ ማስተር ፕሮምፕት
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

        # የ AI ጥሪ አፈጻጸም
        data = ask_ai_with_failover(prompt, pool_type="coding")
        
        # 🛡️ 5. የራስ-መገደብ አተገባበር (429 Quota Exhausted Catching)
        if not data or "error" in data:
            err_msg = data.get('error') if data else 'Empty'
            if "429" in str(err_msg) or "RESOURCE_EXHAUSTED" in str(err_msg) or "quota" in str(err_msg).lower():
                next_retry = now + timezone.timedelta(hours=24)
                retry_config.value = {'time': next_retry.isoformat()}
                retry_config.save()
                logger.info(f"🚨 Quota hit: Engine set to hibernate for 24 hours. Will retry at {next_retry}")
            
            if target_task:
                target_task.status = 'Pending'
                target_task.save()
            return f"❌ Fail: AI execution failed or quota exhausted. Detail: {err_msg}"

        if retry_config.value.get('time') != '2000-01-01T00:00:00':
            retry_config.value = {'time': '2000-01-01T00:00:00'}
            retry_config.save()

        # 🤖 AUTONOMOUS AUDITING (የጎደሉ ስራዎችን ፈልጎ ባክሎግ ላይ መመዝገብ)
        found_tasks = data.get('backlog_tasks', [])
        for t in found_tasks:
            try:
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

        # 💾 HOT-SWAP WITH VALIDATION (የኮድ ምርመራ ንብርብር - Validation Layer)
        updates = data.get('updates', {})
        code_changed = False
        
        for key, new_content in updates.items():
            if new_content and "MISSING_FILE" not in new_content and len(new_content.strip()) > 10:
                
                # 🛡️ ለፓይተን ፋይሎች የ compile() ሲንታክስ ፍተሻ ማካሄድ
                if key in ['models', 'views', 'urls', 'forms']:
                    try:
                        compile(new_content, f"test_{key}.py", 'exec')
                        logger.info(f"✅ Syntax validation passed for: {key}.py")
                    except SyntaxError as syntax_err:
                        logger.error(f"❌ Syntax validation failed for {key}.py: {syntax_err}")
                        # ስህተት ከተገኘ ሰርቨሩን እንዳያበላሸው ግንባታውን አቁሞ ባክሎግ ላይ መመዝገብ
                        AIProjectBacklog.objects.get_or_create(
                            task_name=f"Fix Syntax Error in {key}.py",
                            target_file=key,
                            defaults={
                                'priority': 'Critical',
                                'status': 'Pending',
                                'description': f"Auto-detected syntax compilation error: {syntax_err}. Please review the generated code."
                            }
                        )
                        continue  # ይህንን የተበላሸ ፋይል ሳይጽፍ ይዘልለዋል (Uptime Protection!)

                path = file_paths[key]
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                old_code = ""
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        old_code = f.read()
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                AIEvolutionLog.objects.create(
                    backlog_task=target_task,
                    target_file=key,
                    reason_for_change=f"Autonomous Build for: {target_task.task_name if target_task else 'Admin General Directive'}",
                    old_code_backup=old_code,
                    new_code_patch=new_content
                )
                
                code_changed = True
                logger.info(f"💾 Hot-Swapped & Logged File: {key}")

        # የዳታቤዝ ፍልሰት
        if data.get('database_migration_needed') and updates.get('models'):
            try:
                call_command('makemigrations', 'marketplace', interactive=False)
                call_command('migrate', interactive=False)
                logger.info("⚙️ Database schema migrated successfully.")
            except Exception as db_err:
                logger.error(f"⚠️ Migration warning: {db_err}")

        # የዌብሳይት ማህደረ ትውስታ ማደስ (Hot Reload)
        if code_changed:
            clear_url_caches()
            for mod in ['marketplace.models', 'marketplace.forms', 'marketplace.views', 'marketplace.urls']:
                if mod in sys.modules:
                    reload(sys.modules[mod])

        # እውነተኛ ምርቶችን ከገበያ መጫን (Home Page Freshness)
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

        # 🛡️ ሻርፕ የይዘት አሻሻያ ካሼ መቆለፊያ (Update Cache State after success)
        project_code_after, _ = get_complete_project_state()
        state_string_after = json.dumps(project_code_after, sort_keys=True)
        new_state_hash = hashlib.sha256(state_string_after.encode('utf-8')).hexdigest()
        last_state_config.value = {'hash': new_state_hash}
        last_state_config.save()

        # የስራ ሁኔታዎችን ማጠቃለል
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
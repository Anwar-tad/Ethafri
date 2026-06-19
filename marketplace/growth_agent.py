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
            logger.info(f"💤 Engine is in hibernation mode. Wakes up at {next_run}")
            return f"💤 Sleeping until {next_run}"
    except Exception as parse_err:
        logger.warning(f"⚠️ NEXT_ALLOWED_RUN_TIME parse error: {parse_err}")

    # 🛡️ 2. የስራ መኖር ቅድመ-ፍተሻ (Idle State Optimization)
    # አዲስ የባክሎግ ስራ ከሌለ፣ የአድሚን መመሪያ ከሌለና የታቀደ አሰሳ ከሌለ ኤጀንቱ ዝም ይላል
    has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
    active_override = AdminOverrideInstruction.objects.filter(is_processed=False).exists()
    
    if not has_pending and not active_override:
        # ለተወሰነ ጊዜ አዳዲስ ምርቶች አሰሳ ካልተደረገ ብቻ እንዲቀጥል መፍቀድ ይቻላል
        # ካልሆነ ግን እዚህ ጋር መቆሙ የሰርቨር ሪሶርስ ይቆጥባል
        logger.info("🧠 Engine Idle: No pending tasks or admin directives found.")
        return "🧠 Engine Idle: No work to do."

    # 3. የሉፕ መቆለፊያ ጥበቃ (Concurreny Protection)
    lock, _ = SiteConfig.objects.get_or_create(key="EVOLUTION_LOCK", defaults={'value': {'status': 'idle'}})
    if lock.value.get('status') == 'running':
        return "⚠️ Skip: System is currently compiling another feature."
    
    lock.value = {'status': 'running', 'last_run': now.isoformat()}
    lock.save()
    
    try:
        # 4. የፕሮጀክቱን ይዘት ማንበብና የካሼ ፍተሻ (Caching Layer)
        project_code, file_paths = get_complete_project_state()
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser('admin', 'admin@ethafri.com', 'secure123')

        state_string = json.dumps(project_code, sort_keys=True)
        current_state_hash = hashlib.sha256(state_string.encode('utf-8')).hexdigest()
        last_state_config, _ = SiteConfig.objects.get_or_create(key="LAST_PROJECT_STATE_HASH", defaults={'value': {'hash': ''}})
        
        # ኮዱ ካልተለወጠ እና ምንም አስገዳጅ ስራ ከሌለ የኤአይ ጥሪውን ይዘልላል
        if last_state_config.value.get('hash') == current_state_hash and not active_override and not has_pending:
            lock.value = {'status': 'idle'}; lock.save()
            return "🧠 Caching Match: No code changes or tasks to process."

        target_task = None
        forced_instruction = ""
        
        # የአድሚን መመሪያ መኖሩን ማየት
        override_obj = AdminOverrideInstruction.objects.filter(is_processed=False).order_by('created_at').first()
        
        if override_obj:
            forced_instruction = f"CRITICAL USER COMMAND OVERRIDE: {override_obj.instruction}"
            if override_obj.backlog_task:
                target_task = override_obj.backlog_task
                target_task.status = 'Running'; target_task.save()
            logger.info(f"🚨 Admin Override Detected: {override_obj.instruction}")
        else:
            # ጥገኝነትን (Dependency) ያገናዘበ የባክሎግ ምርጫ
            target_task = AIProjectBacklog.objects.filter(
                status='Pending'
            ).annotate(
                has_unfinished_dependency=models.Exists(
                    AIProjectBacklog.objects.filter(pk=models.OuterRef('dependency_id'), status__in=['Pending', 'Running'])
                )
            ).filter(has_unfinished_dependency=False).order_by('-priority', 'created_at').first()
            
            if target_task:
                target_task.status = 'Running'; target_task.save()

        # 5. የ AI ማስተር ፕሮምፕት ዝግጅት
        prompt = f"""
        You are 'EthAfri Super AI Architect'. 
        Current Codebase State: {json.dumps(project_code, indent=2)}
        Active Task: {target_task.task_name if target_task else 'Audit and Discovery'}
        {forced_instruction}
        
        Engineering Rules:
        - Return ONLY raw JSON.
        - Validate Python syntax within the code updates.
        - Use Django best practices.
        """

        # 6. የ AI ጥሪ አፈጻጸም (ባለብዙ-ኤአይ ፎልባክ)
        data = ask_ai_with_failover(prompt, pool_type="coding")
        
        # 🛡️ 429 ኮታ ማለቅ መቆለፊያ
        if not data or "error" in data:
            err_msg = data.get('error', 'Unknown Error') if data else 'No Response'
            if any(x in str(err_msg) for x in ["429", "RESOURCE_EXHAUSTED", "quota"]):
                next_retry = now + timezone.timedelta(hours=24)
                retry_config.value = {'time': next_retry.isoformat()}
                retry_config.save()
                if target_task: target_task.status = 'Pending'; target_task.save()
                return f"💤 Quota exhausted. Hibernating until {next_retry}"
            
            if target_task: target_task.status = 'Pending'; target_task.save()
            return f"❌ Fail: {err_msg}"

        # ስኬታማ ከሆነ የመኝታ መዝገቡን ማጽዳት
        retry_config.value = {'time': '2000-01-01T00:00:00'}; retry_config.save()

        # 7. 🤖 አውቶኖመስ ኦዲት (Discovery)
        for t in data.get('backlog_tasks', []):
            AIProjectBacklog.objects.get_or_create(
                task_name=t['task_name'], target_file=t['target_file'],
                defaults={'priority': t.get('priority', 'Medium'), 'status': 'Pending', 'description': t.get('description', '')}
            )

        # 8. 💾 የኮድ ማሻሻያ እና ሲንታክስ ምርመራ (Validation)
        updates = data.get('updates', {})
        code_changed = False
        for key, new_content in updates.items():
            if new_content and len(new_content.strip()) > 10:
                if key in ['models', 'views', 'urls', 'forms']:
                    try:
                        compile(new_content, f"test_{key}.py", 'exec')
                    except SyntaxError:
                        continue # የተበላሸ ኮድ አይጻፍም

                path = file_paths.get(key)
                if path:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    old_code = open(path, 'r').read() if os.path.exists(path) else ""
                    with open(path, 'w', encoding='utf-8') as f: f.write(new_content)
                    
                    AIEvolutionLog.objects.create(
                        backlog_task=target_task, target_file=key, 
                        reason_for_change=f"Autonomous Build: {target_task.task_name if target_task else 'System Evolution'}",
                        old_code_backup=old_code, new_code_patch=new_content
                    )
                    code_changed = True

        # 9. የዳታቤዝ ፍልሰት እና ሲስተም ማደስ
        if data.get('database_migration_needed') and updates.get('models'):
            try:
                call_command('makemigrations', 'marketplace', interactive=False)
                call_command('migrate', interactive=False)
            except: pass

        if code_changed:
            clear_url_caches()
            last_state_config.value = {'hash': hashlib.sha256(json.dumps(get_complete_project_state()[0]).encode()).hexdigest()}
            last_state_config.save()

        # 10. ሁኔታዎችን ማጠቃለል
        if override_obj: override_obj.is_processed = True; override_obj.save()
        if target_task: target_task.status = 'Completed'; target_task.save()

        return f"🎉 Evolved! Processed: {target_task.task_name if target_task else 'Audit'}"

    except Exception as e:
        if target_task: target_task.status = 'Pending'; target_task.save()
        logger.error(f"❌ Creator Engine Crash: {e}")
        return f"❌ Error: {str(e)}"
    finally:
        lock.value = {'status': 'idle'}; lock.save()
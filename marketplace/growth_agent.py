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
    ተሻሻለ የኤአይ ፎልባክ ሞተር፡ ቁልፎችን የመለየት፣ የመመዝገብ እና ዙር-ተኮር (Round-Robin) 
    የጥሪ ማመጣጠኛ አቅም ያለው።
    """
    # 🚨 አንተ የጨመርከው የቁልፎች መኖር (Debugging) ፍተሻ
    keys_to_check = ['GEMINI_API_KEY', 'GROQ_API_KEY', 'GITHUB_TOKEN', 'HUGGINGFACE_API_KEY', 'HF_TOKEN', 'MISTRAL_API_KEY', 'OPENROUTER_API_KEY']
    for k in keys_to_check:
        val = os.environ.get(k)
        logger.info(f"🔑 DEBUG: Key {k} exists: {bool(val)}")

    # 1. ቁልፎችን ከሰርቨር (Render Environment) ማውጣት
    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    mistral_key = os.environ.get('MISTRAL_API_KEY')
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    huggingface_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_TOKEN')
    github_token = os.environ.get('GITHUB_TOKEN')

    # 🚨 የጎደሉ ቁልፎች ካሉ አጠቃላይ ማሳወቂያ ሎግ
    missing = [k for k, v in {
        "Gemini": gemini_keys, "Groq": groq_key, "Mistral": mistral_key, 
        "GitHub": github_token, "HuggingFace": huggingface_key
    }.items() if not v]
    if missing:
        logger.warning(f"⚠️ Missing API Keys: {missing}. Check Render Environment Variables!")

    # የ JSON ማውጫ ረዳት
    def extract_json(text):
        if not text: return None
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            return json.loads(match.group(0)) if match else None
        except Exception: return None

    # --- 🤖 የኤአይ አቅራቢዎች (Providers) ---

    def call_gemini():
        if not gemini_keys: return None
        for idx, key in enumerate(gemini_keys):
            try:
                client = genai.Client(api_key=key)
                res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                data = extract_json(res.text)
                if data and "error" not in data: return data
            except Exception as e:
                logger.warning(f"🔄 Gemini Key {idx+1} exhausted: {e}")
        return None

    def call_github():
        if not github_token: return None
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"}
        # ለትክክለኛ ስራ ክፍፍል ሞዴሎችን መምረጥ
        model = "azure-openai/gpt-4o-mini" if "translation" in pool_type else "meta-llama-3.1-405b-instruct"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=20)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception as e:
            logger.error(f"GitHub Error: {e}"); return None

    def call_groq():
        if not groq_key: return None
        try:
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            return extract_json(chat.choices[0].message.content)
        except Exception: return None

    def call_mistral():
        if not mistral_key: return None
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
        model = "codestral-latest" if pool_type == "coding" else "mistral-large-latest"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=20)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception: return None

    def call_huggingface():
        if not huggingface_key: return None
        url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1/chat/completions"
        headers = {"Authorization": f"Bearer {huggingface_key}", "Content-Type": "application/json"}
        try:
            res = requests.post(url, headers=headers, json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": [{"role": "user", "content": prompt}]}, timeout=25)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception: return None

    def call_openrouter():
        if not openrouter_key: return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        model = "google/gemini-2.5-flash" if "translation" in pool_type else "deepseek/deepseek-chat"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=25)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception: return None

    # --- 🎯 ስልታዊ የጥሪ ቅደም ተከተል (Strategic Order) ---
    providers = []
    
    if pool_type == "translation_github":
        providers = [call_github, call_gemini, call_huggingface, call_openrouter]
    elif pool_type == "translation_huggingface":
        providers = [call_huggingface, call_github, call_gemini, call_openrouter]
    elif pool_type == "translation":
        providers = [call_gemini, call_github, call_huggingface, call_openrouter, call_groq]
    elif pool_type == "coding":
        providers = [call_mistral, call_github, call_groq, call_openrouter, call_huggingface]
    else:
        providers = [call_groq, call_mistral, call_github, call_huggingface, call_openrouter]

    # የማስፈጸሚያ ሉፕ
    for provider in providers:
        try:
            result = provider()
            if result and "error" not in result: 
                return result
        except Exception as e:
            logger.warning(f"Provider {provider.__name__} failed: {e}")

    return {"error": "All AI providers failed or keys are missing."}

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
    
    # 🛡️ 1. የራስ-መገደብ ፍተሻ (Adaptive Throttling / Hibernation Check) - ሳይለወጥ
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

    # 🛡️ 2. የስራ መኖር ቅድመ-ፍተሻ (Idle State Optimization) — ✅ FIXED
    # ከዚህ በፊት: ባክሎጉ ካለቀ ኤጀንቱ ለዘላለም ይቆልፍ ነበር (ምንም አዲስ discovery አይደርግም ነበር)
    # አሁን: በየተወሰነ ጊዜ (AUDIT_INTERVAL) ኤጀንቱ አስገድዶ የ discovery audit ያደርጋል
    has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
    active_override = AdminOverrideInstruction.objects.filter(is_processed=False).exists()

    audit_config, _ = SiteConfig.objects.get_or_create(
        key="LAST_AUDIT_TIME",
        defaults={'value': {'time': '2000-01-01T00:00:00'}}
    )
    try:
        last_audit = timezone.datetime.fromisoformat(audit_config.value.get('time'))
        if timezone.is_naive(last_audit):
            last_audit = timezone.make_aware(last_audit)
    except Exception:
        last_audit = timezone.make_aware(timezone.datetime(2000, 1, 1))

    AUDIT_INTERVAL = timezone.timedelta(hours=6)  # ⚙️ ፍጥነቱን እዚህ ማስተካከል ይቻላል
    audit_due = (now - last_audit) >= AUDIT_INTERVAL

    if not has_pending and not active_override and not audit_due:
        logger.info(f"🧠 Engine Idle. Next forced audit in {AUDIT_INTERVAL - (now - last_audit)}")
        return "🧠 Engine Idle: No work to do, next audit not due yet."

    # 🛡️ 3. የሉፕ መቆለፊያ ጥበቃ (Concurrency Protection) — ✅ FIXED (Stale Lock Detection)
    lock, _ = SiteConfig.objects.get_or_create(key="EVOLUTION_LOCK", defaults={'value': {'status': 'idle'}})
    if lock.value.get('status') == 'running':
        stale = True
        last_run_str = lock.value.get('last_run')
        if last_run_str:
            try:
                last_run_dt = timezone.datetime.fromisoformat(last_run_str)
                if timezone.is_naive(last_run_dt):
                    last_run_dt = timezone.make_aware(last_run_dt)
                stale = (now - last_run_dt) > timezone.timedelta(minutes=15)
            except Exception:
                stale = True
        
        if not stale:
            return "⚠️ Skip: System is currently compiling another feature."
        logger.warning("🛡️ Stale EVOLUTION_LOCK detected (>15min) — auto-overriding to prevent permanent deadlock.")

    lock.value = {'status': 'running', 'last_run': now.isoformat()}
    lock.save()
    
    try:
        # ✅ FIXED: audit time እዚህ መመዝገብ - አሁን audit እየተደረገ ስለሆነ
        audit_config.value = {'time': now.isoformat()}
        audit_config.save()

        # 4. የፕሮጀክቱን ይዘት ማንበብና የካሼ ፍተሻ (Caching Layer)
        project_code, file_paths = get_complete_project_state()
        
        # ✅ FIXED: ደካማ hardcoded password እና ጥቅም ላይ ያልዋለ unused variable ተወግዷል
        # (ምንም ኮድ ቦታ admin_user ላይ ጥገኛ አይደለም - ስለዚህ ሙሉ በሙሉ ተወግዷል)

        state_string = json.dumps(project_code, sort_keys=True)
        current_state_hash = hashlib.sha256(state_string.encode('utf-8')).hexdigest()
        last_state_config, _ = SiteConfig.objects.get_or_create(key="LAST_PROJECT_STATE_HASH", defaults={'value': {'hash': ''}})
        
        if last_state_config.value.get('hash') == current_state_hash and not active_override and not has_pending:
            lock.value = {'status': 'idle'}; lock.save()
            return "🧠 Caching Match: No code changes or tasks to process."

        target_task = None
        forced_instruction = ""
        
        override_obj = AdminOverrideInstruction.objects.filter(is_processed=False).order_by('created_at').first()
        
        if override_obj:
            forced_instruction = f"CRITICAL USER COMMAND OVERRIDE: {override_obj.instruction}"
            if override_obj.backlog_task:
                target_task = override_obj.backlog_task
                target_task.status = 'Running'; target_task.save()
            logger.info(f"🚨 Admin Override Detected: {override_obj.instruction}")
        else:
            target_task = AIProjectBacklog.objects.filter(
                status='Pending'
            ).annotate(
                has_unfinished_dependency=models.Exists(
                    AIProjectBacklog.objects.filter(pk=models.OuterRef('dependency_id'), status__in=['Pending', 'Running'])
                )
            ).filter(has_unfinished_dependency=False).order_by('-priority', 'created_at').first()
            
            if target_task:
                target_task.status = 'Running'; target_task.save()

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

        data = ask_ai_with_failover(prompt, pool_type="coding")
        
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

        retry_config.value = {'time': '2000-01-01T00:00:00'}; retry_config.save()

        for t in data.get('backlog_tasks', []):
            AIProjectBacklog.objects.get_or_create(
                task_name=t['task_name'], target_file=t['target_file'],
                defaults={'priority': t.get('priority', 'Medium'), 'status': 'Pending', 'description': t.get('description', '')}
            )

                # 8. የኮድ ማሻሻያ እና ሲንታክስ ምርመራ (Validation)
        updates = data.get('updates', {})
        code_changed = False
        
        for key, new_content in updates.items():
            if new_content and len(new_content.strip()) > 10:
                # 🛡️ አዲስ የራስ-አራሚ (Self-Correction) ሎጂክ
                if key in ['models', 'views', 'urls', 'forms']:
                    try:
                        compile(new_content, f"test_{key}.py", 'exec')
                    except SyntaxError as e:
                        logger.error(f"❌ Syntax Error recorded in memory: {e}")
                        AgentErrorLog.objects.create(
                            task_name=target_task.task_name if target_task else "Audit",
                            error_message=str(e),
                            code_attempted=new_content
                        )
                        continue # ስህተት ያለበት ኮድ ወደ ፋይል አይጻፍም

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



        if data.get('database_migration_needed') and updates.get('models'):
            try:
                call_command('makemigrations', 'marketplace', interactive=False)
                call_command('migrate', interactive=False)
            except: pass

        if code_changed:
            clear_url_caches()
            last_state_config.value = {'hash': hashlib.sha256(json.dumps(get_complete_project_state()[0]).encode()).hexdigest()}
            last_state_config.save()

        if override_obj: override_obj.is_processed = True; override_obj.save()
        if target_task: target_task.status = 'Completed'; target_task.save()

        return f"🎉 Evolved! Processed: {target_task.task_name if target_task else 'Audit'}"

    except Exception as e:
        if target_task: target_task.status = 'Pending'; target_task.save()
        logger.error(f"❌ Creator Engine Crash: {e}")
        return f"❌ Error: {str(e)}"
    finally:
        lock.value = {'status': 'idle'}; lock.save()
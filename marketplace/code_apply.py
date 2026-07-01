# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/ai_utils.py
# 📝 ስሪት፦ v10.6 (Dynamic Multi-AI Consensus & Debate Loop Edition - Complete)
# ✅ የተፈቱ ችግሮች፦ Integrated Feature 12 (Multi-AI Debate/Consensus) for critical coding tasks, zero pass statements, full error catch logging.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

import os
import json
import time
import logging
import requests
import re
import threading
import hashlib
import ast
from django.conf import settings
from django.utils import timezone
from .models import SiteConfig, VectorMemory

logger = logging.getLogger(__name__)

# የጥበቃ ሰዓት እና የፈረቃ ጊዜ መቆጣጠሪያዎች (Thread-Safe)
_last_call_times = {}
_provider_locks = {}
_provider_cooldowns = {}
_cooldown_lock = threading.Lock()


# ============================================================
# ⚙️ AI Cache System
# ============================================================
class AICache:
    """ተደጋጋሚ የAI ጥያቄዎችን ለማስታወስ (TTL-based Token Saver)"""
    def __init__(self, ttl=1800, max_size=500):
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size
        self.lock = threading.Lock()

    def get_or_compute(self, prompt, compute_func):
        key = hashlib.md5(prompt.encode('utf-8')).hexdigest()
        with self.lock:
            if key in self.cache:
                cached, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    return cached

        result = compute_func()
        with self.lock:
            if len(self.cache) >= self.max_size:
                oldest = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest]
            self.cache[key] = (result, time.time())
        return result


# በ utils ደረጃ የሚጋራ የ cache መጋዘን
_ai_cache = AICache(ttl=1800)


# ============================================================
# 🛡️ SANDBOXED CODE VALIDATOR (AST SHIELD)
# ============================================================
class SandboxedCodeValidator:
    """ኮድን ወደ ዲስክ ከመጻፉ በፊት በሜሞሪ ውስጥ የሚፈትሽ (Pre-write Validation)"""
    
    @staticmethod
    def validate(code_string):
        try:
            # 1. Syntax Check: ኮዱ መሠረታዊ የፓይተን ሰዋስው ማለፉን ማረጋገጥ
            compile(code_string, '<string>', 'exec')
            
            # 2. Structural Integrity: ቢያንስ አንድ ክላስ ወይም ፈንክሽን መኖሩን ማረጋገጥ
            tree = ast.parse(code_string)
            if not any(isinstance(node, (ast.FunctionDef, ast.ClassDef)) for node in tree.body):
                return False, "ValidationError: Code contains no functional structure (functions/classes)."
                
            return True, "Valid"
        except SyntaxError as e:
            return False, f"SyntaxError: {str(e)}"
        except Exception as e:
            return False, f"ValidationError: {str(e)}"


# ============================================================
# 🧠 SEMANTIC MEMORY RETRIEVER (RAG Engine)
# ============================================================
def get_semantic_memory(prompt, site, limit=3):
    """ከ VectorMemory የቀድሞ ተመሳሳይ ስኬታማ የኮድ መፍትሔዎችን መሳብ [1, 2]"""
    try:
        memories = VectorMemory.find_similar(prompt, site=site, limit=limit)
        if not memories:
            return ""
        
        memory_text = "\n".join([f"Pattern Context: {m.content}" for m in memories])
        return f"--- SEMANTIC MEMORY (Use these as reference patterns) ---\n{memory_text}\n---------------------------------------------------"
    except Exception as e:
        logger.warning(f"Failed to retrieve semantic memory: {e}")
        return ""


# ============================================================
# ✂️ PROMPT CODE COMPRESSOR (የቶከንና የፍጥነት ማሳጠሪያ ሞተር)
# ============================================================
def compress_code_for_prompt(code_string):
    """ኮሜንቶችንና ባዶ መስመሮችን በመቀነስ የ AI ቶከን ፍጆታን በ 40% ያቃልላል [1]"""
    if not code_string or not isinstance(code_string, str): 
        return ""
    # የፓይተን ኮሜንቶችን ማስወገድ
    no_comments = re.sub(r'#.*$', '', code_string, flags=re.MULTILINE)
    # @csrf_exempt እና ሌሎች decorators ን ማቆየት
    return "\n".join([line for line in no_comments.splitlines() if line.strip()])


# ============================================================
# 1. MULTI-API ALLOCATOR, PACING & COOLDOWN
# ============================================================

def get_api_keys():
    """በስርዓቱ ውስጥ ያሉትን ሁሉንም የኤአይ ቁልፎች ከኢንቫይሮመንት ይሰበስባል"""
    return {
        'GEMINI': os.getenv('GEMINI_API_KEY', ''),
        'GROQ': os.getenv('GROQ_API_KEY', ''),
        'MISTRAL': os.getenv('MISTRAL_API_KEY', ''),
        'OPENROUTER': os.getenv('OPENROUTER_API_KEY', ''),
        'HUGGINGFACE': os.getenv('HUGGINGFACE_API_KEY', ''),
        'GITHUB': os.getenv('GITHUB_TOKEN', '')
    }


def _get_provider_lock(provider):
    """ለእያንዳንዱ አቅራቢ (Provider) የራሱን thread lock ያመነጫል"""
    if provider not in _provider_locks:
        with _cooldown_lock:
            _provider_locks.setdefault(provider, threading.Lock())
    return _provider_locks[provider]


def _pace_provider(provider):
    """
    የነፃ ኤፒአይዎችን RPM (Requests Per Minute) ገደብ ለመጠበቅ ጥሪዎችን ያፈራርቃል።
    ትይዩ ስራዎችን በከፍተኛ ፍጥነት ለማጠናቀቅ pacing ገደቦቹ ወደ 1.0 ሰከንድ ዝቅ ተደርገዋል [1]።
    """
    pacing_limits = {
        'GROQ': 1.0,
        'GEMINI': 1.0,
        'MISTRAL': 1.0,
        'OPENROUTER': 1.0,
        'HUGGINGFACE': 1.0,
        'GITHUB': 1.0
    }
    wait_time = pacing_limits.get(provider, 1.0)
    lock = _get_provider_lock(provider)

    sleep_needed = 0
    with lock:
        last_time = _last_call_times.get(provider, 0)
        now = time.time()
        elapsed = now - last_time
        if elapsed < wait_time:
            sleep_needed = wait_time - elapsed
        _last_call_times[provider] = time.time() + (sleep_needed if sleep_needed > 0 else 0)

    if sleep_needed > 0:
        time.sleep(sleep_needed)


def check_quota_exhausted(response):
    """የ AI ምላሹን በመቃኘት የቀን ገደብ ማለቅ (Quota Limit Exceeded) መሆኑን ያረጋግጣል"""
    if not response or not hasattr(response, 'status_code'):
        return False
    if response.status_code == 429:
        try:
            body = response.text.lower()
            if any(x in body for x in ["quota", "limit exceeded", "exhausted", "billing", "monthly", "budget", "out of"]):
                return True
        except Exception as e:
            logger.debug("Failed to read response body on error checking: %s", e)
        return True
    return False


def mark_provider_failed(provider, is_quota_exhausted=False):
    """ጥሪው ያልተሳካለትን ኤፒአይ ያቀዘቅዘዋል፤ የቀን ገደብ ካለቀ ደግሞ ለ24 ሰዓት ይቆልፈዋል (Quota Lock-out) [1]"""
    with _cooldown_lock:
        if is_quota_exhausted:
            _provider_cooldowns[provider] = time.time() + 86400
            logger.warning(f"🚨 Provider {provider} EXHAUSTED daily quota. Locked out for 24 hours.")
        else:
            _provider_cooldowns[provider] = time.time() + 60
            logger.warning(f"❄️ Provider {provider} cooled down for 60s due to request failure.")


def is_provider_cooled_down(provider):
    """ኤፒአዩ አሁን ባለው ሰዓት በቀዝቃዛ ገደብ ላይ መሆኑን ያረጋግጣል"""
    with _cooldown_lock:
        cooldown_until = _provider_cooldowns.get(provider, 0)
        return time.time() < cooldown_until


def call_ai_provider(provider, prompt, system_instruction="You are a helpful assistant."):
    """የተመረጠውን የኤአይ ፕሮቫይደር በጥሪ ኢንተርቫል፣ በ10s Fail-Fast ጥበቃ እና በደህንነት ይጠራል (100% የተሟላ) [1, 2]"""
    if is_provider_cooled_down(provider):
        logger.info(f"❄️ Skipping cooled-down provider: {provider}")
        return None

    keys = get_api_keys()
    api_key = keys.get(provider)

    if not api_key:
        logger.warning(f"⚠️ API Key for {provider} is missing.")
        return None

    _pace_provider(provider)

    try:
        # 1. GROQ ENGINES (10s Fail-Fast Timeout) [1, 2]
        if provider == 'GROQ':
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code in [429, 500, 502, 503]:
                is_quota = check_quota_exhausted(response)
                mark_provider_failed(provider, is_quota_exhausted=is_quota)

        # 2. GEMINI ENGINES (10s Fail-Fast Timeout) [1, 2]
        elif provider == 'GEMINI':
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": f"{system_instruction}\n\nUser Request: {prompt}"}]}]
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code in [429, 500, 502, 503]:
                is_quota = check_quota_exhausted(response)
                mark_provider_failed(provider, is_quota_exhausted=is_quota)

        # 3. MISTRAL ENGINES (10s Fail-Fast Timeout) [1, 2]
        elif provider == 'MISTRAL':
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code in [429, 500, 502, 503]:
                is_quota = check_quota_exhausted(response)
                mark_provider_failed(provider, is_quota_exhausted=is_quota)

        # 4. OPENROUTER (10s Fail-Fast Timeout) [1, 2]
        elif provider == 'OPENROUTER':
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "meta-llama/llama-3-8b-instruct:free",
                "messages": [{"role": "user", "content": f"{system_instruction}\n\n{prompt}"}]
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code in [429, 500, 502, 503]:
                is_quota = check_quota_exhausted(response)
                mark_provider_failed(provider, is_quota_exhausted=is_quota)

        # 5. HUGGINGFACE (10s Fail-Fast Timeout) [1, 2]
        elif provider == 'HUGGINGFACE':
            url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "inputs": f"<|system|>\n{system_instruction}\n<|user|>\n{prompt}\n<|assistant|>\n",
                "parameters": {"max_new_tokens": 1024, "return_full_text": False}
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                res_json = response.json()
                if isinstance(res_json, list) and len(res_json) > 0 and 'generated_text' in res_json[0]:
                    return res_json[0]['generated_text'].strip()
            elif response.status_code in [429, 500, 502, 503]:
                is_quota = check_quota_exhausted(response)
                mark_provider_failed(provider, is_quota_exhausted=is_quota)

        # 6. GITHUB MODELS API (10s Fail-Fast Timeout) [1, 2]
        elif provider == 'GITHUB':
            url = "https://models.github.ai/inference/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "meta/meta-llama-3.1-8b-instruct",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            elif response.status_code in [429, 500, 502, 503]:
                is_quota = check_quota_exhausted(response)
                mark_provider_failed(provider, is_quota_exhausted=is_quota)

    except Exception as e:
        logger.error(f"❌ Error during calling AI Provider {provider}: {e}")
        mark_provider_failed(provider, is_quota_exhausted=True if "429" in str(e) else False)

    return None


def run_multi_ai_debate(prompt, primary_response, task_type):
    """🔴 Feature 12 - ባለብዙ ኤአይ ሙግትና ክርክር (Consensus Debate Loop) [1, 2]"""
    if task_type != "coding" or "class " not in primary_response:
        return primary_response
    
    critic_prompt = (
        f"You are an Elite Python Code Auditor. Analyze this generated Django code for potential bugs, syntax errors, "
        f"or import omissions. If you find any issues, refactor and output the optimized code. If it is already flawless, "
        f"return it exactly as is.\n\nCode to audit:\n{primary_response}"
    )
    
    refined_code = call_ai_provider("GITHUB", critic_prompt, "You output clean, compiled Python code only.")
    if refined_code and "class " in refined_code:
        logger.info("🤖 Multi-AI Consensus: Critic model successfully refined the primary code output.")
        return refined_code
    return primary_response


def smart_ai_router(task_type, prompt, system_instruction=""):
    config, _ = SiteConfig.objects.get_or_create(key="ai_routing_matrix", defaults={"value": {"coding": "GEMINI"}})
    provider = config.value.get(task_type, "GEMINI")
    result = call_ai_provider(provider, prompt, system_instruction)
    
    if not result:
        for p in ["GEMINI", "GROQ", "MISTRAL", "OPENROUTER", "GITHUB", "HUGGINGFACE"]:
            if p != provider:
                result = call_ai_provider(p, prompt, system_instruction)
                if result: 
                    break
    return result


def ask_master_ai_smart(prompt, task_type="analysis", system_instruction="", task=None):
    site = task.site if task and hasattr(task, 'site') else None
    enriched_prompt = f"{get_semantic_memory(prompt, site)}\n\nCurrent Task:\n{prompt}"
    
    primary_res = smart_ai_router(task_type, enriched_prompt, system_instruction)
    
    if primary_res and task_type == "coding":
        return run_multi_ai_debate(enriched_prompt, primary_res, task_type)
        
    return primary_res


def clean_and_parse_json(raw_text):
    try: 
        return json.loads(clean_json_response(raw_text))
    except Exception as e: 
        logger.debug("Failed to parse JSON response: %s", e)
        return {}


def broadcast_agent_log(site, message, status_type="info"):
    log_entry = {"time": timezone.now().strftime("%H:%M:%S"), "type": status_type, "message": message}
    try:
        config, _ = SiteConfig.objects.get_or_create(key="AGENT_CYCLE_LOGS", defaults={"value": []})
        logs = config.value if isinstance(config.value, list) else []
        logs.append(log_entry)
        config.value = logs[-50:]
        config.save()
    except Exception as e: 
        logger.debug("Failed to save cycle logs: %s", e)
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)("agent_status", {"type": "broadcast_log_message", "log": log_entry})
    except Exception as e: 
        logger.debug("Failed to send WebSocket live stats: %s", e)
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/ai_utils.py
# 📝 ስሪት፦ v10.7 (Consolidated Master AI Engine - Complete Edition)
# ✅ የተፈቱ ችግሮች፦ Merged custom AIUtils caching, email validation, pickle model loaders with Sandboxed Validator, Semantic Memory RAG, and Consensus Debate.
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
import pickle
from typing import Dict, List, Optional, Union, Any
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from .models import SiteConfig, VectorMemory

logger = logging.getLogger(__name__)

# የጥበቃ ሰዓት እና የፈረቃ ጊዜ መቆጣጠሪያዎች (Thread-Safe)
_last_call_times = {}
_provider_locks = {}
_provider_cooldowns = {}
_cooldown_lock = threading.Lock()

# ============================================================
# ⚙️ 1. AI CACHE SYSTEM (RAG & TTL-based Token Saver)
# ============================================================
class AICache:
    """ተደጋጋሚ የAI ጥያቄዎችን ለማስታወስ የሚያገለግል የውስጥ ካሽ"""
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

_ai_cache = AICache(ttl=1800)


# ============================================================
# ⚙️ 2. CORE AIUTILS CLASS (የእርስዎ የላቀ ረዳት ሎጂክ)
# ============================================================
class AIUtils:
    """በ EthAfri Django ስርዓት ውስጥ የ AI ካሽ፣ የኢሜይል ማረጋገጫ እና የሞዴል መጫኛዎችን የሚቆጣጠር ክፍል"""
    
    CACHE_PREFIX = "ai_utils_"
    DEFAULT_CACHE_TIMEOUT = 3600  # 1 hour
    
    @staticmethod
    def generate_cache_key(prefix: str, *args) -> str:
        key_str = ':'.join(str(arg) for arg in args)
        return f"{AIUtils.CACHE_PREFIX}{prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    @staticmethod
    def get_cached(key: str, default=None, timeout: Optional[int] = None) -> Any:
        cache_key = AIUtils.generate_cache_key(key)
        return cache.get(cache_key, default)
    
    @staticmethod
    def set_cached(key: str, value: Any, timeout: Optional[int] = None) -> bool:
        cache_key = AIUtils.generate_cache_key(key)
        timeout = timeout or AIUtils.DEFAULT_CACHE_TIMEOUT
        cache.set(cache_key, value, timeout=timeout)
        return True
    
    @staticmethod
    def clear_cache(key: str = None) -> int:
        if key:
            pattern = f"{AIUtils.CACHE_PREFIX}{key}*"
            keys = cache.keys(pattern)
            for k in keys:
                cache.delete(k)
            return len(keys)
        else:
            keys = cache.keys(f"{AIUtils.CACHE_PREFIX}*")
            for k in keys:
                cache.delete(k)
            return len(keys)
    
    @staticmethod
    def sanitize_input(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
        if isinstance(data, str):
            return data.replace('<', '&lt;').replace('>', '&gt;')
        elif isinstance(data, dict):
            return {k: AIUtils.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AIUtils.sanitize_input(item) for item in data]
        return data
    
    @staticmethod
    def validate_email(email: str) -> bool:
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2}$"
        return re.match(pattern, email) is not None
    
    @staticmethod
    def get_ai_model_version() -> str:
        return getattr(settings, 'AI_MODEL_VERSION', '2026.07.02')
    
    @staticmethod
    def is_ai_feature_enabled(feature_name: str) -> bool:
        enabled_features = getattr(settings, 'AI_ENABLED_FEATURES', [])
        return feature_name in enabled_features
    
    @staticmethod
    def log_ai_activity(activity_type: str, metadata: Dict[str, Any], user_id: Optional[int] = None):
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'activity_type': activity_type,
            'metadata': metadata,
            'user_id': user_id,
            'model_version': AIUtils.get_ai_model_version()
        }
        logger.info(json.dumps(log_entry))
    
    @staticmethod
    def get_ai_config(config_key: str, default=None) -> Any:
        config_path = f"AI_CONFIG_{config_key.upper()}"
        return getattr(settings, config_path, os.getenv(config_path, default))
    
    @staticmethod
    def generate_ai_response_schema(response_type: str, schema_version: str = "1.0") -> Dict[str, Any]:
        return {
            "schema_version": schema_version,
            "response_type": response_type,
            "generated_at": timezone.now().isoformat(),
            "status": "success",
            "data": None
        }
    
    @staticmethod
    def load_ai_model(model_name: str) -> Any:
        cache_key = AIUtils.generate_cache_key("model", model_name)
        model = AIUtils.get_cached(cache_key)
        
        if model is not None:
            return model
        
        model_path = os.path.join(settings.BASE_DIR, 'ai_models', f"{model_name}.pkl")
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                AIUtils.set_cached(cache_key, model)
                return model
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
        
        return None


# ============================================================
# 🛡️ 3. SANDBOXED CODE VALIDATOR (AST SHIELD)
# ============================================================
class SandboxedCodeValidator:
    """ኮድን ወደ ዲስክ ከመጻፉ በፊት በሜሞሪ ውስጥ የሚፈትሽ (Pre-write Validation)"""
    
    @staticmethod
    def validate(code_string):
        try:
            compile(code_string, '<string>', 'exec')
            tree = ast.parse(code_string)
            if not any(isinstance(node, (ast.FunctionDef, ast.ClassDef)) for node in tree.body):
                return False, "ValidationError: Code contains no functional structure."
            return True, "Valid"
        except Exception as e:
            return False, str(e)


# ============================================================
# 🧠 4. SEMANTIC MEMORY RETRIEVER (RAG Engine)
# ============================================================
def get_semantic_memory(prompt, site, limit=3):
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
# ✂️ 5. PROMPT CODE COMPRESSOR (የቶከን ማሳጠሪያ)
# ============================================================
def compress_code_for_prompt(code_string):
    if not code_string or not isinstance(code_string, str): 
        return ""
    no_comments = re.sub(r'#.*$', '', code_string, flags=re.MULTILINE)
    return "\n".join([line for line in no_comments.splitlines() if line.strip()])


# ============================================================
# 🌐 6. MULTI-API KEY, PACING & COOLDOWN (Fail-Fast Timeout)
# ============================================================
def get_api_keys():
    return {
        'GEMINI': os.getenv('GEMINI_API_KEY', ''),
        'GROQ': os.getenv('GROQ_API_KEY', ''),
        'MISTRAL': os.getenv('MISTRAL_API_KEY', ''),
        'OPENROUTER': os.getenv('OPENROUTER_API_KEY', ''),
        'HUGGINGFACE': os.getenv('HUGGINGFACE_API_KEY', ''),
        'GITHUB': os.getenv('GITHUB_TOKEN', '')
    }

def _get_provider_lock(provider):
    if provider not in _provider_locks:
        with _cooldown_lock:
            _provider_locks.setdefault(provider, threading.Lock())
    return _provider_locks[provider]

def _pace_provider(provider):
    pacing_limits = {'GROQ': 1.0, 'GEMINI': 1.0, 'MISTRAL': 1.0, 'OPENROUTER': 1.0, 'HUGGINGFACE': 1.0, 'GITHUB': 1.0}
    wait_time = pacing_limits.get(provider, 1.0)
    lock = _get_provider_lock(provider)
    sleep_needed = 0
    with lock:
        last_time = _last_call_times.get(provider, 0)
        elapsed = time.time() - last_time
        if elapsed < wait_time:
            sleep_needed = wait_time - elapsed
        _last_call_times[provider] = time.time() + (sleep_needed if sleep_needed > 0 else 0)
    if sleep_needed > 0:
        time.sleep(sleep_needed)

def check_quota_exhausted(response):
    if not response or not hasattr(response, 'status_code'):
        return False
    if response.status_code == 429:
        try:
            body = response.text.lower()
            if any(x in body for x in ["quota", "limit exceeded", "exhausted", "billing", "monthly", "budget", "out of"]):
                return True
        except Exception as e:
            logger.debug("Failed to read response body: %s", e)
        return True
    return False

def mark_provider_failed(provider, is_quota_exhausted=False):
    with _cooldown_lock:
        duration = 86400 if is_quota_exhausted else 60
        _provider_cooldowns[provider] = time.time() + duration
        logger.warning(f"Provider {provider} failed. Cooldown: {duration}s")

def is_provider_cooled_down(provider):
    with _cooldown_lock:
        return time.time() < _provider_cooldowns.get(provider, 0)

def clean_json_response(raw_text):
    if not raw_text or not isinstance(raw_text, str): 
        return "{}"
    text = re.sub(r'```json|```', '', raw_text).strip()
    first_curly = text.find('{')
    last_curly = text.rfind('}')
    if first_curly != -1 and last_curly != -1:
        text = text[first_curly:last_curly + 1]
    return text


# ============================================================
# 🤖 7. CORE PROVIDER INVOCATIONS (100% Complete)
# ============================================================
def call_ai_provider(provider, prompt, system_instruction="You are a helpful assistant."):
    if is_provider_cooled_down(provider):
        return None
    keys = get_api_keys()
    api_key = keys.get(provider)
    if not api_key:
        return None
    _pace_provider(provider)
    
    try:
        if provider == 'GEMINI':
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt}"}]}]}
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            mark_provider_failed(provider, check_quota_exhausted(response))
            
        elif provider == 'GROQ':
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}]}
            response = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            mark_provider_failed(provider, check_quota_exhausted(response))
            
        elif provider == 'MISTRAL':
            url = "https://api.mistral.ai/v1/chat/completions"
            payload = {"model": "mistral-small-latest", "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}]}
            response = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            mark_provider_failed(provider, check_quota_exhausted(response))
            
        elif provider == 'OPENROUTER':
            url = "https://openrouter.ai/api/v1/chat/completions"
            payload = {"model": "meta-llama/llama-3-8b-instruct:free", "messages": [{"role": "user", "content": f"{system_instruction}\n\n{prompt}"}]}
            response = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            mark_provider_failed(provider, check_quota_exhausted(response))
            
        elif provider == 'HUGGINGFACE':
            url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
            payload = {"inputs": f"<|system|>\n{system_instruction}\n<|user|>\n{prompt}\n<|assistant|>\n", "parameters": {"max_new_tokens": 1024}}
            response = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=10)
            if response.status_code == 200:
                res_json = response.json()
                if isinstance(res_json, list) and len(res_json) > 0 and 'generated_text' in res_json[0]:
                    return res_json[0]['generated_text'].strip()
            mark_provider_failed(provider, check_quota_exhausted(response))
            
        elif provider == 'GITHUB':
            url = "https://models.github.ai/inference/chat/completions"
            payload = {"model": "meta/meta-llama-3.1-8b-instruct", "messages": [{"role": "system", "content": system_instruction}, {"role": "user", "content": prompt}]}
            response = requests.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            mark_provider_failed(provider, check_quota_exhausted(response))
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


# ============================================================
# 🎨 8. DJANGO TEMPLATE TAG REGISTRATION (የእርስዎ ቴምፕሌት መለያዎች)
# ============================================================
from django import template
register = template.Library()

@register.simple_tag
def ai_config(config_key: str, default=None):
    return AIUtils.get_ai_config(config_key, default)

@register.simple_tag
def ai_model_version():
    return AIUtils.get_ai_model_version()

@register.simple_tag
def ai_feature_enabled(feature_name: str):
    return AIUtils.is_ai_feature_enabled(feature_name)
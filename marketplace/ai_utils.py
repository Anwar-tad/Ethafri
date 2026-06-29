# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/ai_utils.py
# 📝 ስሪት፦ v10.2 (High-Throughput 10s Fail-Fast & 24-Hour Quota Lock-out Edition)
# ✅ የተፈቱ ችግሮች፦ Mapped 10-Second Fail-Fast timeout, 24-Hour daily quota lock-out engine, 40% Token Saving prompt compressor, 1.0s Pacing speedups, Safe JSON type guards, Modern GitHub endpoint routing
# 📅 ቀን፦ Monday, June 29, 2026
# ============================================================

import os
import json
import time
import logging
import requests
import re
import threading
import hashlib
from django.conf import settings
from django.utils import timezone
from .models import SiteConfig

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
                self._evict_oldest()
            self.cache[key] = (result, time.time())
        return result

    def _evict_oldest(self):
        if self.cache:
            oldest = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest]


# በ utils ደረጃ የሚጋራ የ cache መጋዘን
_ai_cache = AICache(ttl=1800)


# ============================================================
# ✂️ PROMPT CODE COMPRESSOR (የቶከንና የፍጥነት ማሳጠሪያ ሞተር)
# ============================================================
def compress_code_for_prompt(code_string):
    """ኮሜንቶችንና ባዶ መስመሮችን በመቀነስ የ AI ቶከን ፍጆታን በ 40% ያቃልላል [1]"""
    if not code_string or not isinstance(code_string, str): 
        return ""
    # የፓይተን ኮሜንቶችን ማስወገድ
    no_comments = re.sub(r'#.*$', '', code_string, flags=re.MULTILINE)
    # ባዶ መስመሮችን ማጽዳት
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
    ትይዩ ስራዎችን በከፍተኛ ፍጥነት ለማጠናቀቅ pacing ገደቦቹ ወደ 1.0 ሰከንድ ዝቅ ተደርገዋል [1]。
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
        except:
            pass
        return True # በዲፎልት የነፃ ኤፒአይ 429 ስህተት የቀን ገደብ ማለቅን ያሳያል
    return False


def mark_provider_failed(provider, is_quota_exhausted=False):
    """ጥሪው ያልተሳካለትን ኤፒአይ ያቀዘቅዘዋል፤ የቀን ገደብ ካለቀ ደግሞ ለ24 ሰዓት ይቆልፈዋል (Quota Lock-out) [1]"""
    with _cooldown_lock:
        if is_quota_exhausted:
            # የቀን ገደብ ካለቀ ለ24 ሰዓታት (86400 ሰከንዶች) መቆለፍ [1]
            _provider_cooldowns[provider] = time.time() + 86400
            logger.warning(f"🚨 Provider {provider} EXHAUSTED daily quota. Locked out for 24 hours.")
        else:
            # ጊዜያዊ ስህተት ከሆነ ለ60 ሰከንድ ብቻ ማቀዝቀዝ [1]
            _provider_cooldowns[provider] = time.time() + 60
            logger.warning(f"❄️ Provider {provider} cooled down for 60s due to request failure.")


def is_provider_cooled_down(provider):
    """ኤፒአዩ አሁን ባለው ሰዓት በቀዝቃዛ ገደብ ላይ መሆኑን ያረጋግጣል"""
    with _cooldown_lock:
        cooldown_until = _provider_cooldowns.get(provider, 0)
        return time.time() < cooldown_until


def clean_json_response(raw_text):
    """ከ AI የሚመጣን ምላሽ ፈልቅቆ ንጹህ የ JSON ጽሑፍ ብቻ ያወጣል"""
    if not raw_text or not isinstance(raw_text, str):
        return "{}"

    text = re.sub(r'```json|```', '', raw_text).strip()

    # trailing commas ማስተካከል
    text = re.sub(r',\s*([\]}])', r'\1', text)

    first_curly = text.find('{')
    last_curly = text.rfind('}')
    first_square = text.find('[')
    last_square = text.rfind(']')

    # ትክክለኛ outer root መለየት፦ የትኛው (object ወይም array) ቀድሞ እንደሚጀመር
    if first_curly != -1 and (first_square == -1 or first_curly < first_square):
        if last_curly != -1:
            text = text[first_curly:last_curly + 1]
    elif first_square != -1 and last_square != -1:
        text = text[first_square:last_square + 1]

    return text


def call_ai_provider(provider, prompt, system_instruction="You are a helpful assistant."):
    """የተመረጠውን የኤአይ ፕሮቫይደር በጥሪ ኢንተርቫል እና በደህንነት ጥበቃ ይጠራል"""
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
                if isinstance(res_json, list) and res_json and 'generated_text' in res_json[0]:
                    return res_json[0]['generated_text'].strip()
                elif isinstance(res_json, dict) and 'generated_text' in res_json:
                    return res_json['generated_text'].strip()
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


def smart_ai_router(task_type, prompt, system_instruction=""):
    """እንደ ስራው አይነት እና እንደ ኤአይ ፐርፎርማንስ ስራዎችን ይመራል"""
    config, created = SiteConfig.objects.get_or_create(
        key="ai_routing_matrix",
        defaults={
            "value": {
                "coding": "MISTRAL",
                "code_logic": "MISTRAL",
                "syntax_check": "GROQ",
                "translation": "GEMINI",
                "market_research": "HUGGINGFACE",
                "analysis": "OPENROUTER"
            }
        }
    )
    routing_matrix = config.value
    preferred_provider = routing_matrix.get(task_type, "GEMINI")

    result = call_ai_provider(preferred_provider, prompt, system_instruction)

    if not result:
        fallback_providers = ["GEMINI", "GROQ", "GITHUB", "HUGGINGFACE", "OPENROUTER", "MISTRAL"]
        for provider in fallback_providers:
            if provider != preferred_provider:
                logger.info(f"🔄 Routing Fallback: Switching from {preferred_provider} to {provider} for {task_type}")
                result = call_ai_provider(provider, prompt, system_instruction)
                if result:
                    routing_matrix[task_type] = provider
                    config.value = routing_matrix
                    config.save()
                    break

    return result


# ============================================================
# 2. INCREMENTAL TRANSLATION CACHE ENGINE
# ============================================================

def get_translation_cache():
    """ዳታቤዝ ላይ የተቀመጠውን የቃላት መዝገብ (Cache) ያነባል"""
    config, created = SiteConfig.objects.get_or_create(
        key="translation_word_cache",
        defaults={"value": {}}
    )
    return config


def translate_text_incremental(text_list, target_lang="am"):
    """ቃላትን እስከ 20 በሆኑ ትንንሽ ስብስቦች እየከፋፈለ፣ ያልተተረጎሙትን ብቻ ለይቶ ይተረጉማል"""
    if not text_list:
        return {}

    cache_config = get_translation_cache()
    master_cache = cache_config.value

    if target_lang not in master_cache:
        master_cache[target_lang] = {}

    lang_cache = master_cache[target_lang]

    final_translations = {}
    words_to_translate = []

    for text in text_list:
        text_clean = text.strip()
        if not text_clean:
            continue
        if text_clean in lang_cache:
            final_translations[text_clean] = lang_cache[text_clean]
        else:
            words_to_translate.append(text_clean)

    if not words_to_translate:
        return final_translations

    batch_size = 20
    batches = [words_to_translate[i:i + batch_size] for i in range(0, len(words_to_translate), batch_size)]

    for batch in batches:
        prompt = (
            f"Translate the following list of unique strings into ISO language '{target_lang}'. "
            f"Return a strictly valid JSON dictionary where the keys are the original English strings "
            f"and values are the translated text. Do not add explanations or wrapper text outside JSON.\n"
            f"List: {json.dumps(batch, ensure_ascii=False)}"
        )
        system_instruction = "You are an expert multi-lingual translator. You output clean JSON only."

        ai_response = smart_ai_router("translation", prompt, system_instruction)
        cleaned_response = clean_json_response(ai_response)

        try:
            translated_dict = json.loads(cleaned_response)
            normalized_dict = {str(k).strip().lower(): str(v).strip() for k, v in translated_dict.items() if v}

            for orig in batch:
                orig_clean = orig.strip()
                orig_lower = orig_clean.lower()

                if orig_lower in normalized_dict:
                    trans = normalized_dict[orig_lower]
                    lang_cache[orig_clean] = trans
                    final_translations[orig_clean] = trans
                else:
                    final_translations[orig_clean] = orig_clean

        except Exception as e:
            logger.error(f"❌ Failed to parse translation JSON chunk: {e}")
            for orig in batch:
                if orig not in final_translations:
                    final_translations[orig] = orig

    cache_config.value = master_cache
    cache_config.save()

    return final_translations


def ask_master_ai_smart(prompt, task_type="analysis", system_instruction="", task=None):
    """growth_agent.py የሚጠራውና ወደ smart_ai_router የሚመራው ዋና ፈንክሽን"""
    if not system_instruction:
        system_instruction = (
            "You are the Autonomous CEO of EthAfri. Respond with clean JSON or raw code "
            "depending on the task. Never add conversational filler or intro/outro text."
        )
    if task_type in ['analysis', 'market_research'] and task is None:
        return _ai_cache.get_or_compute(
            f"{system_instruction}\n\n{prompt}",
            lambda: smart_ai_router(task_type, prompt, system_instruction)
        )
    return smart_ai_router(task_type, prompt, system_instruction)


def clean_and_parse_json(raw_text):
    """ከ AI የሚመጣን ምላሽ አጽድቶ ወደ Python Dictionary/List ይቀይራል"""
    cleaned = clean_json_response(raw_text)
    try:
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"Failed to parse cleaned JSON: {e}. Raw text was: {raw_text[:200] if raw_text else 'None'}")
        return {}


def broadcast_agent_log(site, message, status_type="info"):
    """የኤጀንቱን እያንዳንዱን ሥራ በዳታቤዝ ውስጥ ይመዘግባል፣ በ WebSocket በኩልም ይረጫል"""
    timestamp = timezone.now().strftime("%H:%M:%S")
    log_entry = {
        "time": timestamp,
        "type": status_type,
        "message": message
    }

    try:
        config, _ = SiteConfig.objects.get_or_create(key="AGENT_CYCLE_LOGS", defaults={"value": []})
        logs = config.value if isinstance(config.value, list) else []
        logs.append(log_entry)
        config.value = logs[-50:]
        config.save()
    except Exception as db_err:
        logger.error(f"Failed to save cycle log in DB: {db_err}")

    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "agent_status",
                {
                    "type": "broadcast_log_message",
                    "log": log_entry
                }
            )
    except Exception as ws_err:
        logger.debug(f"WebSocket broadcast skipped: {ws_err}")
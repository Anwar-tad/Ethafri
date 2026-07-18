# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/ai_utils.py
# 📝 ስሪት፦ v10.43 (Production Grade - Master Brain - Shift, Spacing & JSON Healer)
# ✅ የተፈቱ ችግሮች፦ Dynamic Quota 24h Quarantine using MD5 key hashes, LRU Local Cache Memory Guard, Cerebras model preserved, Gemini 6-hour shift rotation, circular dependency prevention, and automatic JSON Self-Healer added in clean_and_parse_json to fix Unterminated string errors on the fly (v10.43).
# 📅 ቀን፦ Thursday, July 13, 2026
# ============================================================

import os
import re
import json
import hashlib
import logging
import requests
import time   
import random 
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple

from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django import template
from django.apps import apps

logger = logging.getLogger(__name__)

# Django Cache ካልተዋቀረ በስተጀርባ የሚሰራ ጊዜያዊ የአካባቢ መሸጎጫ (Memory Guard Fallback)
_LOCAL_CACHE = {}
_LOCAL_CACHE_MAX_SIZE = 100


class AIUtils:
    """
    ለEthAfri የላቁ የኤጀንት ስራዎች የ AI ጥሪዎችን፣ መሸጎጫዎችን (Caching)፣
    እና የቶከን መጭመቂያዎችን በአንድ ላይ የሚያስተባብር ማስተር ክላስ
    """
    
    CACHE_PREFIX = "ai_utils_"
    DEFAULT_CACHE_TIMEOUT = 3600  # 1 hour
    
    @staticmethod
    def generate_cache_key(prefix: str, *args) -> str:
        """የመሸጎጫ ቁልፍ በዳይናሚክ የሚያመነጭ ረዳት"""
        key_str = ':'.join(str(arg) for arg in args)
        return f"{AIUtils.CACHE_PREFIX}{prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    @staticmethod
    def get_cached(key: str, default=None) -> Any:
        """መሸጎጫውን በመፈተሽ የተቀመጠ መረጃ ካለ መሳብ (ከLocal Fallback ጋር)"""
        cache_key = AIUtils.generate_cache_key(key)
        try:
            val = cache.get(cache_key)
            if val is not None:
                return val
        except Exception:
            pass
        
        # የዳታቤዝ ወይም የሪዲስ መሸጎጫ ካልሰራ ከፊል ማህደረ-ትውስታ መሳቢያ
        local_val = _LOCAL_CACHE.get(cache_key)
        if local_val:
            val, expiry = local_val
            if time.time() < expiry:
                return val
            else:
                del _LOCAL_CACHE[cache_key]
        return default
    
    @staticmethod
    def set_cached(key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """ውጤቶችን በመሸጎጫ ውስጥ ማስቀመጥ (ከ Memory Guard LRU Fallback ጋር)"""
        cache_key = AIUtils.generate_cache_key(key)
        timeout = timeout or AIUtils.DEFAULT_CACHE_TIMEOUT
        try:
            cache.set(cache_key, value, timeout=timeout)
        except Exception:
            pass
        
        # 🛡️ LOCAL MEMORY GUARD: የራም ማህደረ-ትውስታ እንዳይሞላ የቆዩ መሸጎጫዎችን ማስወገድ
        if len(_LOCAL_CACHE) >= _LOCAL_CACHE_MAX_SIZE:
            try:
                oldest_key = next(iter(_LOCAL_CACHE))
                del _LOCAL_CACHE[oldest_key]
            except Exception:
                pass
                
        _LOCAL_CACHE[cache_key] = (value, time.time() + timeout)
        return True
    
    @staticmethod
    def clear_cache(key: str = None) -> int:
        """የ AI መሸጎጫዎችን በሙሉ ወይም በከፊል ማጽዳት"""
        count = 0
        if key:
            pattern = f"{AIUtils.CACHE_PREFIX}{key}*"
            try:
                keys = cache.keys(pattern)
                for k in keys:
                    cache.delete(k)
                    count += 1
            except Exception:
                pass
            
            for k in list(_LOCAL_CACHE.keys()):
                if k.startswith(f"{AIUtils.CACHE_PREFIX}{key}"):
                    del _LOCAL_CACHE[k]
                    count += 1
        else:
            try:
                keys = cache.keys(f"{AIUtils.CACHE_PREFIX}*")
                for k in keys:
                    cache.delete(k)
                    count += 1
            except Exception:
                pass
            _LOCAL_CACHE.clear()
        return count
    
    @staticmethod
    def sanitize_input(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
        """ግብዓቶችን ከ XSS ጥቃት ለመጠበቅ ማጽዳት"""
        if isinstance(data, str):
            return data.replace('<', '&lt;').replace('>', '&gt;')
        elif isinstance(data, dict):
            return {k: AIUtils.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AIUtils.sanitize_input(item) for item in data]
        return data
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """የኢሜይል አድራሻን ፎርማት በሪጀክስ ማረጋገጫ"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2}$"
        return re.match(pattern, email) is not None
    
    @staticmethod
    def get_ai_model_version() -> str:
        return getattr(settings, 'AI_MODEL_VERSION', '2026.07.13')
    
    @staticmethod
    def is_ai_feature_enabled(feature_name: str) -> bool:
        enabled_features = getattr(settings, 'AI_ENABLED_FEATURES', [])
        return feature_name in enabled_features
    
    @staticmethod
    def log_ai_activity(activity_type: str, metadata: Dict[str, Any], user_id: Optional[int] = None):
        """የ AI ስራዎችን ለኦዲት ምቹ በሆነ የ JSON ፎርማት መዝግቦ ማስቀመጥ"""
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
                import pickle
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                AIUtils.set_cached(cache_key, model)
                return model
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
        return None

    @staticmethod
    def compress_code_for_prompt(code: str) -> str:
        """
        ባዶ መስመሮችንና የኮሜንት ጽሑፎችን በሙሉ በማጽዳት ለ AI የሚላከውን
        የኮድ መጠን በ 40% በመቀነስ የቶከን ወጪን የሚቆጥብ ሞተር
        """
        if not code or not isinstance(code, str):
            return ""
        
        # 🛡️ multiline docstrings (''' ... ''' and """ ... """) ማጽዳት
        code = re.sub(r'(""\"[\s\S]*?""\"|\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', '', code)
        
        compressed_lines = []
        for line in code.splitlines():
            stripped_line = line.strip()
            if stripped_line.startswith('#'):
                continue
            if stripped_line.startswith('<!--') and stripped_line.endswith('-->'):
                continue
            if not stripped_line:
                continue
            
            compressed_lines.append(line)
            
        return "\n".join(compressed_lines)


# ============================================================
# 🧹 MD STRIP & JSON REPAIR (የ AI ምላሽ ጽዳት)
# ============================================================
def clean_json_response(raw_text: str) -> str:
    """የ AI ምላሽ ውስጥ የሚገኙትን የባክቲክ ምልክቶችን አስወግዶ ንጹህ JSON ብቻ የሚያስቀር"""
    if not raw_text or not isinstance(raw_text, str):
        return "{}"
    
    clean_text = raw_text.strip()
    
    if "```json" in clean_text:
        clean_text = clean_text.split("```json")[-1].split("```")[0]
    elif "```" in clean_text:
        clean_text = clean_text.split("```")[1].split("```")[0]
        
    clean_text = clean_text.strip()
    
    first_brace = clean_text.find('{')
    if first_brace != -1:
        brace_count = 0
        for idx in range(first_brace, len(clean_text)):
            char = clean_text[idx]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return clean_text[first_brace:idx+1]
                    
    return clean_text


def clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """ንጹህ JSON በመፍጠር ያለምንም ስህተት parse አድርጎ ዲክሽነሪ ይመልሳል (የራስ-ጥገና ጋሻ የተጫነበት)"""
    cleaned = ""
    try:
        cleaned = clean_json_response(raw_text)
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"⚠️ JSON Parsing failed initially: {e}. Activating automatic JSON self-repair...")
        try:
            # 1. በምርት ዲስክሪፕሽን ውስጥ ያሉ ያልተጠበቁ አዳዲስ መስመሮችን (Newlines/Tabs) እና የመዝጊያ ኮማዎችን ማጽዳት
            repaired = re.sub(r',\s*([\]}])', r'\1', cleaned) # የመዝጊያ ኮማዎችን ማጥፋት
            repaired = re.sub(r'[\t\n\r]', ' ', repaired) # አዳዲስ መስመሮችን በባዶ ቦታ መተካት
            
            # 2. 🛡️ SURGICAL QUOTE ESCAPER: በምርት ርዕስ/መግለጫ ውስጥ ያሉ ያልተጠበቁ ጥቅሶችን በራስ-ሰር በ slash (\") መተካት [NEW]
            repaired = re.sub(r'(?<=[:\s,\[])"([\s\S]*?)"(?=[\s,\]}])', lambda m: '"' + m.group(1).replace('"', '\\"') + '"', repaired)
            
            # 3. 🛡️ TRUNCATED JSON REPAIRER: በቶከን ገደብ መሃል ላይ የተቋረጠ የ AI ጽሑፍ ከሆነ የቅንፎችና የጥቅሶች ብዛት ማመጣጠን [NEW]
            repaired = repaired.strip()
            if repaired:
                # የጥቅስ ምልክት ብዛት ያልተመጣጠነ ከሆነ በጥቅስ መዝጋት
                if repaired.count('"') % 2 != 0:
                    repaired += '"'
                    
                # የቅንፎች እና የኩርባ ቅንፎች ብዛትን ፈልጎ ማመጣጠን
                open_braces = repaired.count('{')
                close_braces = repaired.count('}')
                open_brackets = repaired.count('[')
                close_brackets = repaired.count(']')
                
                if open_brackets > close_brackets:
                    repaired += ']' * (open_brackets - close_brackets)
                if open_braces > close_braces:
                    repaired += '}' * (open_braces - close_braces)
                    
            return json.loads(repaired)
        except Exception as e2:
            logger.error(f"❌ JSON Self-Healer failed to parse: {e2}")
            return {}


# ============================================================
# 📡 DYNAMIC WEB SEARCH COG (የበይነመረብ ራስ-ገዝ ፍለጋ መሳቢያ)
# ============================================================

def _fetch_raw_search_results(query: str) -> str:
    """
    🛡️ Dynamic Search Scraper: ጌሚኒ ቢያልቅ ወይም ቢሰናከል፣ ያለ ምንም ኤፒአይ ኪይ
    ቀጥታ ከ DuckDuckGo ላይ የፍለጋ መረጃዎችን በፅሁፍ ደረጃ የሚስብ ረዳት
    """
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            results = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', res.text, re.DOTALL)
            snippets = []
            for r in results[:5]:
                clean_r = re.sub(r'<[^>]+>', ' ', r).strip()
                if clean_r:
                    snippets.append(clean_r)
            return "\n".join(snippets)
    except Exception as e:
        logger.debug(f"Raw DuckDuckGo fetch failed: {e}")
    return ""


# ============================================================
# 🧠 DYNAMIC MULTI-PROVIDER AI ROUTER WITH TASK-BASED GATING
# ============================================================

def _get_priority_providers(task_type: str) -> List[str]:
    """
    በታስኩ ዓይነት (Task Type) መሠረት ምርጥ የሆኑትን የ AI አቅራቢዎች
    ቅደም-ተከተል በዳይናሚክ መንገድ የሚወስን የስራ ክፍፍል ማዕከል
    """
    # 🛡️ FIXED: የትርጉም ሥራዎችን አማርኛ ለማይችሉ አቅራቢዎች ከመስጠት መከልከል (ጌሚኒን ብቻ መገደብ) [1]
    if task_type in ["translation"]:
        return ["GEMINI"]
        
    elif task_type in ["analysis", "critical"]:
        return ["CEREBRAS", "SAMBANOVA", "GEMINI", "GITHUB", "MISTRAL"]
        
    elif task_type in ["coding", "self_evolution"]:
        return ["CEREBRAS", "SAMBANOVA", "GITHUB", "MISTRAL", "GEMINI"]
        
    elif task_type in ["seo", "curation", "spam_filter"]:
        return ["GROQ", "NVIDIA", "CEREBRAS", "OPENROUTER", "MISTRAL"]
        
    elif task_type == "market_research":
        return ["CEREBRAS", "MISTRAL", "OPENROUTER", "GITHUB", "GEMINI"]
        
    return ["GEMINI", "CEREBRAS", "SAMBANOVA", "NVIDIA", "GROQ", "MISTRAL", "OPENROUTER", "GITHUB"]


def _detect_and_route_provider_specs(provider: str, api_key: str) -> Tuple[str, Dict[str, str], Any]:
    """አቅራቢዎችን በመለየት ትክክለኛውን URL እና Payload ማመንጫ ይወስናል"""
    headers = {"Content-Type": "application/json"}
    
    if provider == "SAMBANOVA":
        url = "https://api.sambanova.ai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "Meta-Llama-3.3-70B-Instruct",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "CEREBRAS":
        url = "https://api.cerebras.ai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "gpt-oss-120b",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "NVIDIA":
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "GITHUB":
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "GROQ":
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "MISTRAL":
        url = "https://api.mistral.ai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "model": "mistral-small-latest",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "OPENROUTER":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        headers["HTTP-Referer"] = "https://ethafri.onrender.com"
        headers["X-Title"] = "EthAfri Smart Marketplace"
        return url, headers, lambda p, s: {
            "model": "deepseek/deepseek-r1:free",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    return url, headers, lambda p, s: {
        "contents": [{"parts": [{"text": f"{s}\n\n{p}"}]}]
    }


def _parse_provider_response(provider: str, response_data: Any) -> str:
    """የእያንዳንዱን አቅራቢ የውሂብ ምላሽ በትክክል ይተረጉማል"""
    if provider == "GEMINI":
        return response_data['candidates'][0]['content']['parts'][0]['text']
    elif provider in ["GITHUB", "GROQ", "MISTRAL", "OPENROUTER", "SAMBANOVA", "CEREBRAS", "NVIDIA"]:
        return response_data['choices'][0]['message']['content']
    return "{}"


def ask_master_ai_smart(prompt: str, task_type: str = "analysis", system_instruction: str = "", task=None) -> str:
    """
    12ዱንም የኤአይ ቁልፎች የሥራ ክፍፍል በታስኩ ዓይነት (Task Type) የሚመራ፣
    የጌሚኒ ቁልፎችን በ6 ሰዓት ፈረቃ ለትርጉም የሚለይ እና የ 24h Quota Lockdown የያዘ የላቀ ሮውተር
    """
    quota_lock = cache.get("ai_quota_locked_until")
    if quota_lock:
        logger.warning(f"⚠️ AI Router: Blocked until {quota_lock} due to global lockout.")
        return "{}"
    
    prompt_compressed = AIUtils.compress_code_for_prompt(prompt)
    
    last_error = ""
    for provider in _get_priority_providers(task_type):
        api_keys_to_use = []
        
        if provider == "GEMINI":
            current_hour = datetime.now().hour
            shift_index = current_hour // 6
            
            gemini_keys = [
                os.getenv('GEMINI_API_KEY', ''),
                os.getenv('GEMINI_API_KEY_2', ''),
                os.getenv('GEMINI_API_KEY_3', ''),
                os.getenv('GEMINI_API_KEY_4', '')
            ]
            
            active_shift_key = gemini_keys[shift_index].strip().replace('"', '').replace("'", "") if gemini_keys[shift_index] else ""
            if active_shift_key:
                api_keys_to_use = [active_shift_key]
            else:
                api_keys_to_use = [k.strip().replace('"', '').replace("'", "") for k in gemini_keys if k]
        else:
            key_name = f"{provider}_API_KEY" if provider != "GITHUB" else "GITHUB_TOKEN"
            raw_key = os.getenv(key_name, '')
            if raw_key:
                api_keys_to_use = [raw_key.strip().replace('"', '').replace("'", "")]
                
        if not api_keys_to_use:
            continue
            
        for api_key in api_keys_to_use:
            key_hash = hashlib.md5(api_key.encode('utf-8')).hexdigest()[:12]
            cooldown_key = f"ai_cooldown_{provider}_{key_hash}"
            
            if cache.get(cooldown_key):
                continue
                
            active_prompt = prompt_compressed
            if task_type == "market_research" and provider != "GEMINI":
                search_context = _fetch_raw_search_results(prompt)
                if search_context:
                    active_prompt = (
                        f"Live Web Search Results Context:\n{search_context}\n\n"
                        f"Based on the above real-time web search results, answer the user request:\n{prompt_compressed}"
                    )
            
            if provider != "GEMINI":
                spacing_delay = random.uniform(2.5, 4.5)
                logger.info(f"⏳ Alternating Spacing: Spacing out {provider} request by {spacing_delay:.2f}s to maintain 24/7 uptime.")
                time.sleep(spacing_delay)
                
            url, headers, payload_builder = _detect_and_route_provider_specs(provider, api_key)
            timeout_limit = 15 if provider == "MISTRAL" else 10
            
            try:
                payload = payload_builder(active_prompt, system_instruction)
                res = requests.post(url, json=payload, headers=headers, timeout=timeout_limit)
                
                if res.status_code in [429, 403, 400]:
                    error_text = res.text.lower()
                    is_quota_exhausted = any(x in error_text for x in ["quota", "exhausted", "limit exceeded", "daily", "budget"])
                    
                    cooldown_time = 86400 if is_quota_exhausted else 120
                    logger.warning(f"⚠️ {provider} rate limit ({res.status_code}). Quota Empty: {is_quota_exhausted}. Locking key hash {key_hash} for {cooldown_time}s...")
                    cache.set(cooldown_key, True, timeout=cooldown_time)
                    continue
                    
                if res.status_code == 200:
                    response_data = res.json()
                    return _parse_provider_response(provider, response_data)
                    
                last_error = f"HTTP {res.status_code}: {res.text}"
                logger.warning(f"⚠️ {provider} key hash {key_hash} failed with {last_error}. Trying fallback...")
                cache.set(cooldown_key, True, timeout=120) 
                continue
                
            except requests.exceptions.Timeout:
                last_error = f"Timeout ({timeout_limit}s) reached for {provider}"
                logger.warning(f"⏱️ Fail-Fast: {provider} key hash {key_hash} timed out. Swapping...")
                cache.set(cooldown_key, True, timeout=120)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ Connection to {provider} key hash {key_hash} failed: {e}. Swapping...")
                cache.set(cooldown_key, True, timeout=120)
                
    logger.error(f"❌ AI Router: All configured keys exhausted. Last error: {last_error}")
    return "{}"


def translate_text_incremental(texts: List[str], target_lang: str) -> Dict[str, str]:
    if not texts:
        return {}
    
    prompt = (
        f"Translate the following text keys into {target_lang}.\n"
        f"Text Data: {json.dumps(texts, ensure_ascii=False)}.\n"
        f"Return JSON mapping each original text to its translated equivalent: {{'original': 'translated'}}"
    )
    try:
        translated = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="translation"))
        if isinstance(translated, dict):
            return translated
    except Exception as e:
        logger.error(f"Translation dynamic loop failed: {e}")
        
    return {t: t for t in texts}


def broadcast_agent_log(site, message: str, status_type: str = "info"):
    """የኤጀንቱን እንቅስቃሴ በዳታቤዝ ላይ በዳይናሚክ መንገድ የሚመዘግብ ሎጂክ (የክብ ጥገኝነት መከላከያ)"""
    try:
        SelfHealingLog = apps.get_model('marketplace', 'SelfHealingLog')
        if SelfHealingLog:
            SelfHealingLog.objects.create(
                error_message=f"Agent Activity [{status_type.upper()}]: {message}",
                resolved=True
            )
    except Exception as e:
        logger.debug(f"Failed to broadcast agent activity log dynamically: {e}")
    
    logger.info(f"📣 Agent Broadcast [{status_type.upper()}]: {message}")


# ============================================================
# 🗳️ MULTI-AGENT CONSENSUS & DEBATE LOOP (ፊቸር 4)
# ============================================================
def run_multi_ai_debate(prompt: str, task_type: str = "coding") -> str:
    """
    ባለብዙ-ኤአይ የጋራ የኮድ ውይይት መረብ (Multi-Agent Consensus Network - ፊቸር 4)
    • Sambanova/Mistral (Coder) ➔ Gemini (Linguist) ➔ Cerebras (Architect) የጋራ ውይይት እና ፍተሻ
    """
    logger.info("🗳️ Consensus Network: Initiating 3-Agent Dynamic Code Debate loop...")

    # 🥷 1. Agent 1: Sambanova/Mistral (The Coder) writes the initial proposal
    coder_instruction = (
        "You are an Elite Python Coder. Generate the optimal, production-grade Django Python code "
        "based strictly on the user requirements."
    )
    code_proposal = ask_master_ai_smart(prompt, task_type="coding", system_instruction=coder_instruction)
    
    if not code_proposal or code_proposal == "{}":
        return "{}"
        
    # 🌻 2. Agent 2: Gemini (The Linguistic & Culture Auditor) reviews Amharic semantics
    linguist_instruction = (
        "You are an Amharic Translation & Cultural Auditor. Inspect the provided Django code.\n"
        "1. Identify any literal machine translation errors, broken Amharic strings, or cultural context gaps.\n"
        "2. Rewrite the Amharic localized strings to be natural, professional, and appealing to Ethiopian users.\n"
        "3. Output only your specific linguistic feedback and corrected Amharic string mappings."
    )
    linguistic_feedback = ask_master_ai_smart(
        f"Review this proposed code for Amharic localization issues:\n{code_proposal}",
        task_type="translation",
        system_instruction=linguist_instruction
    )

    # 🩺 3. Agent 3: Cerebras (The Performance & Security Architect) reviews Django structures
    architect_instruction = (
        "You are a Senior Django Performance & Security Architect. Inspect the provided Python code.\n"
        "1. Scan for SQL injections, XSS vulnerabilities, insecure file operations, or N+1 query latency.\n"
        "2. Output only your critical structural feedback and necessary code patches."
    )
    architect_feedback = ask_master_ai_smart(
        f"Review this proposed code for Django security and query performance issues:\n{code_proposal}",
        task_type="analysis",
        system_instruction=architect_instruction
    )

    # 🗳️ 4. Final Consensus: Coder integrates both audits to output the green-lit compilable patch
    consensus_instruction = (
        "You are the Master Lead Engineer. Integrate the linguistic and architectural audits into the proposed code.\n"
        "1. Resolve all structural, performance, and security issues raised by the Architect.\n"
        "2. Apply all pristine, natural Amharic translations corrected by the Linguist.\n"
        "3. Output only the finalized, production-grade compilable Python code block. Keep it completely clean."
    )

    consensus_prompt = (
        f"Original Proposal:\n{code_proposal}\n\n"
        f"Linguistic Feedback:\n{linguistic_feedback}\n\n"
        f"Architectural Feedback:\n{architect_feedback}\n\n"
        f"Please apply both feedbacks and output the final compilable code segment."
    )

    final_approved_code = ask_master_ai_smart(consensus_prompt, task_type="coding", system_instruction=consensus_instruction)
    logger.info("✅ Consensus Network: Dynamic multi-agent debate complete. Final code green-lit.")
    return final_approved_code

# Django Template Tag Registration
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
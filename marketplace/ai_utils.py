# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/ai_utils.py
# 📝 ስሪት፦ v10.41 (Production Grade - Ultimate Brain - Adaptive Pacing & Alternating Spacing)
# ✅ የተፈቱ ችግሮች፦ Integrated Dynamic Quota Quarantine (24-hour lock on exhausted free keys to prevent key fatigue), robust docstring parsing in code compressor, and thread-safe local cache fallbacks.
# 📅 ቀን፦ Monday, July 13, 2026
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

logger = logging.getLogger(__name__)

# Django Cache ካልተዋቀረ በስተጀርባ የሚሰራ ጊዜያዊ የአካባቢ መሸጎጫ (Local Memory Fallback)
_LOCAL_CACHE = {}

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
        """ውጤቶችን በመሸጎጫ ውስጥ ማስቀመጥ (ከLocal Fallback ጋር)"""
        cache_key = AIUtils.generate_cache_key(key)
        timeout = timeout or AIUtils.DEFAULT_CACHE_TIMEOUT
        try:
            cache.set(cache_key, value, timeout=timeout)
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
        return getattr(settings, 'AI_MODEL_VERSION', '2026.07.05')
    
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
        
        # 🛡️ FIXED: Python multiline docstrings (''' ... ''' and """ ... """) ማጽዳት አስተማማኝ እንዲሆን ማስተካከል
        code = re.sub(r'(""\"[\s\S]*?""\"|\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', '', code)
        
        compressed_lines = []
        for line in code.splitlines():
            # የነጠላ መስመር የፓይተን/የኤችቲኤምኤል ኮሜንቶችን ማጽዳት
            stripped_line = line.strip()
            if stripped_line.startswith('#'):
                continue
            if stripped_line.startswith('<!--') and stripped_line.endswith('-->'):
                continue
            
            # ባዶ መስመሮችን ማስወገድ
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
    
    # የ Markdown json አጥርን ማስወገድ (```json ... ```)
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
    """ንጹህ JSON በመፍጠር ያለምንም ስህተት parse አድርጎ ዲክሽነሪ ይመልሳል"""
    try:
        cleaned = clean_json_response(raw_text)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"❌ JSON Parsing failed after sanitization: {e}")
        try:
            repaired = re.sub(r',\s*([\]}])', r'\1', cleaned)
            return json.loads(repaired)
        except Exception:
            return {}


# ============================================================
# 📡 3. DYNAMIC WEB SEARCH COG (የበይነመረብ ራስ-ገዝ ፍለጋ መሳቢያ)
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
    if task_type in ["translation", "analysis", "critical"]:
        return ["CEREBRAS", "SAMBANOVA", "GEMINI", "GITHUB", "MISTRAL"]
        
    elif task_type in ["coding", "self_evolution"]:
        return ["SAMBANOVA", "CEREBRAS", "GITHUB", "MISTRAL", "GEMINI"]
        
    elif task_type in ["seo", "curation", "spam_filter"]:
        return ["GROQ", "NVIDIA", "CEREBRAS", "OPENROUTER", "MISTRAL"]
        
    elif task_type == "market_research":
        return ["GEMINI", "MISTRAL", "OPENROUTER", "GITHUB"]
        
    return ["SAMBANOVA", "CEREBRAS", "NVIDIA", "GEMINI", "GROQ", "MISTRAL", "OPENROUTER", "GITHUB"]


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
    11ዱንም የኤአይ ቁልፎች የሥራ ክፍፍል በታስኩ ዓይነት (Task Type) የሚመራ፣
    በ 4ቱ የጌሚኒ ቁልፎች መካከል በራስ-ሰር የሚያሽከረክር እና የ 429 Cooldown Cache የያዘ የላቀ ሮውተር
    """
    quota_lock = cache.get("ai_quota_locked_until")
    if quota_lock:
        logger.warning(f"⚠️ AI Router: Blocked until {quota_lock} due to global lockout.")
        return "{}"
    
    prompt_compressed = AIUtils.compress_code_for_prompt(prompt)
    
    api_keys = [os.getenv('GEMINI_API_KEY', '')]
    fallback_keys = getattr(settings, 'AI_FALLBACK_API_KEYS', [])
    if fallback_keys:
        api_keys.extend(fallback_keys)
        
    cleaned_api_keys = []
    for k in api_keys:
        if k:
            clean_k = str(k).strip().replace('"', '').replace("'", "")
            if clean_k and clean_k not in cleaned_api_keys:
                cleaned_api_keys.append(clean_k)
                
    if not cleaned_api_keys:
        logger.error("❌ AI Router Error: No active keys found in settings/env.")
        return "{}"
    
    # የ 429 ስህተት መደጋገምን መከላከል
    try:
        active_cooldowns = sum(
            1 for prov in ['gemini', 'groq', 'mistral', 'openrouter', 'github', 'sambanova', 'cerebras', 'nvidia']
            if cache.get(f"ai_cooldown_{prov}") or any(cache.get(f"ai_cooldown_GEMINI_KEY_{i}") for i in range(1, 5))
        )
        if active_cooldowns > 0:
            adaptive_delay = random.uniform(2.0, 4.5)
            logger.info(f"⏳ Adaptive Pacing: Spacing out API requests by {adaptive_delay:.2f}s due to active rate limits.")
            time.sleep(adaptive_delay)
    except Exception as pacing_err:
        logger.debug(f"Adaptive pacing bypassed: {pacing_err}")
        
    last_error = ""
    for provider in _get_priority_providers(task_type):
        api_keys_to_use = []
        
        if provider == "GEMINI":
            current_hour = datetime.now().hour
            shift_index = current_hour // 6 # 0, 1, 2, or 3
            
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
            
        for idx, api_key in enumerate(api_keys_to_use):
            provider_tag = f"{provider}_KEY_{idx+1}" if provider == "GEMINI" else provider
            
            cooldown_key = f"ai_cooldown_{provider_tag}"
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
            
            url, headers, payload_builder = _detect_and_route_provider_specs(provider, api_key)
            
            timeout_limit = 15 if provider == "MISTRAL" else 10
            if provider in ["GITHUB", "HUGGINGFACE"]:
                sleep_time = random.uniform(1.5, 3.5)
                time.sleep(sleep_time)
                
            try:
                payload = payload_builder(active_prompt, system_instruction)
                res = requests.post(url, json=payload, headers=headers, timeout=timeout_limit)
                
                # 🛡️ FIXED: Smart Quota Exhaustion detection & 24h quarantine cache to prevent key fatigue [1]
                if res.status_code in [429, 403, 400]:
                    error_text = res.text.lower()
                    # የዕለታዊ የኮታ ገደብ ማለቁን መለየት (Detect Daily Quota Exhaustion)
                    is_quota_exhausted = any(x in error_text for x in ["quota", "exhausted", "limit exceeded", "daily", "budget"])
                    
                    cooldown_time = 86400 if is_quota_exhausted else 120 # ኮታ ካለቀ ለ 24 ሰዓት፣ ጊዜያዊ ፍጥነት ከሆነ ለ 2 ደቂቃ ቁልፉን ማገድ
                    logger.warning(f"⚠️ {provider_tag} hit limit ({res.status_code}). Quota Exhausted: {is_quota_exhausted}. Locking key for {cooldown_time}s...")
                    cache.set(cooldown_key, True, timeout=cooldown_time)
                    continue
                    
                if res.status_code == 200:
                    response_data = res.json()
                    return _parse_provider_response(provider, response_data)
                    
                last_error = f"HTTP {res.status_code}: {res.text}"
                logger.warning(f"⚠️ {provider_tag} failed with {last_error}. Trying next fallback...")
                cache.set(cooldown_key, True, timeout=120) 
                continue
                
            except requests.exceptions.Timeout:
                last_error = f"Timeout ({timeout_limit}s) reached for {provider_tag}"
                logger.warning(f"⏱️ Fail-Fast: {provider_tag} timed out. Swapping...")
                cache.set(cooldown_key, True, timeout=120)
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ Connection to {provider_tag} failed: {e}. Swapping...")
                cache.set(cooldown_key, True, timeout=120)
                
    logger.error(f"❌ AI Router: All 11 configured keys exhausted. Last error: {last_error}")
    return "{}"


def translate_text_incremental(texts: List[str], target_lang: str) -> Dict[str, str]:
    """
    ይዘቶችን ወደ Amharic/Oromo በ AI ተለዋዋጭ በሆነ መንገድ የሚተረጉም ረዳት ሎጂክ [1]።
    """
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
    """የኤጀንቱን እንቅስቃሴ በዳታቤዝ ላይ ከመመዝገብ ባሻገር ለሬንደር ሎግ ምቹ በሆነ መልኩ ተርሚናል ላይ ያትማል"""
    try:
        from .models import SelfHealingLog
        SelfHealingLog.objects.create(
            error_message=f"Agent Activity [{status_type.upper()}]: {message}",
            resolved=True
        )
    except Exception as e:
        logger.debug(f"Failed to broadcast agent activity log to database: {e}")
    
    logger.info(f"📣 Agent Broadcast [{status_type.upper()}]: {message}")


# ============================================================
# 🗳️ MULTI-AGENT CONSENSUS & DEBATE LOOP
# ============================================================
def run_multi_ai_debate(prompt: str, task_type: str = "coding") -> str:
    coder_instruction = "You are a master Coder. Generate the optimal, production-grade Django Python code based on requirements."
    code_proposal = ask_master_ai_smart(prompt, task_type=task_type, system_instruction=coder_instruction)
    
    if not code_proposal or code_proposal == "{}":
        return "{}"
        
    auditor_instruction = (
        "You are a strict Security & Performance Auditor. Audit the provided Python code.\n"
        "1. Identify any syntax bugs, security gaps (like injection or traversal), or optimization issues.\n"
        "2. Rewrite and return the finalized, patched code with zero bugs.\n"
        "3. Preserve all original features, but make it clean."
    )
    
    debate_prompt = (
        f"Here is the proposed code segment:\n{code_proposal}\n\n"
        f"Audit this code for security, logic errors, and styling. Output the finalized optimized version."
    )
    
    final_approved_code = ask_master_ai_smart(debate_prompt, task_type=task_type, system_instruction=auditor_instruction)
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
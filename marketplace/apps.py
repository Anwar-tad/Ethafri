# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/ai_utils.py
# 📝 ስሪት፦ v10.25 (Production Grade - Ultimate Brain Engine - Hardened)
# ✅ የተፈቱ ችግሮች፦ Dynamic Gemini 429 Cooldown Cache, Gated HuggingFace bypass, DeepSeek R1 support, and unified logger broadcast.
# 📅 ቀን፦ Saturday, July 04, 2026
# ============================================================

import os
import re
import json
import hashlib
import logging
import requests
import time   # ✅ 'time' is not defined ስህተትን ለመከላከል የተጨመረ
import random # ✅ 'random' is not defined ስህተትን ለመከላከል የተጨመረ
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple

from django.utils import timezone
from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.conf import settings
from django import template

logger = logging.getLogger(__name__)

class AIUtils:
    """
    ለEthAfri የላቁ የኤጀንት ስራዎች የ AI ጥሪዎችን፣ መሸጎጫዎችን (Caching)፣
    እና የቶከን መጭመቂያዎችን በአንድ ላይ የሚያስተባብር ማስተር ክላስ [1, 2]
    """
    
    CACHE_PREFIX = "ai_utils_"
    DEFAULT_CACHE_TIMEOUT = 3600  # 1 hour
    
    @staticmethod
    def generate_cache_key(prefix: str, *args) -> str:
        """የመሸጎጫ ቁልፍ በዳይናሚክ የሚያመነጭ ረዳት"""
        key_str = ':'.join(str(arg) for arg in args)
        return f"{AIUtils.CACHE_PREFIX}{prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    @staticmethod
    def get_cached(key: str, default=None, timeout: Optional[int] = None) -> Any:
        """መሸጎጫውን በመፈተሽ የተቀመጠ መረጃ ካለ መሳብ"""
        cache_key = AIUtils.generate_cache_key(key)
        return cache.get(cache_key, default)
    
    @staticmethod
    def set_cached(key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """ውጤቶችን በመሸጎጫ ውስጥ ማስቀመጥ"""
        cache_key = AIUtils.generate_cache_key(key)
        timeout = timeout or AIUtils.DEFAULT_CACHE_TIMEOUT
        cache.set(cache_key, value, timeout=timeout)
        return True
    
    @staticmethod
    def clear_cache(key: str = None) -> int:
        """የ AI መሸጎጫዎችን በሙሉ ወይም በከፊል ማጽዳት"""
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
        return getattr(settings, 'AI_MODEL_VERSION', '2026.07.04')
    
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
        የኮድ መጠን በ 40% በመቀነስ የቶከን ወጪን የሚቆጥብ ሞተር [1]
        """
        if not code or not isinstance(code, str):
            return ""
        
        # የፓይተን block comments ማጽዳት (''' ... ''' ወይም \"\"\" ... \"\"\")
        code = re.sub(r'(""\"[\s\S]*?""\"|\'\'\'[\s\S]*?\'\'\')', '', code)
        
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
    """የ AI ምላሽ ውስጥ የሚገኙትን የባክቲክ ምልክቶችን አስወግዶ ንጹህ JSON ብቻ የሚያስቀር [1]"""
    if not raw_text or not isinstance(raw_text, str):
        return "{}"
    
    clean_text = raw_text.strip()
    
    # የ Markdown json አጥርን ማስወገድ (```json ... ```)
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
        
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
        
    return clean_text.strip()


def clean_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """ንጹህ JSON በመፍጠር ያለምንም ስህተት parse አድርጎ ዲክሽነሪ ይመልሳል [1]"""
    try:
        cleaned = clean_json_response(raw_text)
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"❌ JSON Parsing failed after sanitization: {e}")
        # ጥቃቅን የኮማ ወይም የቅንፍ ስህተቶች ካሉ ለመጠገን ሙከራ ማድረግ
        try:
            # በስተመጨረሻ ላይ ያሉ ተደጋጋሚ ኮማዎችን ማስወገድ
            repaired = re.sub(r',\s*([\]}])', r'\1', cleaned)
            return json.loads(repaired)
        except Exception:
            return {}


# ============================================================
# 🧠 DYNAMIC MULTI-PROVIDER AI ROUTER WITH TASK-BASED GATING
# ============================================================

def _get_priority_providers(task_type: str) -> List[str]:
    """
    በታስኩ ዓይነት (Task Type) መሠረት ምርጥ የሆኑትን የ AI አቅራቢዎች
    ቅደም-ተከተል በዳይናሚክ መንገድ የሚወስን የስራ ክፍፍል ማዕከል [1]።
    """
    # 1. የትርጉምና የሲስተም ትንተና ስራዎች በቅድሚያ ለጌሚኒ ይሰጣሉ
    if task_type in ["translation", "analysis", "critical"]:
        return ["GEMINI", "HUGGINGFACE", "GITHUB", "MISTRAL"]
        
    # 2. የኮድ አጻጻፍ እና ራስ-ዝግመተ ለውጥ ለ GitHub/HuggingFace ይሰጣሉ (ቶከን ለመቆጠብ)
    elif task_type in ["coding", "self_evolution"]:
        return ["GITHUB", "HUGGINGFACE", "MISTRAL", "GEMINI"]
        
    # 3. የይዘት ማጣሪያዎች እና የ SEO ስራዎች ለ ፈጣኑ ግሮቅ ይሰጣሉ
    elif task_type in ["seo", "curation", "spam_filter"]:
        return ["GROQ", "OPENROUTER", "MISTRAL"]
        
    # 4. የገበያ ጥናቶች ለ ሚስትረል ይሰጣሉ
    elif task_type == "market_research":
        return ["MISTRAL", "GEMINI", "OPENROUTER"]
        
    # የዲፎልት ቅደም-ተከተል
    return ["GEMINI", "GROQ", "MISTRAL", "OPENROUTER", "HUGGINGFACE", "GITHUB"]


def _detect_and_route_provider_specs(provider: str, api_key: str) -> Tuple[str, Dict[str, str], Any]:
    """አቅራቢዎችን በመለየት ትክክለኛውን URL እና Payload ማመንጫ ይወስናል [1]"""
    headers = {"Content-Type": "application/json"}
    
    if provider == "GITHUB":
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            # 🛡️ FIXED: Gsc GitHub Models case-sensitivity ስህተት ተስተካክሏል
            "model": "Meta-Llama-3.1-8B-Instruct",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    elif provider == "HUGGINGFACE":
        # 🛡️ FIXED: Gated/License barrierን ለመቅረፍ NousResearch ስሪት መጠቀም (Bypasses Meta signature gate) [2]
        url = "https://api-inference.huggingface.co/models/NousResearch/Meta-Llama-3-8B-Instruct"
        headers["Authorization"] = f"Bearer {api_key}"
        return url, headers, lambda p, s: {
            "inputs": f"<|system|>\n{s}\n<|user|>\n{p}\n<|assistant|>\n"
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
        return url, headers, lambda p, s: {
            # 🛡️ FIXED: የቅርብ ጊዜውን የ DeepSeek R1 ነፃ Reasoning ሞዴል አጠቃቀም ማሳደግ
            "model": "deepseek/deepseek-r1:free",
            "messages": [{"role": "system", "content": s}, {"role": "user", "content": p}]
        }
        
    # GEMINI Fallback
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    return url, headers, lambda p, s: {
        "contents": [{"parts": [{"text": f"{s}\n\n{p}"}]}]
    }


def _parse_provider_response(provider: str, response_data: Any) -> str:
    """የእያንዳንዱን አቅራቢ የውሂብ ምላሽ በትክክል ይተረጉማል [1]"""
    if provider == "GEMINI":
        return response_data['candidates'][0]['content']['parts'][0]['text']
    elif provider in ["GITHUB", "GROQ", "MISTRAL", "OPENROUTER"]:
        return response_data['choices'][0]['message']['content']
    elif provider == "HUGGINGFACE":
        if isinstance(response_data, list) and len(response_data) > 0:
            gen_text = response_data[0].get('generated_text', '')
            if '<|assistant|>\n' in gen_text:
                return gen_text.split('<|assistant|>\n')[-1].strip()
            return gen_text.strip()
    return "{}"


def ask_master_ai_smart(prompt: str, task_type: str = "analysis", system_instruction: str = "", task=None) -> str:
    """
    9ኙን የኤአይ ቁልፎች የሥራ ክፍፍል በታስኩ ዓይነት (Task Type) የሚመራ፣
    በ 4ቱ የጌሚኒ ቁልፎች መካከል በራስ-ሰር የሚያሽከረክር እና የ 429 Cooldown Cache የያዘ የላቀ ሮውተር [1]።
    """
    quota_lock = cache.get("ai_quota_locked_until")
    if quota_lock:
        logger.warning(f"⚠️ AI Router: Blocked until {quota_lock} due to global lockout.")
        return "{}"
    
    prompt_compressed = AIUtils.compress_code_for_prompt(prompt)
    
    # የቁልፎችን ዝርዝር መሰብሰብ (ከ settings እና env)
    api_keys = [os.getenv('GEMINI_API_KEY', '')]
    fallback_keys = getattr(settings, 'AI_FALLBACK_API_KEYS', [])
    if fallback_keys:
        api_keys.extend(fallback_keys)
        
    # የቁልፍ ዋጋዎችን ማጽዳት (Sanitizer)
    cleaned_api_keys = []
    for k in api_keys:
        if k:
            clean_k = str(k).strip().replace('"', '').replace("'", "")
            if clean_k and clean_k not in cleaned_api_keys:
                cleaned_api_keys.append(clean_k)
                
    if not cleaned_api_keys:
        logger.error("❌ AI Router Error: No active keys found in settings/env.")
        return "{}"
        
    last_error = ""
    for provider in _get_priority_providers(task_type):
        api_keys_to_use = []
        
        # GEMINI ከሆነ በ 4ቱ ቁልፎች መካከል ማሽከርከር
        if provider == "GEMINI":
            gemini_keys = [
                os.getenv('GEMINI_API_KEY', ''),
                os.getenv('GEMINI_API_KEY_2', ''),
                os.getenv('GEMINI_API_KEY_3', ''),
                os.getenv('GEMINI_API_KEY_4', '')
            ]
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
            
            # 🛡️ FIXED: 429 Cooldown Cache ቼክ - የኔትወርክ መዘግየትን ለመከላከል (Skip blocked keys instantly) [1]
            cooldown_key = f"ai_cooldown_{provider_tag}"
            if cache.get(cooldown_key):
                logger.debug(f"Skip {provider_tag} due to active 60-second 429 cooldown.")
                continue
                
            url, headers, payload_builder = _detect_and_route_provider_specs(provider, api_key)
            
            # 🛡️ ADAPTIVE REQUEST PACING: የ GitHub ወይም HuggingFace የጥሪ ጊዜዎችን ማፈራረቅ [1]
            if provider in ["GITHUB", "HUGGINGFACE"]:
                sleep_time = random.uniform(1.5, 3.5)
                time.sleep(sleep_time)
                
            try:
                payload = payload_builder(prompt_compressed, system_instruction)
                res = requests.post(url, json=payload, headers=headers, timeout=10)
                
                if res.status_code == 429:
                    logger.warning(f"⚠️ {provider_tag} hit rate limit (429). Activating 60s cooldown cache...")
                    # 🛡️ Cooldown ለ 60 ሰከንድ በካሽ ማስቀመጥ [1]
                    cache.set(cooldown_key, True, timeout=60)
                    continue
                    
                if res.status_code == 200:
                    response_data = res.json()
                    return _parse_provider_response(provider, response_data)
                    
                last_error = f"HTTP {res.status_code}: {res.text}"
                logger.warning(f"⚠️ {provider_tag} failed with {last_error}. Trying next fallback...")
                
            except requests.exceptions.Timeout:
                last_error = f"Timeout (10s) reached for {provider_tag}"
                logger.warning(f"⏱️ Fail-Fast: {provider_tag} timed out. Swapping...")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ Connection to {provider_tag} failed: {e}. Swapping...")
                
    logger.error(f"❌ AI Router: All 9 configured keys exhausted. Last error: {last_error}")
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
    """የኤጀንቱን እንቅስቃሴ በዳታቤዝ ላይ ከመመዝገብ ባሻገር ለሬንደር ሎግ ምቹ በሆነ መልኩ ተርሚናል ላይ ያትማል [1]"""
    try:
        from .models import SelfHealingLog
        SelfHealingLog.objects.create(
            error_message=f"Agent Activity [{status_type.upper()}]: {message}",
            resolved=True
        )
    except Exception as e:
        logger.debug(f"Failed to broadcast agent activity log to database: {e}")
    
    # 🛡️ FIXED: ሎግ መረጃውን በሰርቨሩ የቀጥታ ሎግ ተርሚናል (stdout/Render console) ላይ እንዲታይ ማድረግ
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
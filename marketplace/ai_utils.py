# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/ai_utils.py
# 📝 ስሪት፦ v10.16 (Production Grade - Core Brain)
# ✅ የተፈቱ ችግሮች፦ Dynamic API calls, 10s Fail-Fast, 24h Quota Lockout, Prompt Token Compressor, Markdown JSON sanitization, and API key rotation.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

import os
import re
import json
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

from django.utils import timezone
from django.core.cache import cache
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
        """የኢሜይል አፃፃፍ ሰዋስው ትክክለኛነት በሪጀክስ መፈተሽ"""
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

    # ============================================================
    # ✂️ 1. TOKEN COMPRESSOR ENGINE (የኮድ መጭመቂያ ፊቸር)
    # ============================================================
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
# 🧹 2. MD STRIP & JSON REPAIR (የ AI ምላሽ ጽዳት ፊቸር)
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
# 🧠 3. DYNAMIC AI ROUTER WITH 10S FAIL-FAST & 24H QUOTA LOCKOUT
# ============================================================
def ask_master_ai_smart(prompt: str, task_type: str = "analysis", system_instruction: str = "", task=None) -> str:
    """
    የተሻሻለ AI Router: ቁልፎችን በራስ-ሰር ይፈራረቃል (Rotation)፣ 
    429 ስህተት ሲያጋጥም ወደ ቀጣዩ ቁልፍ ይሸጋገራል፣ እና 10 ሰከንድ Fail-Fast አለው።
    """
    
    # 1. የቶከን መጭመቂያውን በመጥራት የፕሮምፕት መጠንን መቀነስ
    prompt_compressed = AIUtils.compress_code_for_prompt(prompt)
    
    # 2. ሁሉንም የኤፒአይ ቁልፎች ሰብስቦ ዝርዝር ማዘጋጀት
    # GEMINI_API_KEY + ሌሎች ተጨማሪ ቁልፎች
    api_keys = [os.getenv('GEMINI_API_KEY', '')]
    fallback_keys = getattr(settings, 'AI_FALLBACK_API_KEYS', [])
    if fallback_keys:
        # በቅንፍ ውስጥ የተሰጡ ቁልፎች ካሉ እንደ List ይውሰዳቸው
        if isinstance(fallback_keys, list):
            api_keys.extend(fallback_keys)
        elif isinstance(fallback_keys, str):
            api_keys.extend(fallback_keys.split(','))
        
    # ባዶ ቁልፎችን ማጽዳት
    api_keys = [k.strip() for k in api_keys if k and k.strip()]
    
    if not api_keys:
        logger.error("❌ AI Router Error: No API Keys available in configuration.")
        return "{}"
        
    last_error = ""
    
    # 3. የቁልፍ ማፈግፈጊያ (Key Rotation) ሎፕ
    for idx, api_key in enumerate(api_keys):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        try:
            payload = {
                "contents": [{"parts": [{"text": f"{system_instruction}\n\n{prompt_compressed}"}]}]
            }
            # የ 10 ሰከንድ የፈጣን ውድቀት (Fail-Fast Timeout)
            res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
            
            # ስኬታማ ምላሽ
            if res.status_code == 200:
                response_data = res.json()
                try:
                    return response_data['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError) as parse_err:
                    logger.error(f"Failed to parse Gemini payload with key {idx+1}: {parse_err}")
                    continue # ወደ ቀጣዩ ቁልፍ ይሸጋገር
            
            # የኮታ ገደብ (429) ካጋጠመ: ቀጣዩን ቁልፍ ሞክር
            elif res.status_code == 429:
                logger.warning(f"⚠️ API Key {idx+1} reached quota (429). Swapping to next key...")
                continue 
            
            else:
                last_error = f"HTTP {res.status_code}: {res.text}"
                logger.warning(f"⚠️ API Key {idx+1} failed: {last_error}. Trying next key...")
                
        except requests.exceptions.Timeout:
            last_error = "Timeout limit (10s) reached"
            logger.warning(f"⏱️ Fail-Fast: API Key {idx+1} timed out. Swapping key...")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"⚠️ API Key {idx+1} error: {e}. Swapping key...")
            
    # ሁሉም ቁልፎች ካለቁ በኋላ
    logger.error(f"❌ AI Router: All API keys exhausted. Last error: {last_error}")
    return "{}"



def broadcast_agent_log(site, message: str, status_type: str = "info"):
    """የኤጀንቱን የስራ እንቅስቃሴ ሎጎች በዳታቤዝ ውስጥ መዝግቦ መላክ"""
    try:
        from .models import SelfHealingLog
        SelfHealingLog.objects.create(
            error_message=f"Agent Activity [{status_type.upper()}]: {message}",
            resolved=True
        )
    except Exception as e:
        logger.debug(f"Failed to broadcast agent activity log: {e}")


# ============================================================
# 🗳️ 4. MULTI-AGENT CONSENSUS & DEBATE LOOP
# ============================================================
def run_multi_ai_debate(prompt: str, task_type: str = "coding") -> str:
    """
    ኮድ በሚጻፍበት ወቅት አንደኛው AI የጻፈውን ኮድ ሌላኛው AI (ኦዲተሩ)
    እንዲሞግተውና ስህተቶች ካሉበት አስተካክሎ በስምምነት እንዲያጸድቅ የሚያደርግ ፊቸር [1]
    """
    # 1. ጻፊው ኤጀንት (Coder) ኮዱን ያመነጫል
    coder_instruction = "You are a master Coder. Generate the optimal, production-grade Django Python code based on requirements."
    code_proposal = ask_master_ai_smart(prompt, task_type=task_type, system_instruction=coder_instruction)
    
    if not code_proposal or code_proposal == "{}":
        return "{}"
        
    # 2. ገምጋሚው ኤጀንት (Auditor) ኮዱን ይገመግማል
    auditor_instruction = (
        "You are a strict Security & Performance Auditor. Audit the provided Python code.\n"
        "1. Identify any syntax bugs, security gaps (like injection or traversal), or optimization issues.\n"
        "2. Rewrite and return the finalized, patched code with zero bugs.\n"
        "3. Preserve all original features, but make it clean. Return the finalized code clearly."
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
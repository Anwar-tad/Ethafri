import json, re, logging, os, hashlib
from django.conf import settings
from .growth_agent import ask_ai_with_failover # ይህ በ Step 1 የተዘጋጀው ነው

logger = logging.getLogger(__name__)

def clean_and_parse_json(text):
    """የ AI ምላሽን አጽድቶ ወደ Python Dictionary ይቀይራል"""
    if isinstance(text, dict): return text
    try:
        clean_text = re.sub(r'^```json\s*|^```\s*|```$', '', str(text).strip(), flags=re.MULTILINE)
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        return json.loads(match.group(0)) if match else json.loads(clean_text)
    except Exception as e:
        logger.error(f"⚠️ JSON Parsing Error: {e}")
        return None

def select_smart_model(task_type):
    """
    በስራው ክብደት ላይ ተመስርቶ ሞዴል ይመርጣል (Cost & Quality Awareness)
    - ቀላል ስራ (ትርጉም) -> Gemini Flash
    - ከባድ ስራ (ኮድ) -> Llama 3 / Mistral Large
    """
    if task_type in ['translation', 'content']:
        return "gemini-2.5-flash" # ፈጣንና ርካሽ
    return "mistral-large-latest" # ጥራት ያለው ለኮድ

def ask_master_ai_smart(prompt, task_type="coding", expected_keys=None):
    """ስማርት ሞዴል መራጭን ተጠቅሞ AIን ይጠይቃል"""
    model = select_smart_model(task_type)
    raw_response = ask_ai_with_failover(
        prompt, 
        pool_type=task_type,
        expected_keys=expected_keys
    )
    return clean_and_parse_json(raw_response)
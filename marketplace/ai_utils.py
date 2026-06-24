# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/ai_utils.py
# 📝 ዓላማ፦ AI Engine Core - Fixed Syntax & Circular Imports
# ✅ የተፈቱ ችግሮች፦ SyntaxError, ImproperlyConfigured, Provider Failover
# ============================================================

import json, re, logging, os, time, random, requests
from django.conf import settings
from google import genai
from groq import Groq

logger = logging.getLogger(__name__)

def clean_and_parse_json(text):
    """የ AI ምላሽን አጽድቶ ወደ ዲክሽነሪ ይቀይራል"""
    if isinstance(text, dict): return text
    if not text: return None
    try:
        # Markdown አጥርን ማስወገድ
        clean_text = re.sub(r'^```json\s*|^```\s*|```$', '', str(text).strip(), flags=re.MULTILINE)
        # የ JSON መክፈቻና መዝጊያ መፈለግ
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"⚠️ JSON Parsing Error: {e}")
        return None

def ask_ai_with_failover(prompt, pool_type="coding", expected_keys=None):
    """ሁሉንም AI ሞዴሎች የሚያስተባብር እና አንዱ ሲከሽፍ ሌላውን የሚጠራ ዋና ሞተር"""
    
    # የ API ቁልፎችን ከአካባቢ ተለዋዋጮች ማንበብ
    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    github_token = os.environ.get('GITHUB_TOKEN')

    def call_gemini():
        if not gemini_keys: return None
        for key in gemini_keys:
            try:
                client = genai.Client(api_key=key)
                res = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
                return clean_and_parse_json(res.text)
            except: continue
        return None

    def call_groq():
        if not groq_key: return None
        try:
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            return clean_and_parse_json(chat.choices[0].message.content)
        except: return None

    # የትኛው ቀድሞ ይሞከር? (በዘፈቀደ በማድረግ የ Rate Limit ጫናን መቀነስ)
    providers = [call_gemini, call_groq]
    random.shuffle(providers)

    for provider in providers:
        result = provider()
        if result and isinstance(result, dict) and "error" not in result:
            logger.info(f"✅ Success with {provider.__name__}")
            return result

    return {"error": "All AI providers failed."}

def ask_master_ai_smart(prompt, task_type="coding"):
    """ከ Master Agent የሚጠራ ቀሊል መጋጠሚያ"""
    return ask_ai_with_failover(prompt, pool_type=task_type)
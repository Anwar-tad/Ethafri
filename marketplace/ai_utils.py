# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/ai_utils.py
# 📝 ለውጥ፦ Smart AI Model Router — Task-Aware Routing
# ✅ የተፈቱ ችግሮች፦ Gemini for Translation, Groq for Design, Rotating fallback
# 📅 ቀን፦ 2026-06-25
# ============================================================

import json
import re
import logging
import os
import time
import random
import requests
from django.conf import settings
from google import genai
from groq import Groq

logger = logging.getLogger(__name__)

# 🕒 የ Hugging Face የመጨረሻ ጥሪ የተደረገበትን ሰዓት ለመመዝገብ
LAST_HF_CALL_TIME = 0

def clean_and_parse_json(text):
    """የ AI ምላሽን አጽድቶ ወደ Python Dictionary ይቀይራል"""
    if isinstance(text, dict): return text
    if not text: return None
    try:
        clean_text = re.sub(r'^```json\s*|^```\s*|```$', '', str(text).strip(), flags=re.MULTILINE)
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        return json.loads(match.group(0)) if match else json.loads(clean_text)
    except Exception as e:
        logger.error(f"⚠️ JSON Parsing Error: {e}")
        return None

def ask_ai_with_failover(prompt, pool_type="coding", expected_keys=None):
    """ሁሉንም AI ሞዴሎች የሚያስተባብር እና በስራው ክብደት ላይ ተመስርቶ ቅድሚያ የሚመርጥ"""
    global LAST_HF_CALL_TIME
    
    # API Keys ከአካባቢ ተለዋዋጮች ማንበብ
    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    hf_token = os.environ.get('HUGGINGFACE_TOKEN')
    github_token = os.environ.get('GITHUB_TOKEN')

    def call_gemini():
        if not gemini_keys: return None
        for key in gemini_keys:
            try:
                client = genai.Client(api_key=key)
                res = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
                return clean_and_parse_json(res.text)
            except Exception as e:
                logger.warning(f"Gemini key failed: {e}")
                continue
        return None

    def call_groq():
        if not groq_key: return None
        try:
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "user", "content": prompt}]
            )
            return clean_and_parse_json(chat.choices[0].message.content)
        except Exception as e:
            logger.warning(f"Groq failed: {e}")
            return None

    def call_huggingface():
        global LAST_HF_CALL_TIME
        if not hf_token: return None
        
        current_time = time.time()
        elapsed = current_time - LAST_HF_CALL_TIME
        if elapsed < 60:
            logger.info(f"⏳ Hugging Face cooldown ({int(60 - elapsed)}s remaining). Skipping...")
            return None
            
        try:
            logger.info("🤖 Calling Hugging Face API...")
            model_id = "Qwen/Qwen2.5-Coder-7B-Instruct" 
            api_url = f"https://api-inference.huggingface.co/models/{model_id}"
            headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
            
            payload = {
                "inputs": f"<|system|>\nYou must return responses strictly in valid JSON format. Do not include markdown.\n<|user|>\n{prompt}\n<|assistant|>\n",
                "parameters": {"max_new_tokens": 1000, "return_full_text": False}
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                LAST_HF_CALL_TIME = time.time()
                res_json = response.json()
                generated_text = res_json[0].get('generated_text', '') if isinstance(res_json, list) else res_json.get('generated_text', '')
                return clean_and_parse_json(generated_text)
            return None
        except Exception as e:
            logger.warning(f"Hugging Face failed: {e}")
            return None

    def call_github_models():
        if not github_token: return None
        try:
            logger.info("🛡️ Calling GitHub Models API...")
            api_url = "https://models.inference.ai.azure.com/chat/completions"
            headers = {"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"}
            payload = {
                "messages": [
                    {"role": "system", "content": "You are a coding assistant. Return output strictly in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                "model": "meta-llama-3.1-405b-instruct", 
                "max_tokens": 2048,
                "temperature": 0.1
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=25)
            if response.status_code == 200:
                res_data = response.json()
                return clean_and_parse_json(res_data['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.warning(f"GitHub Models API failed: {e}")
            return None

    # 🔀 በስራው አይነት ላይ ተመስርቶ የሞዴል ቅደም ተከተል መወሰን (Smart Model Routing)
    if pool_type == 'translation':
        # 1. ጂሚኒ ለትርጉም ስራዎች (ምርጥ የአማርኛ ችሎታ አለው)
        providers = [call_gemini, call_github_models, call_groq, call_huggingface]
    elif pool_type == 'design':
        # 2. ግሮክ ለዲዛይንና HTML ስራዎች (እጅግ ፈጣንና ቀልጣፋ)
        providers = [call_groq, call_gemini, call_github_models, call_huggingface]
    else:
        # 3. ጊትሃብ እና ሃንጊንግ ፌስ ለኮድ ግንባታ መፈራረቅ
        primary_coding = [call_github_models, call_huggingface]
        random.shuffle(primary_coding)
        providers = primary_coding + [call_groq, call_gemini]

    for provider in providers:
        result = provider()
        if result and isinstance(result, dict) and "error" not in result:
            logger.info(f"✅ Success with {provider.__name__}")
            return result
        time.sleep(1.5)

    return {"error": "All AI providers failed."}

def ask_master_ai_smart(prompt, task_type="coding"):
    return ask_ai_with_failover(prompt, pool_type=task_type)
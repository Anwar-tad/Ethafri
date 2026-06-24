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

# 🕒 የ Hugging Face የመጨረሻ ጥሪ የተደረገበትን ሰዓት ለመመዝገብ (Global Variable)
LAST_HF_CALL_TIME = 0

def clean_and_parse_json(text):
    """የ AI ምላሽን አጽድቶ ወደ ዲክሽነሪ ይቀይራል"""
    if isinstance(text, dict): return text
    if not text: return None
    try:
        clean_text = re.sub(r'^```json\s*|^
```\s*|```$', '', str(text).strip(), flags=re.MULTILINE)
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"⚠️ JSON Parsing Error: {e}")
        return None

def ask_ai_with_failover(prompt, pool_type="coding", expected_keys=None):
    """ሁሉንም AI ሞዴሎች የሚያስተባብር እና አንዱ ሲከሽፍ ሌላውን የሚጠራ ዋና ሞተር"""
    global LAST_HF_CALL_TIME
    
    # የ API ቁልፎችን ከአካባቢ ተለዋዋጮች ማንበብ
    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    hf_token = os.environ.get('HUGGINGFACE_TOKEN')
    github_token = os.environ.get('GITHUB_TOKEN') # 👈 የ GitHub Models API ቁልፍ

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
        """🔴 የ 1 ደቂቃ የጊዜ ክፍተት (Cooldown) የሚጠብቅ ተጠባባቂ AI"""
        global LAST_HF_CALL_TIME
        if not hf_token: return None
        
        # ⏱️ ካለፈው ጥሪ 60 ሰከንድ ማለፉን ማረጋገጥ
        current_time = time.time()
        elapsed = current_time - LAST_HF_CALL_TIME
        if elapsed < 60:
            logger.info(f"⏳ Hugging Face በእረፍት ላይ ነው ({int(60 - elapsed)} ሰከንድ ይቀረዋል)። ይዘለላል...")
            return None
            
        try:
            logger.info("🤖 Calling Hugging Face API...")
            model_id = "Qwen/Qwen2.5-Coder-7B-Instruct" 
            # ✅ የተስተካከለ ንጹህ URL (ማርክዳውን ተወግዷል)
            api_url = f"[https://api-inference.huggingface.co/models/](https://api-inference.huggingface.co/models/){model_id}"
            headers = {"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"}
            
            payload = {
                "inputs": f"<|system|>\nYou must return responses strictly in valid JSON format. Do not include markdown.\n<|user|>\n{prompt}\n<|assistant|>\n",
                "parameters": {"max_new_tokens": 1000, "return_full_text": False}
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                LAST_HF_CALL_TIME = time.time() # 🔄 የጥሪ ሰዓቱን ማደስ
                res_json = response.json()
                generated_text = res_json[0].get('generated_text', '') if isinstance(res_json, list) else res_json.get('generated_text', '')
                return clean_and_parse_json(generated_text)
            else:
                logger.warning(f"Hugging Face API returned status {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Hugging Face failed: {e}")
            return None

    def call_github_models():
        """🍏 በሃንጊንግ ፌስ ክፍተት መሃል ተክቶ የሚሰራው GitHub Models API"""
        if not github_token: 
            logger.warning("⚠️ GITHUB_TOKEN አልተገኘም!")
            return None
        try:
            logger.info("🛡️ Calling GitHub Models API (Fallback)...")
            # ✅ የተስተካከለ ንጹህ URL (ማርክዳውን ተወግዷል)
            api_url = "[https://models.inference.ai.azure.com/chat/completions](https://models.inference.ai.azure.com/chat/completions)"
            headers = {
                "Authorization": f"Bearer {github_token}",
                "Content-Type": "application/json"
            }
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
                content = res_data['choices'][0]['message']['content']
                return clean_and_parse_json(content)
            else:
                logger.warning(f"GitHub Models API returned status {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.warning(f"GitHub Models API failed: {e}")
            return None

    # 🔀 መጀመሪያ ሁለቱ ዋና የ AI አቅራቢዎች በዘፈቀደ ይመረጣሉ
    primary_providers = [call_gemini, call_groq]
    random.shuffle(primary_providers)
    
    # 🔗 የጥሪ ቅደም ተከተል፦ [ዋና 1፣ ዋና 2፣ ሃንጊንግ ፌስ፣ ጊትሃብ]
    providers = primary_providers + [call_huggingface, call_github_models]

    for provider in providers:
        result = provider()
        if result and isinstance(result, dict) and "error" not in result:
            logger.info(f"✅ Success with {provider.__name__}")
            return result
        time.sleep(1.5) # በሞዴሎች መለዋወጫ መሃል የ 1.5 ሰከንድ ጥበቃ

    return {"error": "All AI providers (Gemini, Groq, HF, GitHub) failed."}

def ask_master_ai_smart(prompt, task_type="coding"):
    """ከ Master Agent የሚጠራ ቀሊል መጋጠሚያ"""
    return ask_ai_with_failover(prompt, pool_type=task_type)

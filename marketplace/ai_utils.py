import google.generativeai as genai
from groq import Groq
import json
from django.conf import settings

def call_gemini(prompt):
    """Google Gemini 2.0 Flash ን በመጠቀም"""
    try:
        if not settings.GEMINI_API_KEY:
            return "ERROR: GEMINI_API_KEY is missing"
            
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # ወደ አዲሱ 2.0 flash ቀይረነዋል
        model = genai.GenerativeModel('gemini-2.0-flash') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini API Error: {str(e)}")
        return None

def call_groq(prompt):
    """Groq Llama 3 AI (እንደ አማራጭ)"""
    try:
        if not settings.GROQ_API_KEY:
            return "ERROR: GROQ_API_KEY is missing"
            
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # በጣም አዲሱና ጠንካራው ሞዴል
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Groq API Error: {str(e)}")
        return None

def clean_and_parse_json(text):
    if not text or "ERROR" in text:
        return None
    try:
        clean_content = text.strip().replace('```json', '').replace('```', '')
        # አንዳንድ ጊዜ AIው መግቢያ ጽሁፍ ከጨመረ እሱን ለማጽዳት
        start_idx = clean_content.find('{')
        end_idx = clean_content.rfind('}') + 1
        return json.loads(clean_content[start_idx:end_idx])
    except Exception as e:
        print(f"⚠️ JSON Parsing Error: {e}")
        return None

def analyze_product_smartly(title, description, price):
    prompt = f"""
    አንተ የ EthAfri AI ነህ። እቃ: {title}, መግለጫ: {description}, ዋጋ: {price} ETB
    መረጃውን በዚህ JSON ብቻ መልስ:
    {{
      "category": "ምድብ",
      "specs": {{"ቁልፍ": "እሴት"}},
      "tags": ["tag1", "tag2"],
      "valuation": "Fair/Cheap/Expensive",
      "marketing_tip": "ምክር በአማርኛ"
    }}
    """
    raw_response = call_gemini(prompt)
    if not raw_response:
        raw_response = call_groq(prompt)
    return clean_and_parse_json(raw_response)
import google.generativeai as genai
from groq import Groq
import json
from django.conf import settings

def analyze_with_gemini(prompt):
    """የመጀመሪያ ምርጫ - Gemini"""
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini failed: {e}")
        return None

def analyze_with_groq(prompt):
    """ሁለተኛ ምርጫ (Backup) - Groq (Llama 3)"""
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq failed: {e}")
        return None

def analyze_product_smartly(title, description, price):
    prompt = f"""
    አንተ የ EthAfri Smart Marketplace AI ነህ። እቃ: {title}, መግለጫ: {description}, ዋጋ: {price} ETB
    መረጃውን በዚህ JSON ብቻ መልስ:
    {{
      "category": "ምድብ",
      "specs": {{"ቁልፍ": "እሴት"}},
      "tags": ["tag1", "tag2"],
      "valuation": "Fair/Cheap/Expensive",
      "marketing_tip": "የሽያጭ ምክር"
    }}
    """
    
    # 1. መጀመሪያ ጀሚኒን ሞክር
    result = analyze_with_gemini(prompt)
    
    # 2. ጀሚኒ ካልሰራ ግሮክን (Groq) ሞክር
    if not result:
        print("Switching to Backup AI (Groq)...")
        result = analyze_with_groq(prompt)
        
    if result:
        try:
            content = result.strip().replace('```json', '').replace('```', '')
            return json.loads(content)
        except:
            return None
    return None
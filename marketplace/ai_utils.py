import google.generativeai as genai
from groq import Groq
import json
from django.conf import settings

# ---------------------------------------------------------
# 1. ረዳት ተግባራት (Helper Functions)
# ---------------------------------------------------------

def call_gemini(prompt):
    """Google Gemini AIን ለመጥራት"""
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini API Error: {e}")
        return None

def call_groq(prompt):
    """Groq Llama 3 AIን ለመጥራት (እንደ Fallback)"""
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Groq API Error: {e}")
        return None

def clean_and_parse_json(text):
    """ከ AI የሚመጣን ጽሁፍ ወደ JSON ለመቀየር"""
    if not text:
        return None
    try:
        # ከጽሁፉ ውስጥ የ JSON ምልክቶችን (```json ...) ማጽዳት
        clean_content = text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_content)
    except Exception as e:
        print(f"⚠️ JSON Parsing Error: {e}")
        return None

# ---------------------------------------------------------
# 2. ዋና ተግባራት (Main AI Features)
# ---------------------------------------------------------

def analyze_product_smartly(title, description, price):
    """
    ተጠቃሚ እቃ ሲለጥፍ AIው መርምሮ ምድብ፣ ዝርዝር መረጃ እና 
    የገበያ ምክር እንዲሰጥ ያደርጋል።
    """
    prompt = f"""
    አንተ የ EthAfri Smart Marketplace AI ነህ። ይህንን እቃ መርምር፡
    እቃ: {title}
    መግለጫ: {description}
    ዋጋ: {price} ETB

    እባክህ የሚከተሉትን መረጃዎች በ JSON ቅርጽ ብቻ መልስ (ምንም ሌላ ጽሁፍ አትጨምር)፦
    {{
      "category": "ምድብ (ለምሳሌ፡ መኪና፣ ኤሌክትሮኒክስ፣ ሪል-ስቴት...)",
      "specs": {{"ቁልፍ": "እሴት", "ቀለም": "ነጭ"}},
      "tags": ["tag1", "tag2", "tag3"],
      "valuation": "ከገበያ አንጻር ዋጋው፡ Fair/Cheap/Expensive",
      "marketing_tip": "ሻጩ እቃውን ቶሎ እንዲሸጥ የሚሰጥ ምክር በአማርኛ"
    }}
    """
    
    # መጀመሪያ ጀሚኒን ሞክር፣ ካልሰራ ግሮክን ተጠቀም
    raw_response = call_gemini(prompt)
    if not raw_response:
        print("🔄 Gemini አልሰራም፣ ወደ Groq በመቀየር ላይ...")
        raw_response = call_groq(prompt)
        
    return clean_and_parse_json(raw_response)

def get_advanced_market_insight(title, description, price):
    """
    ይህ ተግባር ለወደፊት የላቀ የገበያ ትንተና ለመስጠት ያገለግላል።
    (በ views.py ውስጥ ሊጠራ ይችላል)
    """
    # ለጊዜው ከላይ ያለውን ተግባር ይጠቀማል
    return analyze_product_smartly(title, description, price)
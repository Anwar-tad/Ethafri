import google.generativeai as genai
import json
from django.conf import settings

def analyze_product_smartly(title, description, price):
    # API ቁልፍህን እዚህ ጋር ያገናኛል
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    አንተ የ EthAfri Smart Marketplace AI ነህ። ይህንን እቃ መርምር፡
    እቃ: {title}
    መግለጫ: {description}
    ዋጋ: {price} ETB

    እባክህ የሚከተሉትን መረጃዎች በ JSON ቅርጽ ብቻ መልስ (ምንም ሌላ ጽሁፍ አትጨምር)፦
    {{
      "category": "ምድብ (ለምሳሌ፡ መኪና፣ ቤት...)",
      "specs": {{"ቁልፍ": "እሴት"}},
      "tags": ["tag1", "tag2"],
      "valuation": "Fair/Cheap/Expensive",
      "marketing_tip": "የሽያጭ ምክር"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # JSON መረጃውን ማጽዳት
        content = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(content)
    except Exception as e:
        print(f"AI Error: {e}")
        return None
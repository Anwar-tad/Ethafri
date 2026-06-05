import google.generativeai as genai
import json

def analyze_product_smartly(title, description, price):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    አንተ የ EthAfri Smart Marketplace AI ነህ። ይህንን እቃ መርምር፡
    እቃ: {title}
    መግለጫ: {description}
    ዋጋ: {price} ETB

    እባክህ የሚከተሉትን መረጃዎች በ JSON ብቻ መልስ፡
    1. category: (እቃው የሚመደብበት - መኪና፣ ኤሌክትሮኒክስ፣ ሪል-ስቴት፣ ወዘተ)
    2. specs: (የእቃው ዝርዝር መረጃ በ ቁልፍ፡እሴት መልክ - ለምሳሌ 'ቀለም':'ቀይ')
    3. tags: (ለፍለጋ የሚረዱ 5 ቃላት በአማርኛ እና በእንግሊዝኛ)
    4. valuation: (ዋጋው ከገበያ አንጻር፡ 'Fair', 'Cheap', ወይም 'Expensive')
    5. marketing_tip: (ሻጩ እቃውን ቶሎ እንዲሸጥ የሚሰጥ ምክር)
    """
    
    try:
        response = model.generate_content(prompt)
        # JSON መረጃውን መውሰድ
        clean_response = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_response)
    except:
        return None
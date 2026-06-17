# EthAfri/marketplace/ai_utils.py

import json, re
from .growth_agent import ask_gemini_with_rotation, ask_groq_fast

def clean_and_parse_json(text):
    """ከ AI መልስ ውስጥ JSON ዳታን ብቻ ለይቶ ያወጣል"""
    if not text: return None
    try:
        # የ JSON መጀመሪያ እና መጨረሻ ምልክቶችን አጽድቶ ለማውጣት
        start_idx = text.find('{')
        end_idx = text.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            return json.loads(text[start_idx:end_idx])
        return None
    except Exception as e:
        print(f"⚠️ JSON Parsing Error: {e}")
        return None

def analyze_product_smartly(title, description, price):
    """እቃ ሲለጠፍ በ AI መርምሮ ምድብ ለመስጠት"""
    prompt = f"""
    Categorize the following product and provide exactly 3 tags for photo matching.
    Product: {title}
    Desc: {description}
    Price: {price}
    
    Return as pure JSON:
    {{
        "category": "Category Name",
        "tags": ["tag1", "tag2", "tag3"],
        "translations": {{
            "en": "Title ||| Description",
            "am": "Title ||| Description",
            "om": "Title ||| Description",
            "ar": "Title ||| Description",
            "so": "Title ||| Description",
            "ti": "Title ||| Description",
            "fr": "Title ||| Description"
        }}
    }}
    """
    
    # ⚠️ 1. የትርጉም ፑልን (Translation Pool) በመጠቀም ጀሚኒን ይጠይቃል
    raw_response = ask_gemini_with_rotation(prompt, pool_type="translation")
    
    # 2. ጀሚኒ ከከሸፈ በ Groq ይሞክራል
    if not raw_response:
        raw_response = ask_groq_fast(prompt)
        
    return clean_and_parse_json(raw_response)

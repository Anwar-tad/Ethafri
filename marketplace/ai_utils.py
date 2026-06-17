# EthAfri/marketplace/ai_utils.py

import json, re
from .growth_agent import ask_ai_with_failover

def clean_and_parse_json(text):
    """ከ AI መልስ ውስጥ JSON ዳታን ብቻ ለይቶ ያወጣል"""
    if not text: return None
    try:
        # የ JSON መጀመሪያ እና መጨረሻ ምልክቶችን አጽድቶ ለማውጣት (Robust Parsing)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(text)
    except Exception as e:
        print(f"⚠️ JSON Parsing Error: {e}")
        return None

def analyze_product_smartly(title, description, price):
    """እቃ ሲለጠፍ በ AI መርምሮ ምድብ ለመስጠት (በFailover Chain የተደገፈ)"""
    prompt = f"""
    Categorize the following product and provide exactly 3 tags for photo matching.
    Product: {title}
    Desc: {description}
    Price: {price}
    
    Return as pure JSON (no extra text):
    {{
        "category": "Category Name",
        "tags": ["tag1", "tag2", "tag3"],
        "translations": {{
            "en": "...", "am": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."
        }}
    }}
    """
    
    # ⚠️ አሁን የጠየቅከውን Failover ሎጂክ በሙሉ ይይዛል
    # ይህ አንድ መስመር ጀሚኒ -> ግሮቅ -> ኦፕንራውተር -> ሚስትራልን በቅደም ተከተል ይፈትሻል
    raw_response = ask_ai_with_failover(prompt, pool_type="translation")
        
    return clean_and_parse_json(raw_response)

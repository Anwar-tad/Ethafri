# EthAfri/marketplace/ai_utils.py

import json
import re
import logging
from .growth_agent import ask_ai_with_failover

logger = logging.getLogger(__name__)

def clean_and_parse_json(text):
    """የ AI መልስን አጽድቶ ወደ ትክክለኛ የፓይተን ዲክሽነሪ ይቀይራል"""
    if isinstance(text, dict): return text  # ቀድሞውንም ዲክሽነሪ ከሆነ
    
    if not text: return None
    try:
        # ለተጨማሪ ደህንነት ማርክዳውን ብሎኮችን ያስወግዳል
        clean_text = re.sub(r'^```json\s*|^```\s*|```$', '', str(text).strip(), flags=re.MULTILINE)
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"⚠️ JSON Parsing Error: {e} | Raw Data: {text}")
        return None

def analyze_product_smartly(title, description, price):
    """እቃ ሲለጠፍ በ AI መርምሮ ምድብ ለመስጠት እና ወደ 7 ቋንቋዎች ለመተርጎም"""
    
    # 🛡️ ፕሮምፕቱን ሕግ 1ን እንዲያከብር እና ጥብቅ የ JSON መመለሻ እንዲኖረው ማጠንከር
    prompt = f"""
    [CRITICAL DIRECTIVE]
    You are the EthAfri AI Categorization & Translation Engine.
    Analyze the following product:
    Title: {title}
    Description: {description}
    Price: {price}

    Task:
    1. Determine the best category.
    2. Generate 3 specific search tags.
    3. Translate the title and description into Amharic, Oromo, Arabic, Somali, Tigrinya, and French.

    Output Constraint:
    Return ONLY a pure JSON object. No markdown, no explanations. 
    Strict JSON format:
    {{
        "category": "String",
        "tags": ["tag1", "tag2", "tag3"],
        "translations": {{
            "en": "...", "am": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."
        }}
    }}
    """
    
    # የ Failover ሎጂክን ይጠቀማል (Translation Pool -> Gemini first)
    raw_response = ask_ai_with_failover(prompt, pool_type="translation")
        
    return clean_and_parse_json(raw_response)

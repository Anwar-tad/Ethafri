# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/ai_utils.py
# 📝 ለውጥ፦ Multi-Site Support + Enhanced Translation + Schema Validation Gating
# ✅ የተፈቱ ችግሮች፦ JSON Truncation, View KeyError Crashes
# 📅 ቀን፦ 2026-06-23
# ============================================================

import json
import re
import logging
from django.conf import settings
from .growth_agent import ask_ai_with_failover
from .models import SiteRegistry

logger = logging.getLogger(__name__)


def clean_and_parse_json(text):
    """የ AI መልስን አጽድቶ ወደ ትክክለኛ የፓይተን ዲክሽነሪ ይቀይራል"""
    if isinstance(text, dict): 
        return text
    
    if not text: 
        return None
    
    try:
        clean_text = re.sub(r'^```json\s*|^```\s*|```$', '', str(text).strip(), flags=re.MULTILINE)
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"⚠️ JSON Parsing Error: {e} | Raw Data: {text[:200]}")
        return None


# ============================================================
# 1. ነባሪ የምርት ትንተና (የተመቻቸ)
# ============================================================

def analyze_product_smartly(title, description, price):
    """
    እቃ ሲለጠፍ በ AI መርምሮ ምድብ ለመስጠት እና ወደ 7 ቋንቋዎች ለመተርጎም
    """
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
    
    # ✅ ማሻሻያ 1፦ የተዋቀረ ምላሽ ማረጋገጫ (expected_keys) በማካተት የ KeyError ስህተቶችን መከላከል
    raw_response = ask_ai_with_failover(
        prompt, 
        pool_type="translation",
        expected_keys=["category", "tags", "translations"]
    )
    return clean_and_parse_json(raw_response)


# ============================================================
# 2. ለአንድ የተወሰነ ጣቢያ የምርት ትንተና (የተመቻቸ)
# ============================================================

def analyze_product_for_site(title, description, price, site: SiteRegistry):
    """
    ለአንድ የተወሰነ ጣቢያ የምርት ትንተና ያካሂዳል
    የጣቢያውን ኒች እና ዒላማ ገበያ ግምት ውስጥ ያስገባል
    """
    site_context = f"""
    Site Information:
    - Name: {site.name}
    - Niche: {site.niche}
    - Target Market: {site.target_market}
    - Keywords: {site.primary_keywords}
    - Target Audience: {site.target_audience}
    """
    
    prompt = f"""
    [CRITICAL DIRECTIVE]
    You are the EthAfri AI Categorization & Translation Engine.
    
    {site_context}
    
    Analyze the following product for this specific site:
    Title: {title}
    Description: {description}
    Price: {price}

    Task:
    1. Determine the best category (aligned with the site's niche).
    2. Generate 3 specific search tags (aligned with the site's keywords).
    3. Translate the title and description into Amharic, Oromo, Arabic, Somali, Tigrinya, and French.
    4. Suggest an optimal price range based on the target market.

    Output Constraint:
    Return ONLY a pure JSON object. No markdown, no explanations. 
    Strict JSON format:
    {{
        "category": "String",
        "tags": ["tag1", "tag2", "tag3"],
        "suggested_price": 100.00,
        "translations": {{
            "en": "...", "am": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."
        }}
    }}
    """
    
    # ✅ ማሻሻያ 2፦ የተዋቀረ ምላሽ ማረጋገጫ (expected_keys) መጨመር
    raw_response = ask_ai_with_failover(
        prompt, 
        pool_type="translation",
        expected_keys=["category", "tags", "suggested_price", "translations"]
    )
    return clean_and_parse_json(raw_response)


# ============================================================
# 3. የጣቢያ ኒች ትንተና (የተመቻቸ)
# ============================================================

def analyze_site_niche_ai(site: SiteRegistry):
    """
    የጣቢያውን ይዘት እና ኮድ በመተንተን ኒች እና ገበያ ይለያል
    """
    from .growth_agent import get_site_project_state
    
    project_code, _ = get_site_project_state(site)
    
    if not project_code:
        return None
    
    # የጣቢያውን ይዘት አጠቃላይ ማጠቃለያ
    # ✅ ማሻሻያ 3፦ የኮድ ይዘቱ በድንገት ተቆርጦ የ JSON መዋቅሩ እንዳይበላሽ የእያንዳንዱን ፋይል መጠን በራሱ ማሳጠር
    code_summary = {}
    for key, value in project_code.items():
        if value:
            code_summary[key] = value[:1200] + "..." if len(value) > 1200 else value
    
    prompt = f"""
    [CRITICAL DIRECTIVE]
    You are the EthAfri Market Intelligence Analyst.
    
    Analyze this website to determine its market position:
    Website: {site.display_name}
    Current Niche: {site.niche or 'Unknown'}
    Target Market: {site.target_market or 'Unknown'}
    
    Codebase Summary:
    {json.dumps(code_summary, indent=2)}
    
    Task:
    1. Identify the primary niche/market
    2. Identify the top 5 keywords
    3. Identify the top 3 competitors
    4. Describe the target audience
    5. Suggest the best content style
    
    Output Constraint:
    Return ONLY a pure JSON object. No markdown, no explanations.
    {{
        "niche": "string",
        "primary_keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"],
        "competitor_urls": ["https://comp1.com", "https://comp2.com", "https://comp3.com"],
        "target_audience": "string description",
        "content_style": "professional|casual|storytelling|educational"
    }}
    """
    
    raw_response = ask_ai_with_failover(
        prompt, 
        pool_type="analysis",
        expected_keys=["niche", "primary_keywords", "competitor_urls"]
    )
    return clean_and_parse_json(raw_response)


# ============================================================
# 4. የምርት SEO ማሻሻያ (የተመቻቸ)
# ============================================================

def enhance_product_seo(product_title, product_description, site: SiteRegistry):
    """
    የምርት ርዕስ እና መግለጫ ለ SEO ያሻሽላል
    """
    prompt = f"""
    [CRITICAL DIRECTIVE]
    You are the EthAfri SEO Optimization Engine.
    
    Site Information:
    - Niche: {site.niche}
    - Keywords: {site.primary_keywords}
    - Target Market: {site.target_market}
    
    Product:
    - Title: {product_title}
    - Description: {product_description}
    
    Task:
    Enhance the product title and description for better SEO ranking.
    1. Create an SEO-optimized title (include primary keywords)
    2. Create an SEO-optimized description (include keywords, benefits, and CTA)
    3. Suggest 5 additional tags
    4. Suggest a meta description (max 160 characters)
    
    Output Constraint:
    Return ONLY a pure JSON object. No markdown, no explanations.
    {{
        "optimized_title": "string",
        "optimized_description": "string",
        "additional_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
        "meta_description": "string (max 160 chars)"
    }}
    """
    
    raw_response = ask_ai_with_failover(
        prompt, 
        pool_type="coding",
        expected_keys=["optimized_title", "optimized_description", "additional_tags", "meta_description"]
    )
    return clean_and_parse_json(raw_response)
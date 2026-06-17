# EthAfri/marketplace/self_doctor.py

import json
import re
import traceback
from django.db import connection
from django.conf import settings
from django.utils.text import slugify # ⚠️ ይህ መስመር ስህተቱን ለመከላከል ተጨምሯል
from .models import SelfHealingLog, SiteConfig
from .growth_agent import ask_ethafri_ceo 

MODEL_NAME = 'gemini-2.5-flash'

def generalize_error_message(error_msg):
    """የተለያዩ ተለዋዋጭ እሴቶችን በማጥፋት ስህተቱን ወደ አጠቃላይ አሻራ ይቀይራል"""
    clean_msg = re.sub(r"'\d+'|\d+", "[NUM]", error_msg)
    clean_msg = re.sub(r'"[^"]+"', "[IDENTIFIER]", clean_msg)
    return clean_msg.strip()

def validate_css_syntax(css_content):
    """የ AIው CSS መሠረታዊ የቅንፍ ስህተት እንደሌለበት ያረጋግጣል (Dry Run)"""
    open_brackets = css_content.count('{')
    close_brackets = css_content.count('}')
    if open_brackets != close_brackets:
        raise ValueError(f"CSS Syntax Mismatch: {open_brackets} open vs {close_brackets} close brackets.")
    return True

def discover_and_heal_ui_design(current_theme_color, trend_context="Modern Minimalist"):
    """
    📌 አዳዲስና የተሻሉ የዲዛይን ስታይሎችን ያሰሳል设计፣ ስህተቶች ሲኖሩም ራሱን ያክማል።
    ይህ ሲስተሙ ደጋግሞ ዲዛይን በመስራት ቢዚ እንዳይሆን ይከላከላል።
    """
    style_key = f"DESIGN_STYLE_{slugify(trend_context)}"
    
    # 1. 🔍 የዲዛይን ትውስታ ፍተሻ (ቢዚ እንዳይሆን ከዚህ በፊት የተመዘገበን ምርጥ ስታይል በቀጥታ ያነባል)
    cached_style = SiteConfig.objects.filter(key=style_key).first()
    if cached_style:
        print(f"🧠 Memory Match Found for Design Style! Applying Cached CSS UI...")
        return cached_style.value  # የተሸሸገውን የ CSS/UI ቅንብር በቀጥታ ይመልሳል

    # 2. 🤖 የአካባቢው መዝገብ ከሌለ አዲስ የተሻለ የዲዛይን ስታይል ከ AI ይጠይቃል
    prompt = f"""
    You are the Chief UI/UX Architect of EthAfri.
    Current Theme Color: {current_theme_color}
    Target Trend Direction: {trend_context}

    Generate an optimized CSS variable block and smart design adjustments to enhance the marketplace visual appeal.
    Ensure to fix any common scaling or border-radius overflow bugs on product cards.
    Return ONLY a valid JSON string with two keys: 'theme_color' and 'custom_css'. No markdown, no explanations.
    {{
       "theme_color": "#hex_code",
       "custom_css": ":root {{ --primary-color: #hex; }} .product-card {{ border-radius: 20px; }}"
    }}
    """
    
    try:
        ai_response = ask_ethafri_ceo(prompt)
        start_idx = ai_response.find('{')
        end_idx = ai_response.rfind('}') + 1
        clean_json = ai_response[start_idx:end_idx]
        design_data = json.loads(clean_json)
        
        # የ CSS ሲንታክስ ደህንነት ምርመራ
        validate_css_syntax(design_data.get('custom_css', ''))
        
        # 3. 📝 ምርጡን አዲስ ዲዛይን በቋሚነት በትውስታ መዝገብ ላይ መቆለፍ (ሁለተኛ እንዳይደክም)
        SiteConfig.objects.update_or_create(
            key=style_key,
            defaults={'value': design_data}
        )
        
        # ስኬታማነቱን በሎግ መመዝገብ
        SelfHealingLog.objects.create(
            error_message=f"UI_EVOLUTION: Applied {trend_context} style",
            solution_sql=design_data.get('custom_css'),
            resolved=True
        )
        return design_data

    except Exception as ui_err:
        print(f"❌ UI Healing/Evolution Failed: {ui_err}")
        # ዲዛይኑ ከተበላሸ ወደ ነባሪው አስተማማኝ ስታይል ይመልሰዋል (Fallback Design)
        return {
            "theme_color": current_theme_color,
            "custom_css": f":root {{ --primary-color: {current_theme_color}; }}"
        }

def heal_any_system_error(error_category, error_msg, target_context=None):
    """የዳታቤዝም ሆነ የኮድ አፈጻጸም ስህተቶች ሲከሰቱ ራሱን የሚያክም ዋና ሞተር"""
    general_error = generalize_error_message(error_msg)
    
    past_solution = SelfHealingLog.objects.filter(
        error_message__icontains=general_error[:150], 
        resolved=True
    ).order_by('-created_at').first()
    
    if past_solution:
        print(f"🧠 Memory Match Found for Error! Applying Cached Solution...")
        if error_category == 'DATABASE':
            try:
                with connection.cursor() as cursor:
                    cursor.execute(past_solution.solution_sql)
                return f"✅ Database Healed using Local Memory!"
            except Exception as e: pass
        elif error_category == 'CODE_EXECUTION':
            return past_solution.solution_sql

    if error_category == 'DATABASE':
        prompt = f"You are the Autonomous Database Doctor of EthAfri. Fix this PostgreSQL error: {error_msg} for query: {target_context}. Return raw SQL ONLY."
    else:
        prompt = f"You are the Lead Systems Engineer of EthAfri. Fix this python runtime error: {error_msg} in context: {target_context}. Return raw code ONLY."

    try:
        ai_response = ask_ethafri_ceo(prompt)
        if not ai_response: return "❌ AI Failover chain failed."
        clean_solution = re.sub(r'^```[a-zA-Z]*\s*|^```\s*|```$', '', ai_response.strip(), flags=re.MULTILINE)

        if error_category == 'DATABASE':
            with connection.cursor() as cursor:
                cursor.execute(clean_solution)
        elif error_category == 'CODE_EXECUTION':
            compile(clean_solution, '<string>', 'exec')

        SelfHealingLog.objects.create(
            error_message=general_error,
            solution_sql=clean_solution,
            resolved=True
        )
        return f"✅ System Automatically Healed! Category: {error_category}"

    except Exception as heal_err:
        SelfHealingLog.objects.create(
            error_message=f"Category: {error_category} | Error: {general_error} | Failed with: {str(heal_err)}",
            solution_sql=clean_solution if 'clean_solution' in locals() else "No solution",
            resolved=False
        )
        return f"❌ Auto-Healing Failed: {str(heal_err)}"
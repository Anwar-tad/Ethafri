# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_doctor.py
# 📝 ለውጥ፦ Multi-Site Support + SiteRegistry Integration
# 📅 ቀን፦ 2026-06-20
# ============================================================

import json
import re
import traceback
import os
from django.db import connection
from django.conf import settings
from django.utils.text import slugify
from .models import SelfHealingLog, SiteConfig, SiteRegistry, AgentErrorLog, AIEvolutionLog
from .growth_agent import ask_ethafri_ceo, get_site_project_state

logger = logging.getLogger(__name__)


# ============================================================
# 1. ረዳት ተግባራት (Helper Functions)
# ============================================================

def generalize_error_message(error_msg):
    """የተለያዩ ተለዋዋጭ እሴቶችን በማጥፋት ስህተቱን ወደ አጠቃላይ አሻራ (Signature) ይቀይራል"""
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


# ============================================================
# 2. የዲዛይን ጥገና እና ዝግመተ-ለውጥ (የተሻሻለ - Multi-Site)
# ============================================================

def discover_and_heal_ui_design(current_theme_color, trend_context="Modern Minimalist", site=None):
    """
    📌 አዳዲስና የተሻሉ የዲዛይን ስታይሎችን ያሰሳል፣ ስህተቶች ሲኖሩም ራሱን ያክማል።
    አሁን ለብዙ ጣቢያዎች ይሰራል
    """
    site_name = site.name if site else "primary"
    style_key = f"DESIGN_STYLE_{slugify(trend_context)}_{slugify(site_name)}"
    
    # 1. 🔍 የዲዛይን ትውስታ ፍተሻ
    cached_style = SiteConfig.objects.filter(key=style_key).first()
    if cached_style:
        print(f"🧠 Memory Match Found for Design Style ({site_name})! Applying Cached CSS UI...")
        return cached_style.value

    # 2. 🤖 አዲስ የተሻለ የዲዛይን ስታይል ከ AI ይጠይቃል
    site_context = ""
    if site:
        site_context = f"""
        Site Information:
        - Name: {site.name}
        - Niche: {site.niche}
        - Target Market: {site.target_market}
        - Growth Level: {site.growth_level}
        - Target Audience: {site.target_audience}
        """
    
    prompt = f"""
    [CRITICAL DIRECTIVE]
    You are the Chief UI/UX Architect of EthAfri.
    Current Theme Color: {current_theme_color}
    Target Trend Direction: {trend_context}
    {site_context}

    Task:
    Generate an optimized CSS variable block and smart design adjustments to enhance the marketplace visual appeal.
    Ensure to fix any common scaling or border-radius overflow bugs on product cards.
    Consider the site's niche and target audience for appropriate design choices.

    Output Constraint:
    Return ONLY a valid JSON string with exactly two keys: 'theme_color' and 'custom_css'. 
    Do NOT include markdown blockticks (```json), formatting, or explanations. Just the raw JSON object.
    Example format:
    {{
       "theme_color": "#1a2a6c",
       "custom_css": ":root {{ --primary-color: #1a2a6c; }} .product-card {{ border-radius: 20px; }}"
    }}
    """
    
    try:
        ai_response = ask_ethafri_ceo(prompt, pool_type="coding")
        
        if isinstance(ai_response, dict):
            design_data = ai_response
        else:
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON object found in AI response.")
                
            clean_json = ai_response[start_idx:end_idx]
            design_data = json.loads(clean_json)
        
        # የ CSS ሲንታክስ ደህንነት ምርመራ
        validate_css_syntax(design_data.get('custom_css', ''))
        
        # 3. 📝 ምርጡን አዲስ ዲዛይን በቋሚነት በትውስታ መዝገብ ላይ መቆለፍ
        SiteConfig.objects.update_or_create(
            key=style_key,
            defaults={'value': design_data}
        )
        
        # ስኬታማነቱን በሎግ መመዝገብ
        SelfHealingLog.objects.create(
            error_message=f"UI_EVOLUTION: Applied {trend_context} style for {site_name}",
            solution_sql=design_data.get('custom_css', ''),
            resolved=True
        )
        return design_data

    except Exception as ui_err:
        print(f"❌ UI Healing/Evolution Failed for {site_name}: {ui_err}")
        return {
            "theme_color": current_theme_color,
            "custom_css": f":root {{ --primary-color: {current_theme_color}; }}"
        }


# ============================================================
# 3. ለአንድ ጣቢያ ስህተት ጥገና (የተሻሻለ)
# ============================================================

def heal_single_site_error(site: SiteRegistry, error_category, error_msg, target_context=None):
    """
    ለአንድ የተወሰነ ጣቢያ ስህተት ያስተካክላል
    """
    site_name = site.name
    general_error = generalize_error_message(error_msg)
    
    # 1. በዚህ ጣቢያ ላይ ቀደም ብሎ የተፈታ ስህተት ካለ
    past_solution = SelfHealingLog.objects.filter(
        error_message__icontains=general_error[:150], 
        resolved=True
    ).order_by('-created_at').first()
    
    if past_solution:
        print(f"🧠 Memory Match Found for Error on {site_name}! Applying Cached Solution...")
        if error_category == 'DATABASE':
            try:
                with connection.cursor() as cursor:
                    cursor.execute(past_solution.solution_sql)
                return f"✅ Database Healed for {site_name} using Local Memory!"
            except Exception as e:
                pass
        elif error_category == 'CODE_EXECUTION':
            return past_solution.solution_sql

    # 2. የጣቢያውን ኮድ አንብብ
    project_code, file_paths = get_site_project_state(site)
    
    # 3. AI መመሪያ (Prompt)
    if error_category == 'DATABASE':
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Autonomous Database Doctor of EthAfri for site: {site_name}.
        
        Site Information:
        - Niche: {site.niche}
        - Target Market: {site.target_market}
        
        Fix this PostgreSQL error: {error_msg} 
        For query/context: {target_context}. 
        Return ONLY raw SQL statements to fix the issue. No markdown blocks, no explanations.
        """
    else:
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Lead Systems Engineer of EthAfri for site: {site_name}.
        
        Site Information:
        - Niche: {site.niche}
        - Target Market: {site.target_market}
        - Current Codebase: {json.dumps(project_code, indent=2)[:3000]}
        
        Fix this Python runtime error: {error_msg} 
        In context: {target_context}. 
        Return ONLY the corrected raw Python code. No markdown blocks, no explanations.
        """

    try:
        ai_response = ask_ethafri_ceo(prompt, pool_type="healing")
        if not ai_response:
            return f"❌ AI Failover chain failed for {site_name}."
            
        raw_solution = ""
        if isinstance(ai_response, dict):
            if "error" in ai_response:
                return f"❌ AI Failover chain failed for {site_name}."
            raw_solution = (
                ai_response.get('solution') or 
                ai_response.get('code') or 
                list(ai_response.values())[0]
            )
        else:
            raw_solution = ai_response

        # የኮድ ማርክዳውን ማጽዳት
        clean_solution = re.sub(r'^```[a-zA-Z]*\s*|^```\s*|```$', '', raw_solution.strip(), flags=re.MULTILINE).strip()

        if error_category == 'DATABASE':
            with connection.cursor() as cursor:
                cursor.execute(clean_solution)
        elif error_category == 'CODE_EXECUTION':
            compile(clean_solution, '<string>', 'exec')
            # የተስተካከለውን ኮድ ለጣቢያው ያስቀምጥ
            # (በእውነተኛ ስራ ላይ ይህ ወደ ፋይል ይጻፋል)

        SelfHealingLog.objects.create(
            error_message=general_error,
            solution_sql=clean_solution,
            resolved=True
        )
        
        # ስህተቱን እንደተፈታ ምልክት አድርግ
        AgentErrorLog.objects.filter(site=site, error_message__icontains=general_error[:100], resolved=False).update(resolved=True)
        
        return f"✅ System Healed for {site_name}! Category: {error_category}"

    except Exception as heal_err:
        SelfHealingLog.objects.create(
            error_message=f"Site: {site_name} | Category: {error_category} | Error: {general_error} | Failed with: {str(heal_err)}",
            solution_sql=clean_solution if 'clean_solution' in locals() else "No solution generated",
            resolved=False
        )
        return f"❌ Auto-Healing Failed for {site_name}: {str(heal_err)}"


# ============================================================
# 4. ዋናው ስህተት ጥገና ተግባር (የተሻሻለ - Multi-Site)
# ============================================================

def heal_any_system_error(error_category, error_msg, target_context=None):
    """
    የዳታቤዝም ሆነ የኮድ አፈጻጸም ስህተቶች ሲከሰቱ ራሱን የሚያክም ዋና ሞተር
    አሁን ሁሉንም ጣቢያዎች ያስተዳድራል
    """
    results = []
    
    # 1. ስህተቱ የትኛውን ጣቢያ እንደሚመለከት ለይ
    site_id = None
    if target_context and 'site_id' in str(target_context):
        try:
            import re
            match = re.search(r'site_id[=:]\s*(\d+)', str(target_context))
            if match:
                site_id = int(match.group(1))
        except:
            pass
    
    # 2. ሁሉንም ንቁ ጣቢያዎች ራስ-ጥገና አድርግ (ወይም አንዱን)
    sites = SiteRegistry.objects.filter(is_active=True)
    
    if not sites.exists():
        # ነባሪ ጣቢያ ከሌለ መደበኛ ጥገና አድርግ
        return _heal_system_error_single(error_category, error_msg, target_context)
    
    # የተወሰነ ጣቢያ ከተለየ
    if site_id:
        site = sites.filter(id=site_id).first()
        if site:
            result = heal_single_site_error(site, error_category, error_msg, target_context)
            return result
    
    # ሁሉንም ጣቢያዎች አስኬድ
    for site in sites:
        try:
            result = heal_single_site_error(site, error_category, error_msg, target_context)
            results.append(result)
        except Exception as e:
            results.append(f"❌ Failed to heal {site.name}: {str(e)}")
    
    if not results:
        return _heal_system_error_single(error_category, error_msg, target_context)
    
    return f"🛠️ Multi-Site Heal Summary: {' | '.join(results)}"


# ============================================================
# 5. ነባሪ ጥገና ተግባር (ለአሮጌ ተኳሃኝነት)
# ============================================================

def _heal_system_error_single(error_category, error_msg, target_context=None):
    """
    የመጀመሪያው የስህተት ጥገና ተግባር (ለአሮጌ ተኳሃኝነት)
    """
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
            except Exception as e:
                pass
        elif error_category == 'CODE_EXECUTION':
            return past_solution.solution_sql

    if error_category == 'DATABASE':
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Autonomous Database Doctor of EthAfri. 
        Fix this PostgreSQL error: {error_msg} 
        For query/context: {target_context}. 
        Return ONLY raw SQL statements to fix the issue. No markdown blocks, no explanations.
        """
    else:
        prompt = f"""
        [CRITICAL DIRECTIVE]
        You are the Lead Systems Engineer of EthAfri. 
        Fix this Python runtime error: {error_msg} 
        In context: {target_context}. 
        Return ONLY the corrected raw Python code. No markdown blocks, no explanations.
        """

    try:
        ai_response = ask_ethafri_ceo(prompt, pool_type="healing")
        if not ai_response:
            return "❌ AI Failover chain failed."
            
        raw_solution = ""
        if isinstance(ai_response, dict):
            if "error" in ai_response:
                return "❌ AI Failover chain failed."
            raw_solution = (
                ai_response.get('solution') or 
                ai_response.get('code') or 
                list(ai_response.values())[0]
            )
        else:
            raw_solution = ai_response

        clean_solution = re.sub(r'^```[a-zA-Z]*\s*|^```\s*|```$', '', raw_solution.strip(), flags=re.MULTILINE).strip()

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
            solution_sql=clean_solution if 'clean_solution' in locals() else "No solution generated",
            resolved=False
        )
        return f"❌ Auto-Healing Failed: {str(heal_err)}"
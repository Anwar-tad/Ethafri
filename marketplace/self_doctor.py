# EthAfri/marketplace/growth_agent.py ወይም views.py ውስጥ ስህተት ሲፈጠር የሚጠራው ዋና ሐኪም

import google.generativeai as genai
import json, re
from django.db import connection
from django.conf import settings
from .models import SelfHealingLog

MODEL_NAME = 'gemini-2.5-flash'

def heal_database_error(error_msg, failed_query=None):
    """
    በዳታቤዝ ላይ ስህተት ሲፈጠር AIው አይቶ ራሱ SQL በማመንጨት
    ሰንጠረዦቹን የሚጠግንበት ራስ-አራሚ ሞተር
    """
    # 1. ይህ ስህተት ከዚህ በፊት የተከሰተ እና የተፈታ መሆኑን ማረጋገጥ (ደግሞ እንዳይሳሳት)
    already_healed = SelfHealingLog.objects.filter(error_message__icontains=error_msg[:100], resolved=True).exists()
    if already_healed:
        return "⚠️ ይህ ስህተት አስቀድሞ ተፈትቷል። ማለፍ ይቻላል።"

    # 2. ለ AIው ስህተቱን ማስረዳት
    prompt = f"""
    አንተ የ EthAfri Smart Marketplace ራስ-አራሚ የዳታቤዝ ሐኪም (Database Doctor) ነህ።
    ዳታቤዝ ላይ የሚከተለው የ PostgreSQL ስህተት አጋጥሟል፦
    
    የከሸፈው የ SQL ትዕዛዝ: {failed_query}
    የስህተት መልዕክት: {error_msg}

    እባክህ ይህንን ስህተት የሚፈታውን ትክክለኛ የ PostgreSQL ALTER TABLE ወይም ተዛማጅ የ SQL ማስተካከያ ትዕዛዝ ብቻ ስጠኝ።
    መልስህን በ SQL ብቻ አቅርብ (ምንም ዓይነት ማብራሪያ ወይም የሰው ወሬ አትጨምር፣ SQL ኮድ ብቻ ይሁን)።
    """

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        
        if response and response.text:
            sql_solution = response.text.strip().replace('```sql', '').replace('```', '')
            
            # --- ⚠️ AUTO-HEAL: ማስተካከያውን በራሱ ዳታቤዙ ላይ ያሄደዋል ---
            with connection.cursor() as cursor:
                cursor.execute(sql_solution)
            
            # ስራውን በታሪክ መዝገብ ማስቀመጥ
            SelfHealingLog.objects.create(
                error_message=error_msg,
                solution_sql=sql_solution,
                resolved=True
            )
            return f"✅ Database Healed Automatically! Applied SQL: {sql_solution[:50]}..."
            
    except Exception as heal_err:
        # ሕክምናው ካልተሳካ እንዲመዘግብ
        SelfHealingLog.objects.create(
            error_message=f"Heal Failed: {error_msg} | Doctor Err: {str(heal_err)}",
            resolved=False
        )
        return f"❌ Auto-Healing Failed: {str(heal_err)}"
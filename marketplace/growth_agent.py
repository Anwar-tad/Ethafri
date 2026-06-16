# EthAfri/marketplace/growth_agent.py

import google.generativeai as genai
from groq import Groq
import json, datetime, re, requests
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product, ProductTranslation, SiteConfig, AISystemTask
from django.contrib.auth.models import User

# ተጠቃሚው እንዲሠራ ያዘዘው ሞዴል ስም
MODEL_NAME = 'gemini-2.5-flash' 

def ask_ethafri_ceo(prompt):
    """Gemini 2.5 Flash ን ይጠቀማል፣ ካልሰራ ወደ Groq ይቀይራል"""
    try:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
    except Exception as e:
        print(f"⚠️ Gemini Error: {e}")

    try:
        if settings.GROQ_API_KEY:
            client = Groq(api_key=settings.GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Groq Error: {e}")
    return None

def run_daily_market_analysis():
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        return "❌ አድሚን አልተገኘም።"

    # ትዕዛዙ (Prompt) የሪፖርት ስሞችን (Keys) በትክክል እንዲሰጥ ተስተካክሏል
    ceo_prompt = f"""
    አንተ የ EthAfri ራስ-ገዝ CEO ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. ቅድሚያ የሚሰጠውን ስራ ወስን (Design, Market, or Global)።
    2. የዲዛይን ለውጥ ካለ JSON ስጠኝ።
    3. አንድ ምርት መርጠህ በ 7 ቋንቋዎች መግለጫ ጻፍ።
    4. ምርቱ ፎቶ እንዲኖረው 3 የእንግሊዝኛ Keywords ስጠኝ።

    መልስህን በዚህ JSON ብቻ አቅርብ (ከJSON ውጭ ምንም ጽሁፍ አትጨምር)፦
    {{
      "task_name": "የተግባሩ ስም",
      "priority_reason": "ይህ ስራ ለምን እንደቀደመ ዝርዝር ማብራሪያ",
      "ui_config": {{
          "banner_title": "አዲስ ባነር", "banner_sub": "ንዑስ ጽሁፍ", "theme_color": "#1a2a6c", "logo_text": "EthAfri Smart"
      }},
      "market_entry": {{
          "category": "ምድብ", "title_am": "ርዕስ", "price": 100, "img_keywords": "keywords",
          "translations": {{
              "am": "...", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."
          }}
      }}
    }}
    """

    ai_response = ask_ethafri_ceo(ceo_prompt)
    if not ai_response: return "❌ AI አልሰራም።"

    try:
        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        data = json.loads(match.group(0))

        # --- 1. ዲዛይን ማዘመን ---
        SiteConfig.objects.update_or_create(key="DYNAMIC_UI", defaults={'value': data.get('ui_config', {})})

        # --- 2. ምርት መፍጠር (ምስልን ጨምሮ) ---
        entry = data.get('market_entry', {})
        cat, _ = Category.objects.get_or_create(name=entry.get('category', 'General'))
        
        # ምስል ማግኛ (አስተማማኝው loremflickr)
        img_q = entry.get('img_keywords', 'market').replace(" ", ",")
        image_url = f"https://loremflickr.com/800/600/{img_q}"

        product = Product.objects.create(
            seller=admin_user, category=cat, title=entry.get('title_am', 'New Item'),
            description=entry.get('translations', {}).get('am', 'AI Item'),
            price=entry.get('price', 0), image_url=image_url, is_active=True
        )
        
        # ትርጉም ማስቀመጥ
        t = entry.get('translations', {})
        ProductTranslation.objects.create(
            product=product, am=t.get('am'), en=t.get('en'), om=t.get('om'),
            ar=t.get('ar'), so=t.get('so'), ti=t.get('ti'), fr=t.get('fr')
        )

        # --- 3. ሪፖርት መመዝገብ (ስሞቹ ተስተካክለዋል) ---
        AISystemTask.objects.create(
            task_name=data.get('task_name', 'System Update'),
            priority_reason=data.get('priority_reason', 'Normal growth flow'),
            status='Completed'
        )

        return f"✅ EthAfri Evolved: {data.get('task_name')}."
    except Exception as e:
        return f"⚠️ Logic Error: {str(e)}"
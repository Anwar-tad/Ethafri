# EthAfri/marketplace/growth_agent.py

import google.generativeai as genai
from groq import Groq
import json, datetime, re, requests
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product, ProductTranslation, SiteConfig, AISystemTask
from django.contrib.auth.models import User

# በእርስዎ መመሪያ መሰረት የሚሰራው ብቸኛው ሞዴል
MODEL_NAME = 'gemini-2.5-flash' 

def ask_ethafri_ceo(prompt):
    """Gemini 2.5 Flash ን ይጠቀማል፣ ካልሰራ ወደ Groq ይቀይራል"""
    # 1. Gemini 2.5 Flash ሙከራ
    try:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Error: {e}")

    # 2. Groq (Llama 3.3) እንደ ቤካፕ
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
    """
    EthAfri Autonomous CEO: ራሱን የሚገነባ፣ ዲዛይን የሚቀይር እና ገበያ የሚያጠና ሞተር
    """
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        return "❌ አድሚን አልተገኘም። እባክዎ መጀመሪያ create_admin.py ይኑር።"

    ceo_prompt = f"""
    አንተ የ EthAfri (ኢቲአፍሪ) ራስ-ገዝ CEO እና ዲዛይነር ነህ። ዛሬ {now} ነው።
    ዌብሳይቱ 'ከመርፌ እስከ መርከብ' የሚሸጥበት ግሎባል ማርኬት እንዲሆን ነው አላማው።

    ተግባርህ፦
    1. ቅድሚያ የሚሰጠውን ስራ ወስን (ዲዛይን ማሻሻል፣ አዲስ ገበያ ማጥናት፣ ወይም ቋንቋ ማስፋፋት)።
    2. የዌብሳይቱን UI (Logo Text, Banner, Primary Color) የሚቀይር አዲስ JSON አዘጋጅ።
    3. አንድ አዲስ ምርት መርጠህ በ 7 ቋንቋዎች (AM, EN, OM, AR, SO, TI, FR) መግለጫ ጻፍ።
    4. ለእቃው የሚሆን Unsplash Image Search Keywords ስጠኝ።

    መልስህን በዚህ JSON ብቻ አቅርብ (መግቢያ ወሬ አትጨምር)፦
    {{
      "priority_decision": "ለምን ይህ ስራ እንደቀደመ ማብራሪያ",
      "ui_design": {{
          "banner_title": "ማራኪ ባነር ጽሁፍ",
          "banner_sub": "ንዑስ ጽሁፍ",
          "theme_color": "#1a2a6c",
          "logo_text": "EthAfri Smart"
      }},
      "market_entry": {{
          "category": "ምድብ ስም",
          "title_am": "የእቃው ስም በአማርኛ",
          "price": 500,
          "img_keywords": "product keywords for image",
          "translations": {{
              "am": "...", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."
          }}
      }},
      "seo_keywords": ["keyword1", "keyword2"]
    }}
    """

    ai_response = ask_ethafri_ceo(ceo_prompt)
    if not ai_response:
        return "❌ AI ሞተሮች አልሰሩም። API ቁልፎችን አረጋግጥ።"

    try:
        # JSONን መለየት
        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        data = json.loads(match.group(0))

        # --- 1. ዲዛይን ኦቶሜሽን ---
        SiteConfig.objects.update_or_create(
            key="DYNAMIC_UI",
            defaults={'value': data.get('ui_design', {})}
        )

        # --- 2. የገበያ እና የቋንቋ ዕድገት ---
        entry = data.get('market_entry', {})
        cat, _ = Category.objects.get_or_create(name=entry.get('category', 'General'))
        
        # ምስል ከ Unsplash በራሱ ማገናኘት
        img_q = entry.get('img_keywords', 'marketplace')
        image_url = f"https://source.unsplash.com/800x600/?{img_q}"

        product = Product.objects.create(
            seller=admin_user,
            category=cat,
            title=entry.get('title_am', 'New Growth Item'),
            description=entry.get('translations', {}).get('am', 'በ AI የተጠቆመ'),
            price=entry.get('price', 0),
            image_url=image_url,
            location="Global / ኢትዮጵያ",
            is_active=True,
            ai_tags=data.get('seo_keywords', [])
        )

        # በ 7 ቋንቋዎች መመዝገብ
        trans = entry.get('translations', {})
        ProductTranslation.objects.create(
            product=product,
            am=trans.get('am', ''),
            en=trans.get('en', ''),
            om=trans.get('om', ''),
            ar=trans.get('ar', ''),
            so=trans.get('so', ''),
            ti=trans.get('ti', ''),
            fr=trans.get('fr', '')
        )

        # --- 3. SEO እና Task Logging ---
        for kw in data.get('seo_keywords', []):
            UserSearch.objects.get_or_create(query=kw.strip())

        AISystemTask.objects.create(
            task_name=f"CEO Autonomous Update: {cat.name}",
            priority_reason=data.get('priority_decision', 'Daily Growth'),
            status='Completed'
        )

        return f"✅ EthAfri Evolved: CEO Priority - {data.get('priority_decision')[:60]}..."

    except Exception as e:
        return f"⚠️ CEO Logic Error: {str(e)} | AI Raw: {ai_response[:50]}"
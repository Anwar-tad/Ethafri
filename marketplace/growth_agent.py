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
    """Gemini 2.5 Flash ን ይጠቀማል፣ ካልሰራ ወደ Groq ይቀይራል (Failover)"""
    # 1. Try Gemini 2.5 Flash
    try:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
    except Exception as e:
        print(f"⚠️ Gemini 2.5 Error: {e}")

    # 2. Try Groq (Llama 3.3) as Backup
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
    EthAfri Autonomous CEO: ራሱን የሚገነባ፣ ዲዛይን የሚቀይር እና ገበያ የሚያጠና ዋና ሞተር
    """
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    
    if not admin_user:
        return "❌ አድሚን አልተገኘም። መጀመሪያ Superuser መፈጠሩን ያረጋግጡ።"

    # AIው ስራዎችን በቅደም ተከተል እንዲያከናውን የሚሰጥ ዝርዝር ትዕዛዝ
    ceo_prompt = f"""
    አንተ የ EthAfri.com ራስ-ገዝ CEO እና ዲዛይነር ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. የዌብሳይቱን ወቅታዊ ሁኔታ መርምርና ቅድሚያ የሚሰጠውን ስራ ወስን (Design, Market Study, or Language Expansion)።
    2. የዲዛይን ለውጥ ካለ (Logo text, Banner, Theme color) አዲስ JSON ዳታ ስጠኝ።
    3. አንድ ትርፋማ ምርት መርጠህ በ 7 ቋንቋዎች (AM, EN, OM, AR, SO, TI, FR) መግለጫ ጻፍ።
    4. ለምርቱ የሚሆን Unsplash Image Search Keywords ስጠኝ።

    መልስህን በዚህ JSON ብቻ አቅርብ (ከJSON ውጭ ምንም ጽሁፍ አትጨምር)፦
    {{
      "task": "የተግባሩ ስም",
      "priority_reason": "ይህ ተግባር ለምን እንደቀደመ ማብራሪያ",
      "ui_config": {{
          "banner_title": "ባነር ጽሁፍ",
          "banner_sub": "ንዑስ ጽሁፍ",
          "theme_color": "#1a2a6c",
          "logo_text": "EthAfri Smart"
      }},
      "market_entry": {{
          "category": "ምድብ",
          "title_am": "ርዕስ",
          "price": 0,
          "img_keywords": "product keywords",
          "translations": {{
              "am": "...", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."
          }}
      }}
    }}
    """

    ai_response = ask_ethafri_ceo(ceo_prompt)
    if not ai_response:
        return "❌ AI ሞተሮች አልሰሩም። API ቁልፎችን አረጋግጥ።"

    try:
        # JSONን ከጽሁፉ ውስጥ ፈልጎ ማውጣት
        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        data = json.loads(match.group(0))

        # --- 1. ዲዛይን ኦቶሜሽን (Dynamic UI) ---
        ui_data = data.get('ui_config', {})
        SiteConfig.objects.update_or_create(
            key="DYNAMIC_UI",
            defaults={'value': ui_data}
        )

        # --- 2. የገበያ እና የቋንቋ ዕድገት ---
        entry = data.get('market_entry', {})
        cat_name = entry.get('category', 'General').strip()
        cat, _ = Category.objects.get_or_create(name=cat_name)
        
        # ምስል ከ Unsplash በራሱ ማገናኘት
        img_q = entry.get('img_keywords', 'marketplace').replace(" ", ",")
        image_url = f"https://source.unsplash.com/800x600/?{img_q}"

        # ምርቱን መፍጠር
        product = Product.objects.create(
            seller=admin_user,
            category=cat,
            title=entry.get('title_am', 'New Growth Item'),
            description=entry.get('translations', {}).get('am', 'በ AI የተጠቆመ'),
            price=entry.get('price', 0),
            image_url=image_url,
            location="Global / ኢትዮጵያ",
            is_active=True
        )

        # በ 7 ቋንቋዎች መመዝገብ
        trans = entry.get('translations', {})
        ProductTranslation.objects.create(
            product=product,
            am=trans.get('am', ''), en=trans.get('en', ''), om=trans.get('om', ''),
            ar=trans.get('ar', ''), so=trans.get('so', ''), ti=trans.get('ti', ''),
            fr=trans.get('fr', '')
        )

        # --- 3. ዝርዝር ተግባር መመዝገብ (ለሪፖርት ገጹ) ---
        log_reason = f"ውሳኔ፦ {data.get('priority_reason')}\n\nየተቀየረ ኮድ፦ {json.dumps(ui_data, indent=2)}"
        AISystemTask.objects.create(
            task_name=data.get('task', 'EthAfri System Update'),
            priority_reason=log_reason,
            status='Completed'
        )

        return f"✅ EthAfri Evolved: Priority set to '{data.get('task')}'. New item added with image."

    except Exception as e:
        return f"⚠️ CEO Logic Error: {str(e)} | Raw: {ai_response[:50]}"
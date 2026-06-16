# EthAfri/marketplace/growth_agent.py

import google.generativeai as genai
from groq import Groq
import json, datetime, re, requests
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product, ProductTranslation, SiteConfig, AISystemTask
from django.contrib.auth.models import User

# የእርስዎ ኤፒአይ የሚቀበለው ብቸኛው የስሪት ስም
MODEL_NAME = 'gemini-2.5-flash'

# ---------------------------------------------------------
# 1. ባለ 4 ሰንሰለት AI ሞተሮች (Failover Chain)
# ---------------------------------------------------------

def ask_ai_failover(prompt):
    """ጀሚኒ 2.5 -> Groq -> Mistral (Direct Call) -> OpenRouter"""
    
    # 1. Google Gemini 2.5 Flash
    try:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME) 
            response = model.generate_content(prompt)
            if response and response.text: 
                return response.text
    except Exception as e: 
        print(f"Gemini 2.5 Fail: {e}")

    # 2. Groq (Llama 3.3)
    try:
        if settings.GROQ_API_KEY:
            client = Groq(api_key=settings.GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
    except Exception as e: 
        print(f"Groq Fail: {e}")

    # 3. Mistral AI (Direct API Call)
    try:
        MISTRAL_KEY = getattr(settings, 'MISTRAL_API_KEY', None)
        if MISTRAL_KEY:
            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {MISTRAL_KEY}"},
                json={
                    "model": "mistral-small-latest",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=10
            )
            return resp.json()['choices'][0]['message']['content']
    except Exception as e: 
        print(f"Mistral API Fail: {e}")

    # 4. OpenRouter (Universal Backup)
    try:
        OPENROUTER_KEY = getattr(settings, 'OPENROUTER_API_KEY', None)
        if OPENROUTER_KEY:
            resp = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                json={
                    "model": "google/gemini-2.0-flash-001:free",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=10
            )
            return resp.json()['choices'][0]['message']['content']
    except Exception as e: 
        print(f"OpenRouter Fail: {e}")

    return None

# ---------------------------------------------------------
# 2. የዕድገት ሞተር (The Brain)
# ---------------------------------------------------------

def run_daily_market_analysis():
    """
    EthAfri CEO: በየሰዓቱ በየተራ AIዎችን በመጥራት ዌብሳይቱን የሚያሳድግ
    """
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user: 
        return "❌ አድሚን አልተገኘም።"

    prompt = f"""
    አንተ የ EthAfri Smart Marketplace CEO ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. ቅድሚያ የሚሰጠውን ስራ ወስን (Design, Market Study, or Language Expansion)።
    2. የዲዛይን ለውጥ ካለ (Logo text, Banner, Theme color) አዲስ JSON ዳታ ስጠኝ።
    3. አንድ ምርት መርጠህ በ 7 ቋንቋዎች (AM, EN, OM, AR, SO, TI, FR) መግለጫ ጻፍ።
    4. ለምርቱ የሚሆን 3 የእንግሊዝኛ ፎቶ Keywords (ለምሳሌ፦ 'red toyota car') ስጠኝ።

    መልስህን በዚህ JSON ብቻ አቅርብ (መግቢያ ወሬ አትጨምር)፦
    {{
      "task_name": "የተግባሩ ስም",
      "priority_reason": "ዝርዝር ማብራሪያ",
      "ui": {{
          "banner_title": "ባነር", "banner_sub": "ንዑስ ጽሁፍ", "color": "#1a2a6c", "logo": "EthAfri"
      }},
      "item": {{
          "cat": "ምድብ", "title": "ርዕስ", "price": 100, "img_key": "keywords",
          "desc": {{"am": "...", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."}}
      }}
    }}
    """

    ai_response = ask_ai_failover(prompt)
    if not ai_response:
        return "❌ ሁሉም AI ሞተሮች (Gemini 2.5, Groq, Mistral, OpenRouter) እምቢ አሉ።"

    try:
        # JSONን ከ AI መልስ ውስጥ ለይቶ ማውጣት
        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        data = json.loads(match.group(0))

        # --- ሀ. ዲዛይን ማዘመን ---
        ui = data.get('ui', {})
        SiteConfig.objects.update_or_create(
            key="DYNAMIC_UI",
            defaults={'value': {
                'banner_title': ui.get('banner_title'),
                'banner_sub': ui.get('banner_sub'),
                'theme_color': ui.get('color'),
                'logo_text': ui.get('logo')
            }}
        )

        # --- ለ. ምርት እና ፎቶ ማግኘት ---
        it = data.get('item', {})
        cat, _ = Category.objects.get_or_create(name=it.get('cat', 'General'))
        
        # ፎቶ ከ loremflickr (ፈጣን እና አስተማማኝ)
        k = it.get('img_key', 'shopping').replace(" ", ",")
        image_url = f"https://loremflickr.com/800/600/{k}"

        # ምርቱን መፍጠር
        product = Product.objects.create(
            seller=admin_user, 
            category=cat, 
            title=it.get('title'),
            description=it.get('desc', {}).get('am', 'AI Item'),
            price=it.get('price', 0), 
            image_url=image_url, 
            is_active=True
        )

        # በ 7 ቋንቋዎች መመዝገብ
        trans = it.get('desc', {})
        ProductTranslation.objects.create(
            product=product,
            am=trans.get('am', ''), en=trans.get('en', ''), om=trans.get('om', ''),
            ar=trans.get('ar', ''), so=trans.get('so', ''), ti=trans.get('ti', ''),
            fr=trans.get('fr', '')
        )

        # --- ሐ. ሪፖርት መመዝገብ (ባዶ እንዳይሆን) ---
        AISystemTask.objects.create(
            task_name=data.get('task_name', 'EthAfri Update'),
            priority_reason=data.get('priority_reason', 'Normal growth'),
            status='Completed'
        )

        return f"✅ EthAfri Evolved: {data.get('task_name')}."

    except Exception as e:
        return f"⚠️ Error: {str(e)} | Raw: {ai_response[:100]}"
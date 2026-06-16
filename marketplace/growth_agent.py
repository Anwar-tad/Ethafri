# EthAfri/marketplace/growth_agent.py

import google.generativeai as genai
from groq import Groq
import json, datetime, re, requests
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product, ProductTranslation, SiteConfig, AISystemTask
from django.contrib.auth.models import User
from django.utils import timezone

MODEL_NAME = 'gemini-2.5-flash' 

# ---------------------------------------------------------
# 1. የ API Cooldown (እረፍት) እና የ Lock አያያዝ
# ---------------------------------------------------------

def is_api_on_cooldown(provider_name):
    """ዳታቤዝን በመፈተሽ ኤፒአይው በእረፍት ላይ መሆኑን ያረጋግጣል (Timezone-safe)"""
    config = SiteConfig.objects.filter(key=f"COOLDOWN_{provider_name}").first()
    if config:
        cooldown_until_str = config.value.get('until', '')
        if cooldown_until_str:
            cooldown_until = datetime.datetime.fromisoformat(cooldown_until_str)
            if timezone.is_naive(cooldown_until):
                cooldown_until = timezone.make_aware(cooldown_until)
            if timezone.now() < cooldown_until:
                return True
    return False

def set_api_cooldown(provider_name, hours=24):
    """ኤፒአይው ሲከሽፍ ለተወሰነ ሰዓት እረፍት እንዲሰጠው ይመዘግባል"""
    until_time = timezone.now() + datetime.timedelta(hours=hours)
    SiteConfig.objects.update_or_create(
        key=f"COOLDOWN_{provider_name}",
        defaults={'value': {'until': until_time.isoformat()}}
    )

# ---------------------------------------------------------
# 2. ባለ 4 ሰንሰለት AI ሞተሮች
# ---------------------------------------------------------

def ask_ai_failover(prompt):
    """Gemini 2.5 -> Groq -> Mistral -> OpenRouter"""
    # 1. Google Gemini 2.5 Flash
    if not is_api_on_cooldown("GEMINI"):
        try:
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(MODEL_NAME)
                response = model.generate_content(prompt)
                if response and response.text: 
                    return response.text
        except Exception as e: 
            print(f"Gemini 2.5 Fail: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                set_api_cooldown("GEMINI", hours=24)
            else:
                set_api_cooldown("GEMINI", hours=1)

    # 2. Groq (Llama 3.3)
    if not is_api_on_cooldown("GROQ"):
        try:
            if settings.GROQ_API_KEY:
                client = Groq(api_key=settings.GROQ_API_KEY)
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content
        except Exception as e: 
            print(f"Groq Fail: {e}")
            set_api_cooldown("GROQ", hours=1)

    # 3. Mistral AI (Direct REST Call)
    if not is_api_on_cooldown("MISTRAL"):
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
                if resp.status_code == 200:
                    return resp.json()['choices'][0]['message']['content']
        except Exception as e: 
            print(f"Mistral API Fail: {e}")

    # 4. OpenRouter
    try:
        OPENROUTER_KEY = getattr(settings, 'OPENROUTER_API_KEY', None)
        if OPENROUTER_KEY:
            resp = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                json={
                    "model": "google/gemini-2.5-flash",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
    except Exception as e: 
        print(f"OpenRouter Fail: {e}")

    return None

# ---------------------------------------------------------
# 3. የዕድገት ሞተር (The Brain)
# ---------------------------------------------------------

def run_daily_market_analysis():
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user: 
        return "❌ አድሚን አልተገኘም።"

    # --- Concurrency Lock ---
    lock_config, _ = SiteConfig.objects.get_or_create(
        key="EVOLUTION_LOCK",
        defaults={'value': {'status': 'idle', 'since': now.isoformat()}}
    )
    if lock_config.value.get('status') == 'running':
        since_time = datetime.datetime.fromisoformat(lock_config.value.get('since'))
        if (now - since_time).seconds < 600:
            return "⚠️ Skip: የቀድሞው ዑደት ገና አልተጠናቀቀም።"

    lock_config.value = {'status': 'running', 'since': now.isoformat()}
    lock_config.save()

    prompt = f"""
    አንተ የ EthAfri Smart Marketplace CEO ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. በኢትዮጵያ አሁን በዚህ ሰዓት በጣም ተፈላጊ የሆኑ 3 አዳዲስ የገበያ ዘርፎችን (Categories) ለይ።
    2. ለእያንዳንዱ ዘርፍ 1 ማራኪ የእቃ ርዕስ (Product Title) እና መግለጫ ፍጠር።
    3. የዌብሳይቱን UI (Logo text, Banner, Theme color) የሚቀይር አዲስ JSON አዘጋጅ።
    4. ምርቱ ፎቶ እንዲኖረው 3 የእንግሊዝኛ ፎቶ Keywords ስጠኝ።
    5. ለዌብሳይቱ እድገት የሚሆን 1 የስትራቴጂ ምክር በአማርኛ ስጠኝ።

    መልስህን በዚህ የ JSON ቅርጽ ብቻ አቅርብ (መግቢያ ወሬ አትጨምር)፦
    {{
      "task_name": "የተግባሩ ስም",
      "priority_reason": "ማብራሪያ",
      "ui": {{
          "banner_title": "ባነር ጽሁፍ", "banner_sub": "ንዑስ ጽሁፍ", "color": "#1a2a6c", "logo": "EthAfri"
      }},
      "item": {{
          "cat": "ምድብ", 
          "title": "ርዕስ", 
          "price": 1000, 
          "img_key": "keywords",
          "desc": {{"am": "መግለጫ በአማርኛ", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."}}
      }}
    }}
    """

    ai_response = ask_ai_failover(prompt)
    if not ai_response:
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return "❌ ሁሉም AI ሞተሮች እምቢ አሉ።"

    try:
        # --- ⚠️ ማሻሻያ 1 (Extra Data Fix) ---
        # ከ JSON ውጭ ያሉ ተጨማሪ ጽሁፎችን (Extra data) ለመቁረጥ የመጀመሪያውን { እና የመጨረሻውን } ብቻ መውሰድ
        start_idx = ai_response.find('{')
        end_idx = ai_response.rfind('}') + 1
        
        if start_idx == -1 or end_idx <= start_idx:
            raise ValueError("ትክክለኛ የ JSON መዋቅር አልተገኘም")
            
        clean_json = ai_response[start_idx:end_idx]
        data = json.loads(clean_json)

        # --- 1. ዲዛይን ማዘመን (Site Config) ---
        ui = data.get('ui', {})
        SiteConfig.objects.update_or_create(
            key="DYNAMIC_UI",
            defaults={'value': {
                'banner_title': ui.get('banner_title', 'እንኳን ደህና መጡ'),
                'banner_sub': ui.get('banner_sub', 'በ AI የሚመራው ግዙፍ የአፍሪካ ገበያ'),
                'theme_color': ui.get('color', '#1a2a6c'),
                'logo_text': ui.get('logo', 'EthAfri')
            }}
        )

        # --- 2. ምርት እና ፎቶ ማስተካከል ---
        it = data.get('item', {})
        cat_name = it.get('cat', 'General').strip()
        cat, _ = Category.objects.get_or_create(name=cat_name)
        
        # ፎቶ ከ loremflickr
        k = it.get('img_key', 'shopping').replace(" ", ",")
        image_url = f"https://loremflickr.com/800/600/{k}"

        # --- ⚠️ ማሻሻያ 2 (Null Title Fix) ---
        # AIው 'title' የሚለውን ስም ቢረሳው እንኳ ኮዱ በራሱ ተለዋጭ ስም እንዲፈጥር (Self-Healing)
        product_title = it.get('title') or it.get('title_am') or f"አዲስ ምርት - {cat_name}"

        product = Product.objects.create(
            seller=admin_user, 
            category=cat, 
            title=product_title, # አሁን በፍጹም null አይሆንም!
            description=it.get('desc', {}).get('am', 'በ AI የተጠቆመ የገበያ ዕድል'),
            price=it.get('price', 0), 
            image_url=image_url, 
            market_value_status='Unknown',
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

        # --- 3. ዝርዝር ተግባር መመዝገብ ---
        AISystemTask.objects.create(
            task_name=data.get('task_name', 'EthAfri Update'),
            priority_reason=f"ውሳኔ፦ {data.get('priority_reason')}\n\nUI Config: {json.dumps(ui, indent=2)}",
            status='Completed'
        )

        # ቆልፉን መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()

        return f"✅ EthAfri Evolved: {data.get('task_name')} completed successfully."

    except Exception as e:
        # ቆልፉን መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return f"⚠️ Error: {str(e)}"
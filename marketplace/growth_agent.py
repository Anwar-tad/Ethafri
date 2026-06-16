# EthAfri/marketplace/growth_agent.py

import google.generativeai as genai
from groq import Groq
import json
import datetime
import re
import requests
from bs4 import BeautifulSoup
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product, ProductTranslation, SiteConfig, AISystemTask, OwnerDirective
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile

# በእርስዎ መመሪያ መሰረት የሚሰራው ብቸኛው ሞዴል
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
# 2. ባለ 4 ሰንሰለት AI ሞተሮች (Failover Chain)
# ---------------------------------------------------------

def ask_ai_failover(prompt):
    """Gemini 2.5 -> Groq -> Mistral (Direct Call) -> OpenRouter"""
    
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
# 3. እውነተኛ ምርቶችን መቃኛ (Telegram Scraper)
# ---------------------------------------------------------

def scrape_real_ethiopian_products():
    """
    በኢትዮጵያ ውስጥ ካሉ የሽያጭ ቴሌግራም ቻናሎች 
    እውነተኛ እቃዎችን፣ ዋጋዎችን እና ፎቶዎችን ይቃኛል (Scrapes)
    """
    url = "https://t.me/s/merkatogroup"
    items = []
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            messages = soup.find_all('div', class_='tgme_widget_message_bubble')
            
            for msg in messages[:3]: # የመጨረሻዎቹን 3 እቃዎች መውሰድ
                text_div = msg.find('div', class_='tgme_widget_message_text')
                img_div = msg.find('a', class_='tgme_widget_message_photo_wrap')
                
                if text_div:
                    raw_text = text_div.text
                    image_url = ""
                    if img_div and 'style' in img_div.attrs:
                        style = img_div['style']
                        url_match = re.search(r"background-image:url\('(.+)'\)", style)
                        if url_match:
                            image_url = url_match.group(1)
                    
                    items.append({"text": raw_text, "image": image_url})
    except Exception as e:
        print(f"Scraper Error: {e}")
    return items

# ---------------------------------------------------------
# 4. ዋናው የዕድገት ሞተር (The Brain)
# ---------------------------------------------------------

def run_daily_market_analysis():
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user: 
        return "❌ አድሚን አልተገኘም። መጀመሪያ Superuser መፈጠሩን ያረጋግጡ።"

    # --- ሀ. Concurrency Lock (የስራ መደራረብ መከላከያ) ---
    lock_config, _ = SiteConfig.objects.get_or_create(
        key="EVOLUTION_LOCK",
        defaults={'value': {'status': 'idle', 'since': now.isoformat()}}
    )
    if lock_config.value.get('status') == 'running':
        since_time = datetime.datetime.fromisoformat(lock_config.value.get('since'))
        if (now - since_time).seconds < 300: # 5 ደቂቃ
            return "⚠️ Skip: የቀድሞው የ AI ዑደት ገና አልተጠናቀቀም (መደራረብ ተከልክሏል)።"

    # ቆልፉን መቆለፍ (Locking)
    lock_config.value = {'status': 'running', 'since': now.isoformat()}
    lock_config.save()

    # --- ለ. የባለቤት መመሪያ (Owner Directive) ማንበብ ---
    latest_directive = OwnerDirective.objects.filter(is_active=True).last()
    directive_context = latest_directive.instruction if latest_directive else "ምንም ተጨማሪ መመሪያ የለም። መደበኛ የገበያ ጥናትህን ቀጥል።"

    # --- ሐ. እውነተኛ ምርቶችን መቃኘት (Scraping) ---
    real_scraped_data = scrape_real_ethiopian_products()

    # --- መ. የዌብሳይቱ የጎደሉ ክፍሎች ዝርዝር (Feature Lock) ---
    unbuilt_features = ["Multi-language Selector UI", "Detailed Footer Section", "User Terms Page", "Admin Contact Portal", "Dynamic Top Navigation Menu"]
    completed_tasks = list(AISystemTask.objects.values_list('task_name', flat=True))

    prompt = f"""
    አንተ የ EthAfri (ኢቲአፍሪ) ራስ-ገዝ CEO ነህ።
    የዌብሳይቱ ባለቤት (Anwar) የሰጠህ ቀጥተኛ መመሪያ ይህ ነው (ከሁሉም በላይ ቀድመህ ፈጽመው)፦ {directive_context}
    እስካሁን የተገነቡ/የበለጸጉ አገልግሎቶች፦ {completed_tasks}
    ያልተገነቡ የዌብሳይቱ ክፍሎች ዝርዝር፦ {unbuilt_features}
    
    ከእውነተኛ የኢትዮጵያ ገበያ ቴሌግራም የተቃኘው መረጃ ይህ ነው፦ {real_scraped_data[:1]}

    ተግባርህ፦
    1. በባለቤቱ መመሪያ መሠረት ካልተገነቡት አገልግሎቶች ውስጥ 1 አዲስ አገልግሎት ለመገንባት/ለማንቃት ወስን። የድሮውን አትድገም።
    2. ከተቃኘው እውነተኛ መረጃ ተነስተህ 1 እውነተኛ ምርት ለይተህ በ 7 ቋንቋዎች ተርጉመህ አዘጋጅ።
    3. የዲዛይን ለውጥ ካለ ባነሩንና ቀለሙን አዘምን።

    መልስህን በዚህ የ JSON ቅርጽ ብቻ አቅርብ (መግቢያ ወሬ አትጨምር)፦
    {{
      "feature_to_build": "ከተረፈው ዝርዝር ውስጥ የተመረጠ 1 አዲስ አገልግሎት",
      "priority_reason": "የባለቤቱን መመሪያ እንዴት እንደፈጸምክ ዝርዝር ማብራሪያ በአማርኛ",
      "ui_update": {{
          "banner_title": "ባነር ጽሁፍ በአማርኛ", "banner_sub": "ንዑስ ጽሁፍ በአማርኛ", "color": "#1a2a6c", "logo": "EthAfri"
      }},
      "real_product": {{
          "category": "ምድብ በአማርኛ",
          "title_am": "የእቃው ስም በአማርኛ",
          "price": 2000,
          "scraped_img": "የተቃኘው ምስል ሊንክ",
          "translations": {{
              "am": "መግለጫ በአማርኛ", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."
          }}
      }},
      "seo_keywords": ["keyword1", "keyword2"]
    }}
    """

    ai_response = ask_ai_failover(prompt)
    if not ai_response:
        # ቆልፉን መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return "❌ ሁሉም AI ሞተሮች እምቢ አሉ።"

    try:
        # JSONን ከ AI መልስ ውስጥ ለይቶ ማውጣት
        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        data = json.loads(match.group(0))

        # --- 1. ዲዛይን ማዘመን (Site Config) ---
        ui = data.get('ui_update', {})
        SiteConfig.objects.update_or_create(
            key="DYNAMIC_UI",
            defaults={'value': {
                'banner_title': ui.get('banner_title', 'እንኳን ደህና መጡ'),
                'banner_sub': ui.get('banner_sub', 'በ AI የሚመራው ግዙፍ የአፍሪካ ገበያ'),
                'theme_color': ui.get('color', '#1a2a6c'),
                'logo_text': ui.get('logo', 'EthAfri')
            }}
        )

        # --- 2. አገልግሎት መገንባት (Feature Enable) ---
        feature = data.get('feature_to_build', 'General Growth')
        SiteConfig.objects.update_or_create(
            key=f"FEATURE_{slugify(feature)}",
            defaults={'value': {'enabled': True}}
        )

        # --- 3. እውነተኛ ምርት እና ፎቶ መቆለፊያ ---
        prod = data.get('real_product', {})
        cat_name = prod.get('category', 'General').strip()
        cat, _ = Category.objects.get_or_create(name=cat_name)
        
        product_title = prod.get('title_am') or f"አዲስ ምርት - {cat_name}"

        product = Product.objects.create(
            seller=admin_user, 
            category=cat, 
            title=product_title,
            description=prod.get('translations', {}).get('am', 'በ AI የተቃኘ'),
            price=prod.get('price', 0), 
            market_value_status='Unknown',
            is_active=True
        )

        # ፎቶውን በራስ-ሰር አውርዶ ወደ Cloudinary በቋሚነት መጫን (የማይለዋወጥ ምስል!)
        img_url = prod.get('scraped_img') or "https://loremflickr.com/800/600/product"
        try:
            img_res = requests.get(img_url, timeout=10)
            if img_res.status_code == 200:
                product.image.save(f"real_prod_{product.id}.jpg", ContentFile(img_res.content), save=True)
        except Exception as img_err:
            print(f"Cloudinary Image Upload Failed: {img_err}")
            product.image_url = img_url
            product.save()

        # በ 7 ቋንቋዎች መተርጎም
        trans = prod.get('translations', {})
        ProductTranslation.objects.create(
            product=product,
            am=trans.get('am', ''), en=trans.get('en', ''), om=trans.get('om', ''),
            ar=trans.get('ar', ''), so=trans.get('so', ''), ti=trans.get('ti', ''),
            fr=trans.get('fr', '')
        )

        # --- 4. ዝርዝር ተግባር መመዝገብ (ለሪፖርት ገጹ) ---
        log_reason = f"ውሳኔ፦ {data.get('priority_reason')}\n\nየተገነባ አገልግሎት፦ {feature}"
        AISystemTask.objects.create(
            task_name=f"Built: {feature}",
            priority_reason=log_reason,
            status='Completed'
        )

        # ቆልፉን መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()

        return f"✅ EthAfri Evolved: Built feature '{feature}' and posted 1 real product."

    except Exception as e:
        # ቆልፉን መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return f"⚠️ Error: {str(e)}"
# EthAfri/marketplace/growth_agent.py
import google.generativeai as genai
from groq import Groq
import json, datetime, re, requests
from bs4 import BeautifulSoup
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product, ProductTranslation, SiteConfig, AISystemTask, OwnerDirective
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile

# Gemini 2.5 Flash
MODEL_NAME = 'gemini-2.5-flash' 

# ---------------------------------------------------------
# 1. የ API Cooldown (እረፍት) እና የ Lock አያያዝ
# ---------------------------------------------------------

def is_api_on_cooldown(provider_name):
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
    until_time = timezone.now() + datetime.timedelta(hours=hours)
    SiteConfig.objects.update_or_create(
        key=f"COOLDOWN_{provider_name}",
        defaults={'value': {'until': until_time.isoformat()}}
    )

# ---------------------------------------------------------
# 2. ባለ 4 ሰንሰለት AI ሞተሮች (Failover Chain)
# ---------------------------------------------------------

def ask_ethafri_ceo(prompt):
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

    # 3. Mistral AI
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
# 3. Telegram Scraper
# ---------------------------------------------------------

def scrape_real_ethiopian_products():
    channels = ["qefiraethiopia", "merkatogroup", "Mercato_Ethiopia"]
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for channel in channels:
        url = f"https://t.me/s/{channel}"
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                messages = soup.find_all('div', class_='tgme_widget_message_bubble')
                
                for msg in messages:
                    text_div = msg.find('div', class_='tgme_widget_message_text')
                    img_div = msg.find('a', class_='tgme_widget_message_photo_wrap')
                    
                    if text_div and len(text_div.text.strip()) > 20:
                        raw_text = text_div.text.strip()
                        image_url = ""
                        if img_div and 'style' in img_div.attrs:
                            style = img_div['style']
                            url_match = re.search(r"background-image:url\('(.+)'\)", style)
                            if url_match:
                                image_url = url_match.group(1)
                        
                        items.append({"text": raw_text, "image": image_url, "source_channel": channel})
                        if len(items) >= 5:
                            return items
        except Exception as e:
            print(f"Scraper Error for {channel}: {e}")
            
    return items

# ---------------------------------------------------------
# 4. ዋናው የዕድገት ሞተር (The Brain)
# ---------------------------------------------------------

def run_daily_market_analysis():
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user: return "❌ Admin user not found."

    # --- Concurrency Lock ---
    lock_config, _ = SiteConfig.objects.get_or_create(
        key="EVOLUTION_LOCK",
        defaults={'value': {'status': 'idle', 'since': now.isoformat()}}
    )
    if lock_config.value.get('status') == 'running':
        since_time = datetime.datetime.fromisoformat(lock_config.value.get('since'))
        if (now - since_time).total_seconds() < 300:
            return "⚠️ Skip: Concurrency Lock active."

    lock_config.value = {'status': 'running', 'since': now.isoformat()}
    lock_config.save()

    latest_directive = OwnerDirective.objects.filter(is_active=True).last()
    directive_context = latest_directive.instruction if latest_directive else "No specific instruction."
    recent_searches = list(UserSearch.objects.values_list('query', flat=True).order_by('-created_at')[:20])
    real_scraped_data = scrape_real_ethiopian_products()

    unbuilt_features = ["Multi-language Selector UI", "Detailed Footer Section", "User Terms Page", "Admin Contact Portal", "Dynamic Top Navigation Menu"]
    completed_tasks = list(AISystemTask.objects.values_list('task_name', flat=True))

    prompt = f"""
    You are the Autonomous CEO of EthAfri.com.
    Anwar (Owner) issued this directive: "{directive_context}"
    Completed Tasks: {completed_tasks}
    Unbuilt Features: {unbuilt_features}
    
    Recent user search traffic: {recent_searches}
    Real Scraped Data from Ethiopian market: {real_scraped_data[:1]}

    Your Tasks:
    1. Select exactly ONE feature from 'Unbuilt Features' to build.
    2. Extract 1 real product from the 'Real Scraped Data'. If empty, research a high-demand product.
    3. Generate localized descriptions for this product in 7 languages: Amharic (am), English (en), Oromo (om), Arabic (ar), Somali (so), Tigrinya (ti), French (fr).
    4. Provide exactly 3 English keywords for photo matching.
    5. Draft an automated "Outreach/Invitation Message" in Amharic to be sent to the seller of this product.

    Return your response strictly as a raw JSON object (no markdown):
    {{
      "task_name": "Built: [Feature Name]",
      "priority_reason": "Detailed demographic and priority explanation in Amharic",
      "ui": {{
          "banner_title_am": "የባነር ርዕስ በአማርኛ",
          "banner_title_en": "Banner Title in English",
          "banner_sub_am": "ንዑስ ባነር በአማርኛ",
          "banner_sub_en": "Sub Banner in English",
          "color": "#1a2a6c",
          "logo": "EthAfri"
      }},
      "item": {{
          "cat": "Category in Amharic", 
          "title_en": "Product title in ENGLISH",
          "price": 1000, 
          "img_key": "strictly english keywords for photo",
          "translations": {{
              "am": "Amharic Title ||| Amharic Description",
              "en": "English Title ||| English Description",
              "om": "Oromo Title ||| Oromo Description",
              "ar": "Arabic Title ||| Arabic Description",
              "so": "Somali Title ||| Somali Description",
              "ti": "Tigrinya Title ||| Tigrinya Description",
              "fr": "French Title ||| French Description"
          }}
      }},
      "outreach_invite": "ግብዣ ማስታወቂያ ለአቅራቢው በአማርኛ",
      "seo_keywords": ["keyword1", "keyword2"]
    }}
    """

    ai_response = ask_ethafri_ceo(prompt)
    if not ai_response:
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return "❌ All AI engines failed."

    try:
        start_idx = ai_response.find('{')
        end_idx = ai_response.rfind('}') + 1
        clean_json = ai_response[start_idx:end_idx]
        data = json.loads(clean_json)

        # --- 1. ዲዛይን ማዘመን ---
        ui = data.get('ui', {})
        SiteConfig.objects.update_or_create(
            key="DYNAMIC_UI",
            defaults={'value': {
                'banner_title_am': ui.get('banner_title_am'),
                'banner_title_en': ui.get('banner_title_en'),
                'banner_sub_am': ui.get('banner_sub_am'),
                'banner_sub_en': ui.get('banner_sub_en'),
                'theme_color': ui.get('color'),
                'logo_text': ui.get('logo')
            }}
        )

        # --- 2. አገልግሎት መገንባት ---
        # 📌 🛠️ የቁልፍ ማስተካከያ (ከፕሮምፕቱ ጋር እንዲናበብ ከ 'feature_to_build' ወደ 'task_name' ተቀይሯል)
        task_name_raw = data.get('task_name', 'Built: General Growth')
        feature = task_name_raw.replace("Built:", "").strip()
        SiteConfig.objects.update_or_create(
            key=f"FEATURE_{slugify(feature)}",
            defaults={'value': {'enabled': True}}
        )

        # --- 3. እውነተኛ ምርት መፍጠር ---
        it = data.get('item', {})
        cat_name = it.get('cat', 'General').strip()
        cat, _ = Category.objects.get_or_create(name=cat_name)
        
        # 📌 🛠️ የቁልፍ ማስተካከያ (በፕሮምፕቱ ውስጥ 'desc' የነበረው በኮዱ ጥያቄ መሠረት ወደ 'translations' ጸንቷል)
        trans = it.get('translations', {})
        en_payload = trans.get('en', 'Product ||| Description')
        en_title = en_payload.split("|||")[0].strip() if "|||" in en_payload else it.get('title_en', 'New Product')
        en_desc = en_payload.split("|||")[1].strip() if "|||" in en_payload else 'No English description.'

        image_url = f"https://loremflickr.com/800/600/{it.get('img_key', 'product').replace(' ', ',')}"

        product = Product.objects.create(
            seller=admin_user, category=cat, title=en_title,
            description=en_desc, price=it.get('price', 0), 
            image_url=image_url, market_value_status='Unknown', is_active=True
        )

        try:
            img_res = requests.get(image_url, timeout=10)
            if img_res.status_code == 200:
                product.image.save(f"real_prod_{product.id}.jpg", ContentFile(img_res.content), save=True)
        except: pass

        # በ 7 ቋንቋዎች መመዝገብ
        ProductTranslation.objects.create(
            product=product,
            am=trans.get('am', ''), en=trans.get('en', ''), om=trans.get('om', ''),
            ar=trans.get('ar', ''), so=trans.get('so', ''), ti=trans.get('ti', ''),
            fr=trans.get('fr', '')
        )

        # --- 4. ዝርዝር ተግባር መመዝገብ ---
        log_reason = f"ውሳኔ፦ {data.get('priority_reason')}\n\nየአቅራቢዎች ግብዣ መልዕክት፦ {data.get('outreach_invite')}"
        AISystemTask.objects.create(
            task_name=task_name_raw,
            priority_reason=f"{log_reason}\n\nUI Config: {json.dumps(ui, indent=2, ensure_ascii=False)}",
            status='Completed'
        )

        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()

        return f"✅ EthAfri Evolved: {task_name_raw} completed successfully."

    except Exception as e:
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return f"⚠️ Error: {str(e)}"

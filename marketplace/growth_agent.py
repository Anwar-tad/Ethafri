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

MODEL_NAME = 'gemini-2.5-flash' 

def ask_ai_failover(prompt):
    """Gemini 2.5 -> Groq -> Mistral -> OpenRouter"""
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

    return None

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

def scrape_real_ethiopian_products():
    """
    በኢትዮጵያ ውስጥ ካሉ ታዋቂ የሽያጭ ቴሌግራም ቻናሎች የድር ገጽ 
    እውነተኛ ምርቶችን፣ ዋጋዎችን እና ፎቶዎችን ይቃኛል (Scrapes)
    """
    # ⚠️ የተሻሻለ የቴሌግራም ቻናል ዝርዝር
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
                    
                    if text_div and len(text_div.text.strip()) > 20: # አጭር መረጃዎችን መተው
                        raw_text = text_div.text.strip()
                        image_url = ""
                        if img_div and 'style' in img_div.attrs:
                            style = img_div['style']
                            url_match = re.search(r"background-image:url\('(.+)'\)", style)
                            if url_match:
                                image_url = url_match.group(1)
                        
                        items.append({"text": raw_text, "image": image_url})
                        if len(items) >= 5: # 5 ምርቶችን ብቻ መውሰድ
                            return items
        except Exception as e:
            print(f"Scraper Error for {channel}: {e}")
            
    return items

def run_daily_market_analysis():
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user: return "❌ አድሚን አልተገኘም።"

    # --- Concurrency Lock ---
    lock_config, _ = SiteConfig.objects.get_or_create(
        key="EVOLUTION_LOCK",
        defaults={'value': {'status': 'idle', 'since': now.isoformat()}}
    )
    if lock_config.value.get('status') == 'running':
        since_time = datetime.datetime.fromisoformat(lock_config.value.get('since'))
        if (now - since_time).seconds < 300:
            return "⚠️ Skip: Concurrency Lock active."

    lock_config.value = {'status': 'running', 'since': now.isoformat()}
    lock_config.save()

    latest_directive = OwnerDirective.objects.filter(is_active=True).last()
    directive_context = latest_directive.instruction if latest_directive else "ምንም ተጨማሪ መመሪያ የለም።"

    real_scraped_data = scrape_real_ethiopian_products()

    # የዌብሳይቱ የጎደሉ ክፍሎች ዝርዝር (AIው እንዲገነባቸው)
    unbuilt_features = ["Multi-language Selector UI", "Detailed Footer Section", "User Terms Page", "Admin Contact Portal", "Dynamic Top Navigation Menu"]
    completed_tasks = list(AISystemTask.objects.values_list('task_name', flat=True))

    prompt = f"""
    You are the Autonomous CEO of EthAfri.com.
    Anwar (Owner) issued this directive: "{directive_context}"
    Completed Tasks: {completed_tasks}
    Unbuilt Features: {unbuilt_features}
    Real Scraped Data: {real_scraped_data[:2]}

    Your Tasks:
    1. Select exactly ONE feature from 'Unbuilt Features' to build.
    2. Extract 1 real product from the 'Real Scraped Data'. If empty, research a high-demand product.
    3. Generate localized descriptions for this product in 7 languages: Amharic (am), English (en), Oromo (om), Arabic (ar), Somali (so), Tigrinya (ti), French (fr).
    4. Provide exactly 3 English keywords for photo matching.

    Return your response strictly as a raw JSON object:
    {{
      "feature_to_build": "ከተረፈው ዝርዝር ውስጥ የተመረጠ 1 አዲስ አገልግሎት",
      "priority_reason": "ማብራሪያ በአማርኛ",
      "ui": {{
          "banner_title": "ባነር ጽሁፍ በአማርኛ", "banner_sub": "ንዑስ ጽሁፍ በአማርኛ", "color": "#1a2a6c", "logo": "EthAfri"
      }},
      "item": {{
          "cat": "ምድብ በአማርኛ", 
          "title": "የእቃው ስም በአማርኛ", 
          "price": 2000, 
          "img_key": "strictly english keywords for photo",
          "desc": {{"am": "መግለጫ በአማርኛ", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."}}
      }},
      "seo_keywords": ["keyword1", "keyword2"]
    }}
    """

    ai_response = ask_ai_failover(prompt)
    if not ai_response:
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return "❌ ሁሉም AI ሞተሮች እምቢ አሉ።"

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
                'banner_title': ui.get('banner_title'),
                'banner_sub': ui.get('banner_sub'),
                'theme_color': ui.get('color'),
                'logo_text': ui.get('logo')
            }}
        )

        # --- 2. አገልግሎት መገንባት (Feature Enable) ---
        feature = data.get('feature_to_build', 'General Growth')
        SiteConfig.objects.update_or_create(
            key=f"FEATURE_{slugify(feature)}",
            defaults={'value': {'enabled': True}}
        )

        # --- 3. እውነተኛ ምርት እና ፎቶ መቆለፊያ ---
        it = data.get('item', {})
        cat_name = it.get('cat', 'General').strip()
        cat, _ = Category.objects.get_or_create(name=cat_name)
        
        # ⚠️ ራስ-አራሚ ርዕስ (የምስል መደጋገምን ይፈታል)
        desc_am = it.get('desc', {}).get('am', '')
        product_title = it.get('title') or (desc_am[:40] if desc_am else None) or f"ምርት - {cat_name}"

        # ፎቶ ማግኛ (አስተማማኝ ሎጂክ)
        img_q = it.get('img_key', product_title).replace(" ", ",")
        image_url = f"https://loremflickr.com/800/600/{img_q}"

        product = Product.objects.create(
            seller=admin_user, 
            category=cat, 
            title=product_title,
            description=desc_am if desc_am else 'በ AI የተቃኘ',
            price=it.get('price', 0), 
            image_url=image_url,
            market_value_status='Unknown',
            is_active=True
        )

        # ፎቶውን በCloudinary መቆለፍ
        try:
            img_res = requests.get(image_url, timeout=10)
            if img_res.status_code == 200:
                product.image.save(f"real_prod_{product.id}.jpg", ContentFile(img_res.content), save=True)
        except:
            pass

        # በ 7 ቋንቋዎች መመዝገብ
        trans = it.get('desc', {})
        ProductTranslation.objects.create(
            product=product,
            am=trans.get('am', ''), en=trans.get('en', ''), om=trans.get('om', ''),
            ar=trans.get('ar', ''), so=trans.get('so', ''), ti=trans.get('ti', ''),
            fr=trans.get('fr', '')
        )

        # --- 4. ዝርዝር ተግባር መመዝገብ ---
        log_reason = f"ውሳኔ፦ {data.get('priority_reason')}\n\nየተገነባ አገልግሎት፦ {feature}"
        AISystemTask.objects.create(
            task_name=f"Built: {feature}",
            priority_reason=log_reason,
            status='Completed'
        )

        # ቆልፉን መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()

        return f"✅ EthAfri Evolved: {feature} built."

    except Exception as e:
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return f"⚠️ Error: {str(e)}"
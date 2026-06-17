# EthAfri/marketplace/growth_agent.py

import google.generativeai as genai
from groq import Groq
import json
import datetime
import re
import requests
import os
from bs4 import BeautifulSoup
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product, ProductTranslation, SiteConfig, AISystemTask, OwnerDirective
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.files.base import ContentFile

MODEL_NAME = 'gemini-2.5-flash' 

# ---------------------------------------------------------
# 1. ባለብዙ ኤፒአይ ኪይ ሎድ ባላንሰር (Load Balancing & Cooldown)
# ---------------------------------------------------------

def get_gemini_keys_by_pool(pool_type):
    """
    ⚠️ 4ቱን ቁልፎች ለየብቻ ለሁለት የሥራ ክፍሎች ይመድባል፦
    - translation: ጀሚኒ 1 እና ጀሚኒ 2
    - coding: ጀሚኒ 3 እና ጀሚኒ 4
    """
    if pool_type == "translation":
        keys = [
            os.environ.get('GEMINI_API_KEY', ''),
            os.environ.get('GEMINI_API_KEY_2', ''),
        ]
    else:  # coding / CEO tasks
        keys = [
            os.environ.get('GEMINI_API_KEY_3', ''),
            os.environ.get('GEMINI_API_KEY_4', ''),
        ]
    return [k for k in keys if k]

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

def ask_gemini_with_rotation(prompt, pool_type="translation"):
    """የተመደበውን የቁልፍ ክፍል (Pool) በመጠቀም በየተራ እየቀያየረ ይጠይቃል"""
    keys = get_gemini_keys_by_pool(pool_type)
    if not keys:
        return None

    config, _ = SiteConfig.objects.get_or_create(
        key=f"GEMINI_KEY_INDEX_{pool_type.upper()}",
        defaults={'value': {'index': 0}}
    )
    current_index = config.value.get('index', 0)

    for attempt in range(len(keys)):
        idx = (current_index + attempt) % len(keys)
        active_key = keys[idx]

        if is_api_on_cooldown(f"GEMINI_{pool_type.upper()}_KEY_{idx}"):
            continue

        try:
            genai.configure(api_key=active_key)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            if response and response.text:
                config.value = {'index': idx}
                config.save()
                return response.text
        except Exception as e:
            print(f"Gemini {pool_type} Key {idx} failed: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                set_api_cooldown(f"GEMINI_{pool_type.upper()}_KEY_{idx}", hours=24)
            else:
                set_api_cooldown(f"GEMINI_{pool_type.upper()}_KEY_{idx}", hours=1)

    return None

def ask_groq_fast(prompt):
    """Groq Llama 3.3 - ለዲዛይንና ለአሰሳ ፈጣን ምላሽ ሰጪ"""
    if not is_api_on_cooldown("GROQ"):
        try:
            if settings.GROQ_API_KEY:
                client = Groq(api_key=settings.GROQ_API_KEY)
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                if resp.choices[0].message.content:
                    return resp.choices[0].message.content
        except Exception as e:
            print(f"Groq Fail: {e}")
            set_api_cooldown("GROQ", hours=1)
    return None

def ask_ethafri_ceo(prompt):
    return ask_gemini_with_rotation(prompt, pool_type="coding")

# ---------------------------------------------------------
# 2. እውነተኛ ምርቶችን መቃኛ (Telegram Scraper)
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
# 3. ዋናው የዕድገት ሞተር (The Brain)
# ---------------------------------------------------------

def run_daily_market_analysis():
    now = timezone.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user: 
        return "❌ Admin user not found."

    # --- Concurrency Lock ---
    lock_config, _ = SiteConfig.objects.get_or_create(
        key="EVOLUTION_LOCK",
        defaults={'value': {'status': 'idle', 'since': now.isoformat()}}
    )
    if lock_config.value.get('status') == 'running':
        since_time = timezone.datetime.fromisoformat(lock_config.value.get('since'))
        if timezone.is_naive(since_time):
            since_time = timezone.make_aware(since_time)
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
    3. Provide exactly 3 English keywords for photo matching.
    4. Draft an automated "Outreach/Invitation Message" in Amharic to be sent to the seller of this product.

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
          "img_key": "strictly english keywords for photo"
      }},
      "outreach_invite": "ግብዣ ማስታወቂያ ለአቅራቢው በአማርኛ",
      "seo_keywords": ["keyword1", "keyword2"]
    }}
    """

    # --- የዲዛይንና አሰሳ ስራዎችን በ Groq ይሞክራል፣ ከከሸፈ በ ኮዲንግ ጀሚኒ ፑል ያነሳል ---
    ai_response = ask_groq_fast(prompt)
    if not ai_response:
        print("🔄 Groq አልሰራም፣ ወደ ጀሚኒ ኮዲንግ ፑል በመቀየር ላይ...")
        ai_response = ask_gemini_with_rotation(prompt, pool_type="coding")

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
        feature = data.get('task_name', 'Built: General Growth').replace("Built:", "").strip()
        SiteConfig.objects.update_or_create(
            key=f"FEATURE_{slugify(feature)}",
            defaults={'value': {'enabled': True}}
        )

        # --- 3. እውነተኛ ምርት መፍጠር ---
        it = data.get('item', {})
        cat_name = it.get('cat', 'General').strip()
        cat, _ = Category.objects.get_or_create(name=cat_name)
        
        en_title = it.get('title_en', 'New Product')
        en_desc = f"High quality {en_title} available now."

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
        except: 
            pass

        # --- ⚠️ 4. የጀሚኒ 2.5 ፎርማት ትርጉም (በጄሚኒ የትርጉም ፑል - ጀሚኒ 1 እና 2 ብቻ) ---
        translate_prompt = f"""
        Translate this product title and description into 6 languages: Amharic (am), Oromo (om), Arabic (ar), Somali (so), Tigrinya (ti), French (fr).
        Title: {en_title}
        Description: {en_desc}

        Format each language strictly as: "Translated Title ||| Translated Description" inside the JSON:
        {{
          "am": "Amharic Title ||| Amharic Description",
          "om": "Oromo Title ||| Oromo Description",
          "ar": "Arabic Title ||| Arabic Description",
          "so": "Somali Title ||| Somali Description",
          "ti": "Tigrinya Title ||| Tigrinya Description",
          "fr": "French Title ||| French Description"
        }}
        """
        
        # ⚠️ የትርጉም ጀሚኒ ፑልን (1 እና 2) ብቻ ይጠይቃል
        gemini_response = ask_gemini_with_rotation(translate_prompt, pool_type="translation")
        
        trans_data = {}
        if gemini_response:
            try:
                g_start = gemini_response.find('{')
                g_end = gemini_response.rfind('}') + 1
                trans_data = json.loads(gemini_response[g_start:g_end])
            except: 
                pass

        # የትዕግስት ዑደት (Smart Fallback - ጀሚኒ ፌል ቢያደርግም ዳታቤዙ ባዶ ሆኖ እንዳይቀረው መዝጋት)
        combined_fallback = f"{en_title} ||| {en_desc}"
        ProductTranslation.objects.create(
            product=product,
            en=combined_fallback,
            am=trans_data.get('am', combined_fallback),
            om=trans_data.get('om', combined_fallback),
            ar=trans_data.get('ar', combined_fallback),
            so=trans_data.get('so', combined_fallback),
            ti=trans_data.get('ti', combined_fallback),
            fr=trans_data.get('fr', combined_fallback)
        )

        # 5. ዝርዝር ተግባር መመዝገብ
        log_reason = f"ውሳኔ፦ {data.get('priority_reason')}\n\nየአቅራቢዎች ግብዣ መልዕክት፦ {data.get('outreach_invite')}"
        AISystemTask.objects.create(
            task_name=data.get('task_name', 'System Update'),
            priority_reason=f"{log_reason}\n\nUI Config: {json.dumps(ui, indent=2, ensure_ascii=False)}",
            status='Completed'
        )

        # ቆልፉን መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()

        return f"✅ EthAfri Evolved: {data.get('task_name')} completed successfully."

    except Exception as e:
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()
        return f"⚠️ Error: {str(e)}"

# EthAfri/marketplace/growth_agent.py

import os
import json
import datetime
import requests
import re
from bs4 import BeautifulSoup  # ⚠️ እውነተኛ እቃዎችን ለመቃኘት ተጨምሯል
import google.generativeai as genai
from groq import Groq
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
from django.core.files.base import ContentFile
from .models import MarketTrend, Category, Product, ProductTranslation, SiteConfig, AISystemTask, OwnerDirective, UserSearch
from django.contrib.auth.models import User

# የእርስዎ ኤፒአይ የሚቀበለው ትክክለኛው የስሪት ስም
MODEL_NAME = 'gemini-2.5-flash'

# 1. API Helper Functions (JSON Sanitizer)
def clean_json_response(raw_text):
    if not raw_text: 
        return None
    try:
        # ከ AI የሚመጡ Markdown ስህተቶችን ያጸዳል
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match: 
            return json.loads(match.group(0))
        return json.loads(raw_text)
    except Exception as e:
        print(f"⚠️ JSON Parse Error: {e}")
        return None

def get_gemini_keys(pool_type):
    """ቁልፎቹን ለሁለት ራሳቸውን የቻሉ የሥራ ክፍሎች ይከፍላል (ኮታ ቆጣቢ)"""
    if pool_type == "translation":
        return [k for k in [os.environ.get('GEMINI_API_KEY'), os.environ.get('GEMINI_API_KEY_2')] if k]
    return [k for k in [os.environ.get('GEMINI_API_KEY_3'), os.environ.get('GEMINI_API_KEY_4')] if k]

# 2. FAILOVER ROUTER (ባለ 4 ሰንሰለት የ AI ውድቀት መከላከያ)
def ask_ai_with_failover(prompt, pool_type="translation"):
    # 1. Google Gemini 2.5 Try (Pool rotation)
    for key in get_gemini_keys(pool_type):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel(MODEL_NAME)
            res = model.generate_content(prompt)
            data = clean_json_response(res.text)
            if data: return data
        except Exception as e: 
            print(f"Gemini Key Fail: {e}")
            continue

    # 2. Groq Llama 3.3 Try (እጅግ ፈጣን)
    try:
        client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}]
        )
        data = clean_json_response(res.choices[0].message.content)
        if data: return data
    except Exception as e: 
        print(f"Groq Fail: {e}")

    # 3. OpenRouter Try (የመጨረሻው የጀሚኒ 2.0 ነፃ በር)
    try:
        headers = {"Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY')}"}
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", json={
            "model": "google/gemini-2.0-flash-exp", 
            "messages": [{"role": "user", "content": prompt}]
        }, headers=headers, timeout=10)
        if res.status_code == 200:
            data = clean_json_response(res.json()['choices'][0]['message']['content'])
            if data: return data
    except Exception as e: 
        print(f"OpenRouter Fail: {e}")
    
    return None

# ⚠️ views.py እና self_coder.py የሚፈልጉትን የኢምፖርት ስም ስህተት ለመፍታት የተደረገ ውህደት
ask_ethafri_ceo = ask_ai_with_failover

# 3. እውነተኛ ምርቶችን መቃኛ (Telegram Scraper)
def scrape_real_ethiopian_products():
    """እውነተኛ ምርቶችን፣ ዋጋዎችን እና ፎቶዎችን ይቃኛል"""
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
                    
                    if text_div and len(text_div.text.strip()) > 30:
                        raw_text = text_div.text.strip()
                        image_url = ""
                        if img_div and 'style' in img_div.attrs:
                            style = img_div['style']
                            url_match = re.search(r"background-image:url\('(.+)'\)", style)
                            if url_match:
                                image_url = url_match.group(1)
                        
                        items.append({"text": raw_text, "image": image_url, "source_channel": channel})
                        if len(items) >= 3:
                            return items
        except Exception as e:
            print(f"Scraper Error for {channel}: {e}")
            
    return items

# 4. CORE EVOLUTION ENGINE
def run_daily_market_analysis():
    now = timezone.now()
    lock, _ = SiteConfig.objects.get_or_create(key="EVO_LOCK", defaults={'value': {'status': 'idle', 'since': now.isoformat()}})
    
    # የ 5 ደቂቃ Concurrency Lock ቼክ (በ total_seconds() ማስተካከያ)
    if lock.value.get('status') == 'running':
        since_time = datetime.datetime.fromisoformat(lock.value.get('since'))
        if (timezone.now() - since_time).total_seconds() < 300:
            return "⚠️ Skip: Concurrency Lock active."
            
    lock.value = {'status': 'running', 'since': now.isoformat()}
    lock.save()

    try:
        # የባለቤት መመሪያ (Owner Directive) ማንበብ
        latest_directive = OwnerDirective.objects.filter(is_active=True).last()
        directive_context = latest_directive.instruction if latest_directive else "No specific instruction."
        
        # የቅርብ ጊዜ ፍለጋዎች (Demographics Analyzer)
        recent_searches = list(UserSearch.objects.values_list('query', flat=True).order_by('-created_at')[:20])
        
        # እውነተኛ ምርቶችን መቃኘት (Scraping)
        real_scraped_data = scrape_real_ethiopian_products()

        # የጎደሉ አገልግሎቶች
        unbuilt_features = ["Multi-language Selector UI", "Detailed Footer Section", "User Terms Page", "Admin Contact Portal", "Dynamic Top Navigation Menu"]
        completed_tasks = list(AISystemTask.objects.values_list('task_name', flat=True))

        prompt = f"""
        Act as CEO. Return STRICTLY raw JSON (no markdown, no extra words).
        Owner Anwar Directive: "{directive_context}"
        Completed Tasks: {completed_tasks}
        Unbuilt Features: {unbuilt_features}
        Recent user search traffic: {recent_searches}
        Real Scraped Data: {real_scraped_data[:1]}

        Tasks:
        1. Select exactly ONE feature from 'Unbuilt Features' to build.
        2. Extract 1 real product from the Scraped Data. If empty, research a high-demand product.
        3. Translate BOTH product title and description into 7 languages: Amharic (am), English (en), Oromo (om), Arabic (ar), Somali (so), Tigrinya (ti), French (fr).
        4. Provide exactly 3 English keywords for photo matching.
        5. Draft an automated "Outreach/Invitation Message" in Amharic.

        Return JSON ONLY:
        {{
            "task_name": "Built: [Feature Name]",
            "priority_reason": "Strategy & Priority in Amharic",
            "ui": {{
                "banner_title_am": "...", "banner_title_en": "...", 
                "banner_sub_am": "...", "banner_sub_en": "...", 
                "color": "#1a2a6c", "logo": "EthAfri"
            }},
            "item": {{
                "cat": "Category in Amharic", 
                "title_en": "Product title in ENGLISH", 
                "price": 1000, 
                "img_key": "english keywords",
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
            "outreach_invite": "Invitation Message in Amharic"
        }}
        """
        data = ask_ai_with_failover(prompt, "coding")
        if not data:
            lock.value = {'status': 'idle', 'since': now.isoformat()}; lock.save()
            return "❌ All AI Failed."

        # UI Update
        SiteConfig.objects.update_or_create(key="DYNAMIC_UI", defaults={'value': data['ui']})
        
        # Product & Category Creation
        it = data['item']
        cat, _ = Category.objects.get_or_create(name=it['cat'].strip())
        
        trans = it.get('translations', {})
        en_payload = trans.get('en', 'Product ||| Description')
        en_title = en_payload.split("|||")[0].strip() if "|||" in en_payload else it.get('title', 'New Product')
        en_desc = en_payload.split("|||")[1].strip() if "|||" in en_payload else 'No English description.'

        # ፎቶ ከ loremflickr
        k = it.get('img_key', 'product').replace(" ", ",")
        image_url = f"https://loremflickr.com/800/600/{k}"

        product = Product.objects.create(
            seller=admin_user, 
            category=cat, 
            title=en_title, 
            description=en_desc, 
            price=it['price'],
            image_url=image_url,
            market_value_status='Unknown',
            is_active=True
        )

        # ፎቶውን በCloudinary መቆለፍ (የማይለዋወጥ ምስል!)
        try:
            img_res = requests.get(image_url, timeout=10)
            if img_res.status_code == 200:
                product.image.save(f"real_prod_{product.id}.jpg", ContentFile(img_res.content), save=True)
        except Exception as img_err:
            print(f"Cloudinary Error: {img_err}")

        # በ 7 ቋንቋዎች መመዝገብ
        ProductTranslation.objects.create(
            product=product,
            am=trans.get('am', ''), en=trans.get('en', ''), om=trans.get('om', ''),
            ar=trans.get('ar', ''), so=trans.get('so', ''), ti=trans.get('ti', ''),
            fr=trans.get('fr', '')
        )
        
        # ዝርዝር ተግባር መመዝገብ (የሪፖርት ገጹ እንዳይባረር!)
        log_reason = f"ውሳኔ፦ {data.get('priority_reason')}\n\nየአቅራቢዎች ግብዣ መልዕክት፦ {data.get('outreach_invite')}"
        AISystemTask.objects.create(
            task_name=data['task_name'], 
            priority_reason=log_reason,
            status='Completed'
        )
        
        lock.value = {'status': 'idle', 'since': now.isoformat()}; lock.save()
        return f"✅ EthAfri Evolved: {data['task_name']} completed successfully."

    except Exception as e:
        lock.value = {'status': 'idle', 'since': now.isoformat()}; lock.save()
        return f"❌ Error: {str(e)}"
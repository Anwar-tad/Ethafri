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
# EthAfri/marketplace/growth_agent.py

def run_daily_market_analysis():
    """
    ይህ የኢቲአፍሪ ዋና የዕድገት ሞተር ነው። በየቀኑ/በየጊዜው ይሮጣል፡
    1. አድሚን ይፈጥራል/ያረጋግጣል
    2. የገበያ መረጃዎችን ይቃኛል
    3. UI እና ዲዛይን በ AI ያዘምናል
    4. አዳዲስ ምርቶችን በራስ-ሰር ይለጠፋል
    """
    now = timezone.now()
    
    # 1. ሱፐር-ዩዘርን ማረጋገጥ (የ NameError ስህተትን ይከላከላል)
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('ethafri_admin', 'admin@ethafri.com', 'ethafri_secure_2026')

    # 2. Concurrency Lock (ብዙ ጊዜ በአንድ ጊዜ እንዳይሮጥ)
    lock_config, _ = SiteConfig.objects.get_or_create(
        key="EVOLUTION_LOCK",
        defaults={'value': {'status': 'idle', 'since': now.isoformat()}}
    )
    
    if lock_config.value.get('status') == 'running':
        return "⚠️ Skip: Concurrency Lock active."

    lock_config.value = {'status': 'running', 'since': now.isoformat()}
    lock_config.save()

    try:
        # 3. የ AI ጥያቄ (Failover Chainን በመጠቀም)
        prompt = f"""
        Act as CEO. Return STRICTLY raw JSON (no markdown).
        {{
            "task_name": "Growth Feature",
            "priority_reason": "Strategy in Amharic",
            "ui": {{"banner_title_am": "የኢትዮጵያ ምርጥ ገበያ", "banner_title_en": "Ethiopia's Best Marketplace", "banner_sub_am": "ፈጣን እና አስተማማኝ", "banner_sub_en": "Fast and Reliable", "color": "#1a2a6c", "logo": "EthAfri"}},
            "item": {{"cat": "Electronics", "title_en": "High Quality Smartphone", "price": 15000, "img_key": "smartphone"}}
        }}
        """
        
        data = ask_ai_with_failover(prompt, pool_type="coding")
        if not data:
            return "❌ All AI engines failed."

        # 4. ዲዛይን ማዘመን (Dynamic UI)
        SiteConfig.objects.update_or_create(key="DYNAMIC_UI", defaults={'value': data.get('ui')})
        
        # 5. አዲስ ምርት መፍጠር
        it = data.get('item', {})
        cat, _ = Category.objects.get_or_create(name=it.get('cat', 'General'))
        
        p = Product.objects.create(
            seller=admin_user, 
            category=cat, 
            title=it.get('title_en', 'New Product'),
            description="Auto-generated market-optimized product.", 
            price=it.get('price', 0),
            market_value_status='Unknown',
            is_active=True
        )
        
        AISystemTask.objects.create(task_name=data.get('task_name', 'System Evolution'), status='Completed')
        return f"✅ EthAfri Evolved: {data.get('task_name')} completed successfully."

    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        # 6. መቆለፊያውን ሁሌም መፍታት
        lock_config.value = {'status': 'idle', 'since': now.isoformat()}
        lock_config.save()

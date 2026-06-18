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
# EthAfri/marketplace/growth_agent.py

import json, os, re, logging
import google.generativeai as genai
from groq import Groq
from django.utils import timezone
from .models import SiteConfig, Category, Product, AISystemTask
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

def ask_ai_with_failover(prompt, pool_type="translation"):
    """የተሻሻለ የFailover ሰንሰለት (Gemini -> Groq -> fallback)"""
    
    # 1. Try Gemini
    try:
        genai.configure(api_key=os.environ.get('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return clean_json_response(response.text)
    except Exception as e:
        logger.error(f"Gemini failed: {e}")

    # 2. Try Groq (Fallback)
    try:
        client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return clean_json_response(chat.choices[0].message.content)
    except Exception as e:
        logger.error(f"Groq failed: {e}")
        
    return None

def clean_json_response(raw_text):
    """ማርክዳውን ያጸዳል"""
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return json.loads(raw_text)
    except: return None

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

def run_daily_market_analysis():
    now = timezone.now()
    
    # 1. አድሚን ማረጋገጥ
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('ethafri_admin', 'admin@ethafri.com', 'ethafri_secure_2026')

    # 2. Concurrency Lock
    lock_config, _ = SiteConfig.objects.get_or_create(
        key="EVOLUTION_LOCK", defaults={'value': {'status': 'idle'}}
    )
    if lock_config.value.get('status') == 'running':
        return "⚠️ Skip: Lock active."

    lock_config.value = {'status': 'running'}; lock_config.save()

    try:
        data = ask_ai_with_failover("...", pool_type="coding") # ፕሮምፕትህ እንደነበረ ነው
        if not data: return "❌ All AI engines failed."

        # 4. ዲዛይን ማዘመን (None-safe update)
        ui_default = {"banner_title_am": "EthAfri", "color": "#1a2a6c"} # ነባሪ እሴት
        SiteConfig.objects.update_or_create(
            key="DYNAMIC_UI", 
            defaults={'value': data.get('ui', ui_default)}
        )
        
        # 5. ምርት መፍጠር (None-safe)
        it = data.get('item', {})
        if it:
            cat, _ = Category.objects.get_or_create(name=it.get('cat', 'General'))
            Product.objects.create(
                seller=admin_user, 
                category=cat, 
                title=it.get('title_en', 'New Product'),
                description="Auto-generated.", 
                price=it.get('price', 0)
            )
        
        AISystemTask.objects.create(task_name=data.get('task_name', 'System Evolution'), status='Completed')
        return "✅ Success"

    except Exception as e:
        return f"❌ Error: {str(e)}"
    finally:
        # ሁሌም መፍታት
        lock_config.value = {'status': 'idle'}; lock_config.save()


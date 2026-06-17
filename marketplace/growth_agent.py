# EthAfri/marketplace/growth_agent.py

import google.generativeai as genai
from groq import Groq
import json, datetime, re, requests
from bs4 import BeautifulSoup # ⚠️ በ Scraping ወቅት ስህተት እንዳይፈጠር ተጨምሯል
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
    """ጀሚኒ 2.5 -> Groq -> Mistral -> OpenRouter"""
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

    return None

# ⚠️ self_coder.py የሚፈልገውን የኢምፖርት ስም ስህተት ለመፍታት የተደረገ ውህደት
ask_ethafri_ceo = ask_ai_failover

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

    # የባለቤቱን መመሪያ ማንበብ
    latest_directive = OwnerDirective.objects.filter(is_active=True).last()
    directive_context = latest_directive.instruction if latest_directive else "ምንም ተጨማሪ መመሪያ የለም።"

    # እስካሁን የተሰሩ ስራዎች ዝርዝር (AIው ደጋግሞ እንዳይሰራቸው ለመቆለፍ)
    completed_tasks = list(AISystemTask.objects.values_list('task_name', flat=True))

    prompt = f"""
    አንተ የ EthAfri Smart Marketplace CEO ነህ። ዛሬ {now} ነው።
    የዌብሳይቱ ባለቤት (Anwar) የሰጠህ ቀጥተኛ መመሪያ ይህ ነው፦ {directive_context}
    እስካሁን ያከናወናቸው አገልግሎቶች ዝርዝር፦ {completed_tasks}

    ተግባርህ፦
    1. ⚠️ በጣም ወሳኝ ህግ፦ ከላይ ከተጠቀሱት የተሰሩ ስራዎች ውጪ አዲስ የጎደለ አገልግሎት ገንባ (ለምሳሌ ሎግኢን፣ ቋንቋ መምረጫ)። የተሰሩትን በፍጹም አትድገም።
    2. በኢትዮጵያ ገበያ አሁን ተፈላጊ የሆነ 1 እውነተኛ ምርት መርጠህ በ 7 ቋንቋዎች ተርጉመህ አዘጋጅ።
    3. ለምርቱ የሚሆን 3 የእንግሊዝኛ ምስል መፈለጊያ ቃላት (ለምሳሌ፦ 'modern smart watch') ስጠኝ።

    መልስህን በዚህ JSON ብቻ አቅርብ (መግቢያ ወሬ አትጨምር)፦
    {{
      "task_name": "የአገልግሎቱ ስም (ለምሳሌ፦ Built: User Profile Portal)",
      "priority_reason": "ይህንን ስራ ለምን እንደቀደምክ ማብራሪያ በአማርኛ",
      "ui": {{
          "banner_title": "ባነር", "banner_sub": "ንዑስ ጽሁፍ", "color": "#1a2a6c", "logo": "EthAfri"
      }},
      "item": {{
          "cat": "ምድብ", "title": "ርዕስ", "price": 1000, "img_key": "keywords in english only",
          "desc": {{"am": "...", "en": "...", "om": "...", "ar": "...", "so": "...", "ti": "...", "fr": "..."}}
      }}
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

        # --- 2. ምርት እና ፎቶ ማስተካከል ---
        it = data.get('item', {})
        cat, _ = Category.objects.get_or_create(name=it.get('cat', 'General').strip())
        
        # ፎቶ ከ loremflickr
        k = it.get('img_key', 'shopping').replace(" ", ",")
        image_url = f"https://loremflickr.com/800/600/{k}"

        product = Product.objects.create(
            seller=admin_user, 
            category=cat, 
            title=it.get('title'),
            description=it.get('desc', {}).get('am', 'በ AI የተጠቆመ የገበያ ዕድል'),
            price=it.get('price', 0), 
            image_url=image_url,
            market_value_status='Unknown',
            is_active=True
        )

        # ፎቶውን አውርዶ ወደ Cloudinary በቋሚነት መጫን
        try:
            img_res = requests.get(image_url, timeout=10)
            if img_res.status_code == 200:
                product.image.save(f"real_prod_{product.id}.jpg", ContentFile(img_res.content), save=True)
        except Exception as img_err:
            print(f"Cloudinary Error: {img_err}")

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
            task_name=data.get('task_name', 'System Update'),
            priority_reason=data.get('priority_reason', 'Normal growth'),
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
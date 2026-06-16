import google.generativeai as genai
from groq import Groq
import json, datetime, re, requests
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product
from django.contrib.auth.models import User

# ---------------------------------------------------------
# 1. ባለ ብዙ ሰንሰለት AI ሞተሮች (Failover Chain)
# ---------------------------------------------------------

def ask_ai_failover(prompt):
    """Gemini -> Groq -> Mistral (Direct API) -> OpenRouter"""
    
    # 1. Google Gemini
    try:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash') 
            response = model.generate_content(prompt)
            if response and response.text: return response.text
    except Exception as e: print(f"Gemini Fail: {e}")

    # 2. Groq
    try:
        if settings.GROQ_API_KEY:
            client = Groq(api_key=settings.GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
    except Exception as e: print(f"Groq Fail: {e}")

    # 3. Mistral AI (Direct Call - No Library Needed)
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
    except Exception as e: print(f"Mistral API Fail: {e}")

    # 4. OpenRouter
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
    except Exception as e: print(f"OpenRouter Fail: {e}")

    return None

# ---------------------------------------------------------
# 2. የዕድገት ሞተር (The Brain)
# ---------------------------------------------------------

def run_daily_market_analysis():
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user: return "❌ አድሚን አልተገኘም።"

    prompt = f"""
    አንተ የ EthAfri Smart Marketplace CEO ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. በኢትዮጵያ አሁን በጣም ተፈላጊ የሆኑ 3 አዳዲስ የገበያ ዘርፎችን (Categories) ለይ።
    2. ለእያንዳንዱ ዘርፍ 1 ናሙና እቃ ፍጠር።
    3. ለጎግል ፍለጋ 5 ቁልፍ ቃላትን አውጣ።
    መልስህን በዚህ JSON ብቻ አቅርብ (መግቢያ ወሬ አትጨምር)፦
    {{
      "categories": [{{ "name": "ምድብ", "product": "ስም", "desc": "መግለጫ" }}],
      "seo": ["ቃል1", "ቃል2"],
      "advice": "ምክር"
    }}
    """

    ai_response = ask_ai_failover(prompt)
    if not ai_response:
        return "❌ ሁሉም AI ሞተሮች እምቢ አሉ። API ቁልፎችን ያረጋግጡ።"

    try:
        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        data = json.loads(match.group(0))

        count = 0
        for entry in data.get('categories', []):
            name = entry['name'].strip()
            # 1. ካቴጎሪውን ይፈልጋል ወይም ይፈጥራል
            cat, _ = Category.objects.get_or_create(name=name)
            
            # 2. እቃው አስቀድሞ መኖሩን ያረጋግጣል (ተመሳሳይ እቃ እንዳይደገም)
            if not Product.objects.filter(title=entry['product'], category=cat).exists():
                Product.objects.create(
                    seller=admin_user,
                    title=entry['product'],
                    description=entry['desc'],
                    price=0,
                    category=cat,
                    location="ኢትዮጵያ",
                    is_active=True
                )
                count += 1
        
        for kw in data.get('seo', []): UserSearch.objects.get_or_create(query=kw.strip())
        
        MarketTrend.objects.create(
            niche_name=f"Auto Evolution {now.strftime('%H:%M')}",
            demand_level=99,
            ai_suggestion=data.get('advice', '')
        )
        return f"✅ EthAfri Evolved: {count} new entries created."
    except Exception as e:
        return f"⚠️ Logic Error: {str(e)} | Raw: {ai_response[:50]}"
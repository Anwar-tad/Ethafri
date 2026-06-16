import google.generativeai as genai
from groq import Groq
import json
import datetime
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch

# ---------------------------------------------------------
# 1. AI ሞተሮች (Gemini + Groq Fallback)
# ---------------------------------------------------------

def ask_gemini(prompt):
    """የመጀመሪያ ምርጫ - Google Gemini"""
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

def ask_groq(prompt):
    """ሁለተኛ ምርጫ (Fallback) - Groq Llama 3"""
    try:
        # settings.py ውስጥ GROQ_API_KEY መኖሩን አረጋግጥ
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"Groq Error: {e}")
        return None

# ---------------------------------------------------------
# 2. ዋናው የዕድገት ሞተር (The Brain)
# ---------------------------------------------------------

def run_daily_market_analysis():
    now = datetime.datetime.now()
    
    prompt = f"""
    አንተ የ EthAfri (ኢቲአፍሪ) ራስ-ገዝ CEO ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. በኢትዮጵያ አሁን በጣም ተፈላጊ የሆኑ 3 አዳዲስ ዘርፎችን (Niches) ለይ።
    2. ለእነዚህ ዘርፎች 5 ቁልፍ ቃላትን (SEO Keywords) አውጣ።
    መልስህን በዚህ JSON ብቻ ስጠኝ፦
    {{
      "categories": ["ዘርፍ 1", "ዘርፍ 2"],
      "seo_keywords": ["ቃል 1", "ቃል 2"],
      "strategy_report": "ምክር በአማርኛ"
    }}
    """

    ai_response = ask_gemini(prompt)
    if not ai_response:
        ai_response = ask_groq(prompt)

    if not ai_response:
        return "❌ AI ሞተሮች አልሰሩም።"

    try:
        clean_data = ai_response.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_data)

        created_cats = []
        for cat_name in data.get('categories', []):
            name = cat_name.strip()
            if name: # ባዶ ካልሆነ ብቻ
                # እዚህ ጋር ስህተቱን ለመከላከል 'defaults' ውስጥ slug አንሰጥም
                # ይልቁንም በ models.py ውስጥ በራሱ እንዲመነጭ እናደርጋለን
                cat, created = Category.objects.get_or_create(name=name)
                if created:
                    created_cats.append(name)

        for kw in data.get('seo_keywords', []):
            if kw.strip():
                UserSearch.objects.get_or_create(query=kw.strip())

        MarketTrend.objects.create(
            niche_name=f"Update {now.strftime('%H:%M')}",
            demand_level=98,
            ai_suggestion=data.get('strategy_report', 'ምንም ምክር የለም')
        )

        return f"✅ EthAfri Evolved: {len(created_cats)} new categories. {len(data.get('seo_keywords', []))} SEO keywords."

    except Exception as e:
        return f"⚠️ JSON Error: {str(e)}"
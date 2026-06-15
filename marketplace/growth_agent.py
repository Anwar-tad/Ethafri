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
        model = genai.GenerativeModel('gemini-1.5-flash')
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
    """
    ስሙ 'run_daily_market_analysis' ቢሆንም ስራው ግን በየሰዓቱ 
    ራሱን የሚያሳድግ (Autonomous Evolution) ነው።
    """
    now = datetime.datetime.now()
    
    # AIው የኢትዮጵያን ገበያ አጥንቶ እንዲመልስ የሚሰጠው ትዕዛዝ
    prompt = f"""
    አንተ የ EthAfri (ኢቲአፍሪ) ራስ-ገዝ ስትራቴጂስት እና CEO ነህ። ዛሬ ቀኑ {now} ነው።
    ኢቲአፍሪ 'ከመርፌ እስከ መርከብ' የሚሸጥበት የአፍሪካ ግዙፍ ማርኬት ፕሌስ ነው።
    
    ተግባርህ፦
    1. በኢትዮጵያና በአፍሪካ አሁን በከፍተኛ ሁኔታ የሚፈለጉ 3 አዳዲስ ዘርፎችን (Niches) ለይ።
    2. ለእነዚህ ዘርፎች ሰዎች ጎግል ላይ ሊፈልጓቸው የሚችሉ 5 ቁልፍ ቃላትን (SEO Keywords) አውጣ።
    3. ለዌብሳይቱ እድገት የሚሆን 1 የስትራቴጂ ምክር ስጥ።

    መልስህን በዚህ የ JSON ቅርጽ ብቻ ስጠኝ (ምንም ሌላ ጽሁፍ አትጨምር)፦
    {{
      "categories": ["Category Name 1", "Category Name 2"],
      "seo_keywords": ["keyword1", "keyword2", "keyword3"],
      "strategy_report": "የገበያ ትንተና ሪፖርት በአማርኛ"
    }}
    """

    # --- AI ምርጫ ሂደት ---
    ai_response = ask_gemini(prompt)
    
    if not ai_response:
        print("⚠️ Gemini አልሰራም፣ ወደ Groq AI በመቀየር ላይ...")
        ai_response = ask_groq(prompt)

    if not ai_response:
        return "❌ ሁለቱም AI ሞተሮች አልሰሩም። ዕድገት ለጊዜው ቆሟል።"

    # --- መረጃውን ወደ ተግባር የመለወጥ ሂደት (Action) ---
    try:
        # JSON መረጃውን ማጽዳት እና መተርጎም
        clean_data = ai_response.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_data)

        # 1. አዳዲስ ምድቦችን (Categories) በራሱ መክፈት
        created_cats = []
        for cat_name in data.get('categories', []):
            cat, created = Category.objects.get_or_create(
                name=cat_name, 
                defaults={'slug': slugify(cat_name)}
            )
            if created:
                created_cats.append(cat_name)

        # 2. የ SEO ፍላጎት (UserSearch) በራሱ መመዝገብ
        # ይህ ጎግል ዌብሳይቱን እንደ 'Trending' እንዲቆጥረው ይረዳዋል
        for kw in data.get('seo_keywords', []):
            UserSearch.objects.get_or_create(query=kw)

        # 3. የገበያ ትንተናውን በዳታቤዝ ማስቀመጥ
        MarketTrend.objects.create(
            niche_name=f"Autonomous Update {now.strftime('%H:%M')}",
            demand_level=98,
            ai_suggestion=data.get('strategy_report', 'ምንም ምክር አልተሰጠም')
        )

        log_msg = f"✅ EthAfri Evolved: {len(created_cats)} new categories added. SEO keywords updated."
        return log_msg

    except Exception as e:
        return f"⚠️ JSON Parsing Error: {str(e)}"
import google.generativeai as genai
from groq import Groq
import json
import datetime
import re # JSONን ለይቶ ለማውጣት
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product
from django.contrib.auth.models import User

# ---------------------------------------------------------
# 1. AI ሞተሮች (Gemini 2.0 Flash + Groq)
# ---------------------------------------------------------

def ask_ai(prompt):
    """Gemini 2.0 Flash ን ይጠቀማል፣ ካልሰራ ወደ Groq ይቀይራል"""
    
    # 1. Gemini 2.0 Flash ሙከራ
    try:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash') 
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
    except Exception as e:
        print(f"⚠️ Gemini Error: {str(e)}")

    # 2. Groq (Llama 3.3) Fallback
    try:
        if settings.GROQ_API_KEY:
            client = Groq(api_key=settings.GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Groq Error: {str(e)}")
    
    return None

# ---------------------------------------------------------
# 2. ዋናው የዕድገት ሞተር
# ---------------------------------------------------------

def run_daily_market_analysis():
    now = datetime.datetime.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        return "❌ ስህተት፡ አድሚን ተጠቃሚ አልተገኘም።"

    prompt = f"""
    አንተ የ EthAfri (ኢቲአፍሪ) ራስ-ገዝ CEO ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. በኢትዮጵያ አሁን በጣም ተፈላጊ የሆኑ 3 አዳዲስ የገበያ ዘርፎችን (Categories) ለይ።
    2. ለእያንዳንዱ ዘርፍ 1 ማራኪ የእቃ ርዕስ (Product Title) እና መግለጫ ፍጠር።
    3. ለጎግል ፍለጋ የሚረዱ 5 ቁልፍ ቃላትን (SEO Keywords) አውጣ።

    መልስህን በዚህ የ JSON ቅርጽ ብቻ አቅርብ (ምንም ሌላ ጽሁፍ አትጨምር)፦
    {{
      "categories": [
        {{ "name": "ምድብ ስም", "sample_product": "የእቃ ስም", "sample_desc": "መግለጫ" }}
      ],
      "seo_keywords": ["keyword1", "keyword2"],
      "strategy": "ምክር በአማርኛ"
    }}
    """

    ai_response = ask_ai(prompt)
    
    if not ai_response:
        return "❌ ሁለቱም AI ሞተሮች አልሰሩም። ኢንተርኔት ወይም API ቁልፎችን ያረጋግጡ።"

    try:
        # --- ወሳኝ ማሻሻያ፡ JSONን በ Regex ለይቶ ማውጣት ---
        # ይህ ከ JSON ውጭ ያሉ ጽሁፎችን (ለምሳሌ 'Here is the JSON:') ያጠፋል
        match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if not match:
            return f"⚠️ AIው የላከው መልስ JSON አይደለም: {ai_response[:50]}..."
        
        clean_json = match.group(0)
        data = json.loads(clean_json)

        new_items_count = 0
        for entry in data.get('categories', []):
            cat_name = entry.get('name', '').strip()
            if cat_name:
                cat, _ = Category.objects.get_or_create(name=cat_name)
                
                # ናሙና እቃ መፍጠር
                Product.objects.create(
                    seller=admin_user,
                    title=entry.get('sample_product', f"የሚፈለግ፡ {cat_name}"),
                    description=entry.get('sample_desc', "በ AI የተጠቆመ የገበያ ዕድል"),
                    price=0,
                    category=cat,
                    location="ኢትዮጵያ",
                    is_active=True
                )
                new_items_count += 1

        for kw in data.get('seo_keywords', []):
            UserSearch.objects.get_or_create(query=kw.strip())

        MarketTrend.objects.create(
            niche_name=f"Auto-Update {now.strftime('%H:%M')}",
            demand_level=98,
            ai_suggestion=data.get('strategy', 'ምንም ምክር የለም')
        )

        return f"✅ EthAfri Evolved: {new_items_count} new entries created."

    except Exception as e:
        return f"⚠️ Processing Error: {str(e)} | Raw: {ai_response[:50]}..."
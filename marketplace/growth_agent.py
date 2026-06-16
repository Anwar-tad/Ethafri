import google.generativeai as genai
from groq import Groq
import json
import datetime
from django.utils.text import slugify
from django.conf import settings
from .models import MarketTrend, Category, UserSearch, Product
from django.contrib.auth.models import User

# AI Engines
def ask_ai(prompt):
    """Gemini 2.0 Flash ን ይጠቀማል፣ ካልሰራ ወደ Groq ይቀይራል"""
    
    # 1. Gemini 2.0 Flash ሙከራ
    try:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            # እዚህ ጋር ሞዴሉን ወደ gemini-2.0-flash ቀይረነዋል
            model = genai.GenerativeModel('gemini-2.0-flash') 
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
    except Exception as gemini_err:
        print(f"⚠️ Gemini 2.0 Error: {str(gemini_err)}")

    # 2. Gemini 2.0 ካልሰራ -> Groq (Llama 3.3) ሙከራ
    print("🔄 Gemini 2.0 አልሰራም፣ ወደ Groq AI በመቀየር ላይ...")
    try:
        if settings.GROQ_API_KEY:
            client = Groq(api_key=settings.GROQ_API_KEY)
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile", # እጅግ ፈጣን እና አዲስ ሞዴል
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content
    except Exception as groq_err:
        return f"❌ ሁለቱም AI ሞተሮች አልሰሩም። Groq Error: {str(groq_err)}"
    
    return "❌ ምንም አይነት API Key አልተገኘም ወይም አልሰራም።"

def run_daily_market_analysis():
    now = datetime.datetime.now()
    # ዌብሳይቱ እንዲሞላ መጀመሪያ አንድ አስተዳዳሪ (User) መኖሩን አረጋግጥ
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        return "❌ ስህተት፡ ምንም አድሚን ተጠቃሚ አልተገኘም።"

    prompt = f"""
    አንተ የ EthAfri Autonomous CEO ነህ። ዛሬ {now} ነው።
    ተግባርህ፦
    1. በኢትዮጵያ አሁን በጣም ተፈላጊ የሆኑ 3 አዳዲስ የገበያ ዘርፎችን (Categories) ለይ።
    2. ለእያንዳንዱ ዘርፍ 1 ማራኪ የእቃ ርዕስ (Product Title) እና መግለጫ ፍጠር።
    3. ለጎግል ፍለጋ የሚረዱ 5 ቁልፍ ቃላትን (SEO Keywords) ስጠኝ።

    መልስህን በዚህ JSON ብቻ ስጠኝ፦
    {{
      "categories": [
        {{ "name": "ምድብ 1", "sample_product": "የእቃ ስም", "sample_desc": "መግለጫ" }}
      ],
      "seo_keywords": ["keyword1", "keyword2"],
      "strategy": "ምክር"
    }}
    """

    ai_response = ask_ai(prompt)
    if not ai_response: return "❌ AI ሞተሮች አልሰሩም።"

    try:
        clean_data = ai_response.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_data)

        new_items_count = 0
        for entry in data.get('categories', []):
            cat_name = entry['name'].strip()
            if cat_name:
                # ካቴጎሪ መፍጠር
                cat, created = Category.objects.get_or_create(name=cat_name)
                
                # ናሙና እቃ መፍጠር (ዌብሳይቱ ባዶ እንዳይሆን)
                Product.objects.create(
                    seller=admin_user,
                    title=entry.get('sample_product', f"የሚፈለግ፡ {cat_name}"),
                    description=entry.get('sample_desc', "በ AI የተጠቆመ የገበያ ዕድል"),
                    price=0, # ጥቆማ ስለሆነ
                    category=cat,
                    location="ኢትዮጵያ",
                    is_active=True
                )
                new_items_count += 1

        # SEO ማደሻ
        for kw in data.get('seo_keywords', []):
            UserSearch.objects.get_or_create(query=kw.strip())

        MarketTrend.objects.create(
            niche_name=f"Update {now.strftime('%H:%M')}",
            demand_level=98,
            ai_suggestion=data.get('strategy', '')
        )

        return f"✅ EthAfri Evolved: {new_items_count} new entries created."

    except Exception as e:
        return f"⚠️ ስህተት፡ {str(e)}"
# marketplace/growth_agent.py
import google.generativeai as genai
from .models import Product, MarketTrend, Category
from django.db.models import Count

def run_daily_market_analysis():
    # 1. ዳታ መሰብሰብ፡ የትኛው ምድብ ላይ ብዙ እቃ አለ? የትኛውስ ይፈለጋል?
    categories_count = Category.objects.annotate(num_products=Count('product'))
    
    # ለ AIው መረጃውን እናዘጋጅለት
    market_summary = ""
    for cat in categories_count:
        market_summary += f"ምድብ: {cat.name}, የዕቃ ብዛት: {cat.num_products}. "

    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    አንተ የ EthAfri የገበያ ዕድገት ዳይሬክተር ነህ። የዛሬው የገበያ ሁኔታ ይህ ነው፡ {market_summary}
    
    ከዚህ መረጃ ተነስተህ፡
    1. በኢትዮጵያ ወቅታዊ ሁኔታ ምን አዲስ ትርፋማ 'Niche' (ዘርፍ) መከፈት አለበት? (ምሳሌ፡ የትምህርት መሣሪያዎች፣ የዝናብ ልብስ...)
    2. ለሻጮች ምን አይነት ማበረታቻ ማስታወቂያ እንስራ?
    3. ለዌብሳይቱ አዲስ የኮድ ተግባር (Feature) ምን ይጨመር?
    
    መልስህን በአጭርና ግልጽ በሆነ ነጥብ በአማርኛ አቅርብ።
    """
    
    try:
        response = model.generate_content(prompt)
        # ትንተናውን በዳታቤዝ ውስጥ እናስቀምጠው
        MarketTrend.objects.create(
            niche_name="Daily Global Analysis",
            demand_level=80, # ለሙከራ
            ai_suggestion=response.text
        )
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"
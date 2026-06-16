# EthAfri/marketplace/ai_utils.py

import google.generativeai as genai
from groq import Groq
import json, re
from django.conf import settings

def call_gemini(prompt):
    """Google Gemini 2.5 Flash ን በመጠቀም መረጃ ማውጣት"""
    try:
        if not settings.GEMINI_API_KEY: return None
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # በእርስዎ መመሪያ መሰረት 'gemini-2.5-flash' ጥቅም ላይ ውሏል
        model = genai.GenerativeModel('gemini-2.5-flash') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini API Error: {str(e)}")
        return None

def call_groq(prompt):
    """Gemini ካልሰራ Groq (Llama 3.3) እንደ አማራጭ ይጠቀማል"""
    try:
        if not settings.GROQ_API_KEY: return None
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Groq API Error: {str(e)}")
        return None

def clean_and_parse_json(text):
    """ከ AI መልስ ውስጥ JSON ዳታን ብቻ ለይቶ ያወጣል"""
    if not text: return None
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"⚠️ JSON Parsing Error: {e}")
        return None

def analyze_product_smartly(title, description, price):
    """እቃ ሲለጠፍ በ AI መርምሮ ምድብ ለመስጠት"""
    prompt = f"Product: {title}, Desc: {description}, Price: {price}. Categorize this for a marketplace in one JSON object with 'category' and 'tags' keys."
    raw_response = call_gemini(prompt)
    if not raw_response:
        raw_response = call_groq(prompt)
    return clean_and_parse_json(raw_response)
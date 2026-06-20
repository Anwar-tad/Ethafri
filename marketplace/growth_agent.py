# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ለውጥ፦ Multi-Site Orchestration + Business Growth + Auto-Discovery
# 📅 ቀን፦ 2026-06-20
# ============================================================

import json
import os
import re
import logging
import sys
import requests
import hashlib
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management import call_command
from django.urls import clear_url_caches
from importlib import reload
from groq import Groq
from google import genai
from django.db import models
from django.db.models import Q

# አዲሶቹን አውቶኖመስ ሞዴሎች ማካተት
from .models import (
    SiteConfig, Category, Product, AIProjectBacklog, AIEvolutionLog, 
    AdminOverrideInstruction, AgentErrorLog, SiteRegistry,
    CustomerAcquisitionLog, MarketingCampaign, SellerProfile, NotificationQueue
)

logger = logging.getLogger(__name__)


# ============================================================
# 1. የኤአይ ፎልባክ ሞተር (እንደበፊቱ)
# ============================================================

def ask_ai_with_failover(prompt, pool_type="coding"):
    """
    ተሻሻለ የኤአይ ፎልባክ ሞተር፡ ቁልፎችን የመለየት፣ የመመዝገብ እና ዙር-ተኮር (Round-Robin) 
    የጥሪ ማመጣጠኛ አቅም ያለው።
    """
    keys_to_check = ['GEMINI_API_KEY', 'GROQ_API_KEY', 'GITHUB_TOKEN', 'HUGGINGFACE_API_KEY', 'HF_TOKEN', 'MISTRAL_API_KEY', 'OPENROUTER_API_KEY']
    for k in keys_to_check:
        val = os.environ.get(k)
        logger.info(f"🔑 DEBUG: Key {k} exists: {bool(val)}")

    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    mistral_key = os.environ.get('MISTRAL_API_KEY')
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    huggingface_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_TOKEN')
    github_token = os.environ.get('GITHUB_TOKEN')

    missing = [k for k, v in {
        "Gemini": gemini_keys, "Groq": groq_key, "Mistral": mistral_key, 
        "GitHub": github_token, "HuggingFace": huggingface_key
    }.items() if not v]
    if missing:
        logger.warning(f"⚠️ Missing API Keys: {missing}. Check Render Environment Variables!")

    def extract_json(text):
        if not text: return None
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            return json.loads(match.group(0)) if match else None
        except Exception: return None

    def call_gemini():
        if not gemini_keys: return None
        for idx, key in enumerate(gemini_keys):
            try:
                client = genai.Client(api_key=key)
                res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                data = extract_json(res.text)
                if data and "error" not in data: return data
            except Exception as e:
                logger.warning(f"🔄 Gemini Key {idx+1} exhausted: {e}")
        return None

    def call_github():
        if not github_token: return None
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"}
        model = "azure-openai/gpt-4o-mini" if "translation" in pool_type else "meta-llama-3.1-405b-instruct"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=20)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception as e:
            logger.error(f"GitHub Error: {e}"); return None

    def call_groq():
        if not groq_key: return None
        try:
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            return extract_json(chat.choices[0].message.content)
        except Exception: return None

    def call_mistral():
        if not mistral_key: return None
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
        model = "codestral-latest" if pool_type == "coding" else "mistral-large-latest"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=20)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception: return None

    def call_huggingface():
        if not huggingface_key: return None
        url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1/chat/completions"
        headers = {"Authorization": f"Bearer {huggingface_key}", "Content-Type": "application/json"}
        try:
            res = requests.post(url, headers=headers, json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": [{"role": "user", "content": prompt}]}, timeout=25)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception: return None

    def call_openrouter():
        if not openrouter_key: return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        model = "google/gemini-2.5-flash" if "translation" in pool_type else "deepseek/deepseek-chat"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=25)
            return extract_json(res.json()['choices'][0]['message']['content']) if res.status_code == 200 else None
        except Exception: return None

    providers = []
    
    if pool_type == "translation_github":
        providers = [call_github, call_gemini, call_huggingface, call_openrouter]
    elif pool_type == "translation_huggingface":
        providers = [call_huggingface, call_github, call_gemini, call_openrouter]
    elif pool_type == "translation":
        providers = [call_gemini, call_github, call_huggingface, call_openrouter, call_groq]
    elif pool_type == "coding":
        providers = [call_mistral, call_github, call_groq, call_openrouter, call_huggingface]
    elif pool_type == "marketing":
        providers = [call_openrouter, call_gemini, call_mistral, call_github, call_groq]
    elif pool_type == "analysis":
        providers = [call_gemini, call_openrouter, call_huggingface, call_groq]
    else:
        providers = [call_groq, call_mistral, call_github, call_huggingface, call_openrouter]

    for provider in providers:
        try:
            result = provider()
            if result and "error" not in result: 
                return result
        except Exception as e:
            logger.warning(f"Provider {provider.__name__} failed: {e}")

    return {"error": "All AI providers failed or keys are missing."}

ask_ethafri_ceo = ask_ai_with_failover


# ============================================================
# 2. የፕሮጀክት ሁኔታ አንባቢ (Multi-Site)
# ============================================================

def get_site_project_state(site: SiteRegistry):
    """
    ለአንድ የተወሰነ ጣቢያ የፕሮጀክቱን ኮድ እና የፋይል መዋቅር ያነባል
    """
    if not site.repo_path:
        return {}, {}
    
    base = site.repo_path
    target_files = {
        'models': os.path.join(base, 'marketplace', 'models.py'),
        'views': os.path.join(base, 'marketplace', 'views.py'),
        'urls': os.path.join(base, 'marketplace', 'urls.py'),
        'forms': os.path.join(base, 'marketplace', 'forms.py'),
        'home_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'home.html'),
        'edit_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'edit_product.html'),
    }
    
    state = {}
    for key, path in target_files.items():
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    state[key] = f.read()
            except Exception as e:
                state[key] = f"ERROR: Could not read file - {e}"
        else:
            state[key] = f"❌ MISSING_FILE: This file doesn't exist yet."
    return state, target_files


def get_complete_project_state():
    """
    [DEPRECATED] ለነባር ተኳሃኝነት ብቻ — የመጀመሪያውን ጣቢያ ያነባል
    """
    base = settings.BASE_DIR
    target_files = {
        'models': os.path.join(base, 'marketplace', 'models.py'),
        'views': os.path.join(base, 'marketplace', 'views.py'),
        'urls': os.path.join(base, 'marketplace', 'urls.py'),
        'forms': os.path.join(base, 'marketplace', 'forms.py'),
        'home_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'home.html'),
        'edit_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'edit_product.html'),
    }
    
    state = {}
    for key, path in target_files.items():
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                state[key] = f.read()
        else:
            state[key] = f"❌ MISSING_FILE: This file doesn't exist yet."
    return state, target_files


# ============================================================
# 3. አዲስ ጣቢያ ራስ-ሰር መለየት (Auto-Discovery)
# ============================================================

def discover_new_sites():
    """
    በፋይል ሲስተም ውስጥ አዲስ የፕሮጀክት ፎልደሮችን ያገኛል
    እና በ SiteRegistry ውስጥ ያስመዘግባል
    """
    base_path = settings.BASE_DIR
    discovered = []
    
    if not os.path.exists(base_path):
        return discovered
    
    # በዋናው ማውጫ ውስጥ ያሉ ሁሉንም ፎልደሮች ይመልከት
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            # የ Django ፕሮጀክት መሆኑን አረጋግጥ
            if os.path.exists(os.path.join(item_path, 'manage.py')):
                site_name = item.lower().replace('_', '-').replace(' ', '-')
                
                # ቀድሞ የተመዘገበ እንደሆነ ፈትሽ
                existing = SiteRegistry.objects.filter(name=site_name).first()
                if not existing:
                    # አዲስ ጣቢያ ፍጠር
                    try:
                        site = SiteRegistry.objects.create(
                            name=site_name,
                            display_name=item.replace('_', ' ').title(),
                            niche="general",  # AI ይሞላዋል
                            target_market="Global",
                            repo_path=item_path,
                            is_active=True
                        )
                        discovered.append(site)
                        logger.info(f"🆕 Discovered new site: {site_name}")
                    except Exception as e:
                        logger.error(f"Failed to create site {site_name}: {e}")
    
    return discovered


# ============================================================
# 4. የጣቢያ ኒች እና ገበያ ራስ-ሰር መለየት
# ============================================================

def analyze_site_niche(site: SiteRegistry):
    """
    የጣቢያውን ኮድ እና ይዘት አጥንቶ ኒች፣ ቁልፍ ቃላት እና ተወዳዳሪዎችን ይለያል
    """
    project_code, _ = get_site_project_state(site)
    
    if not project_code:
        return False
    
    # የጣቢያ መረጃን በአጭሩ ለ AI አቅርብ
    code_summary = {}
    for key, value in project_code.items():
        if value:
            code_summary[key] = value[:2000] + "..." if len(value) > 2000 else value
    
    prompt = f"""
    Analyze this website's code and content to determine:
    1. What is the primary niche/market?
    2. What are the main keywords (max 10)?
    3. Who are likely competitors (max 5)?
    4. What is the target audience?
    
    Website name: {site.name}
    Display name: {site.display_name}
    
    Codebase summary:
    {json.dumps(code_summary, indent=2)[:8000]}
    
    Return ONLY JSON:
    {{
        "niche": "string",
        "primary_keywords": ["keyword1", "keyword2"],
        "competitor_urls": ["https://competitor1.com", "https://competitor2.com"],
        "target_audience": "string description",
        "content_style": "professional|casual|storytelling|educational"
    }}
    """
    
    data = ask_ai_with_failover(prompt, pool_type="analysis")
    
    if data and "niche" in data:
        site.niche = data['niche']
        site.primary_keywords = data.get('primary_keywords', [])
        site.competitor_urls = data.get('competitor_urls', [])
        site.target_audience = data.get('target_audience', '')
        site.content_style = data.get('content_style', 'professional')
        site.save()
        logger.info(f"🧠 Analyzed niche for {site.name}: {site.niche}")
        return True
    return False


# ============================================================
# 5. የእድገት ስትራቴጂ ሞተር
# ============================================================

class GrowthStrategyEngine:
    """
    በመልቲ-ሌቭል የእድገት ስትራቴጂ የሚያስተዳድር ሞተር
    Level 1: Local → Level 2: City → Level 3: Country → Level 4: Continent → Level 5: Global
    """
    
    def __init__(self, site: SiteRegistry):
        self.site = site
    
    def get_strategy(self):
        """ለአሁኑ ደረጃ የእድገት ስትራቴጂ ይመልሳል"""
        strategies = {
            1: {
                'name': 'Local Growth',
                'focus': 'አካባቢያዊ ሻጮች እና ገዢዎች',
                'actions': [
                    'የአካባቢውን ንግዶች መዘርዘር',
                    'የአካባቢ ጋዜጣዎች ማስታወቂያ',
                    'የአካባቢ ፌስቡክ ግሩፖች መጠቀም',
                ],
                'target_audience': 'Local businesses and buyers'
            },
            2: {
                'name': 'City Growth',
                'focus': 'የከተማ ሻጮች እና ገዢዎች',
                'actions': [
                    'የከተማ ንግዶችን መዘርዘር',
                    'በትራንስፖርት ማስታወቂያ',
                    'የከተማ ተጽዕኖ ፈጣሪዎች',
                ],
                'target_audience': 'City-wide businesses'
            },
            3: {
                'name': 'National Growth',
                'focus': 'ሀገር አቀፍ ሻጮች እና ገዢዎች',
                'actions': [
                    'የሀገር አቀፍ ማስታወቂያ',
                    'በኢንፍሉዌንሰሮች ግብይት',
                    'የብሎግ ጽሁፎች እና ኤስኢኦ',
                ],
                'target_audience': 'National businesses'
            },
            4: {
                'name': 'Continental Growth',
                'focus': 'የአህጉር አቀፍ ሻጮች እና ገዢዎች',
                'actions': [
                    'የአህጉር አቀፍ ማስታወቂያ',
                    'በዓለም አቀፍ መድረኮች ግብይት',
                    'የቋንቋ ትርጉም እና የአካባቢ ማመቻቸት',
                ],
                'target_audience': 'Continental businesses'
            },
            5: {
                'name': 'Global Growth',
                'focus': 'ዓለም አቀፍ ሻጮች እና ገዢዎች',
                'actions': [
                    'ዓለም አቀፍ ማስታወቂያ',
                    'በአለም አቀፍ ጉባኤዎች ተሳትፎ',
                    'ባለብዙ ቋንቋ ድጋፍ',
                ],
                'target_audience': 'International businesses'
            }
        }
        level = self.site.growth_level or 1
        return strategies.get(level, strategies[1])
    
    def execute_actions(self):
        """የአሁኑን የእድገት ስትራቴጂ ይተገብራል"""
        strategy = self.get_strategy()
        
        logger.info(f"📈 Executing {strategy['name']} strategy for {self.site.name}")
        
        # የተግባር ዝርዝርን ወደ ባክሎግ ይጨምራል
        for action in strategy['actions']:
            AIProjectBacklog.objects.get_or_create(
                task_name=f"Growth_L{self.site.growth_level}_{action[:30]}",
                task_type="growth",
                target_file="growth_strategy.md",
                site=self.site,
                defaults={
                    'priority': 'High',
                    'description': f"Level {self.site.growth_level}: {action}",
                    'status': 'Pending',
                    'estimated_hours': 2.0,
                    'complexity': 3
                }
            )
        
        return strategy


# ============================================================
# 6. የግብይት ካምፔን ሞተር
# ============================================================

class MarketingEngine:
    """የግብይት ካምፔኖችን የሚያስተዳድር ሞተር"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site
    
    def generate_marketing_content(self, product=None):
        """ለግብይት የሚሆን ይዘት ያመነጫል"""
        context = f"Site: {self.site.display_name}\nNiche: {self.site.niche}\n"
        if product:
            context += f"Product: {product.title}\nPrice: {product.price}\nDescription: {product.description[:200]}\n"
        
        prompt = f"""
        Generate marketing content for:
        {context}
        
        Create:
        1. Facebook post (professional, 100-150 words)
        2. Telegram message (concise, 50-80 words)
        3. Twitter/X post (short, 1-2 sentences)
        4. Email subject line (short, 5-8 words)
        5. SEO meta description (150-160 characters)
        
        Return ONLY JSON:
        {{
            "facebook_post": "string",
            "telegram_message": "string",
            "twitter_post": "string",
            "email_subject": "string",
            "seo_meta_description": "string"
        }}
        """
        
        data = ask_ai_with_failover(prompt, pool_type="marketing")
        return data
    
    def create_campaign(self, campaign_type, message, target_audience=None):
        """አዲስ ግብይት ካምፔን ይፈጥራል"""
        campaign = MarketingCampaign.objects.create(
            site=self.site,
            name=f"{campaign_type}_{timezone.now().strftime('%Y%m%d')}",
            campaign_type=campaign_type,
            status='scheduled',
            message=message,
            target_audience=target_audience or {},
            scheduled_at=timezone.now() + timezone.timedelta(hours=1)
        )
        return campaign
    
    def send_notification(self, recipient, message, notification_type='email', subject=''):
        """ማሳወቂያ ወደ ወረፋ ይጨምራል"""
        NotificationQueue.objects.create(
            site=self.site,
            notification_type=notification_type,
            recipient=recipient,
            subject=subject,
            message=message,
            is_sent=False
        )


# ============================================================
# 7. የደንበኛ ማግኛ ሞተር
# ============================================================

class CustomerAcquisitionEngine:
    """ደንበኞችን ለማግኘት እና ለማሳወቅ የሚረዳ ሞተር"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site
    
    def generate_onboarding_message(self, seller_name="there"):
        """ለአዲስ ሻጭ የመጀመሪያ መልእክት ያዘጋጃል"""
        return f"""
        👋 እንኳን ደህና መጡ ለ {self.site.display_name}!
        
        እቃዎትን በፍጥነት ለመሸጥ እና ለማስተዋወቅ ዝግጁ ነን።
        
        📦 እቃዎትን እዚህ ይለጥፉ፦
        {self.site.deployment_url}/post-product/
        
        📊 እቃዎትን ለማስተዳደር፦
        {self.site.deployment_url}/dashboard/
        
        💬 ለጥያቄዎች፦ support@{self.site.name}.com
        
        እንኳን ደህና መጡ! 🚀
        """
    
    def log_acquisition(self, channel, contact_info, name="", message=""):
        """የደንበኛ ማግኛ ተግባርን ይመዘግባል"""
        return CustomerAcquisitionLog.objects.create(
            site=self.site,
            channel=channel,
            contact_info=contact_info,
            name=name,
            message_sent=message,
            response_received=False,
            converted_to_seller=False
        )


# ============================================================
# 8. የአንድ ጣቢያ ትንተና (Single Site Analysis)
# ============================================================

def run_single_site_analysis(site: SiteRegistry):
    """
    ለአንድ የተወሰነ ጣቢያ የዕድገት ትንተና ያካሂዳል
    """
    now = timezone.now()
    site_name = site.name
    results = []
    
    logger.info(f"🚀 Starting analysis for site: {site_name}")
    
    # 1. የጣቢያ ሁኔታ ያንብብ
    project_code, file_paths = get_site_project_state(site)
    
    if not project_code:
        logger.warning(f"⚠️ No code found for site: {site_name}")
        return f"⚠️ No code found for {site_name}"
    
    # 2. ለዚህ ጣቢያ የተለዩ ስራዎችን ያግኝ
    pending_tasks = AIProjectBacklog.objects.filter(
        site=site,
        status='Pending'
    ).annotate(
        has_unfinished_dependency=models.Exists(
            AIProjectBacklog.objects.filter(
                pk=models.OuterRef('dependency_id'), 
                status__in=['Pending', 'Running']
            )
        )
    ).filter(has_unfinished_dependency=False).order_by('-priority', 'created_at')
    
    target_task = pending_tasks.first()
    
    # 3. ከሌሉ ጣቢያውን አዲስ ስራዎችን ይፈልግ
    forced_instruction = ""
    
    # ለዚህ ጣቢያ የተለዩ ኦቨርራይዶችን ያግኝ
    override_obj = AdminOverrideInstruction.objects.filter(
        site=site,
        is_processed=False
    ).order_by('created_at').first()
    
    if override_obj:
        forced_instruction = f"CRITICAL USER COMMAND OVERRIDE: {override_obj.instruction}"
        if override_obj.backlog_task:
            target_task = override_obj.backlog_task
            target_task.status = 'Running'
            target_task.save()
        logger.info(f"🚨 Admin Override for {site_name}: {override_obj.instruction}")
        results.append(f"Override: {override_obj.instruction[:50]}...")
    
    # 4. ፕሮምፕት ያዘጋጅ
    # የጣቢያ መረጃ እና የእድገት ስትራቴጂ
    strategy_engine = GrowthStrategyEngine(site)
    strategy = strategy_engine.get_strategy()
    
    prompt = f"""
    You are 'EthAfri Super AI Architect' for site: {site_name}.
    
    Site Information:
    - Niche: {site.niche}
    - Target Market: {site.target_market}
    - Keywords: {site.primary_keywords}
    - Competitors: {site.competitor_urls}
    - Growth Level: {site.growth_level} - {strategy['name']}
    - Monthly Visitors: {site.monthly_visitors}
    - Total Sellers: {site.total_sellers}
    - Total Products: {site.total_products}
    
    Growth Strategy Focus: {strategy['focus']}
    Target Audience: {site.target_audience}
    
    Current Codebase State: {json.dumps(project_code, indent=2)[:5000]}
    Active Task: {target_task.task_name if target_task else 'Audit and Discovery for this niche'}
    {forced_instruction}
    
    Engineering Rules:
    - Return ONLY raw JSON.
    - Validate Python syntax within the code updates.
    - Use Django best practices.
    - Focus on SEO and marketing improvements for this niche.
    - Suggest business growth actions if needed.
    """
    
    # 5. AI ጥሪ
    data = ask_ai_with_failover(prompt, pool_type="coding")
    
    if not data or "error" in data:
        err_msg = data.get('error', 'Unknown Error') if data else 'No Response'
        if any(x in str(err_msg) for x in ["429", "RESOURCE_EXHAUSTED", "quota"]):
            next_retry = now + timezone.timedelta(hours=24)
            retry_config, _ = SiteConfig.objects.get_or_create(
                key=f"NEXT_ALLOWED_RUN_TIME_{site_name}",
                defaults={'value': {'time': next_retry.isoformat()}}
            )
            retry_config.value = {'time': next_retry.isoformat()}
            retry_config.save()
            if target_task:
                target_task.status = 'Pending'
                target_task.save()
            return f"💤 Quota exhausted for {site_name}. Hibernating until {next_retry}"
        
        if target_task:
            target_task.status = 'Pending'
            target_task.save()
        return f"❌ Fail for {site_name}: {err_msg}"
    
    # 6. አዲስ ስራዎችን ያስመዝግብ (ከጣቢያ ጋር በማገናኘት)
    for t in data.get('backlog_tasks', []):
        AIProjectBacklog.objects.get_or_create(
            task_name=t['task_name'],
            task_type=t.get('task_type', 'code'),
            target_file=t['target_file'],
            site=site,
            defaults={
                'priority': t.get('priority', 'Medium'),
                'status': 'Pending',
                'description': t.get('description', ''),
                'estimated_hours': t.get('estimated_hours', 1.0),
                'complexity': t.get('complexity', 1)
            }
        )
        results.append(f"📋 Added task: {t['task_name']}")
    
    # 7. የኮድ ማሻሻያ
    updates = data.get('updates', {})
    code_changed = False
    improvement_metrics = data.get('improvement_metrics', {})
    
    for key, new_content in updates.items():
        if new_content and len(new_content.strip()) > 10:
            if key in ['models', 'views', 'urls', 'forms']:
                try:
                    compile(new_content, f"test_{key}.py", 'exec')
                except SyntaxError as e:
                    logger.error(f"❌ Syntax Error for {site_name}: {e}")
                    AgentErrorLog.objects.create(
                        task_name=target_task.task_name if target_task else "Audit",
                        error_type='syntax',
                        error_message=str(e),
                        code_attempted=new_content,
                        site=site
                    )
                    results.append(f"⚠️ Syntax error in {key}: {str(e)[:50]}")
                    continue

            path = file_paths.get(key)
            if path:
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    old_code = open(path, 'r').read() if os.path.exists(path) else ""
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    AIEvolutionLog.objects.create(
                        backlog_task=target_task,
                        target_file=key,
                        reason_for_change=f"Autonomous Build for {site_name}: {target_task.task_name if target_task else 'System Evolution'}",
                        old_code_backup=old_code,
                        new_code_patch=new_content,
                        improvement_metrics=improvement_metrics,
                        site=site
                    )
                    code_changed = True
                    results.append(f"✅ Updated {key}")
                except Exception as e:
                    results.append(f"❌ Error updating {key}: {str(e)[:50]}")
    
    # 8. የእድገት ስትራቴጂ ማሻሻያ
    if data.get('growth_actions'):
        for action in data.get('growth_actions', []):
            AIProjectBacklog.objects.get_or_create(
                task_name=f"Growth_{action[:30]}",
                task_type="growth",
                target_file="growth_strategy.md",
                site=site,
                defaults={
                    'priority': 'High',
                    'description': action,
                    'status': 'Pending',
                    'estimated_hours': 2.0,
                    'complexity': 3
                }
            )
            results.append(f"📈 Added growth action: {action[:30]}...")
    
    # 9. የማህበራዊ ሚዲያ ይዘት (ከሆነ)
    if data.get('social_media_content'):
        marketing = MarketingEngine(site)
        # ማህበራዊ ሚዲያ ይዘት ወደ ወረፋ ይጨምር
        # (በእውነተኛ ስራ ላይ ለማህበራዊ ሚዲያ ኤፒአይ ይላካል)
        results.append("📱 Social media content generated")
    
    # 10. የጣቢያ መረጃ ማዘመን
    if improvement_metrics.get('seo_score'):
        site.total_products = Product.objects.filter(seller__isnull=False).count()
        site.save()
    
    # 11. ማጠቃለያ
    if override_obj:
        override_obj.is_processed = True
        override_obj.save()
    
    if target_task:
        target_task.status = 'Completed'
        target_task.save()
    
    return f"✅ Evolved {site_name}! {' | '.join(results[:5])}"


# ============================================================
# 9. ዋናው የዕድገት ሞተር (run_daily_market_analysis)
# ============================================================

def run_daily_market_analysis():
    """
    ሙሉ አውቶኖመስ የንግድ እድገት ሞተር
    አሁን የደንበኛ ማግኛ፣ የግብይት ካምፔን እና የእድገት ስትራቴጂ ያካትታል
    """
    now = timezone.now()
    results = []
    
    # 🛡️ 1. የራስ-መገደብ ፍተሻ (Global Hibernation)
    retry_config, _ = SiteConfig.objects.get_or_create(
        key="NEXT_ALLOWED_RUN_TIME", 
        defaults={'value': {'time': '2000-01-01T00:00:00'}}
    )
    
    try:
        next_run = timezone.datetime.fromisoformat(retry_config.value.get('time'))
        if timezone.is_naive(next_run):
            next_run = timezone.make_aware(next_run)
        
        if now < next_run:
            logger.info(f"💤 Global engine is in hibernation mode. Wakes up at {next_run}")
            return f"💤 Sleeping until {next_run}"
    except Exception as parse_err:
        logger.warning(f"⚠️ NEXT_ALLOWED_RUN_TIME parse error: {parse_err}")
    
    # 🛡️ 2. የመቆለፊያ ጥበቃ
    lock, _ = SiteConfig.objects.get_or_create(key="EVOLUTION_LOCK", defaults={'value': {'status': 'idle'}})
    if lock.value.get('status') == 'running':
        stale = True
        last_run_str = lock.value.get('last_run')
        if last_run_str:
            try:
                last_run_dt = timezone.datetime.fromisoformat(last_run_str)
                if timezone.is_naive(last_run_dt):
                    last_run_dt = timezone.make_aware(last_run_dt)
                stale = (now - last_run_dt) > timezone.timedelta(minutes=15)
            except Exception:
                stale = True
        
        if not stale:
            return "⚠️ Skip: System is currently compiling another feature."
        logger.warning("🛡️ Stale EVOLUTION_LOCK detected (>15min) — auto-overriding.")
    
    lock.value = {'status': 'running', 'last_run': now.isoformat()}
    lock.save()
    
    try:
        # 🔍 3. አዲስ ጣቢያዎችን ያግኝ
        new_sites = discover_new_sites()
        for site in new_sites:
            results.append(f"🆕 Discovered: {site.name}")
            
            # 🧠 4. ኒች እና ገበያ ይተነትን
            if analyze_site_niche(site):
                results.append(f"🧠 Analyzed niche: {site.niche}")
            
            # 📈 5. የእድገት ስትራቴጂ ይጀምር
            strategy = GrowthStrategyEngine(site)
            strategy.execute_actions()
            results.append(f"📈 Started {strategy.get_strategy()['name']} strategy")
        
        # 🌐 6. ሁሉንም ንቁ ጣቢያዎች አስኬድ
        active_sites = SiteRegistry.objects.filter(is_active=True)
        
        if not active_sites.exists():
            logger.info("🧠 No active sites found. Creating default site...")
            default_site, _ = SiteRegistry.objects.get_or_create(
                name="primary",
                defaults={
                    'display_name': "Primary Site",
                    'niche': "general",
                    'target_market': "Global",
                    'repo_path': str(settings.BASE_DIR),
                    'is_active': True
                }
            )
            active_sites = [default_site]
            results.append(f"🏗️ Created default site: {default_site.name}")
        
        for site in active_sites:
            try:
                # 📈 7. የእድገት ስትራቴጂ አስኬድ
                strategy = GrowthStrategyEngine(site)
                strategy.execute_actions()
                
                # 🧠 8. ዋናውን የዕድገት ትንተና አስኬድ
                growth_result = run_single_site_analysis(site)
                results.append(f"[{site.name}] {growth_result}")
                
                # 📊 9. የጣቢያ መረጃ አዘምን
                site.total_products = Product.objects.filter(seller__isnull=False).count()
                site.total_sellers = User.objects.filter(product__isnull=False).distinct().count()
                site.growth_level = site.update_growth_level() if hasattr(site, 'update_growth_level') else site.growth_level
                site.save()
                
            except Exception as e:
                error_msg = f"[{site.name}] ❌ Error: {str(e)}"
                results.append(error_msg)
                logger.error(error_msg)
                
                # ስህተቱን በ AgentErrorLog ውስጥ መዝግብ
                try:
                    AgentErrorLog.objects.create(
                        task_name=f"Site_{site.name}_Analysis",
                        error_type='runtime',
                        error_message=str(e)[:500],
                        code_attempted="Full site analysis",
                        site=site
                    )
                except Exception:
                    pass
        
        # 10. የመጨረሻ ማጠቃለያ
        summary = " | ".join(results[:10])  # ብዙ ከሆነ የመጀመሪያዎቹን 10 ብቻ
        return f"🎉 Business Evolved! {summary}"
        
    except Exception as e:
        logger.error(f"❌ Business Engine Crash: {e}")
        return f"❌ Error: {str(e)}"
    finally:
        lock.value = {'status': 'idle'}
        lock.save()
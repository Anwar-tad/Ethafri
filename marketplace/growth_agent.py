

# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ለውጥ፦ ሙሉ የተጠናከረ ስሪት v5 (የተመቻቸ) — Confirmed Schema + Persistence Fix +
#         Structured Validation + Self-Critique + Real Test Execution + Safe Gating
# ⚙️ ማስተካከያ፦ የሩቅ ጣቢያዎችን በ GitHub API ማንበብ (Fetch Raw) እና የ Preservations Safeguards ተጨምረዋል
# 📅 ቀን፦ 2026-06-23
# ============================================================

import json
import os
import re
import logging
import sys
import time
import random
import hashlib
import requests
from io import StringIO
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management import call_command
from django.urls import clear_url_caches
from importlib import reload
from groq import Groq
from google import genai
from django.db import models, connection, connections
from django.db.models import Q, Avg, Count, Case, When, Value, IntegerField, Sum

from .models import (
    SiteConfig, Category, Product, AIProjectBacklog, AIEvolutionLog,
    AdminOverrideInstruction, AgentErrorLog, SiteRegistry, SelfHealingLog,
    CustomerAcquisitionLog, MarketingCampaign, SellerProfile, NotificationQueue,
    VectorMemory, AgentTask, ABTest, SecurityLog, PredictionLog, ExternalAPI
)
from .code_apply import apply_code_change

logger = logging.getLogger(__name__)


# ============================================================
# 1. ረዳት ተግባራት (Helper Functions)
# ============================================================

def extract_json(text):
    """JSON ከ AI ምላሽ ያወጣል"""
    if not text or not isinstance(text, str):
        return None
    try:
        clean_text = re.sub(r'^```json\s*|^```\s*|```$', '', text.strip(), flags=re.MULTILINE)
        match = re.search(r'\{.*\}', clean_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(clean_text)
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"⚠️ JSON extraction failed: {e}")
        return None


def _validate_response_schema(data, expected_keys=None):
    """AI ምላሹ የሚጠበቀውን structure ማሟላቱን ያረጋግጣል"""
    if not isinstance(data, dict):
        return False
    if expected_keys:
        return all(k in data for k in expected_keys)
    return True


def get_targeted_code_context(project_code, target_file_key=None, max_chars=40000):
    """
    ለኤአይ የሚላከውን የኮድ መጠን በጥንቃቄ ያሳጥራል።
    የሚሻሻለውን ፋይል ሙሉ በሙሉ (እስከ 40,000 ቁምፊዎች) ይልካል፣ ሌሎችን ግን በአጭሩ ያሳያል።
    ይህም ትልቅ JSON ተቆርጦ ኤአይ እንዳይቋረጥ እና የፋይል መጥፋት እንዳይከሰት ይከላከላል።
    """
    optimized = {}
    for key, content in project_code.items():
        if not isinstance(content, str):
            optimized[key] = content
            continue
        
        if target_file_key and key == target_file_key:
            optimized[key] = content[:max_chars] + ("\n... [Truncated due to extreme size]" if len(content) > max_chars else "")
        else:
            lines = content.split('\n')
            if len(lines) > 35:
                optimized[key] = "\n".join(lines[:35]) + f"\n... [Truncated {len(lines)-35} lines to save tokens]"
            else:
                optimized[key] = content
    return optimized


def get_or_create_backlog_task_safe(site, task_name, defaults):
    """
    የተደጋገሙ ስራዎች ቢኖሩ እንኳ MultipleObjectsReturned ሳይጥል 
    የመጀመሪያውን አስቀርቶ የተደጋገሙትን በራሱ የሚያጠፋ (Deduplicate) የራስ-ጥገና ተግባር
    """
    matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name).order_by('id')
    
    if matching.exists():
        task = matching.first()
        if matching.count() > 1:
            deleted_count, _ = matching.exclude(id=task.id).delete()
            logger.info(f"🧹 Self-Healing DB: Cleaned {deleted_count} duplicate tasks for '{task_name}' on {site.name}")
        return task, False
    
    try:
        task = AIProjectBacklog.objects.create(site=site, task_name=task_name, **defaults)
        return task, True
    except Exception as e:
        logger.error(f"Error creating safe backlog task: {e}")
        matching = AIProjectBacklog.objects.filter(site=site, task_name=task_name)
        if matching.exists():
            return matching.first(), False
        raise e


# ============================================================
# 🌐 ጊትሃብ የሩቅ ፋይሎች ንባብ (GitHub API Raw Fetcher)
# ============================================================

def fetch_remote_file_from_github(repo, file_path, token=None):
    """
    ከሩቅ የጊትሃብ ሪፖዚተሪ ላይ የፋይል ይዘትን Raw በሚባል መልክ በቀጥታ ያነባል (ከዲስክ ንክኪ ነጻ)
    """
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return res.text
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch remote file {file_path} from GitHub: {e}")
    return None


def get_site_project_state(site: SiteRegistry, force_refresh=False):
    """
    የጣቢያውን የኮድ ሁኔታ ያነባል። የጣቢያው repo_path የድረ-ገጽ ሊንክ (HTTP) ከሆነ
    በራስ-ሰር በ GitHub API አማካኝነት የሩቅ ጣቢያውን ፋይሎች ከጊትሃብ ያነባል።
    """
    if not site:
        return {}, {}
    
    repo_path = site.repo_path
    is_remote = False
    repo_name = ""
    
    if not repo_path or repo_path.startswith('http') or 'github.com' in repo_path:
        is_remote = True
        repo_name = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
        if repo_path:
            match = re.search(r"github\.com/([^/]+/[^/]+)", repo_path)
            if match:
                repo_name = match.group(1).replace('.git', '')
                
    # የውጭ ሳይት ከሆነ በሰርቨር ላይ በተለየ ጊዜያዊ ማህደር ውስጥ ማስቀመጥ (የፕራይመሪውን እንዳያጠፋ)
    base = repo_path
    if is_remote:
        base = os.path.join('/tmp', 'ethafri_agent', site.name)
    
    target_files = {
        'models': os.path.join(base, 'marketplace', 'models.py'),
        'views': os.path.join(base, 'marketplace', 'views.py'),
        'urls': os.path.join(base, 'marketplace', 'urls.py'),
        'forms': os.path.join(base, 'marketplace', 'forms.py'),
        'admin': os.path.join(base, 'marketplace', 'admin.py'),
        'home_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'home.html'),
    }
    
    state = {}
    file_paths = {}
    github_token = getattr(settings, 'GITHUB_TOKEN', None)
    
    for key, path in target_files.items():
        # የኮድ ጽሕፈት ስራው የሚከናወነው በአገር ውስጥ ማህደር ውስጥ ብቻ ነው
        local_path = os.path.join(settings.BASE_DIR, 'marketplace', f'{key}.py') if site.name == 'primary' else path
        file_paths[key] = local_path
        
        if is_remote:
            relative_path = f"marketplace/{key}.py"
            content = fetch_remote_file_from_github(repo_name, relative_path, token=github_token)
            if content is not None:
                state[key] = content
                site_key = f"site_{site.id}_{key}"
                _project_hashes[f"{site_key}_content"] = content
            else:
                state[key] = "❌ MISSING_FILE: This file doesn't exist on remote repository yet."
        else:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        state[key] = f.read()
                except Exception as e:
                    state[key] = f"ERROR: Could not read file - {e}"
            else:
                state[key] = "❌ MISSING_FILE: This file doesn't exist yet."
                
    return state, file_paths

# ============================================================
# 2. የኤአይ ፎልባክ ሞተር (AI Failover Engine)
# ============================================================

def ask_ai_with_failover(prompt, pool_type="coding", max_retries=2, timeout=60, expected_keys=None):
    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    mistral_key = os.environ.get('MISTRAL_API_KEY')
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    huggingface_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_TOKEN')
    github_token = os.environ.get('GITHUB_TOKEN')

    def call_gemini():
        if not gemini_keys:
            return None
        for idx, key in enumerate(gemini_keys):
            try:
                client = genai.Client(api_key=key)
                res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                data = extract_json(res.text)
                if data and "error" not in data:
                    return data
            except Exception as e:
                logger.warning(f"🔄 Gemini Key {idx+1} exhausted: {e}")
                time.sleep(1)
        return None

    def call_github():
        if not github_token:
            return None
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"}
        model = "azure-openai/gpt-4o-mini" if "translation" in pool_type else "meta-llama-3.1-405b-instruct"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.error(f"GitHub Error: {e}")
            return None

    def call_groq():
        if not groq_key:
            return None
        try:
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], timeout=timeout)
            return extract_json(chat.choices[0].message.content)
        except Exception as e:
            logger.warning(f"🔄 Groq failed: {e}")
            return None

    def call_mistral():
        if not mistral_key:
            return None
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
        model = "codestral-latest" if pool_type == "coding" else "mistral-large-latest"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.warning(f"🔄 Mistral failed: {e}")
            return None

    def call_huggingface():
        if not huggingface_key:
            return None
        url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1/chat/completions"
        headers = {"Authorization": f"Bearer {huggingface_key}", "Content-Type": "application/json"}
        try:
            res = requests.post(url, headers=headers, json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": [{"role": "user", "content": prompt}]}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.warning(f"🔄 Hugging Face failed: {e}")
            return None

    def call_openrouter():
        if not openrouter_key:
            return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        model = "google/gemini-2.5-flash" if "translation" in pool_type else "deepseek/deepseek-chat"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.warning(f"🔄 OpenRouter failed: {e}")
            return None

    provider_configs = {
        "coding": [call_mistral, call_github, call_groq, call_openrouter, call_huggingface, call_gemini],
        "translation": [call_gemini, call_github, call_huggingface, call_openrouter, call_groq],
        "translation_github": [call_github, call_gemini, call_huggingface, call_openrouter],
        "translation_huggingface": [call_huggingface, call_github, call_gemini, call_openrouter],
        "marketing": [call_openrouter, call_gemini, call_mistral, call_github, call_groq],
        "analysis": [call_gemini, call_openrouter, call_huggingface, call_groq],
        "healing": [call_mistral, call_github, call_gemini, call_openrouter, call_huggingface],
        "critique": [call_groq, call_gemini, call_openrouter],
    }

    providers = provider_configs.get(pool_type, [call_groq, call_mistral, call_github, call_huggingface, call_openrouter])
    random.shuffle(providers)

    QUOTA_MARKERS = ["429", "RESOURCE_EXHAUSTED", "quota", "rate_limit"]

    for provider in providers:
        for attempt in range(max_retries):
            try:
                result = provider()
                if result and "error" not in result:
                    if expected_keys and not _validate_response_schema(result, expected_keys):
                        logger.warning(f"⚠️ {provider.__name__} returned malformed schema, trying next...")
                        break
                    logger.info(f"✅ Success with {provider.__name__}")
                    return result
            except Exception as e:
                err_str = str(e)
                if any(marker in err_str for marker in QUOTA_MARKERS):
                    logger.warning(f"💤 {provider.__name__} quota exhausted — moving to next provider")
                    break
                logger.warning(f"⚠️ Attempt {attempt+1} for {provider.__name__} failed: {e}")
                time.sleep(1)

    logger.error("❌ All AI providers failed")
    return {"error": "All AI providers failed after multiple attempts."}


ask_ethafri_ceo = ask_ai_with_failover


# ============================================================
# 4. አዲስ ጣቢያ ራስ-ሰር መለየት
# ============================================================

def discover_new_sites():
    base_path = settings.BASE_DIR
    discovered = []

    if not os.path.exists(base_path):
        return discovered

    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            if os.path.exists(os.path.join(item_path, 'manage.py')):
                site_name = item.lower().replace('_', '-').replace(' ', '-')
                existing = SiteRegistry.objects.filter(name=site_name).first()
                if not existing:
                    try:
                        site = SiteRegistry.objects.create(
                            name=site_name, display_name=item.replace('_', ' ').title(),
                            niche="general", target_market="Global",
                            repo_path=item_path, is_active=True, build_phase=0
                        )
                        discovered.append(site)
                        logger.info(f"🆕 Discovered new site: {site_name}")
                    except Exception as e:
                        logger.error(f"Failed to create site {site_name}: {e}")
    return discovered


# ============================================================
# 5. የጣቢያ ኒች እና ገበያ ራስ-ሰር መለየት
# ============================================================

def analyze_site_niche(site: SiteRegistry):
    project_code, _ = get_site_project_state(site)
    if not project_code:
        return False

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

    data = ask_ai_with_failover(prompt, pool_type="analysis", expected_keys=["niche"])

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
# 6. RAG Memory Engine
# ============================================================

class RAGMemoryEngine:
    def __init__(self, site: SiteRegistry = None):
        self.site = site

    def remember(self, memory_type, content, metadata=None, related_task=None):
        return VectorMemory.objects.create(
            memory_type=memory_type, content=content, metadata=metadata or {},
            site=self.site, related_task=related_task
        )

    def recall(self, query, memory_type=None, limit=5):
        return VectorMemory.find_similar(query, memory_type, self.site, limit)

    def learn_from_task(self, task, success=True):
        memory = VectorMemory.objects.create(
            memory_type='solution',
            content=f"Task: {task.task_name}\nResult: {task.result_data}",
            metadata={'agent_type': task.agent_type, 'success': success,
                      'site_id': task.site.id if task.site else None},
            site=self.site, related_task=task.backlog_task
        )
        memory.mark_used(success)
        return memory

    def get_stats(self):
        return {
            'total': VectorMemory.objects.filter(site=self.site).count(),
            'by_type': VectorMemory.objects.filter(site=self.site).values('memory_type').annotate(count=Count('id')),
            'avg_success': VectorMemory.objects.filter(site=self.site).aggregate(avg=Avg('success_rate'))['avg'] or 0,
        }


# ============================================================
# 7. Multi-Agent Orchestrator
# ============================================================

class AgentOrchestrator:
    AGENT_HANDLERS = {
        'code': 'handle_code_task', 'seo': 'handle_seo_task',
        'marketing': 'handle_marketing_task', 'data': 'handle_data_task',
        'review': 'handle_review_task', 'security': 'handle_security_task',
    }

    def __init__(self, site: SiteRegistry = None):
        self.site = site
        self.memory = RAGMemoryEngine(site)

    def assign_task(self, task_name, description, agent_type, priority=5):
        task = AgentTask.objects.create(
            agent_type=agent_type, task_name=task_name, description=description,
            priority=priority, site=self.site, status='pending'
        )
        logger.info(f"📋 Assigned {agent_type} task: {task_name}")
        return task

    def execute_task(self, task: AgentTask):
        task.start_task()
        try:
            handler_name = self.AGENT_HANDLERS.get(task.agent_type, 'handle_code_task')
            handler = getattr(self, handler_name, self.handle_code_task)

            result = handler(task)
            if result and 'error' not in result:
                task.complete_task(result)
                self.memory.learn_from_task(task, success=True)
                logger.info(f"✅ Task {task.task_name} completed")
            else:
                task.fail_task(str(result))
                self.memory.learn_from_task(task, success=False)
                logger.error(f"❌ Task {task.task_name} failed")
        except Exception as e:
            task.fail_task(str(e))
            logger.error(f"❌ Task {task.task_name} error: {e}")

    def handle_code_task(self, task):
        similar = self.memory.recall(task.description, 'code', limit=3)
        context = "\n".join([f"Previous solution: {m.content}" for m in similar])
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\n{context}\nGenerate code solution."
        return ask_ai_with_failover(prompt, pool_type="coding")

    def handle_seo_task(self, task):
        similar = self.memory.recall(task.description, 'insight', limit=3)
        context = "\n".join([f"Previous insight: {m.content}" for m in similar])
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\n{context}\nGenerate SEO recommendations."
        return ask_ai_with_failover(prompt, pool_type="analysis")

    def handle_marketing_task(self, task):
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\nGenerate marketing content."
        return ask_ai_with_failover(prompt, pool_type="marketing")

    def handle_data_task(self, task):
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\nAnalyze data and provide insights."
        return ask_ai_with_failover(prompt, pool_type="analysis")

    def handle_review_task(self, task):
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\nReview the following and provide feedback."
        return ask_ai_with_failover(prompt, pool_type="analysis")

    def handle_security_task(self, task):
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\nIdentify security issues and provide fixes."
        return ask_ai_with_failover(prompt, pool_type="coding")

    def get_stats(self):
        return {
            'total': AgentTask.objects.filter(site=self.site).count(),
            'by_type': AgentTask.objects.filter(site=self.site).values('agent_type').annotate(
                count=Count('id'), completed=Count('id', filter=Q(status='completed'))
            ),
            'by_status': AgentTask.objects.filter(site=self.site).values('status').annotate(count=Count('id')),
        }


# ============================================================
# 8. Predictive Analytics Engine
# ============================================================

class PredictiveEngine:
    def __init__(self, site: SiteRegistry = None):
        self.site = site

    def predict_traffic(self, days=30):
        now = timezone.now()
        last_30 = Product.objects.filter(site=self.site, created_at__gte=now - timedelta(days=30)).count()
        prev_30 = Product.objects.filter(
            site=self.site, created_at__gte=now - timedelta(days=60), created_at__lt=now - timedelta(days=30)
        ).count()

        if prev_30 > 0:
            growth_rate = (last_30 - prev_30) / prev_30
            confidence = 60.0
        else:
            growth_rate = 0.1 if last_30 > 0 else 0.0
            confidence = 35.0

        base_visitors = (self.site.monthly_visitors or 0) if self.site else 0
        predicted = max(base_visitors * (1 + growth_rate), base_visitors)

        return PredictionLog.objects.create(
            prediction_type='traffic', predicted_value=predicted, confidence_score=confidence,
            input_data={'days': days, 'recent_products': last_30, 'prev_products': prev_30,
                       'growth_rate': round(growth_rate, 3)},
            site=self.site
        )

    def predict_seo_score(self, product_id=None):
        avg_seo = Product.objects.filter(site=self.site, seller__isnull=False).aggregate(avg=Avg('seo_score'))['avg'] or 50
        return PredictionLog.objects.create(
            prediction_type='seo', predicted_value=avg_seo, confidence_score=65.0,
            input_data={'product_id': product_id}, site=self.site
        )

    def get_stats(self):
        return {
            'total': PredictionLog.objects.filter(site=self.site).count(),
            'by_type': PredictionLog.objects.filter(site=self.site).values('prediction_type').annotate(count=Count('id')),
            'avg_confidence': PredictionLog.objects.filter(site=self.site).aggregate(avg=Avg('confidence_score'))['avg'] or 0,
        }


# ============================================================
# 9. Security Scanner
# ============================================================

class SecurityScanner:
    def __init__(self, site: SiteRegistry = None):
        self.site = site

    def scan_code(self, code, file_path="", line_number=None):
        vulnerabilities = []
        patterns = [
            (r'SECRET_KEY\s*=\s*[\'"](?!django-insecure)[^\'"]{10,}[\'"]', 'Possible hardcoded production secret key', 'high'),
            (r'password\s*=\s*[\'"][^\'"]{4,}[\'"]', 'Possible hardcoded password literal', 'high'),
            (r'\beval\s*\(', 'Use of eval() — code injection risk', 'critical'),
            (r'\bexec\s*\(', 'Use of exec() — code injection risk', 'critical'),
            (r'os\.system\s*\(', 'Direct OS command execution', 'high'),
            (r'pickle\.(loads|load)\s*\(', 'Unsafe pickle deserialization', 'high'),
            (r'\.execute\(\s*[\"\'].*?[%+].*?(request\.|f[\"\'])', 'Possible SQL injection (string interpolation in raw query)', 'critical'),
        ]
        for pattern, description, severity in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append({'description': description, 'severity': severity,
                                        'file_path': file_path, 'line_number': line_number})
        for vuln in vulnerabilities:
            SecurityLog.objects.get_or_create(
                category='code_injection', severity=vuln['severity'], description=vuln['description'],
                file_path=vuln['file_path'], site=self.site, is_fixed=False,
                defaults={'line_number': vuln['line_number']}
            )
        return vulnerabilities

    def get_stats(self):
        return {
            'total': SecurityLog.objects.filter(site=self.site).count(),
            'unfixed': SecurityLog.objects.filter(site=self.site, is_fixed=False).count(),
            'by_severity': SecurityLog.objects.filter(site=self.site).values('severity').annotate(count=Count('id')),
        }


# ============================================================
# 10. የእድገት ስትራቴጂ ሞተር (ጂኦግራፊያዊ መድረክ)
# ============================================================

class GrowthStrategyEngine:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def get_strategy(self):
        strategies = {
            1: {'name': 'Local Growth', 'focus': 'አካባቢያዊ ሻጮች እና ገዢዎች',
                'actions': ['የአካባቢውን ንግዶች መዘርዘር', 'የአካባቢ ጋዜጣዎች ማስታወቂያ', 'የአካባቢ ፌስቡክ ግሩፖች መጠቀም']},
            2: {'name': 'City Growth', 'focus': 'የከተማ ሻጮች እና ገዢዎች',
                'actions': ['የከተማ ንግዶችን መዘርዘር', 'በትራንስፖርት ማስታወቂያ', 'የከተማ ተጽዕኖ ፈጣሪዎች']},
            3: {'name': 'National Growth', 'focus': 'ሀገር አቀፍ ሻጮች እና ገዢዎች',
                'actions': ['የሀገር አቀፍ ማስታወቂያ', 'በኢንፍሉዌንሰሮች ግብይት', 'የብሎግ ጽሁፎች SEO']},
            4: {'name': 'Continental Growth', 'focus': 'የአህጉር አቀፍ ሻጮች እና ገዢዎች',
                'actions': ['የአህጉር አቀፍ ማስታወቂያ', 'በዓለም አቀፍ መድረኮች ግብይት', 'የቋንቋ ትርጉም']},
            5: {'name': 'Global Growth', 'focus': 'ዓለም አቀፍ ሻጮች እና ገዢዎች',
                'actions': ['ዓለም አቀፍ ማስታወቂያ', 'በአለም አቀፍ ጉባኤዎች ተሳትፎ', 'ባለብዙ ቋንቋ ድጋፍ']}
        }
        level = self.site.growth_level or 1
        return strategies.get(level, strategies[1])

    def execute_actions(self):
        strategy = self.get_strategy()
        logger.info(f"📈 Executing {strategy['name']} strategy for {self.site.name}")
        for action in strategy['actions']:
            get_or_create_backlog_task_safe(
                self.site,
                task_name=f"Growth_L{self.site.growth_level}_{action[:30]}",
                defaults={
                    'task_type': "growth", 'target_file': "growth_strategy.md",
                    'priority': 'High', 'description': f"Level {self.site.growth_level}: {action}",
                    'status': 'Pending', 'estimated_hours': 2.0, 'complexity': 3,
                    'business_impact_score': 6, 'trigger_condition': f"GrowthStrategy:Level{self.site.growth_level}"
                }
            )
        return strategy


# ============================================================
# 11. Growth Stage Engine
# ============================================================

class GrowthStageEngine:
    PHASE_NAMES = {
        0: "Scaffolding", 1: "Real Data Seeding", 2: "Core Feature Expansion",
        3: "Engagement Features", 4: "Monetization & Growth", 5: "Mature / Replicate",
    }
    SEED_PRODUCT_THRESHOLD = 10
    SEED_CUSTOMER_THRESHOLD = 5

    def __init__(self, site: SiteRegistry):
        self.site = site

    def get_current_phase(self):
        return self.site.build_phase

    def get_real_counts(self):
        product_count = Product.objects.filter(site=self.site, is_active=True).count()
        customer_count = User.objects.filter(product__site=self.site).distinct().count()
        return product_count, customer_count

    def evaluate_and_advance(self):
        current_phase = self.get_current_phase()
        product_count, customer_count = self.get_real_counts()
        new_tasks = []

        if current_phase == 0:
            self._advance_to(1)
            new_tasks.append(self._create_seed_task())

        elif current_phase == 1:
            if product_count >= self.SEED_PRODUCT_THRESHOLD and customer_count >= self.SEED_CUSTOMER_THRESHOLD:
                self._advance_to(2)
                seed_task = AIProjectBacklog.objects.filter(
                    site=self.site, task_name__icontains="Seed Real Products"
                ).order_by('-created_at').first()
                new_tasks.extend(self._create_core_feature_tasks(dependency=seed_task))

        elif current_phase == 2:
            core_done = not AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__in=["Build Product Detail Page", "Build Product Edit Feature", "Build Product Delete Feature"],
                status__in=['Pending', 'Running']
            ).exists()
            if core_done:
                self._advance_to(3)
                new_tasks.extend(self._create_engagement_tasks())

        elif current_phase == 3:
            engagement_done = not AIProjectBacklog.objects.filter(
                site=self.site, task_name__in=["Add Search & Filter", "Add Product Reviews"],
                status__in=['Pending', 'Running']
            ).exists()
            if engagement_done:
                self._advance_to(4)
                new_tasks.extend(self._create_monetization_tasks())

        self.site.real_product_count = product_count
        self.site.real_customer_count = customer_count
        self.site.save()

        return new_tasks

    def _advance_to(self, phase):
        self.site.build_phase = phase
        self.site.phase_transition_date = timezone.now()
        self.site.save()
        logger.info(f"📈 [{self.site.name}] Build Phase → {phase}: {self.PHASE_NAMES.get(phase)}")

    def _create_seed_task(self):
        task, _ = get_or_create_backlog_task_safe(
            self.site, "Seed Real Products & Customers",
            defaults={
                'target_file': "data_seeding",
                'priority': 'Critical', 'status': 'Pending',
                'description': "Phase 1: ድረ-ገጹን ለማነቃቃት እውነተኛ ምርትና ደንበኛ ማግኘት/መለጠፍ ያስፈልጋል።",
                'business_impact_score': 10, 'trigger_condition': 'GrowthStage:Phase0→1'
            }
        )
        return task

    def _create_core_feature_tasks(self, dependency=None):
        specs = [
            ("Build Product Detail Page", "views.py", "Phase 2: Product detail view"),
            ("Build Product Edit Feature", "views.py", "Phase 2: ሻጮች ምርታቸውን እንዲያስተካክሉ"),
            ("Build Product Delete Feature", "views.py", "Phase 2: ሻጮች ምርታቸውን እንዲያጠፉ"),
            ("Build Customer Dashboard", "views.py", "Phase 2: ደንበኞች ግዢ ታሪክ እንዲያዩ"),
        ]
        created = []
        for name, target_file, desc in specs:
            task, _ = get_or_create_backlog_task_safe(
                self.site, name,
                defaults={
                    'target_file': target_file,
                    'priority': 'Critical', 'status': 'Pending', 'description': desc,
                    'dependency': dependency, 'business_impact_score': 9,
                    'trigger_condition': 'GrowthStage:Phase1→2'
                }
            )
            created.append(task)
        return created

    def _create_engagement_tasks(self):
        specs = [
            ("Add Search & Filter", "views.py", "Phase 3: ምርት ፍለጋ እና ማጣሪያ"),
            ("Add Product Reviews", "models.py", "Phase 3: የደንበኛ ግምገማ ስርዓት"),
        ]
        created = []
        for name, target_file, desc in specs:
            task, _ = get_or_create_backlog_task_safe(
                self.site, name,
                defaults={
                    'target_file': target_file,
                    'priority': 'High', 'status': 'Pending', 'description': desc,
                    'business_impact_score': 7, 'trigger_condition': 'GrowthStage:Phase2→3'
                }
            )
            created.append(task)
        return created

    def _create_monetization_tasks(self):
        specs = [
            ("Integrate Payment Gateway", "views.py", "Phase 4: ክፍያ ስርዓት"),
            ("Launch Marketing Campaign", "marketing", "Phase 4: ማርኬቲንግ"),
        ]
        created = []
        for name, target_file, desc in specs:
            task, _ = get_or_create_backlog_task_safe(
                self.site, name,
                defaults={
                    'target_file': target_file,
                    'priority': 'High', 'status': 'Pending', 'description': desc,
                    'business_impact_score': 10, 'trigger_condition': 'GrowthStage:Phase3→4'
                }
            )
            created.append(task)
        return created


# ============================================================
# 12. ማርኬቲንግ እና ደንበኛ ማግኛ ሞተሮች
# ============================================================

class MarketingEngine:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def generate_marketing_content(self, product=None):
        context = f"Site: {self.site.display_name}\nNiche: {self.site.niche}\n"
        if product:
            context += f"Product: {product.title}\nPrice: {product.price}\nDescription: {product.description[:200]}\n"
        prompt = f"""
        Generate marketing content for:
        {context}
        Create: 1. Facebook post (100-150 words) 2. Telegram message (50-80 words)
        3. Twitter/X post (1-2 sentences) 4. Email subject (5-8 words) 5. SEO meta description (150-160 chars)
        Return ONLY JSON: {{"facebook_post": "string", "telegram_message": "string",
        "twitter_post": "string", "email_subject": "string", "seo_meta_description": "string"}}
        """
        return ask_ai_with_failover(prompt, pool_type="marketing", expected_keys=["facebook_post"])

    def create_campaign(self, campaign_type, message, target_audience=None):
        return MarketingCampaign.objects.create(
            site=self.site, name=f"{campaign_type}_{timezone.now().strftime('%Y%m%d')}",
            campaign_type=campaign_type, status='scheduled', message=message,
            target_audience=target_audience or {}, scheduled_at=timezone.now() + timezone.timedelta(hours=1)
        )

    def send_notification(self, recipient, message, notification_type='email', subject=''):
        NotificationQueue.objects.create(
            site=self.site, notification_type=notification_type, recipient=recipient,
            subject=subject, message=message, is_sent=False
        )


class CustomerAcquisitionEngine:
    def __init__(self, site: SiteRegistry):
        self.site = site

    def generate_onboarding_message(self, seller_name="there"):
        return f"""
        👋 እንኳን ደህና መጡ ለ {self.site.display_name}!
        📦 እቃዎትን እዚህ ይለጥፉ፦ {self.site.deployment_url}/post-product/
        📊 እቃዎትን ለማስተዳደር፦ {self.site.deployment_url}/dashboard/
        💬 ለጥያቄዎች፦ support@{self.site.name}.com
        እንኳን ደህና መጡ! 🚀
        """

    def log_acquisition(self, channel, contact_info, name="", message=""):
        return CustomerAcquisitionLog.objects.create(
            site=self.site, channel=channel, contact_info=contact_info, name=name,
            message_sent=message, response_received=False, converted_to_seller=False
        )


# ============================================================
# 13. Self-Critique Loop
# ============================================================

def _self_critique(site, file_key, new_content, task_description):
    critique_prompt = f"""
    You are a senior code reviewer for site: {site.name}.
    Task being addressed: {task_description}
    File: {file_key}

    Proposed code change:
    {new_content[:3000]}

    Review for: correctness, Django best practices, security, breaking changes.
    Return ONLY JSON: {{"confidence_score": <0-100>, "concerns": ["concern1"], "safe_to_apply": true}}
    """
    review = ask_ai_with_failover(critique_prompt, pool_type="critique", expected_keys=["confidence_score"], max_retries=1)
    if review and isinstance(review, dict) and "confidence_score" in review:
        return review
    return {"confidence_score": 65, "concerns": ["Self-critique unavailable"], "safe_to_apply": True}


# ============================================================
# 14. Continuous Multi-Task Cycle
# ============================================================

MAX_TASKS_PER_CYCLE = 5
CYCLE_TIME_BUDGET_SECONDS = 25


def _priority_rank_annotation(queryset):
    rank = Case(
        When(priority='Critical', then=Value(4)), When(priority='High', then=Value(3)),
        When(priority='Medium', then=Value(2)), When(priority='Low', then=Value(1)),
        default=Value(0), output_field=IntegerField()
    )
    return queryset.annotate(priority_rank=rank)


def _select_next_backlog_task(site):
    qs = AIProjectBacklog.objects.filter(site=site, status='Pending').annotate(
        has_unfinished_dependency=models.Exists(
            AIProjectBacklog.objects.filter(pk=models.OuterRef('dependency_id'), status__in=['Pending', 'Running'])
        )
    ).filter(has_unfinished_dependency=False)
    qs = _priority_rank_annotation(qs)
    return qs.order_by('-business_impact_score', '-priority_rank', 'created_at').first()


def _run_django_check():
    out = StringIO()
    try:
        call_command('check', stdout=out, stderr=out)
        output = out.getvalue()
        passed = 'no issues' in output.lower() or output.strip() == ''
        return passed, output[:500]
    except Exception as e:
        return False, str(e)[:500]


def _execute_single_task_cycle(site, target_task, override_obj, project_code, file_paths, memory_engine, strategy):
    results = []
    forced_instruction = f"CRITICAL USER COMMAND OVERRIDE: {override_obj.instruction}" if override_obj else ""

    pending_errors = list(
        SelfHealingLog.objects.filter(resolved=False).order_by('-created_at')[:10]
        .values_list('error_message', flat=True)
    )

    memory_context = ""
    similar_memories = memory_engine.recall(
        f"Site: {site.name}, Task: {target_task.task_name if target_task else 'Audit'}",
        memory_type='strategy', limit=3
    )
    for mem in similar_memories:
        memory_context += f"\nPrevious successful pattern: {mem.content[:200]}\n"

    target_file_key = target_task.target_file if target_task else 'views'
    
    # ✅ FIXED: JSON Truncation bug resolved. Only send targeted summary context.
    optimized_code = get_targeted_code_context(project_code, target_file_key=target_file_key)

    prompt = f"""
    You are 'EthAfri Super AI Architect' for site: {site.name}.

    Site Information:
    - Niche: {site.niche} | Build Phase: {site.build_phase}
    - Target Market: {site.target_market}
    - Growth Strategy Focus: {strategy['focus']}

    Memory Context:
    {memory_context}

    Codebase State (Targeted Context):
    {json.dumps(optimized_code, indent=2)}

    Active Task: {target_task.task_name if target_task else 'Audit and Discovery'}
    {forced_instruction}

    🛡️ Known Production Errors (Self-Healing Queue, unresolved):
    {json.dumps(pending_errors, indent=2, ensure_ascii=False) if pending_errors else "None"}

    ⚠️ CRITICAL INSTRUCTION (PRESERVATION SAFEGUARD):
    - For any file you modify in 'updates', you MUST provide the FULL, COMPLETE file content with your changes merged.
    - Do NOT omit, truncate, or delete any existing models, views, imports, or functions unless explicitly told to.
    - If you return only the changes, you will destroy the existing file.
    
    Return ONLY raw JSON with keys: updates, backlog_tasks, self_healing_actions, database_migration_needed.
    - Validate Python syntax within code updates.
    - Use Django best practices.
    - For 'Known Production Errors' fixable via code, fix them and report in 'self_healing_actions':
      [{{"error_pattern": "<short substring>", "action_taken": "<what you did>", "resolved": true}}]
    - For DATA issues you cannot fix via code, report with "resolved": false and an admin-facing note.
    """

    data = ask_ai_with_failover(prompt, pool_type="coding", expected_keys=["updates"])

    if not data or "error" in data:
        err_msg = data.get('error', 'Unknown Error') if data else 'No Response'
        if any(x in str(err_msg) for x in ["429", "RESOURCE_EXHAUSTED", "quota"]):
            next_retry = timezone.now() + timezone.timedelta(hours=24)
            retry_config, _ = SiteConfig.objects.get_or_create(
                key=f"NEXT_ALLOWED_RUN_TIME_{site.name}", defaults={'value': {'time': next_retry.isoformat()}}
            )
            retry_config.value = {'time': next_retry.isoformat()}
            retry_config.save()
            if target_task:
                target_task.status = 'Pending'; target_task.save()
            return f"💤 Quota exhausted for {site.name}. Hibernating until {next_retry}"
        if target_task:
            target_task.status = 'Pending'; target_task.save()
        return f"❌ Fail for {site.name}: {err_msg}"

    for t in data.get('backlog_tasks', []):
        get_or_create_backlog_task_safe(
            site,
            task_name=t['task_name'],
            defaults={
                'task_type': t.get('task_type', 'code'),
                'target_file': t['target_file'],
                'priority': t.get('priority', 'Medium'), 'status': 'Pending',
                'description': t.get('description', ''), 'estimated_hours': t.get('estimated_hours', 1.0),
                'complexity': t.get('complexity', 1),
                'business_impact_score': t.get('business_impact_score', 5),
                'trigger_condition': 'AI-Discovery'
            }
        )
        results.append(f"📋 Added: {t['task_name'][:30]}")

    for action in data.get('self_healing_actions', []):
        pattern = action.get('error_pattern', '').strip()
        if pattern:
            SelfHealingLog.objects.filter(error_message__icontains=pattern, resolved=False).update(
                resolved=bool(action.get('resolved', False)),
                solution_sql=action.get('action_taken', '')[:5000]
            )
            results.append(f"🛡️ Self-healing: {pattern[:30]}")

    updates = data.get('updates', {})
    code_changed = False
    models_changed = False
    for key, new_content in updates.items():
        if new_content and len(new_content.strip()) > 10:
            path = file_paths.get(key)
            if not path:
                continue

            critique = _self_critique(
                site, key, new_content,
                target_task.task_name if target_task else "Audit"
            )
            confidence = critique.get('confidence_score', 65)
            if critique.get('concerns'):
                results.append(f"🔍 Critique notes for {key}: {', '.join(critique['concerns'][:2])}")

            apply_result = apply_code_change(
                site=site, file_key=key, new_content=new_content, path=path,
                reason=f"Autonomous Build for {site.name}: {target_task.task_name if target_task else 'System Evolution'}",
                confidence_score=confidence, backlog_task=target_task
            )
            results.append(apply_result['message'])
            if apply_result['applied']:
                code_changed = True
                if key == 'models':
                    models_changed = True

    if models_changed:
        check_passed, check_output = _run_django_check()
        if check_passed:
            results.append("✅ Django system check passed")
        else:
            results.append(f"⚠️ Django check found issues: {check_output[:150]}")
            logger.warning(f"⚠️ Post-model-change check issues for {site.name}: {check_output}")

    if data.get('database_migration_needed') and updates.get('models'):
        try:
            call_command('makemigrations', 'marketplace', interactive=False)
            call_command('migrate', interactive=False)
            results.append("✅ Migrations applied")
        except Exception as e:
            results.append(f"⚠️ Migration issue: {str(e)[:100]}")

    if code_changed:
        clear_url_caches()

    if data.get('task_name'):
        memory_engine.remember(
            memory_type='insight',
            content=f"Site {site.name}: {data.get('task_name')} - {data.get('description', '')[:200]}",
            metadata={'success': True, 'task_type': data.get('task_type', 'code')}
        )

    if override_obj:
        override_obj.is_processed = True; override_obj.save()
    if target_task:
        target_task.status = 'Completed'; target_task.save()

    return f"🎉 [{site.name}] {target_task.task_name if target_task else 'Audit'} | {' | '.join(results[:6])}"


def run_single_site_analysis(site: SiteRegistry):
    cycle_start = time.time()
    site_results = []

    stage_engine = GrowthStageEngine(site)
    new_stage_tasks = stage_engine.evaluate_and_advance()
    if new_stage_tasks:
        site_results.append(f"📈 Build Phase → {len(new_stage_tasks)} new tasks queued")

    project_code, file_paths = get_site_project_state(site)
    if not project_code:
        return f"⚠️ No code found for {site.name}"

    security_scanner = SecurityScanner(site)
    total_vulns = 0
    for file_name, code in project_code.items():
        if code and len(code) > 100 and not str(code).startswith("❌"):
            total_vulns += len(security_scanner.scan_code(code, file_path=file_name))
    if total_vulns:
        site_results.append(f"🔒 {total_vulns} security notes")

    predictive = PredictiveEngine(site)
    traffic_pred = predictive.predict_traffic()
    site_results.append(f"📊 Traffic projection: {traffic_pred.predicted_value:.0f} (confidence {traffic_pred.confidence_score:.0f}%)")

    memory_engine = RAGMemoryEngine(site)
    strategy_engine = GrowthStrategyEngine(site)
    strategy = strategy_engine.get_strategy()

    tasks_done = 0
    while tasks_done < MAX_TASKS_PER_CYCLE and (time.time() - cycle_start) < CYCLE_TIME_BUDGET_SECONDS:
        override_obj = AdminOverrideInstruction.objects.filter(site=site, is_processed=False).order_by('created_at').first()

        target_task = None
        if override_obj and override_obj.backlog_task:
            target_task = override_obj.backlog_task
            target_task.status = 'Running'; target_task.save()
        elif not override_obj:
            target_task = _select_next_backlog_task(site)
            if target_task:
                target_task.status = 'Running'; target_task.save()

        if not target_task and not override_obj:
            if not SelfHealingLog.objects.filter(resolved=False).exists():
                break

        outcome = _execute_single_task_cycle(
            site, target_task, override_obj, project_code, file_paths, memory_engine, strategy
        )
        site_results.append(outcome)
        tasks_done += 1

        project_code, file_paths = get_site_project_state(site)

        if not target_task and not override_obj:
            break

    if tasks_done == 0:
        site_results.append("🧠 No pending work this cycle")

    site.total_products = Product.objects.filter(site=site, seller__isnull=False).count()
    site.save()

    return f"✅ [{site.name}] {tasks_done} task(s) in {time.time()-cycle_start:.1f}s | {' | '.join(site_results[:8])}"


# ============================================================
# 15. ዋናው የዕድገት ሞተር (run_daily_market_analysis)
# ============================================================

def run_daily_market_analysis():
    now = timezone.now()
    results = []

    retry_config, _ = SiteConfig.objects.get_or_create(
        key="NEXT_ALLOWED_RUN_TIME", defaults={'value': {'time': '2000-01-01T00:00:00'}}
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
        new_sites = discover_new_sites()
        for site in new_sites:
            results.append(f"🆕 Discovered: {site.name}")
            if analyze_site_niche(site):
                results.append(f"🧠 Analyzed niche: {site.niche}")
            GrowthStrategyEngine(site).execute_actions()

        active_sites = SiteRegistry.objects.filter(is_active=True)

        if not active_sites.exists():
            default_site, _ = SiteRegistry.objects.get_or_create(
                name="primary",
                defaults={'display_name': "Primary Site", 'niche': "general", 'target_market': "Global",
                         'repo_path': str(settings.BASE_DIR), 'is_active': True, 'build_phase': 0}
            )
            active_sites = [default_site]
            results.append(f"🏗️ Created default site: {default_site.name}")

        for site in active_sites:
            try:
                growth_result = run_single_site_analysis(site)
                results.append(growth_result)
                site.total_sellers = User.objects.filter(product__site=site).distinct().count()
                site.update_growth_level()
                site.save()
            except Exception as e:
                error_msg = f"[{site.name}] ❌ Error: {str(e)}"
                results.append(error_msg)
                logger.error(error_msg)
                try:
                    # ✅ get_or_create_backlog_task_safe/create is used
                    AgentErrorLog.objects.create(
                        task_name=f"Site_{site.name}_Analysis", error_type='runtime',
                        error_message=str(e)[:500], code_attempted="Full site analysis", site=site
                    )
                except Exception:
                    pass

        summary = " | ".join(results[:10])
        return f"🎉 Business Evolved! {summary}"

    except Exception as e:
        logger.error(f"❌ Business Engine Crash: {e}")
        return f"❌ Error: {str(e)}"
    finally:
        lock.value = {'status': 'idle'}
        lock.save()


# ============================================================
# 16. የራስ-መነሻ ስርዓት (Autonomous Loop Wrapper)
# ============================================================

class AutonomousGrowthEngine:
    """24/7 ራሱን የሚያስተዳድር የዕድገት ሞተር"""
    
    def __init__(self):
        self.is_running = False
        self.last_cycle = None
        self.cycle_count = 0
        self.error_count = 0
        self.max_errors = 10
        self.max_cycles_per_run = 5
        self.cache = AICache(ttl=1800)
    
    def run_cycle(self, max_cycles=1):
        if self.is_running:
            logger.info("⚠️ Already running a cycle. Skipping...")
            return "Already running"
        
        self.is_running = True
        total_results = []
        
        try:
            for cycle_num in range(min(max_cycles, self.max_cycles_per_run)):
                self.cycle_count += 1
                start_time = timezone.now()
                results = []
                
                logger.info(f"🚀 Starting cycle #{self.cycle_count} at {start_time}")
                
                sites = []
                try:
                    sites = list(SiteRegistry.objects.filter(is_active=True))
                except Exception as e:
                    logger.error(f"❌ Failed to get sites: {e}")
                
                if not sites:
                    primary = self._create_default_site()
                    if primary:
                        sites = [primary]
                        results.append(f"🏗️ Created default site: {primary.name}")
                    else:
                        results.append("⚠️ Could not create default site")
                
                if len(sites) > 1:
                    site_results = self._process_sites_parallel(sites)
                    results.extend(site_results)
                else:
                    for site in sites:
                        try:
                            if site and hasattr(site, 'name'):
                                site_result = self._process_site(site)
                                results.append(f"[{site.name}] {site_result}")
                        except Exception as e:
                            error_msg = f"[{site.name if site else 'Unknown'}] ❌ Error: {str(e)[:100]}"
                            results.append(error_msg)
                            logger.error(error_msg)
                            self.error_count += 1
                
                maintenance_result = self._global_maintenance()
                results.append(f"[Global] {maintenance_result}")
                
                if self.error_count > 3:
                    heal_result = self._self_heal()
                    results.append(f"[Healing] {heal_result}")
                    self.error_count = 0
                
                self.last_cycle = timezone.now()
                
                try:
                    SiteConfig.objects.update_or_create(
                        key='EVOLUTION_LOCK',
                        defaults={'value': {
                            'status': 'idle',
                            'last_run': self.last_cycle.isoformat(),
                            'cycle_count': self.cycle_count,
                            'results': results[:5]
                        }}
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not update EVOLUTION_LOCK: {e}")
                
                try:
                    SiteConfig.objects.update_or_create(
                        key='AGENT_HEARTBEAT',
                        defaults={'value': {
                            'timestamp': timezone.now().isoformat(),
                            'status': 'alive',
                            'cycle': self.engine.cycle_count
                        }}
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not update AGENT_HEARTBEAT: {e}")
                
                cycle_summary = " | ".join(results[:5]) if results else "No results"
                total_results.append(f"Cycle #{self.cycle_count}: {cycle_summary}")
                
                logger.info(f"✅ Cycle #{self.cycle_count} completed in {(timezone.now() - start_time).seconds}s")
                
                if self.error_count > 5:
                    self._emergency_self_heal()
                    break
            
        except Exception as e:
            logger.error(f"❌ Run failed: {e}")
            total_results.append(f"❌ Run error: {str(e)[:100]}")
            self.error_count += 1
        
        finally:
            self.is_running = False
            connections.close_all()
        
        return " | ".join(total_results[:10]) if total_results else "No results"
    
    def _process_sites_parallel(self, sites):
        results = []
        max_workers = min(len(sites), 5)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_site = {
                executor.submit(self._process_site_thread_wrapper, site): site 
                for site in sites if site and hasattr(site, 'name')
            }
            
            for future in as_completed(future_to_site):
                site = future_to_site[future]
                try:
                    result = future.result(timeout=120)
                    results.append(f"[{site.name}] {result}")
                except Exception as e:
                    results.append(f"[{site.name if site else 'Unknown'}] ❌ Timeout/Error: {str(e)[:50]}")
                    logger.error(f"❌ Parallel processing error for {site.name if site else 'Unknown'}: {e}")
        
        return results

    def _process_site_thread_wrapper(self, site):
        try:
            return self._process_site(site)
        finally:
            connections.close_all()
    
    def _process_site(self, site):
        site_name = site.name if hasattr(site, 'name') else 'unknown'
        results = []
        
        try:
            analysis = self._analyze_site_deep(site)
            results.append(f"📊 Analysis: {analysis.get('summary', 'OK')}")
            
            new_tasks = self._generate_dynamic_tasks(site, analysis)
            if new_tasks:
                results.append(f"📋 Created {len(new_tasks)} tasks")
            
            executed = self._execute_pending_tasks_smart(site)
            if executed:
                results.append(f"⚡ Executed {len(executed)} tasks")
            
            self._update_phase(site, analysis)
            
            try:
                errors = AgentErrorLog.objects.filter(site=site, resolved=False)
                if errors.exists():
                    results.append(f"⚠️ {errors.count()} errors found")
                    fixed = self._heal_errors_smart(site, errors[:5])
                    if fixed:
                        results.append(f"🛠️ Fixed {len(fixed)} errors")
            except Exception as e:
                logger.warning(f"⚠️ Error checking errors: {e}")
            
            try:
                if hasattr(site, 'update_real_counts'):
                    site.update_real_counts()
            except Exception as e:
                logger.warning(f"⚠️ Could not update counts: {e}")
            
        except Exception as e:
            logger.error(f"❌ Site processing error for {site_name}: {e}")
            results.append(f"❌ Error: {str(e)[:50]}")
        
        return " | ".join(results[:5]) if results else "No results"
    
    def _analyze_site_deep(self, site):
        try:
            project_code, _ = get_site_project_state(site)
            code_status = {
                'has_models': 'models' in project_code and project_code['models'] and not project_code['models'].startswith('❌'),
                'has_views': 'views' in project_code and project_code['views'] and not project_code['views'].startswith('❌'),
                'has_urls': 'urls' in project_code and project_code['urls'] and not project_code['urls'].startswith('❌'),
                'has_admin': 'admin' in project_code and project_code['admin'] and not project_code['admin'].startswith('❌'),
                'has_templates': 'home_html' in project_code and project_code['home_html'] and not project_code['home_html'].startswith('❌'),
            }
        except Exception:
            code_status = {'has_models': False, 'has_views': False, 'has_urls': False, 'has_admin': False, 'has_templates': False}
        
        try:
            product_count = Product.objects.filter(site=site, is_active=True).count()
            customer_count = User.objects.filter(product__site=site).distinct().count()
            category_count = Category.objects.filter(product__site=site).distinct().count()
        except Exception:
            product_count = 0
            customer_count = 0
            category_count = 0
        
        try:
            task_count = AIProjectBacklog.objects.filter(site=site).count()
            pending_count = AIProjectBacklog.objects.filter(site=site, status='Pending').count()
            completed_count = AIProjectBacklog.objects.filter(site=site, status='Completed').count()
        except Exception:
            task_count = 0
            pending_count = 0
            completed_count = 0
        
        try:
            error_count = AgentErrorLog.objects.filter(site=site, resolved=False).count()
            error_types = AgentErrorLog.objects.filter(site=site, resolved=False).values('error_type').annotate(count=Count('id'))
        except Exception:
            error_count = 0
            error_types = []
        
        try:
            healing_count = SelfHealingLog.objects.filter(resolved=True).count()
        except Exception:
            healing_count = 0
        
        build_phase = getattr(site, 'build_phase', 0)
        missing_features = self._detect_missing_features(site, code_status, product_count)
        
        summary = f"Phase:{build_phase} | Products:{product_count} | Customers:{customer_count} | Tasks:{task_count} | Errors:{error_count}"
        
        return {
            'site': site,
            'code_status': code_status,
            'product_count': product_count,
            'customer_count': customer_count,
            'category_count': category_count,
            'task_count': task_count,
            'pending_count': pending_count,
            'completed_count': completed_count,
            'error_count': error_count,
            'error_types': error_types,
            'healing_count': healing_count,
            'missing_features': missing_features,
            'summary': summary,
            'build_phase': build_phase,
        }
    
    def _detect_missing_features(self, site, code_status, product_count):
        missing = []
        
        if not code_status.get('has_models', False):
            missing.append('Models')
        if not code_status.get('has_views', False):
            missing.append('Views')
        if not code_status.get('has_urls', False):
            missing.append('URLs')
        if not code_status.get('has_admin', False):
            missing.append('Admin')
        if not code_status.get('has_templates', False):
            missing.append('Templates')
        
        if product_count < 5:
            missing.append('Products')
        
        build_phase = getattr(site, 'build_phase', 0)
        if build_phase == 0:
            missing.append('Seed Data')
        elif build_phase == 1:
            if product_count < 10:
                missing.append('More Products')
        elif build_phase == 2:
            missing.append('Engagement Features')
        elif build_phase == 3:
            missing.append('Monetization')
        elif build_phase == 4:
            missing.append('SEO & Growth')
        
        return missing
    
    # ============================================================
    # 3.4 ተለዋዋጭ ስራ ማመንጨት (Dynamic Task Generation)
    # ============================================================
    
    def _get_or_create_task_safe(self, site, task_name, defaults):
        return get_or_create_backlog_task_safe(site, task_name, defaults)

    def _generate_dynamic_tasks(self, site, analysis):
        created = []
        
        try:
            existing = AIProjectBacklog.objects.filter(
                site=site,
                status__in=['Pending', 'Running']
            ).values_list('task_name', flat=True)
            
            priority_map = {
                'Models': 'Critical',
                'Views': 'Critical',
                'Admin': 'Critical',
                'URLs': 'High',
                'Templates': 'High',
                'Products': 'High',
                'Seed Data': 'Critical',
                'More Products': 'High',
                'Engagement Features': 'High',
                'Monetization': 'High',
                'SEO & Growth': 'Medium',
            }
            
            for feature in analysis.get('missing_features', []):
                task_name = f"Build: {feature}"
                
                if task_name not in existing:
                    priority = priority_map.get(feature, 'Medium')
                    impact = self._calculate_impact(feature)
                    
                    task, is_new = self._get_or_create_task_safe(
                        site=site,
                        task_name=task_name,
                        defaults={
                            'task_type': 'code',
                            'target_file': feature.lower().replace(' ', '_'),
                            'priority': priority,
                            'status': 'Pending',
                            'description': f"Implement {feature} for {site.name}",
                            'business_impact_score': impact,
                            'trigger_condition': f"Dynamic: Missing {feature}"
                        }
                    )
                    if is_new:
                        created.append(task)
                        logger.info(f"📋 Dynamic task: {task_name} for {site.name}")
                    else:
                        logger.info(f"⏭️ Task already exists (or duplicates cleaned): {task_name}")
            
            if analysis.get('error_count', 0) > 0:
                error_count = analysis['error_count']
                error_types = analysis.get('error_types', [])
                error_desc = ", ".join([f"{e['error_type']}: {e['count']}" for e in error_types[:3]])
                
                error_task, is_new = self._get_or_create_task_safe(
                    site=site,
                    task_name=f"Fix {error_count} errors",
                    defaults={
                        'task_type': 'code',
                        'target_file': 'error_fix',
                        'priority': 'Critical',
                        'status': 'Pending',
                        'description': f"Fix {error_count} unresolved errors ({error_desc})",
                        'business_impact_score': 10,
                        'trigger_condition': f"Dynamic: {error_count} errors"
                    }
                )
                if is_new:
                    created.append(error_task)
                    logger.info(f"📋 Error fix task: {error_task.task_name}")
            
            if not created and not existing:
                learn_task, is_new = self._get_or_create_task_safe(
                    site=site,
                    task_name='Self-Learning: Analyze & Plan',
                    defaults={
                        'task_type': 'growth',
                        'target_file': 'self_learning',
                        'priority': 'Medium',
                        'status': 'Pending',
                        'description': f"Analyze {site.name} and plan next steps",
                        'business_impact_score': 6,
                        'trigger_condition': "Dynamic: Self-Learning"
                    }
                )
                if is_new:
                    created.append(learn_task)
                    logger.info(f"📋 Self-learning task: {learn_task.task_name}")
                
        except Exception as e:
            logger.error(f"❌ Error generating tasks: {e}")
        
        return created
    
    def _calculate_priority(self, feature, phase):
        critical_features = ['Seed Data', 'Products', 'Models', 'Views', 'Admin']
        high_features = ['Engagement', 'Monetization', 'Payment']
        
        if any(cf in feature for cf in critical_features):
            return 'Critical'
        elif any(hf in feature for hf in high_features):
            return 'High'
        elif phase < 3:
            return 'High'
        else:
            return 'Medium'
    
    def _calculate_impact(self, feature):
        if 'error' in feature.lower():
            return 10
        elif 'Seed' in feature or 'Data' in feature:
            return 10
        elif 'Payment' in feature or 'Monetization' in feature:
            return 10
        elif 'Engagement' in feature:
            return 9
        elif 'SEO' in feature or 'Growth' in feature:
            return 8
        else:
            return 7
    
    # ============================================================
    # 3.5 የስራ አፈጻጸም (Task Execution)
    # ============================================================
    
    def _execute_pending_tasks_smart(self, site):
        executed = []
        
        try:
            priority_order = Case(
                When(priority='Critical', then=Value(1)),
                When(priority='High', then=Value(2)),
                When(priority='Medium', then=Value(3)),
                When(priority='Low', then=Value(4)),
                default=Value(5),
                output_field=IntegerField()
            )
            
            tasks = AIProjectBacklog.objects.filter(
                site=site,
                status='Pending'
            ).annotate(
                priority_num=priority_order
            ).order_by('priority_num', '-business_impact_score', 'created_at')[:5]
            
            for task in tasks:
                try:
                    task.status = 'Running'
                    task.save()
                    
                    result = self._execute_task_smart(task, site)
                    
                    if result and 'error' not in result.lower():
                        task.status = 'Completed'
                        task.save()
                        executed.append(task)
                        logger.info(f"✅ Task completed: {task.task_name}")
                    else:
                        task.status = 'Pending'
                        task.save()
                        logger.warning(f"⚠️ Task failed: {task.task_name} - {result}")
                    
                except Exception as e:
                    task.status = 'Pending'
                    task.save()
                    logger.error(f"❌ Task error: {task.task_name} - {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error executing tasks: {e}")
        
        return executed
    
    def _execute_task_smart(self, task, site):
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                result = self._execute_task_internal(task, site)
                
                if result and 'error' not in result.lower():
                    return result
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"🔄 Retrying {task.task_name} in {wait_time}s (attempt {attempt+2}/{max_retries})")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return "error: All retries failed"
    
    def _execute_task_internal(self, task, site):
        try:
            project_code, _ = get_site_project_state(site)
            
            memory_context = ""
            try:
                similar = VectorMemory.objects.filter(
                    site=site,
                    memory_type='solution'
                ).order_by('-success_rate')[:3]
                for mem in similar:
                    memory_context += f"\nPrevious solution: {mem.content[:200]}\n"
            except Exception as e:
                logger.warning(f"⚠️ RAG memory error: {e}")
            
            target_file = task.target_file or 'views'
            
            optimized_code = get_targeted_code_context(project_code, target_file_key=target_file)
            
            prompt = f"""
            You are the EthAfri AI Agent for site: {site.name if hasattr(site, 'name') else 'unknown'}
            
            Task: {task.task_name}
            Description: {task.description}
            Priority: {task.priority}
            Impact: {task.business_impact_score}/10
            
            Memory Context (past solutions):
            {memory_context}
            
            Codebase Summary (Optimized & Targeted):
            {json.dumps(optimized_code, indent=2)}
            
            Generate code or solution for this task.
            Return ONLY JSON with:
            - 'code': the code to apply
            - 'explanation': brief explanation
            - 'confidence': number 0-100
            - 'target_file': which file to modify
            """
            
            response = ask_ethafri_ceo(prompt, pool_type="coding")
            
            if response and isinstance(response, dict) and 'code' in response:
                code_content = response.get('code', '')
                explanation = response.get('explanation', 'No explanation')
                confidence = response.get('confidence', 80)
                target_file_confirmed = response.get('target_file', target_file)
                
                if target_file_confirmed in ['models', 'views', 'urls', 'forms', 'admin'] or target_file_confirmed.endswith('.py'):
                    try:
                        compile(code_content, '<string>', 'exec')
                    except SyntaxError as compile_err:
                        logger.error(f"⛔ Rejecting generated code for {target_file_confirmed} due to syntax error: {compile_err}")
                        
                        try:
                            # የዳታቤዝ ስህተቶችን መመዝገብ
                            with connection.cursor() as cursor:
                                AgentErrorLog.objects.create(
                                    site=site,
                                    task_name=task.task_name,
                                    error_type='syntax',
                                    error_message=f"SyntaxError in AI generated code: {compile_err}",
                                    code_attempted=code_content,
                                    resolved=False
                                )
                        except Exception:
                            pass
                        finally:
                            connection.close()
                        return f"error: AI code failed local syntax compilation validation: {compile_err}"
                
                path = None
                if site.repo_path:
                    repo_path = site.repo_path
                    if repo_path.startswith('http') or "github.com" in repo_path:
                        repo_path = str(settings.BASE_DIR)
                    path = os.path.join(repo_path, 'marketplace', f'{target_file_confirmed}.py')
                
                if path:
                    result = apply_code_change(
                        site=site,
                        file_key=target_file_confirmed,
                        new_content=code_content,
                        path=path,
                        reason=f"Task: {task.task_name} - {explanation[:100]}",
                        confidence_score=confidence,
                        backlog_task=task,
                        push_to_github=True
                    )
                    
                    if result.get('applied', False):
                        try:
                            VectorMemory.objects.create(
                                site=site,
                                memory_type='solution',
                                content=f"Task: {task.task_name}\nSolution: {explanation[:300]}",
                                success_rate=confidence,
                                usage_count=0,
                                related_task=task
                            )
                        except Exception as e:
                            logger.warning(f"⚠️ Could not save to RAG: {e}")
                    
                    return result['message']
                
                return "success"
            
            return "No valid response from AI"
            
        except Exception as e:
            logger.error(f"❌ Task execution error: {e}")
            return f"error: {str(e)[:50]}"
    
    def _update_phase(self, site, analysis):
        try:
            current = getattr(site, 'build_phase', 0)
            
            if current == 0:
                if analysis.get('product_count', 0) > 0 or analysis.get('task_count', 0) > 0:
                    site.build_phase = 1
                    site.phase_transition_date = timezone.now()
                    site.save()
                    logger.info(f"📈 {site.name} → Phase 1")
            
            elif current == 1:
                if analysis.get('product_count', 0) >= 10 and analysis.get('customer_count', 0) >= 3:
                    site.build_phase = 2
                    site.phase_transition_date = timezone.now()
                    site.save()
                    logger.info(f"📈 {site.name} → Phase 2")
            
            elif current == 2:
                if analysis.get('completed_count', 0) >= 3:
                    site.build_phase = 3
                    site.phase_transition_date = timezone.now()
                    site.save()
                    logger.info(f"📈 {site.name} → Phase 3")
            
            elif current == 3:
                if analysis.get('completed_count', 0) >= 6:
                    site.build_phase = 4
                    site.phase_transition_date = timezone.now()
                    site.save()
                    logger.info(f"📈 {site.name} → Phase 4")
            
            elif current == 4:
                if analysis.get('completed_count', 0) >= 9:
                    site.build_phase = 5
                    site.phase_transition_date = timezone.now()
                    site.save()
                    logger.info(f"📈 {site.name} → Phase 5")
                    
        except Exception as e:
            logger.warning(f"⚠️ Could not update phase: {e}")
    
    def _heal_errors_smart(self, site, errors):
        fixed = []
        
        for error in errors:
            try:
                memory_context = ""
                try:
                    similar = VectorMemory.objects.filter(
                        site=site,
                        memory_type='error',
                        content__icontains=error.error_type
                    ).order_by('-success_rate')[:3]
                    for mem in similar:
                        memory_context += f"\nSimilar error: {mem.content[:200]}\n"
                except Exception as e:
                    logger.warning(f"⚠️ RAG memory error: {e}")
                
                prompt = f"""
                Fix this error:
                Task: {error.task_name}
                Type: {error.error_type}
                Message: {error.error_message}
                Code attempted: {error.code_attempted[:300] if error.code_attempted else 'No code'}
                
                Memory Context (similar errors):
                {memory_context}
                
                Return JSON:
                {{
                    "solution": "fix description",
                    "confidence": 0-100,
                    "code_fix": "fixed code if applicable"
                }}
                """
                
                response = ask_ethafri_ceo(prompt, pool_type="healing")
                
                if response and isinstance(response, dict) and 'solution' in response:
                    error.resolved = True
                    error.correction_applied = response.get('solution', '')
                    error.save()
                    fixed.append(error)
                    
                    try:
                        VectorMemory.objects.create(
                            site=site,
                            memory_type='error',
                            content=f"Error: {error.error_type}\nSolution: {response.get('solution', '')[:200]}",
                            success_rate=response.get('confidence', 70),
                            usage_count=0
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Could not save to RAG: {e}")
                    
                    logger.info(f"✅ Healed error: {error.task_name}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to heal error: {e}")
        
        return fixed
    
    def _self_heal(self):
        try:
            stuck_count = AIProjectBacklog.objects.filter(status='Running').update(status='Pending')
            self.cache.clear()
            
            SelfHealingLog.objects.create(
                error_message=f"Self-Healing: Reset {stuck_count} stuck tasks, cache cleared",
                resolved=True
            )
            
            return f"Reset {stuck_count} stuck tasks, cache cleared"
            
        except Exception as e:
            return f"Self-heal failed: {str(e)[:50]}"
    
    def _emergency_self_heal(self):
        try:
            SiteConfig.objects.update_or_create(
                key='EVOLUTION_LOCK',
                defaults={'value': {'status': 'idle'}}
            )
            AIProjectBacklog.objects.filter(status='Running').update(status='Pending')
            self.cache.clear()
            logger.info("🚨 Emergency self-heal completed")
            return True
        except Exception:
            return False
    
    def _global_maintenance(self):
        results = []
        
        try:
            old_tasks = AIProjectBacklog.objects.filter(
                status='Pending',
                created_at__lt=timezone.now() - timedelta(days=7)
            )
            if old_tasks.exists():
                count = old_tasks.count()
                old_tasks.delete()
                results.append(f"Cleaned {count} old tasks")
            
            error_stats = AgentErrorLog.objects.filter(
                resolved=False
            ).values('error_type').annotate(count=Count('id')).order_by('-count')
            
            if error_stats.exists():
                most_common = error_stats.first()
                results.append(f"📊 Most common: {most_common['error_type']} ({most_common['count']})")
            
            try:
                memory_count = VectorMemory.objects.count()
                if memory_count > 0:
                    avg_success = VectorMemory.objects.aggregate(avg=Avg('success_rate'))['avg']
                    results.append(f"🧠 RAG: {memory_count} memories, {avg_success:.0f}% avg success")
            except Exception:
                pass
            
            healing_stats = SelfHealingLog.objects.aggregate(
                total=Count('id'),
                resolved=Count('id', filter=Q(resolved=True))
            )
            
            if healing_stats.get('total', 0) > 0:
                success_rate = (healing_stats['resolved'] / healing_stats['total']) * 100
                results.append(f"Healing: {success_rate:.0f}% success")
                
        except Exception as e:
            logger.warning(f"⚠️ Maintenance error: {e}")
        
        return " | ".join(results) if results else "All systems normal"
    
    def _create_default_site(self):
        try:
            site, created = SiteRegistry.objects.get_or_create(
                name='primary',
                defaults={
                    'display_name': 'EthAfri Primary',
                    'niche': 'general',
                    'target_market': 'Global',
                    'repo_path': str(settings.BASE_DIR),
                    'is_active': True,
                    'build_phase': 0
                }
            )
            
            if created:
                logger.info("🏗️ Created default primary site")
                self._get_or_create_task_safe(
                    site=site,
                    task_name='Initialize EthAfri',
                    defaults={
                        'task_type': 'growth',
                        'target_file': 'init',
                        'priority': 'Critical',
                        'status': 'Pending',
                        'description': 'Initial setup and configuration',
                        'business_impact_score': 10,
                        'trigger_condition': 'System bootstrap'
                    }
                )
            
            return site
            
        except Exception as e:
            logger.error(f"❌ Failed to create default site: {e}")
            return None
    
    def get_status(self):
        try:
            return {
                'is_running': self.is_running,
                'cycle_count': self.cycle_count,
                'last_cycle': self.last_cycle.isoformat() if self.last_cycle else None,
                'error_count': self.error_count,
                'cache_size': len(self.cache.cache),
                'total_sites': SiteRegistry.objects.filter(is_active=True).count(),
                'total_tasks': AIProjectBacklog.objects.count(),
                'pending_tasks': AIProjectBacklog.objects.filter(status='Pending').count(),
                'total_errors': AgentErrorLog.objects.filter(resolved=False).count(),
                'total_healings': SelfHealingLog.objects.count(),
                'total_memories': VectorMemory.objects.count(),
            }
        except Exception:
            return {
                'is_running': self.is_running,
                'cycle_count': self.cycle_count,
                'last_cycle': self.last_cycle.isoformat() if self.last_cycle else None,
                'error_count': self.error_count,
                'cache_size': 0,
                'total_sites': 0,
                'total_tasks': 0,
                'pending_tasks': 0,
                'total_errors': 0,
                'total_healings': 0,
                'total_memories': 0,
            }
    
    def get_heartbeat(self):
        try:
            heartbeat = SiteConfig.objects.filter(key='AGENT_HEARTBEAT').first()
            if heartbeat:
                return heartbeat.value
        except:
            pass
        return {'status': 'unknown', 'timestamp': None}


# ============================================================
# 4. ሙሉ በሙሉ ራሱን የሚያስተዳድር ሉፕ (Autonomous Loop)
# ============================================================

class AutonomousLoop:
    """24/7 የሚሰራ ራስ-ገዝ ሉፕ"""
    
    def __init__(self):
        self.engine = AutonomousGrowthEngine()
        self.running = True
        self.interval = 60
        self.max_runtime = 300
    
    def start(self):
        logger.info("🚀 Starting Autonomous Loop")
        
        while self.running:
            try:
                logger.info(f"💓 Heartbeat at {timezone.now()}")
                result = self.engine.run_cycle(max_cycles=2)
                logger.info(f"✅ Cycle result: {result[:200] if result else 'No result'}")
                
                try:
                    SiteConfig.objects.update_or_create(
                        key='AUTONOMOUS_LOOP_HEARTBEAT',
                        defaults={'value': {
                            'timestamp': timezone.now().isoformat(),
                            'status': 'alive',
                            'cycle': self.engine.cycle_count,
                            'result': result[:100] if result else 'No result'
                        }}
                    )
                except Exception:
                    pass
                
                if self.engine.error_count > self.engine.max_errors:
                    logger.warning(f"⚠️ Too many errors ({self.engine.error_count}). Restarting...")
                    self.engine._emergency_self_heal()
                    self.engine.error_count = 0
                
                connections.close_all()
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Stopping Autonomous Loop...")
                self.running = False
                break
                
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                connections.close_all()
                time.sleep(60)


# ============================================================
# 5. የራስ-ማስተማር ተግባር (Self-Education)
# ============================================================

def self_educate(site, analysis):
    logger.info(f"📚 Starting Self-Education for {site.name if hasattr(site, 'name') else 'unknown'}")
    
    try:
        if analysis and analysis.get('missing_features'):
            insight = f"Missing features: {', '.join(analysis['missing_features'][:3])}"
        else:
            prompt = f"""
            Analyze site: {site.name if hasattr(site, 'name') else 'unknown'}
            Niche: {site.niche if hasattr(site, 'niche') else 'general'}
            Products: {analysis.get('product_count', 0) if analysis else 0}
            Phase: {analysis.get('build_phase', 0) if analysis else 0}
            
            What should the next growth step be?
            Return JSON: {{"insight": "string", "suggestion": "string", "priority": "High|Medium|Low"}}
            """
            
            response = ask_ethafri_ceo(prompt, pool_type="analysis")
            if response and isinstance(response, dict):
                insight = response.get('insight', "Codebase looks complete. Monitoring for new opportunities.")
                suggestion = response.get('suggestion', '')
                priority = response.get('priority', 'Medium')
                
                try:
                    engine = AutonomousGrowthEngine()
                    task, is_new = engine._get_or_create_task_safe(
                        site=site,
                        task_name=suggestion or 'AI Suggested Growth Task',
                        defaults={
                            'task_type': 'growth',
                            'target_file': 'ai_suggested',
                            'priority': priority,
                            'status': 'Pending',
                            'description': insight,
                            'business_impact_score': 8,
                            'trigger_condition': 'Self-Education: AI suggestion'
                        }
                    )
                    if is_new:
                        logger.info(f"📋 Self-education task created: {task.task_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not create self-education task: {e}")
            else:
                insight = "Codebase looks complete. Monitoring for new opportunities."
        
        try:
            SelfHealingLog.objects.create(
                error_message=f"Self-Learning: {site.name if hasattr(site, 'name') else 'unknown'}",
                solution_sql=insight,
                resolved=True
            )
            logger.info(f"✅ Self-Education logged")
        except Exception as e:
            logger.warning(f"⚠️ Could not log self-education: {e}")
        
        return insight
        
    except Exception as e:
        logger.error(f"❌ Self-Education error: {e}")
        return f"Self-Education error: {str(e)[:50]}"


def analyze_market(site):
    """የገበያ ትንተና ያካሂዳል"""
    try:
        prompt = f"""
        Analyze the market for site: {site.name if hasattr(site, 'name') else 'unknown'}
        Niche: {site.niche if hasattr(site, 'niche') else 'general'}
        Target Market: {site.target_market if hasattr(site, 'target_market') else 'Global'}
        
        What features should be added next?
        What are the competitors doing?
        Return JSON with 'features', 'competitors', 'opportunities'.
        """
        response = ask_ethafri_ceo(prompt, pool_type="analysis")
        return response
    except Exception as e:
        logger.error(f"Market analysis error: {e}")
        return {}


# ============================================================
# 6. ዋና መግቢያ ተግባራት
# ============================================================

def run_autonomous_agent():
    """Lock በመቆጣጠር 24/7 ኤጀንት ይጀምራል"""
    loop = AutonomousLoop()
    loop.start()


def run_single_cycle():
    """አንድ የስራ ዑደት ብቻ ያካሂዳል"""
    engine = AutonomousGrowthEngine()
    return engine.run_cycle(max_cycles=1)


def run_multiple_cycles(count=3):
    """ብዙ ዑደቶችን ያካሂዳል"""
    engine = AutonomousGrowthEngine()
    return engine.run_cycle(max_cycles=count)


def run_daily_market_analysis():
    return run_single_cycle()


def run_single_site_analysis(site):
    engine = AutonomousGrowthEngine()
    return engine._process_site(site)


def get_agent_status():
    engine = AutonomousGrowthEngine()
    return engine.get_status()


def get_agent_heartbeat():
    engine = AutonomousGrowthEngine()
    return engine.get_heartbeat()


def clear_ai_cache():
    _ai_cache.clear()
    logger.info("🧹 AI cache cleared")
    return "AI cache cleared"


# ============================================================
# 7. የአዲስ ጣቢያ ግኝት (Site Discovery)
# ============================================================

def discover_new_sites():
    """በፋይል ሲስተም ውስጥ አዲስ የፕሮጀክት ፎልደሮችን ያገኛል"""
    discovered = []
    try:
        base_path = settings.BASE_DIR
        if not os.path.exists(base_path):
            return discovered
        
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                if os.path.exists(os.path.join(item_path, 'manage.py')):
                    site_name = item.lower().replace('_', '-').replace(' ', '-')
                    
                    existing = SiteRegistry.objects.filter(name=site_name).first()
                    if not existing:
                        try:
                            site = SiteRegistry.objects.create(
                                name=site_name,
                                display_name=item.replace('_', ' ').title(),
                                niche="general",
                                target_market="Global",
                                repo_path=item_path,
                                is_active=True,
                                build_phase=0
                            )
                            discovered.append(site)
                            logger.info(f"🆕 Discovered new site: {site_name}")
                        except Exception as e:
                            logger.error(f"Failed to create site {site_name}: {e}")
    except Exception as e:
        logger.error(f"❌ Site discovery error: {e}")
    
    return discovered


# ============================================================
# 8. የጣቢያ ኒች ትንተና (Niche Analysis)
# ============================================================

def analyze_site_niche(site):
    """የጣቢያውን ኒች በAI ይተነትናል"""
    try:
        project_code, _ = get_site_project_state(site)
        if not project_code:
            return False
        
        code_summary = {}
        for key, content in project_code.items():
            if isinstance(content, str) and len(content) > 500:
                code_summary[key] = content[:500] + "..."
            else:
                code_summary[key] = content
        
        prompt = f"""
        Analyze this website's code to determine its niche:
        Site: {site.name if hasattr(site, 'name') else 'unknown'}
        
        Codebase Summary: {json.dumps(code_summary, indent=2)[:3000]}
        
        Return JSON:
        {{
            "niche": "string",
            "primary_keywords": ["kw1", "kw2"],
            "competitor_urls": ["url1", "url2"],
            "target_audience": "description",
            "content_style": "professional|casual|storytelling|educational"
        }}
        """
        
        data = ask_ethafri_ceo(prompt, pool_type="analysis")
        if data and isinstance(data, dict) and 'niche' in data:
            site.niche = data.get('niche', 'general')
            site.primary_keywords = data.get('primary_keywords', [])
            site.competitor_urls = data.get('competitor_urls', [])
            site.target_audience = data.get('target_audience', '')
            site.content_style = data.get('content_style', 'professional')
            site.save()
            logger.info(f"🧠 Analyzed niche for {site.name}: {site.niche}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Niche analysis error: {e}")
        return False


# ============================================================
# 9. የስራ ትንተና (Task Analysis)
# ============================================================

def analyze_pending_tasks(site=None):
    """የታገዱ ስራዎችን ይተነትናል"""
    try:
        queryset = AIProjectBacklog.objects.filter(status='Pending')
        if site:
            queryset = queryset.filter(site=site)
        
        priority_order = Case(
            When(priority='Critical', then=Value(1)),
            When(priority='High', then=Value(2)),
            When(priority='Medium', then=Value(3)),
            When(priority='Low', then=Value(4)),
            default=Value(5),
            output_field=IntegerField()
        )
        
        return {
            'total': queryset.count(),
            'by_priority': queryset.values('priority').annotate(count=Count('id')),
            'by_type': queryset.values('task_type').annotate(count=Count('id')),
            'critical': queryset.filter(priority='Critical').count(),
            'high': queryset.filter(priority='High').count(),
            'total_impact': queryset.aggregate(total=Sum('business_impact_score'))['total'] or 0,
            'oldest': queryset.order_by('created_at').first(),
            'newest': queryset.order_by('-created_at').first(),
        }
    except Exception as e:
        logger.error(f"❌ Task analysis error: {e}")
        return {'total': 0, 'by_priority': [], 'by_type': [], 'critical': 0, 'high': 0, 'total_impact': 0, 'oldest': None, 'newest': None}


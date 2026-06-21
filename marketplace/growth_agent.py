# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ለውጥ፦ v3 — Data-First, Dependency-Driven Organic Growth Engine
# 📅 ቀን፦ 2026-06-21
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
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.core.management import call_command
from django.urls import clear_url_caches
from importlib import reload
from groq import Groq
from google import genai
from django.db import models
from django.db.models import Q, Count, Avg

from .models import (
    SiteConfig, Category, Product, AIProjectBacklog, AIEvolutionLog, 
    AdminOverrideInstruction, AgentErrorLog, SiteRegistry,
    CustomerAcquisitionLog, MarketingCampaign, SellerProfile, NotificationQueue,
    VectorMemory, AgentTask, ABTest, SecurityLog, PredictionLog, ExternalAPI
)

logger = logging.getLogger(__name__)


# ============================================================
# 1. ረዳት ተግባራት (Helper Functions)
# ============================================================

def extract_json(text):
    """JSON ከ AI ምላሽ ያወጣል — የተሻሻለ"""
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


# ============================================================
# 2. የኤአይ ፎልባክ ሞተር (AI Failover Engine)
# ============================================================

def ask_ai_with_failover(prompt, pool_type="coding", max_retries=2, timeout=60):
    """የተሻሻለ የኤአይ ፎልባክ ሞተር"""
    keys_to_check = ['GEMINI_API_KEY', 'GROQ_API_KEY', 'GITHUB_TOKEN', 'HUGGINGFACE_API_KEY', 
                     'HF_TOKEN', 'MISTRAL_API_KEY', 'OPENROUTER_API_KEY']
    for k in keys_to_check:
        val = os.environ.get(k)
        logger.info(f"🔑 DEBUG: Key {k} exists: {bool(val)}")

    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    mistral_key = os.environ.get('MISTRAL_API_KEY')
    openrouter_key = os.environ.get('OPENROUTER_API_KEY')
    huggingface_key = os.environ.get('HUGGINGFACE_API_KEY') or os.environ.get('HF_TOKEN')
    github_token = os.environ.get('GITHUB_TOKEN')

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
                time.sleep(1)
        return None

    def call_github():
        if not github_token: return None
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"}
        model = "azure-openai/gpt-4o-mini" if "translation" in pool_type else "meta-llama-3.1-405b-instruct"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.error(f"GitHub Error: {e}"); return None

    def call_groq():
        if not groq_key: return None
        try:
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], timeout=timeout)
            return extract_json(chat.choices[0].message.content)
        except Exception: return None

    def call_mistral():
        if not mistral_key: return None
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
        model = "codestral-latest" if pool_type == "coding" else "mistral-large-latest"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception: return None

    def call_huggingface():
        if not huggingface_key: return None
        url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct/v1/chat/completions"
        headers = {"Authorization": f"Bearer {huggingface_key}", "Content-Type": "application/json"}
        try:
            res = requests.post(url, headers=headers, json={"model": "Qwen/Qwen2.5-72B-Instruct", "messages": [{"role": "user", "content": prompt}]}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception: return None

    def call_openrouter():
        if not openrouter_key: return None
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
        model = "google/gemini-2.5-flash" if "translation" in pool_type else "deepseek/deepseek-chat"
        try:
            res = requests.post(url, headers=headers, json={"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception: return None

    provider_configs = {
        "coding": [call_mistral, call_github, call_groq, call_openrouter, call_huggingface, call_gemini],
        "translation": [call_gemini, call_github, call_huggingface, call_openrouter, call_groq],
        "translation_github": [call_github, call_gemini, call_huggingface, call_openrouter],
        "translation_huggingface": [call_huggingface, call_github, call_gemini, call_openrouter],
        "marketing": [call_openrouter, call_gemini, call_mistral, call_github, call_groq],
        "analysis": [call_gemini, call_openrouter, call_huggingface, call_groq],
        "healing": [call_mistral, call_github, call_gemini, call_openrouter, call_huggingface],
    }
    
    providers = provider_configs.get(pool_type, [call_groq, call_mistral, call_github, call_huggingface, call_openrouter])
    random.shuffle(providers)

    for provider in providers:
        for attempt in range(max_retries):
            try:
                result = provider()
                if result and "error" not in result:
                    logger.info(f"✅ Success with {provider.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt+1} for {provider.__name__} failed: {e}")
                time.sleep(1)
    
    logger.error("❌ All AI providers failed")
    return {"error": "All AI providers failed after multiple attempts."}


ask_ethafri_ceo = ask_ai_with_failover


# ============================================================
# 3. የፕሮጀክት ሁኔታ አንባቢ (Multi-Site)
# ============================================================

def get_site_project_state(site: SiteRegistry):
    """ለአንድ የተወሰነ ጣቢያ የፕሮጀክቱን ኮድ እና የፋይል መዋቅር ያነባል"""
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
    """[DEPRECATED] ለነባር ተኳሃኝነት ብቻ"""
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
# 4. አዲስ ጣቢያ ራስ-ሰር መለየት (Auto-Discovery)
# ============================================================

def discover_new_sites():
    """በፋይል ሲስተም ውስጥ አዲስ የፕሮጀክት ፎልደሮችን ያገኛል"""
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
                            name=site_name,
                            display_name=item.replace('_', ' ').title(),
                            niche="general",
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
# 5. የጣቢያ ኒች እና ገበያ ራስ-ሰር መለየት
# ============================================================

def analyze_site_niche(site: SiteRegistry):
    """የጣቢያውን ኮድ እና ይዘት አጥንቶ ኒች፣ ቁልፍ ቃላት እና ተወዳዳሪዎችን ይለያል"""
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
# 6. RAG Memory Engine (ትውስታ ሞተር)
# ============================================================

class RAGMemoryEngine:
    """Retrieval-Augmented Generation ትውስታ ሞተር"""
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
    
    def remember(self, memory_type, content, metadata=None, related_task=None):
        return VectorMemory.objects.create(
            memory_type=memory_type,
            content=content,
            metadata=metadata or {},
            site=self.site,
            related_task=related_task
        )
    
    def recall(self, query, memory_type=None, limit=5):
        return VectorMemory.find_similar(query, memory_type, self.site, limit)
    
    def learn_from_task(self, task, success=True):
        memory = VectorMemory.objects.create(
            memory_type='solution',
            content=f"Task: {task.task_name}\nResult: {task.result_data}",
            metadata={
                'agent_type': task.agent_type,
                'success': success,
                'site_id': task.site.id if task.site else None
            },
            site=self.site,
            related_task=task.backlog_task
        )
        memory.mark_used(success)
        return memory


# ============================================================
# 7. Multi-Agent Orchestrator (ባለብዙ-ኤጀንት አስተባባሪ)
# ============================================================

class AgentOrchestrator:
    """የተለያዩ ኤጀንቶችን ያስተባብራል"""
    
    AGENT_HANDLERS = {
        'code': 'handle_code_task',
        'seo': 'handle_seo_task',
        'marketing': 'handle_marketing_task',
        'data': 'handle_data_task',
        'review': 'handle_review_task',
        'security': 'handle_security_task',
    }
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        self.memory = RAGMemoryEngine(site)
    
    def assign_task(self, task_name, description, agent_type, priority=5):
        task = AgentTask.objects.create(
            agent_type=agent_type,
            task_name=task_name,
            description=description,
            priority=priority,
            site=self.site,
            status='pending'
        )
        logger.info(f"📋 Assigned {agent_type} task: {task_name}")
        return task
    
    def execute_task(self, task: AgentTask):
        task.start_task()
        
        handler = getattr(self, self.AGENT_HANDLERS.get(task.agent_type), None)
        if not handler:
            task.fail_task(f"No handler for agent type: {task.agent_type}")
            return
        
        try:
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
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\nReview and provide feedback."
        return ask_ai_with_failover(prompt, pool_type="analysis")
    
    def handle_security_task(self, task):
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\nIdentify security issues and provide fixes."
        return ask_ai_with_failover(prompt, pool_type="coding")


# ============================================================
# 8. 🆕 Trigger Engine (Data-First, Dependency-Driven)
# ============================================================

class TriggerEngine:
    """
    በመረጃ-ተነሳሽነት (data-triggered) ስራዎችን የሚፈጥር ሞተር
    """
    
    def __init__(self, site: SiteRegistry):
        self.site = site
    
    def evaluate_all_triggers(self):
        """ሁሉንም ትሪገሮች ይገመግማል እና አዲስ ስራዎችን ይፈጥራል"""
        created_tasks = []
        
        # Phase 0 → Phase 1: Real Data Seeding
        if self.site.build_phase == 0:
            task = self._check_scaffolding_complete()
            if task:
                created_tasks.append(task)
        
        # Phase 1 → Phase 2: Core Features
        if self.site.build_phase == 1:
            task = self._check_real_data_ready()
            if task:
                created_tasks.append(task)
        
        # Phase 2 → Phase 3: Engagement
        if self.site.build_phase == 2:
            task = self._check_core_features_ready()
            if task:
                created_tasks.append(task)
        
        # Phase 3 → Phase 4: Monetization
        if self.site.build_phase == 3:
            task = self._check_engagement_ready()
            if task:
                created_tasks.append(task)
        
        # Phase 4 → Phase 5: Mature
        if self.site.build_phase == 4:
            task = self._check_monetization_ready()
            if task:
                created_tasks.append(task)
        
        return created_tasks
    
    def _check_scaffolding_complete(self):
        """Scaffolding ተጠናቅቋል? → Phase 1 ይጀምር"""
        existing = AIProjectBacklog.objects.filter(
            site=self.site,
            task_name__icontains='Seed Real Data'
        ).exists()
        
        if existing:
            return None
        
        return AIProjectBacklog.objects.create(
            site=self.site,
            task_name='Seed Real Data (Products & Customers)',
            task_type='growth',
            target_file='data_seeding',
            priority='Critical',
            status='Pending',
            description='Phase 1: Import/seed real products and customers',
            business_impact_score=10,
            trigger_condition='Scaffolding complete'
        )
    
    def _check_real_data_ready(self):
        """≥10 ምርቶች እና ≥5 ደንበኞች? → Phase 2 ይጀምር"""
        if self.site.real_product_count >= 10 and self.site.real_customer_count >= 5:
            existing = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Core Features'
            ).exists()
            
            if not existing:
                return AIProjectBacklog.objects.create(
                    site=self.site,
                    task_name='Build Core Features (Detail, Edit, Delete)',
                    task_type='code',
                    target_file='product_views',
                    priority='Critical',
                    status='Pending',
                    description='Phase 2: Product detail, edit, delete, user dashboard',
                    business_impact_score=9,
                    trigger_condition=f'Real products: {self.site.real_product_count}, Real customers: {self.site.real_customer_count}'
                )
        return None
    
    def _check_core_features_ready(self):
        """Core features 80%+ ተጠናቀቀ? → Phase 3 ይጀምር"""
        completed = AIProjectBacklog.objects.filter(
            site=self.site,
            task_type='code',
            status='Completed'
        ).count()
        
        total = AIProjectBacklog.objects.filter(
            site=self.site,
            task_type='code'
        ).count()
        
        if total > 0 and (completed / total) >= 0.8:
            existing = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Engagement'
            ).exists()
            
            if not existing:
                return AIProjectBacklog.objects.create(
                    site=self.site,
                    task_name='Build Engagement Features (Search, Filters, Reviews)',
                    task_type='seo',
                    target_file='engagement',
                    priority='High',
                    status='Pending',
                    description='Phase 3: Search, filters, reviews, notifications',
                    business_impact_score=8,
                    trigger_condition=f'Core features: {completed}/{total} completed'
                )
        return None
    
    def _check_engagement_ready(self):
        """Engagement ተጠናቀቀ? → Phase 4 ይጀምር"""
        existing = AIProjectBacklog.objects.filter(
            site=self.site,
            task_name__icontains='Monetization'
        ).exists()
        
        if not existing:
            return AIProjectBacklog.objects.create(
                site=self.site,
                task_name='Build Monetization & Growth (Payment, Marketing, SEO)',
                task_type='marketing',
                target_file='monetization',
                priority='High',
                status='Pending',
                description='Phase 4: Payment integration, marketing campaigns, SEO',
                business_impact_score=10,
                trigger_condition='Engagement phase complete'
            )
        return None
    
    def _check_monetization_ready(self):
        """Monetization ተሳክቷል? → Phase 5 ይጀምር"""
        existing = AIProjectBacklog.objects.filter(
            site=self.site,
            task_name__icontains='Replicate'
        ).exists()
        
        if not existing:
            return AIProjectBacklog.objects.create(
                site=self.site,
                task_name='Mature & Replicate (3-site test)',
                task_type='growth',
                target_file='replication',
                priority='Medium',
                status='Pending',
                description='Phase 5: Mature site, replicate to other niches',
                business_impact_score=7,
                trigger_condition='Monetization success confirmed'
            )
        return None
    
    def update_phase(self):
        """ወቅታዊ የbuild_phase ሁኔታን ያሻሽላል"""
        if self.site.build_phase == 0:
            self.site.build_phase = 1
            self.site.phase_transition_date = timezone.now()
            self.site.save()
            logger.info(f"📈 {self.site.name} → Phase 1 (Real Data)")
        
        elif self.site.build_phase == 1:
            if self.site.real_product_count >= 10 and self.site.real_customer_count >= 5:
                self.site.build_phase = 2
                self.site.phase_transition_date = timezone.now()
                self.site.save()
                logger.info(f"📈 {self.site.name} → Phase 2 (Core Features)")
        
        elif self.site.build_phase == 2:
            completed = AIProjectBacklog.objects.filter(
                site=self.site, task_type='code', status='Completed'
            ).count()
            total = AIProjectBacklog.objects.filter(
                site=self.site, task_type='code'
            ).count()
            if total > 0 and (completed / total) >= 0.8:
                self.site.build_phase = 3
                self.site.phase_transition_date = timezone.now()
                self.site.save()
                logger.info(f"📈 {self.site.name} → Phase 3 (Engagement)")
        
        elif self.site.build_phase == 3:
            engagement_complete = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Engagement',
                status='Completed'
            ).exists()
            if engagement_complete:
                self.site.build_phase = 4
                self.site.phase_transition_date = timezone.now()
                self.site.save()
                logger.info(f"📈 {self.site.name} → Phase 4 (Monetization)")
        
        elif self.site.build_phase == 4:
            monetization_complete = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Monetization',
                status='Completed'
            ).exists()
            if monetization_complete:
                self.site.build_phase = 5
                self.site.phase_transition_date = timezone.now()
                self.site.save()
                logger.info(f"📈 {self.site.name} → Phase 5 (Mature)")


# ============================================================
# 9. የእድገት ስትራቴጂ ሞተር
# ============================================================

class GrowthStrategyEngine:
    """በመልቲ-ሌቭል የእድገት ስትራቴጂ የሚያስተዳድር ሞተር"""
    
    def __init__(self, site: SiteRegistry):
        self.site = site
    
    def get_strategy(self):
        strategies = {
            1: {'name': 'Local Growth', 'focus': 'አካባቢያዊ ሻጮች እና ገዢዎች', 
                'actions': ['የአካባቢውን ንግዶች መዘርዘር', 'የአካባቢ ጋዜጣዎች ማስታወቂያ', 'የአካባቢ ፌስቡክ ግሩፖች መጠቀም'],
                'target_audience': 'Local businesses and buyers'},
            2: {'name': 'City Growth', 'focus': 'የከተማ ሻጮች እና ገዢዎች',
                'actions': ['የከተማ ንግዶችን መዘርዘር', 'በትራንስፖርት ማስታወቂያ', 'የከተማ ተጽዕኖ ፈጣሪዎች'],
                'target_audience': 'City-wide businesses'},
            3: {'name': 'National Growth', 'focus': 'ሀገር አቀፍ ሻጮች እና ገዢዎች',
                'actions': ['የሀገር አቀፍ ማስታወቂያ', 'በኢንፍሉዌንሰሮች ግብይት', 'የብሎግ ጽሁፎች SEO'],
                'target_audience': 'National businesses'},
            4: {'name': 'Continental Growth', 'focus': 'የአህጉር አቀፍ ሻጮች እና ገዢዎች',
                'actions': ['የአህጉር አቀፍ ማስታወቂያ', 'በዓለም አቀፍ መድረኮች ግብይት', 'የቋንቋ ትርጉም እና የአካባቢ ማመቻቸት'],
                'target_audience': 'Continental businesses'},
            5: {'name': 'Global Growth', 'focus': 'ዓለም አቀፍ ሻጮች እና ገዢዎች',
                'actions': ['ዓለም አቀፍ ማስታወቂያ', 'በአለም አቀፍ ጉባኤዎች ተሳትፎ', 'ባለብዙ ቋንቋ ድጋፍ'],
                'target_audience': 'International businesses'}
        }
        level = self.site.growth_level or 1
        return strategies.get(level, strategies[1])
    
    def execute_actions(self):
        strategy = self.get_strategy()
        logger.info(f"📈 Executing {strategy['name']} strategy for {self.site.name}")
        
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
                    'complexity': 3,
                    'business_impact_score': 6
                }
            )
        return strategy


# ============================================================
# 10. የአንድ ጣቢያ ትንተና (Single Site Analysis — v3)
# ============================================================

def run_single_site_analysis(site: SiteRegistry):
    """
    ለአንድ የተወሰነ ጣቢያ የዕድገት ትንተና ያካሂዳል
    v3: Data-First, Dependency-Driven
    """
    now = timezone.now()
    site_name = site.name
    results = []
    
    logger.info(f"🚀 Starting v3 enhanced analysis for site: {site_name}")
    
    # 1. የጣቢያውን ኮድ ያንብብ
    project_code, file_paths = get_site_project_state(site)
    
    if not project_code:
        logger.warning(f"⚠️ No code found for site: {site_name}")
        return f"⚠️ No code found for {site_name}"
    
    # 2. 🆕 Trigger Engine — መረጃ-ተነሳሽ ስራዎችን ይፈጥራል
    trigger = TriggerEngine(site)
    new_tasks = trigger.evaluate_all_triggers()
    for task in new_tasks:
        results.append(f"📋 Triggered: {task.task_name}")
    
    # 3. 🆕 Update build_phase
    trigger.update_phase()
    
    # 4. የባክሎግ ስራዎችን ያግኝ (dependency-aware)
    pending_tasks = AIProjectBacklog.objects.filter(
        site=site, status='Pending'
    ).annotate(
        has_unfinished_dependency=models.Exists(
            AIProjectBacklog.objects.filter(
                pk=models.OuterRef('dependency_id'), 
                status__in=['Pending', 'Running']
            )
        )
    ).filter(has_unfinished_dependency=False).order_by('-business_impact_score', '-priority', 'created_at')
    
    # 5. ከፍተኛ ተጽዕኖ ያላቸውን ስራዎች ምረጥ (max 3 per cycle)
    target_tasks = list(pending_tasks[:3])
    
    if not target_tasks:
        logger.info(f"🧠 No pending tasks for {site_name}")
        return f"🧠 No tasks for {site_name}"
    
    # 6. እያንዳንዱን ስራ አስኬድ
    for target_task in target_tasks:
        target_task.status = 'Running'
        target_task.save()
        
        try:
            # 7. ፕሮምፕት ያዘጋጅ
            prompt = f"""
            You are 'EthAfri Super AI Architect' for site: {site_name}.
            
            Site Information:
            - Niche: {site.niche}
            - Target Market: {site.target_market}
            - Keywords: {site.primary_keywords}
            - Competitors: {site.competitor_urls}
            - Build Phase: {site.build_phase}
            - Monthly Visitors: {site.monthly_visitors}
            
            Task: {target_task.task_name}
            Description: {target_task.description}
            Business Impact Score: {target_task.business_impact_score}
            Trigger Condition: {target_task.trigger_condition}
            
            Codebase State: {json.dumps(project_code, indent=2)[:4000]}
            
            Engineering Rules:
            - Return ONLY raw JSON.
            - Validate Python syntax.
            - Use Django best practices.
            - Focus on this task only.
            """
            
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
                    target_task.status = 'Pending'
                    target_task.save()
                    results.append(f"💤 Quota exhausted for {site_name}")
                    continue
                
                target_task.status = 'Pending'
                target_task.save()
                results.append(f"❌ Fail: {err_msg[:100]}")
                continue
            
            # 8. አዲስ ስራዎችን መዝግብ
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
                        'complexity': t.get('complexity', 1),
                        'business_impact_score': t.get('business_impact_score', 5),
                        'trigger_condition': f"Generated from task: {target_task.task_name}"
                    }
                )
                results.append(f"📋 Added: {t['task_name']}")
            
            # 9. የኮድ ማሻሻያ
            updates = data.get('updates', {})
            code_changed = False
            
            for key, new_content in updates.items():
                if new_content and len(new_content.strip()) > 10:
                    if key in ['models', 'views', 'urls', 'forms']:
                        try:
                            compile(new_content, f"test_{key}.py", 'exec')
                        except SyntaxError as e:
                            logger.error(f"❌ Syntax Error: {e}")
                            AgentErrorLog.objects.create(
                                task_name=target_task.task_name,
                                error_type='syntax',
                                error_message=str(e),
                                code_attempted=new_content,
                                site=site
                            )
                            results.append(f"⚠️ Syntax error in {key}")
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
                                reason_for_change=f"Autonomous Build: {target_task.task_name}",
                                old_code_backup=old_code,
                                new_code_patch=new_content,
                                site=site
                            )
                            code_changed = True
                            results.append(f"✅ Updated {key}")
                        except Exception as e:
                            results.append(f"❌ Error updating {key}: {str(e)[:50]}")
            
            target_task.status = 'Completed'
            target_task.save()
            results.append(f"✅ Completed: {target_task.task_name}")
            
            # 10. የጣቢያ መረጃ አዘምን
            site.real_product_count = Product.objects.filter(site=site, is_active=True).count()
            site.real_customer_count = User.objects.filter(product__site=site).distinct().count()
            site.save()
            
        except Exception as e:
            logger.error(f"❌ Task error: {e}")
            target_task.status = 'Pending'
            target_task.save()
            results.append(f"❌ Error: {str(e)[:100]}")
    
    return f"✅ Evolved {site_name}: {' | '.join(results[:5])}"


# ============================================================
# 11. Parallel Tracks System
# ============================================================

def _process_growth_track(site):
    """መሰረታዊ የእድገት ትራክ"""
    results = []
    
    # Trigger Engine
    trigger = TriggerEngine(site)
    tasks = trigger.evaluate_all_triggers()
    for task in tasks:
        results.append(f"📋 Triggered: {task.task_name}")
    
    # Update phase
    trigger.update_phase()
    
    # Run single site analysis
    growth_result = run_single_site_analysis(site)
    results.append(growth_result)
    
    return results


def _process_healing_track(site):
    """ራስ-ጥገና ትራክ"""
    unresolved = AgentErrorLog.objects.filter(site=site, resolved=False).count()
    
    if unresolved > 0:
        try:
            from .self_coder import self_heal_single_site
            result = self_heal_single_site(site)
            return f"🛠️ {result}"
        except Exception as e:
            return f"⚠️ Healing error: {str(e)[:50]}"
    
    return None


# በ growth_agent.py ውስጥ ያለውን _process_maintenance_track አስተካክል

def _process_maintenance_track(site):
    """ጥገና ትራክ"""
    try:
        # 🔧 ደህንነት ባለው መንገድ አስመጣ
        try:
            from .security import SecurityScanner
        except ImportError:
            from .security_scanner import SecurityScanner
        
        scanner = SecurityScanner(site)
        
        project_code, _ = get_site_project_state(site)
        vulns = 0
        for file_name, code in project_code.items():
            if code and len(code) > 100:
                found = scanner.scan_code(code, file_path=file_name)
                vulns += len(found)
        
        if vulns > 0:
            return f"🔒 Found {vulns} security issues"
        return "✅ Maintenance OK"
    except ImportError:
        logger.warning("⚠️ SecurityScanner not available")
        return "⚠️ Security scanner not available"
    except Exception as e:
        return f"⚠️ Maintenance error: {str(e)[:50]}"


# ============================================================
# 12. ዋናው የዕድገት ሞተር (run_daily_market_analysis — v3)
# ============================================================

def run_daily_market_analysis():
    """
    v3 ሙሉ አውቶኖመስ የንግድ እድገት ሞተር
    Data-First, Dependency-Driven, Parallel Tracks
    """
    now = timezone.now()
    results = []
    
    # 🛡️ 1. የራስ-መገደብ ፍተሻ
    retry_config, _ = SiteConfig.objects.get_or_create(
        key="NEXT_ALLOWED_RUN_TIME", 
        defaults={'value': {'time': '2000-01-01T00:00:00'}}
    )
    
    try:
        next_run = timezone.datetime.fromisoformat(retry_config.value.get('time'))
        if timezone.is_naive(next_run):
            next_run = timezone.make_aware(next_run)
        if now < next_run:
            logger.info(f"💤 Global engine hibernating until {next_run}")
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
        # 3. አዲስ ጣቢያዎችን ያግኝ
        new_sites = discover_new_sites()
        for site in new_sites:
            results.append(f"🆕 Discovered: {site.name}")
            if analyze_site_niche(site):
                results.append(f"🧠 Analyzed niche: {site.niche}")
            strategy = GrowthStrategyEngine(site)
            strategy.execute_actions()
            results.append(f"📈 Started {strategy.get_strategy()['name']} strategy")
        
        # 4. ሁሉንም ንቁ ጣቢያዎች አስኬድ
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
                    'is_active': True,
                    'build_phase': 0
                }
            )
            active_sites = [default_site]
            results.append(f"🏗️ Created default site: {default_site.name}")
        
        # 5. Parallel Tracks: Growth → Healing → Maintenance
        for site in active_sites:
            try:
                site_results = []
                
                # 🎯 Primary Growth Track (always runs)
                growth_results = _process_growth_track(site)
                site_results.extend(growth_results)
                
                # 🛡️ Self-Healing Track (if capacity)
                if len(site_results) < 3:
                    healing_result = _process_healing_track(site)
                    if healing_result:
                        site_results.append(healing_result)
                
                # 🔧 Maintenance Track (if capacity)
                if len(site_results) < 3:
                    maintenance_result = _process_maintenance_track(site)
                    if maintenance_result:
                        site_results.append(maintenance_result)
                
                # Update site counts
                site.real_product_count = Product.objects.filter(site=site, is_active=True).count()
                site.real_customer_count = User.objects.filter(product__site=site).distinct().count()
                site.total_products = Product.objects.filter(site=site).count()
                site.total_sellers = User.objects.filter(product__site=site).distinct().count()
                site.save()
                
                results.append(f"[{site.name}] {' | '.join(site_results[:5])}")
                
            except Exception as e:
                error_msg = f"[{site.name}] ❌ Error: {str(e)}"
                results.append(error_msg)
                logger.error(error_msg)
                
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
        
        summary = " | ".join(results[:10])
        return f"🎉 Business Evolved! {summary}"
        
    except Exception as e:
        logger.error(f"❌ Business Engine Crash: {e}")
        return f"❌ Error: {str(e)}"
    finally:
        lock.value = {'status': 'idle'}
        lock.save()
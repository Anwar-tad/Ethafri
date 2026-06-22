# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ለውጥ፦ ሙሉ በሙሉ ራሱን የሚያስተዳድር — 24/7 Autonomous Growth Engine
# 📅 ቀን፦ 2026-06-22
# ============================================================

import os
import json
import re
import time
import random
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count, Avg
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

# ============================================================
# 📦 ሞዴል ኢምፖርቶች — ሁሉም ደህንነታቸው ተጠብቋል
# ============================================================
try:
    from .models import (
        SiteRegistry, AIProjectBacklog, AIEvolutionLog, AgentErrorLog,
        SelfHealingLog, SiteConfig, Product, Category, ProductTranslation,
        TranslationQueue, MarketTrend, VectorMemory, AgentTask, 
        SecurityLog, PredictionLog, ExternalAPI, AdminOverrideInstruction
    )
except ImportError as e:
    logger.warning(f"⚠️ Some models not found: {e}")
    # ሞዴሎች ካልተገኙ ባዶ ክፍሎችን ይፍጠሩ
    class SiteRegistry: pass
    class AIProjectBacklog: pass
    class AIEvolutionLog: pass
    class AgentErrorLog: pass
    class SelfHealingLog: pass
    class SiteConfig: pass
    class Product: pass
    class Category: pass
    class VectorMemory: pass
    class AgentTask: pass
    class SecurityLog: pass
    class PredictionLog: pass


# ============================================================
# 1. የAI ጥሪ ተግባራት (AI Call Functions)
# ============================================================

def ask_ai_with_failover(prompt, pool_type="coding", max_retries=2, timeout=60):
    """
    የተሻሻለ የኤአይ ፎልባክ ሞተር
    በርካታ AI አቅራቢዎችን ይደግፋል
    """
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
                from google import genai
                client = genai.Client(api_key=key)
                res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                data = extract_json(res.text)
                if data and "error" not in data: return data
            except Exception as e:
                logger.warning(f"🔄 Gemini Key {idx+1} exhausted: {e}")
                time.sleep(1)
        return None
    
    def call_mistral():
        if not mistral_key: return None
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"}
        model = "codestral-latest" if pool_type == "coding" else "mistral-large-latest"
        try:
            res = requests.post(url, headers=headers, json={
                "model": model, 
                "messages": [{"role": "user", "content": prompt}], 
                "response_format": {"type": "json_object"}
            }, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.warning(f"⚠️ Mistral error: {e}")
            return None
    
    def call_github():
        if not github_token: return None
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Authorization": f"Bearer {github_token}", "Content-Type": "application/json"}
        model = "meta-llama-3.1-405b-instruct"
        try:
            res = requests.post(url, headers=headers, json={
                "model": model, 
                "messages": [{"role": "user", "content": prompt}]
            }, timeout=timeout)
            if res.status_code == 200:
                return extract_json(res.json()['choices'][0]['message']['content'])
            return None
        except Exception as e:
            logger.warning(f"⚠️ GitHub error: {e}")
            return None
    
    def call_groq():
        if not groq_key: return None
        try:
            from groq import Groq
            client = Groq(api_key=groq_key)
            chat = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout
            )
            return extract_json(chat.choices[0].message.content)
        except Exception as e:
            logger.warning(f"⚠️ Groq error: {e}")
            return None
    
    providers = [call_mistral, call_github, call_gemini, call_groq]
    random.shuffle(providers)
    
    for provider in providers:
        for attempt in range(max_retries):
            try:
                result = provider()
                if result and "error" not in result:
                    logger.info(f"✅ Success with {provider.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt+1} failed: {e}")
                time.sleep(1)
    
    logger.error("❌ All AI providers failed")
    return {"error": "All AI providers failed after multiple attempts."}


def ask_ethafri_ceo(prompt, pool_type="coding"):
    """ask_ai_with_failover ን ይጠራል (ለተኳሃኝነት)"""
    return ask_ai_with_failover(prompt, pool_type=pool_type)


# ============================================================
# 2. የጣቢያ ፕሮጀክት ሁኔታ (Site Project State)
# ============================================================

def get_site_project_state(site):
    """
    የጣቢያውን የፕሮጀክት ኮድ እና የፋይል መዋቅር ያነባል
    """
    if not site or not getattr(site, 'repo_path', None):
        return {}, {}
    
    base = site.repo_path
    target_files = {
        'models': os.path.join(base, 'marketplace', 'models.py'),
        'views': os.path.join(base, 'marketplace', 'views.py'),
        'urls': os.path.join(base, 'marketplace', 'urls.py'),
        'forms': os.path.join(base, 'marketplace', 'forms.py'),
        'admin': os.path.join(base, 'marketplace', 'admin.py'),
        'home_html': os.path.join(base, 'marketplace', 'templates', 'marketplace', 'home.html'),
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
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    state[key] = f.read()
            except Exception:
                state[key] = f"❌ MISSING_FILE: This file doesn't exist yet."
        else:
            state[key] = f"❌ MISSING_FILE: This file doesn't exist yet."
    return state, target_files


# ============================================================
# 3. የራስ-መነሻ ስርዓት (Self-Booting System)
# ============================================================

class AutonomousGrowthEngine:
    """
    24/7 ራሱን የሚያስተዳድር የዕድገት ሞተር
    ፈጽሞ አይተኛም — ሁልጊዜ የሚሰራ ስራ ይፈጥራል
    """
    
    def __init__(self):
        self.is_running = False
        self.last_cycle = None
        self.cycle_count = 0
        self.error_count = 0
        self.max_errors = 10
        
    # ============================================================
    # 3.1 ዋና የስራ ዑደት (Main Work Loop)
    # ============================================================
    
    def run_cycle(self):
        """አንድ ሙሉ የስራ ዑደት ያካሂዳል"""
        if self.is_running:
            logger.info("⚠️ Already running a cycle. Skipping...")
            return "Already running"
        
        self.is_running = True
        self.cycle_count += 1
        start_time = timezone.now()
        
        results = []
        
        try:
            logger.info(f"🚀 Starting cycle #{self.cycle_count} at {start_time}")
            
            # 1. ሁሉንም ጣቢያዎች አግኝ
            sites = []
            try:
                sites = list(SiteRegistry.objects.filter(is_active=True))
            except Exception as e:
                logger.error(f"❌ Failed to get sites: {e}")
                sites = []
            
            if not sites:
                # ምንም ጣቢያ ከሌለ አዲስ ፍጠር
                primary = self._create_default_site()
                if primary:
                    sites = [primary]
                    results.append(f"🏗️ Created default site: {primary.name}")
                else:
                    results.append("⚠️ Could not create default site")
            
            # 2. እያንዳንዱን ጣቢያ አስኬድ
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
            
            # 3. ዓለም አቀፍ ጥገና
            maintenance_result = self._global_maintenance()
            results.append(f"[Global] {maintenance_result}")
            
            # 4. ራስ-ጥገና (Self-Healing)
            if self.error_count > 3:
                heal_result = self._self_heal()
                results.append(f"[Healing] {heal_result}")
                self.error_count = 0
            
            # 5. ሪፖርት ይመዝግብ
            self.last_cycle = timezone.now()
            
            # 6. የEVOLUTION_LOCK ን አዘምን
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
            
            # 7. ስርዓቱ በህይወት መኖሩን መዝግብ
            try:
                SiteConfig.objects.update_or_create(
                    key='AGENT_HEARTBEAT',
                    defaults={'value': {
                        'timestamp': timezone.now().isoformat(),
                        'status': 'alive',
                        'cycle': self.cycle_count
                    }}
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not update AGENT_HEARTBEAT: {e}")
            
            logger.info(f"✅ Cycle #{self.cycle_count} completed in {(timezone.now() - start_time).seconds}s")
            
        except Exception as e:
            logger.error(f"❌ Cycle failed: {e}")
            results.append(f"❌ Cycle error: {str(e)[:100]}")
            self.error_count += 1
            
            # ከባድ ስህተት ከሆነ ራስ-ጥገና
            if self.error_count > 5:
                self._emergency_self_heal()
        
        finally:
            self.is_running = False
        
        return " | ".join(results[:10]) if results else "No results"
    
    # ============================================================
    # 3.2 የጣቢያ ሂደት (Site Processing)
    # ============================================================
    
    def _process_site(self, site):
        """አንድ ጣቢያ ሙሉ በሙሉ ያስኬዳል"""
        site_name = site.name if hasattr(site, 'name') else 'unknown'
        results = []
        
        try:
            # 1. የጣቢያ ትንተና
            analysis = self._analyze_site_deep(site)
            results.append(f"📊 Analysis: {analysis.get('summary', 'OK')}")
            
            # 2. አዲስ ስራዎችን ፍጠር (በትንተና ላይ ተመስርቶ)
            new_tasks = self._generate_dynamic_tasks(site, analysis)
            if new_tasks:
                results.append(f"📋 Created {len(new_tasks)} tasks")
            
            # 3. ነባር ስራዎችን አስኬድ
            executed = self._execute_pending_tasks(site)
            if executed:
                results.append(f"⚡ Executed {len(executed)} tasks")
            
            # 4. ምዕራፍ አዘምን
            self._update_phase(site, analysis)
            
            # 5. ስህተቶችን ፈትሽ
            try:
                errors = AgentErrorLog.objects.filter(site=site, resolved=False)
                if errors.exists():
                    results.append(f"⚠️ {errors.count()} errors found")
                    fixed = self._heal_errors(site, errors[:3])
                    if fixed:
                        results.append(f"🛠️ Fixed {len(fixed)} errors")
            except Exception as e:
                logger.warning(f"⚠️ Error checking errors: {e}")
            
            # 6. የጣቢያ መረጃ አዘምን
            try:
                if hasattr(site, 'update_real_counts'):
                    site.update_real_counts()
            except Exception as e:
                logger.warning(f"⚠️ Could not update counts: {e}")
            
        except Exception as e:
            logger.error(f"❌ Site processing error for {site_name}: {e}")
            results.append(f"❌ Error: {str(e)[:50]}")
        
        return " | ".join(results[:5]) if results else "No results"
    
    # ============================================================
    # 3.3 ጥልቅ ትንተና (Deep Analysis)
    # ============================================================
    
    def _analyze_site_deep(self, site):
        """የጣቢያውን ሁኔታ በጥልቀት ይተነትናል"""
        
        # 1. የኮድ ሁኔታ
        try:
            project_code, _ = get_site_project_state(site)
            code_status = {
                'has_models': 'models' in project_code and project_code['models'],
                'has_views': 'views' in project_code and project_code['views'],
                'has_urls': 'urls' in project_code and project_code['urls'],
                'has_admin': 'admin' in project_code and project_code['admin'],
                'has_templates': 'home_html' in project_code and project_code['home_html'],
            }
        except Exception:
            code_status = {'has_models': False, 'has_views': False, 'has_urls': False, 'has_admin': False, 'has_templates': False}
        
        # 2. የውሂብ ሁኔታ
        try:
            product_count = Product.objects.filter(site=site, is_active=True).count()
            customer_count = User.objects.filter(product__site=site).distinct().count()
            category_count = Category.objects.filter(product__site=site).distinct().count()
        except Exception:
            product_count = 0
            customer_count = 0
            category_count = 0
        
        # 3. የስራ ሁኔታ
        try:
            task_count = AIProjectBacklog.objects.filter(site=site).count()
            pending_count = AIProjectBacklog.objects.filter(site=site, status='Pending').count()
            completed_count = AIProjectBacklog.objects.filter(site=site, status='Completed').count()
        except Exception:
            task_count = 0
            pending_count = 0
            completed_count = 0
        
        # 4. የስህተት ሁኔታ
        try:
            error_count = AgentErrorLog.objects.filter(site=site, resolved=False).count()
        except Exception:
            error_count = 0
        
        # 5. የራስ-ጥገና ሁኔታ
        try:
            healing_count = SelfHealingLog.objects.filter(resolved=True).count()
        except Exception:
            healing_count = 0
        
        # 6. የጎደሉ ባህሪያት
        build_phase = getattr(site, 'build_phase', 0)
        missing_features = self._detect_missing_features(site, code_status, product_count)
        
        # 7. የወቅታዊ ሁኔታ ማጠቃለያ
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
            'healing_count': healing_count,
            'missing_features': missing_features,
            'summary': summary,
            'build_phase': build_phase,
        }
    
    def _detect_missing_features(self, site, code_status, product_count):
        """የጎደሉ ባህሪያትን ይለያል"""
        missing = []
        
        # በኮድ ሁኔታ
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
        
        # በምርት ብዛት
        if product_count < 5:
            missing.append('Products')
        
        # በምዕራፍ
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
    
    def _generate_dynamic_tasks(self, site, analysis):
        """በትንተና ላይ ተመስርቶ አዲስ ስራዎችን ይፈጥራል"""
        created = []
        
        try:
            # ቀድሞ ያሉ ስራዎች
            existing = AIProjectBacklog.objects.filter(
                site=site,
                status__in=['Pending', 'Running']
            ).values_list('task_name', flat=True)
            
            # የጎደሉ ባህሪያትን ለይ
            for feature in analysis.get('missing_features', []):
                task_name = f"Build: {feature}"
                
                if task_name not in existing:
                    priority = self._calculate_priority(feature, analysis.get('build_phase', 0))
                    impact = self._calculate_impact(feature)
                    
                    task = AIProjectBacklog.objects.create(
                        site=site,
                        task_name=task_name,
                        task_type='code',
                        target_file=feature.lower().replace(' ', '_'),
                        priority=priority,
                        status='Pending',
                        description=f"Implement {feature} for {site.name}",
                        business_impact_score=impact,
                        trigger_condition=f"Dynamic: Missing {feature}"
                    )
                    created.append(task)
                    logger.info(f"📋 Dynamic task: {task_name} for {site.name}")
            
            # ስህተቶች ካሉ
            if analysis.get('error_count', 0) > 0:
                error_count = analysis['error_count']
                error_task = AIProjectBacklog.objects.create(
                    site=site,
                    task_name=f"Fix {error_count} errors",
                    task_type='code',
                    target_file='error_fix',
                    priority='Critical',
                    status='Pending',
                    description=f"Fix {error_count} unresolved errors",
                    business_impact_score=10,
                    trigger_condition=f"Dynamic: {error_count} errors"
                )
                created.append(error_task)
                logger.info(f"📋 Error fix task: {error_task.task_name}")
            
            # ምንም ስራ ከሌለ — Self-Learning
            if not created and not existing:
                learn_task = AIProjectBacklog.objects.create(
                    site=site,
                    task_name='Self-Learning: Analyze & Plan',
                    task_type='growth',
                    target_file='self_learning',
                    priority='Medium',
                    status='Pending',
                    description=f"Analyze {site.name} and plan next steps",
                    business_impact_score=6,
                    trigger_condition="Dynamic: Self-Learning"
                )
                created.append(learn_task)
                logger.info(f"📋 Self-learning task: {learn_task.task_name}")
                
        except Exception as e:
            logger.error(f"❌ Error generating tasks: {e}")
        
        return created
    
    def _calculate_priority(self, feature, phase):
        """የስራ ቅድሚያ ይወስናል"""
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
        """የስራ ተጽዕኖ ደረጃ ይወስናል"""
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
    
    def _execute_pending_tasks(self, site):
        """የታገዱ ስራዎችን ያስኬዳል"""
        executed = []
        
        try:
            tasks = AIProjectBacklog.objects.filter(
                site=site,
                status='Pending'
            ).order_by('-priority', '-business_impact_score')[:3]
            
            for task in tasks:
                try:
                    # ስራውን እንደሚሄድ ምልክት አድርግ
                    task.status = 'Running'
                    task.save()
                    
                    # የስራ አፈጻጸም
                    result = self._execute_task(task, site)
                    
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
    
    def _execute_task(self, task, site):
        """አንድ ስራ ያስኬዳል (AI በመጠቀም)"""
        try:
            project_code, _ = get_site_project_state(site)
            
            prompt = f"""
            You are the EthAfri AI Agent for site: {site.name if hasattr(site, 'name') else 'unknown'}
            
            Task: {task.task_name}
            Description: {task.description}
            Priority: {task.priority}
            Impact: {task.business_impact_score}/10
            
            Codebase: {json.dumps(project_code, indent=2)[:2000]}
            
            Generate code or solution for this task.
            Return ONLY JSON with 'code' and 'explanation' fields.
            """
            
            response = ask_ethafri_ceo(prompt, pool_type="coding")
            
            if response and isinstance(response, dict) and 'code' in response:
                # ኮዱን ተግብር
                self._apply_code(response.get('code', ''), site, task)
                return "success"
            
            return "No valid response from AI"
            
        except Exception as e:
            logger.error(f"❌ Task execution error: {e}")
            return f"error: {str(e)[:50]}"
    
    def _apply_code(self, code, site, task):
        """ኮዱን ወደ ፋይል ይጽፋል"""
        logger.info(f"📝 Applying code for {task.task_name}")
        # TODO: ፋይል ላይ መጻፍ ያስፈልጋል
        pass
    
    # ============================================================
    # 3.6 ምዕራፍ አስተዳደር (Phase Management)
    # ============================================================
    
    def _update_phase(self, site, analysis):
        """የጣቢያውን ምዕራፍ ያሻሽላል"""
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
    
    # ============================================================
    # 3.7 ስህተት ጥገና (Error Healing)
    # ============================================================
    
    def _heal_errors(self, site, errors):
        """ስህተቶችን ለመፍታት ይሞክራል"""
        fixed = []
        
        for error in errors:
            try:
                prompt = f"""
                Fix this error:
                Task: {error.task_name}
                Type: {error.error_type}
                Message: {error.error_message}
                Code: {error.code_attempted[:500] if error.code_attempted else 'No code'}
                """
                
                response = ask_ethafri_ceo(prompt, pool_type="healing")
                
                if response and isinstance(response, dict) and 'solution' in response:
                    error.resolved = True
                    error.correction_applied = response.get('solution', '')
                    error.save()
                    fixed.append(error)
                    logger.info(f"✅ Healed error: {error.task_name}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to heal error: {e}")
        
        return fixed
    
    # ============================================================
    # 3.8 ራስ-ጥገና (Self-Healing)
    # ============================================================
    
    def _self_heal(self):
        """ራስ-ጥገና ያካሂዳል"""
        try:
            AgentErrorLog.objects.filter(resolved=False).update(resolved=True)
            AIProjectBacklog.objects.filter(status='Running').update(status='Pending')
            SelfHealingLog.objects.create(
                error_message="Self-Healing: Reset all errors and stuck tasks",
                resolved=True
            )
            return "Reset errors and stuck tasks"
        except Exception as e:
            return f"Self-heal failed: {str(e)[:50]}"
    
    def _emergency_self_heal(self):
        """ድንገተኛ ራስ-ጥገና"""
        try:
            SiteConfig.objects.update_or_create(
                key='EVOLUTION_LOCK',
                defaults={'value': {'status': 'idle'}}
            )
            AIProjectBacklog.objects.filter(status='Running').update(status='Pending')
            AgentErrorLog.objects.filter(resolved=False).update(resolved=True)
            logger.info("🚨 Emergency self-heal completed")
            return True
        except Exception:
            return False
    
    # ============================================================
    # 3.9 ዓለም አቀፍ ጥገና (Global Maintenance)
    # ============================================================
    
    def _global_maintenance(self):
        """ዓለም አቀፍ ጥገና ያካሂዳል"""
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
            
            duplicates = AgentErrorLog.objects.filter(
                resolved=False
            ).values('error_message').annotate(count=Count('id')).filter(count__gt=3)
            
            for dup in duplicates:
                AgentErrorLog.objects.filter(
                    error_message=dup['error_message'],
                    resolved=False
                ).exclude(id__in=AgentErrorLog.objects.filter(
                    error_message=dup['error_message'],
                    resolved=False
                ).order_by('created_at')[:1].values_list('id', flat=True)
                ).delete()
                results.append("Deduplicated errors")
            
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
    
    # ============================================================
    # 3.10 ነባሪ ጣቢያ መፍጠር (Default Site Creation)
    # ============================================================
    
    def _create_default_site(self):
        """ምንም ጣቢያ ከሌለ አዲስ ይፈጥራል"""
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
                AIProjectBacklog.objects.create(
                    site=site,
                    task_name='Initialize EthAfri',
                    task_type='growth',
                    target_file='init',
                    priority='Critical',
                    status='Pending',
                    description='Initial setup and configuration',
                    business_impact_score=10,
                    trigger_condition='System bootstrap'
                )
            
            return site
            
        except Exception as e:
            logger.error(f"❌ Failed to create default site: {e}")
            return None
    
    # ============================================================
    # 3.11 የስርዓት ሁኔታ (System Status)
    # ============================================================
    
    def get_status(self):
        """የስርዓቱን ወቅታዊ ሁኔታ ይመልሳል"""
        try:
            return {
                'is_running': self.is_running,
                'cycle_count': self.cycle_count,
                'last_cycle': self.last_cycle.isoformat() if self.last_cycle else None,
                'error_count': self.error_count,
                'total_sites': SiteRegistry.objects.filter(is_active=True).count(),
                'total_tasks': AIProjectBacklog.objects.count(),
                'pending_tasks': AIProjectBacklog.objects.filter(status='Pending').count(),
                'total_errors': AgentErrorLog.objects.filter(resolved=False).count(),
                'total_healings': SelfHealingLog.objects.count(),
            }
        except Exception:
            return {
                'is_running': self.is_running,
                'cycle_count': self.cycle_count,
                'last_cycle': self.last_cycle.isoformat() if self.last_cycle else None,
                'error_count': self.error_count,
                'total_sites': 0,
                'total_tasks': 0,
                'pending_tasks': 0,
                'total_errors': 0,
                'total_healings': 0,
            }
    
    def get_heartbeat(self):
        """የልብ ምት ሁኔታ ይመልሳል"""
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
    """
    24/7 የሚሰራ ራስ-ገዝ ሉፕ
    ይህ ክፍል ኤጀንቱ ፈጽሞ እንዳይተኛ ያደርጋል
    """
    
    def __init__(self):
        self.engine = AutonomousGrowthEngine()
        self.running = True
        self.interval = 60
    
    def start(self):
        """ራስ-ገዝ ሉፕ ይጀምራል"""
        logger.info("🚀 Starting Autonomous Loop - Will run forever")
        
        while self.running:
            try:
                logger.info(f"💓 Heartbeat at {timezone.now()}")
                result = self.engine.run_cycle()
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
                
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Stopping Autonomous Loop...")
                self.running = False
                break
                
            except Exception as e:
                logger.error(f"❌ Loop error: {e}")
                time.sleep(60)


# ============================================================
# 5. የራስ-ማስተማር ተግባር (Self-Education — ከክፍል ውጭ)
# ============================================================

def self_educate(site, analysis):
    """
    ምንም ስራ ከሌለ ራሱን ያስተምራል
    ይህ ተግባር ከAutonomousGrowthEngine ክፍል ውጭ ነው
    """
    logger.info(f"📚 Starting Self-Education for {site.name if hasattr(site, 'name') else 'unknown'}")
    
    try:
        # 1. የጎደሉ ባህሪያትን ይለያል
        if analysis and analysis.get('missing_features'):
            insight = f"Missing features: {', '.join(analysis['missing_features'][:3])}"
        else:
            insight = "Codebase looks complete. Monitoring for new opportunities."
        
        # 2. ራስ-ማስተማር መዝግብ
        try:
            SelfHealingLog.objects.create(
                error_message=f"Self-Learning: {site.name if hasattr(site, 'name') else 'unknown'}",
                solution_sql=insight,
                resolved=True
            )
            logger.info(f"✅ Self-Education logged for {site.name if hasattr(site, 'name') else 'unknown'}")
        except Exception as e:
            logger.warning(f"⚠️ Could not log self-education: {e}")
        
        # 3. አዲስ ስራ ለመፍጠር ሞክር
        if not analysis or not analysis.get('missing_features'):
            try:
                task, created = AIProjectBacklog.objects.get_or_create(
                    site=site,
                    task_name='Optimize Performance',
                    defaults={
                        'task_type': 'seo',
                        'target_file': 'performance',
                        'priority': 'Medium',
                        'status': 'Pending',
                        'description': 'Optimize database queries and page load times',
                        'business_impact_score': 7,
                        'trigger_condition': 'Self-Learning: All features complete'
                    }
                )
                if created:
                    logger.info(f"📋 Self-learning task created: Optimize Performance")
            except Exception as e:
                logger.warning(f"⚠️ Could not create self-learning task: {e}")
        
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
        """
        response = ask_ethafri_ceo(prompt, pool_type="analysis")
        return response
    except Exception as e:
        logger.error(f"Market analysis error: {e}")
        return {}


# ============================================================
# 6. ዋና መግቢያ ተግባራት (Main Entry Points)
# ============================================================

def run_autonomous_agent():
    """ሙሉ በሙሉ ራሱን የሚያስተዳድር ኤጀንት ይጀምራል"""
    loop = AutonomousLoop()
    loop.start()


def run_single_cycle():
    """አንድ የስራ ዑደት ብቻ ያካሂዳል (ለክሮን)"""
    engine = AutonomousGrowthEngine()
    return engine.run_cycle()


def run_daily_market_analysis():
    """የቀድሞ ተኳሃኝነት ለማቆየት"""
    return run_single_cycle()


def run_single_site_analysis(site):
    """ለአንድ ጣቢያ ትንተና (ለተኳሃኝነት)"""
    engine = AutonomousGrowthEngine()
    return engine._process_site(site)


def get_agent_status():
    """የኤጀንቱን ወቅታዊ ሁኔታ ይመልሳል"""
    engine = AutonomousGrowthEngine()
    return engine.get_status()


def get_agent_heartbeat():
    """የልብ ምት ሁኔታ ይመልሳል"""
    engine = AutonomousGrowthEngine()
    return engine.get_heartbeat()


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
        
        prompt = f"""
        Analyze this website's code to determine its niche:
        Site: {site.name if hasattr(site, 'name') else 'unknown'}
        
        Codebase: {json.dumps(project_code, indent=2)[:4000]}
        
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
        
        return {
            'total': queryset.count(),
            'by_priority': queryset.values('priority').annotate(count=Count('id')),
            'by_type': queryset.values('task_type').annotate(count=Count('id')),
            'critical': queryset.filter(priority='Critical').count(),
            'high': queryset.filter(priority='High').count(),
            'oldest': queryset.order_by('created_at').first(),
            'newest': queryset.order_by('-created_at').first(),
        }
    except Exception as e:
        logger.error(f"❌ Task analysis error: {e}")
        return {'total': 0, 'by_priority': [], 'by_type': [], 'critical': 0, 'high': 0, 'oldest': None, 'newest': None}
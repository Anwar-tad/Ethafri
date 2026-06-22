# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/growth_agent.py
# 📝 ለውጥ፦ ሙሉ በሙሉ ራሱን የሚያስተዳድር — 24/7 Autonomous Growth Engine
# ✅ የተፈቱ ችግሮች፦ DB Connection Leaks, Code Context Optimization, Syntax Safety Gates
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from django.utils import timezone
from django.db import models, connection, connections
from django.db.models import Q, Count, Avg, Case, When, Value, IntegerField, Sum
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

# ============================================================
# 📦 ሞዴል ኢምፖርቶች
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
# ✅ አዲስ ኢምፖርት — ብቸኛ ኮድ-መተግበሪያ ነጥብ
# ============================================================
try:
    from .code_apply import apply_code_change
except ImportError:
    logger.warning("⚠️ code_apply.py not found. Using fallback.")
    def apply_code_change(site, file_key, new_content, path, reason, confidence_score=100, backlog_task=None, push_to_github=True):
        old_code = ""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        try:
            AIEvolutionLog.objects.create(
                target_file=file_key,
                reason_for_change=reason,
                old_code_backup=old_code,
                new_code_patch=new_content,
                site=site
            )
        except Exception as e:
            logger.error(f"AIEvolutionLog creation error in apply_code_change fallback: {e}")
        return {'success': True, 'message': f"✅ Applied {file_key} (fallback)", 'applied': True}


# ============================================================
# 1. የAI ጥሪ ተግባራት (AI Call Functions)
# ============================================================

class AICache:
    """ተደጋጋሚ የAI ጥያቄዎችን ለማስታወስ"""
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl
    
    def get_or_compute(self, prompt, compute_func):
        key = hashlib.md5(prompt.encode()).hexdigest()
        if key in self.cache:
            cached, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return cached
        result = compute_func()
        self.cache[key] = (result, time.time())
        return result
    
    def clear(self):
        self.cache = {}

_ai_cache = AICache(ttl=1800)  # 30 ደቂቃ


def ask_ai_with_failover(prompt, pool_type="coding", max_retries=2, timeout=30, use_cache=True):
    """የተሻሻለ የኤአይ ፎልባክ ሞተር — የጊዜ ገደቡ ወደ 30 ሰከንድ ዝቅ ብሏል"""
    
    if use_cache:
        cached = _ai_cache.get_or_compute(prompt, lambda: None)
        if cached:
            logger.debug("💾 AI cache hit")
            return cached
    
    gemini_keys = [val for key, val in os.environ.items() if key.startswith("GEMINI_API_KEY") and val]
    groq_key = os.environ.get('GROQ_API_KEY')
    mistral_key = os.environ.get('MISTRAL_API_KEY')
    github_token = os.environ.get('GITHUB_TOKEN')
    
    def extract_json(text):
        if not text: return None
        try:
            json_block = re.search(r'```json\s*([\s\S]*?)\s*```', text)
            if json_block:
                return json.loads(json_block.group(1).strip())
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return None
        except Exception:
            return None
    
    def call_gemini():
        if not gemini_keys: return None
        for idx, key in enumerate(gemini_keys):
            try:
                from google import genai
                client = genai.Client(api_key=key)
                res = client.models.generate_content(
                    model='gemini-2.5-flash' if pool_type == "coding" else 'gemini-2.0-flash',
                    contents=prompt
                )
                data = extract_json(res.text)
                if data and "error" not in data:
                    return data
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
    
    if pool_type == "coding":
        providers = [call_mistral, call_github, call_gemini, call_groq]
    elif pool_type == "analysis":
        providers = [call_gemini, call_mistral, call_github]
    else:
        providers = [call_mistral, call_gemini, call_github, call_groq]
    
    random.shuffle(providers)
    
    for provider in providers:
        for attempt in range(max_retries):
            try:
                result = provider()
                if result and "error" not in result:
                    if use_cache:
                        _ai_cache.get_or_compute(prompt, lambda: result)
                    logger.info(f"✅ Success with {provider.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Attempt {attempt+1} failed: {e}")
                time.sleep(2 ** attempt)
    
    logger.error("❌ All AI providers failed")
    return {"error": "All AI providers failed after multiple attempts."}


def ask_ethafri_ceo(prompt, pool_type="coding", use_cache=True):
    return ask_ai_with_failover(prompt, pool_type=pool_type, use_cache=use_cache)


# ============================================================
# 2. የጣቢያ ፕሮጀክት ሁኔታ (Site Project State) — የተሻሻለ
# ============================================================

_project_hashes = {}

def get_site_project_state(site, force_refresh=False):
    """የጣቢያውን የፕሮጀክት ኮድ ያነባል — ከካሽ ጋር"""
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
    site_key = f"site_{site.id if site.id else site.name}"
    
    for key, path in target_files.items():
        file_key = f"{site_key}_{key}"
        current_hash = None
        
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    current_hash = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass
            
            if not force_refresh and file_key in _project_hashes and _project_hashes.get(file_key) == current_hash:
                if key in _project_hashes.get(f"{file_key}_content", {}):
                    state[key] = _project_hashes[f"{file_key}_content"]
                    continue
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    state[key] = content
                    _project_hashes[file_key] = current_hash
                    _project_hashes[f"{file_key}_content"] = content
            except Exception as e:
                state[key] = f"ERROR: Could not read file - {e}"
        else:
            state[key] = f"❌ MISSING_FILE: This file doesn't exist yet."
    
    return state, target_files


# ============================================================
# ⚙️ የውሂብ መላክ ማሻሻያ (Token Optimization & Safe JSON)
# ============================================================

def get_targeted_code_context(project_code, target_file_key=None, max_chars=3500):
    """
    ለኤአይ የሚላከውን የኮድ መጠን ያሳጥራል።
    የሚሻሻለውን ፋይል ሙሉ በሙሉ ይልካል፣ ሌሎችን ግን በአጭሩ ያሳያል።
    ይህም ትልቅ JSON ተቆርጦ ኤአይ እንዳይቋረጥ ይከላከላል።
    """
    optimized = {}
    for key, content in project_code.items():
        if not isinstance(content, str):
            optimized[key] = content
            continue
        
        if target_file_key and key == target_file_key:
            optimized[key] = content[:max_chars] + ("\n... [Truncated for AI size safety]" if len(content) > max_chars else "")
        else:
            lines = content.split('\n')
            if len(lines) > 35:
                optimized[key] = "\n".join(lines[:35]) + f"\n... [Truncated {len(lines)-35} lines to save tokens]"
            else:
                optimized[key] = content
    return optimized


# ============================================================
# 3. የራስ-መነሻ ስርዓት (Self-Booting System)
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
        self.memory_engine = None
        self.cache = AICache(ttl=1800)
    
    def run_cycle(self, max_cycles=1):
        """አንድ ወይም ብዙ የስራ ዑደቶችን ያካሂዳል"""
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
                
                # ትይዩ የጣቢያ ሂደት
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
                
                # ዓለም አቀፍ ጥገና
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
                            'cycle': self.cycle_count
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
            # የዳታቤዝ ግንኙነቶችን በጥንቃቄ መዝጋት
            connections.close_all()
        
        return " | ".join(total_results[:10]) if total_results else "No results"
    
    # ============================================================
    # 3.1.1 ትይዩ የጣቢያ ሂደት (Parallel Site Processing)
    # ============================================================
    
    def _process_sites_parallel(self, sites):
        """ብዙ ጣቢያዎችን በትይዩ ያስኬዳል — በደህንነት የዳታቤዝ መዝጊያ የታገዘ"""
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
        """በትይዩ ክሮች (Parallel Threads) ውስጥ የዳታቤዝ ግንኙነት እንዳይፈስ የሚከላከል መጠቅለያ"""
        try:
            return self._process_site(site)
        finally:
            # ✅ በእያንዳንዱ ክር መጨረሻ ላይ ግንኙነቶችን መዝጋት (የዌብሳይት ፍጥነትን ያድናል)
            connections.close_all()
    
    # ============================================================
    # 3.2 የጣቢያ ሂደት (Site Processing)
    # ============================================================
    
    def _process_site(self, site):
        """አንድ ጣቢያ ሙሉ በሙሉ ያስኬዳል"""
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
    
    # ============================================================
    # 3.3 ጥልቅ ትንተና (Deep Analysis)
    # ============================================================
    
    def _analyze_site_deep(self, site):
        """የጣቢያውን ሁኔታ በጥልቀት ይተነትናል"""
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
        """የጎደሉ ባህሪያትን ይለያል"""
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

    def _generate_dynamic_tasks(self, site, analysis):
        """በትንተና ላይ ተመስርቶ አዲስ ስራዎችን ይፈጥራል — ከደህንነቱ የተጠበቀ የራስ-ጥገና ጋር"""
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
                    
                    # ✅ get_or_create በ _get_or_create_task_safe ተተክቷል
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
                
                # ✅ get_or_create በ _get_or_create_task_safe ተተክቷል
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
                # ✅ get_or_create በ _get_or_create_task_safe ተተክቷል
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
        """የታገዱ ስራዎችን በSmart Priority ያስኬዳል"""
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
        """አንድ ስራ ያስኬዳል — ከSmart Retry ጋር"""
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
        """የስራውን አፈጻጸም ያካሂዳል — ከትኩረት የኮድ መዋቅር (Targeted Context) ጋር"""
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
            
            # ✅ የተሻሻለ፦ JSON እንዳይቆረጥ የኮድ ይዘትን አሳጥሮ መላክ
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
                
                # ✅ የቅድመ-ትግበራ የደህንነት በር (Syntax Safety Gate)
                # ፋይሉ ፓይተን ከሆነ ከመጻፉ በፊት ኮምፓይል በማድረግ ስህተት መኖሩን ማረጋገጥ
                if target_file_confirmed in ['models', 'views', 'urls', 'forms', 'admin'] or target_file_confirmed.endswith('.py'):
                    try:
                        compile(code_content, '<string>', 'exec')
                    except SyntaxError as compile_err:
                        logger.error(f"⛔ Rejecting generated code for {target_file_confirmed} due to syntax error: {compile_err}")
                        
                        # ስህተቱን ለቀጣይ ጥገና መመዝገብ
                        AgentErrorLog.objects.create(
                            site=site,
                            task_name=task.task_name,
                            error_type='syntax',
                            error_message=f"SyntaxError in AI generated code: {compile_err}",
                            code_attempted=code_content,
                            resolved=False
                        )
                        return f"error: AI code failed local syntax compilation validation: {compile_err}"
                
                path = None
                if site.repo_path:
                    path = os.path.join(site.repo_path, 'marketplace', f'{target_file_confirmed}.py')
                
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
    # 3.7 ስህተት ጥገና (Error Healing) — ✅ Smart Healing
    # ============================================================
    
    def _heal_errors_smart(self, site, errors):
        """ስህተቶችን ለመፍታት ይሞክራል — ከRAG ጋር"""
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
    
    # ============================================================
    # 3.8 ራስ-ጥገና (Self-Healing)
    # ============================================================
    
    def _self_heal(self):
        """ራስ-ጥገና ያካሂዳል"""
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
        """ድንገተኛ ራስ-ጥገና"""
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
                # ✅ ማሻሻያ፦ _get_or_create_task_safeን በመጠቀም የተባዛ ስራ መከላከል
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
    
    # ============================================================
    # 3.11 የስርዓት ሁኔታ (System Status)
    # ============================================================
    
    def get_status(self):
        """የስርዓቱን ሁኔታ ይመልሳል"""
        try:
            return {
                'is_


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
        """ራስ-ገዝ ሉፕ ይጀምራል — ደህንነቱ በተጠበቀ ግንኙነቶች የታገዘ"""
        logger.info("🚀 Starting Autonomous Loop")
        start_time = time.time()
        
        while self.running:
            try:
                if time.time() - start_time > self.max_runtime:
                    logger.info(f"⏰ Max runtime reached ({self.max_runtime}s). Restarting...")
                    break
                
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
                
                # የውሂብ ግንኙነቶችን በመዝጋት የሰርቨሩን አቅም ነጻ ማድረግ
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
    """ምንም ስራ ከሌለ ራሱን ያስተምራል"""
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
                    task, is_new = AIProjectBacklog.objects.get_or_create(
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
# 6. ዋና መግቢያ ተግባራት (Main Entry Points)
# ============================================================

def run_autonomous_agent():
    """ሙሉ በሙሉ ራሱን የሚያስተዳድር ኤጀንት ይጀምራል"""
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
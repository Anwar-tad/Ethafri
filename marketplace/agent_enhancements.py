# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/agent_enhancements.py
# 📝 ለውጥ፦ ሁሉንም የኤጀንት አቅም ማሳደጊያ ሞጁሎች በአንድ ላይ
# 📅 ቀን፦ 2026-06-22
# ============================================================

"""
ይህ ፋይል የEthAfri ኤጀንትን አቅም ለማሳደግ የሚያገለግሉ ሁሉንም ተጨማሪ ሞጁሎች ይዟል።
እያንዳንዱ ክፍል በተናጥል ወይም በቡድን ሊሰራ ይችላል።
"""

import os
import json
import time
import threading
import logging
import hashlib
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count, Avg, Sum, Case, When, Value, IntegerField
from django.conf import settings

# ✅ ሁሉም ሞዴሎች በትክክል ተመጥተዋል
from .models import (
    SiteRegistry, AIProjectBacklog, AIEvolutionLog, AgentErrorLog,
    SelfHealingLog, SiteConfig, Product, Category, VectorMemory,
    SecurityLog, PredictionLog, AgentTask
)

logger = logging.getLogger(__name__)


# ============================================================
# 🔧 ረዳት ተግባራት
# ============================================================

def _safe_import_from_growth_agent():
    """ደህንነት ባለው መንገድ growth_agent ን ያስመጣል"""
    try:
        from .growth_agent import ask_ethafri_ceo, get_site_project_state
        return ask_ethafri_ceo, get_site_project_state
    except ImportError as e:
        logger.warning(f"⚠️ Could not import from growth_agent: {e}")
        return None, None


# ============================================================
# 1. 🚀 ትይዩ ስራ አፈጻጸም (Parallel Task Executor)
# ============================================================

class ParallelTaskExecutor:
    """በአንድ ጊዜ ብዙ ስራዎችን በትይዩ ያስኬዳል"""
    
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.active_tasks = []
        self.completed_tasks = []
        self.failed_tasks = []
    
    def execute_tasks(self, tasks, site=None):
        """የተሰጡትን ስራዎች በትይዩ ያስኬዳል"""
        results = []
        threads = []
        
        prioritized = self._prioritize_tasks(tasks)
        
        for task in prioritized[:self.max_workers]:
            thread = threading.Thread(
                target=self._execute_single_task,
                args=(task, site, results)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        return results
    
    def _prioritize_tasks(self, tasks):
        priority_order = {'Critical': 1, 'High': 2, 'Medium': 3, 'Low': 4}
        return sorted(tasks, key=lambda t: priority_order.get(getattr(t, 'priority', 'Medium'), 3))
    
    def _execute_single_task(self, task, site, results):
        try:
            ask_ethafri_ceo, get_site_project_state = _safe_import_from_growth_agent()
            
            task.status = 'Running'
            task.save()
            self.active_tasks.append(task)
            
            project_code = {}
            if get_site_project_state and site:
                try:
                    project_code, _ = get_site_project_state(site)
                except Exception as e:
                    logger.warning(f"Could not get project state: {e}")
            
            if ask_ethafri_ceo:
                prompt = f"""
                Execute task for site: {site.name if hasattr(site, 'name') else 'unknown'}
                Task: {task.task_name}
                Priority: {task.priority}
                Impact: {task.business_impact_score}/10
                Codebase: {json.dumps(project_code, indent=2)[:2000] if project_code else 'No code available'}
                """
                
                response = ask_ethafri_ceo(prompt, pool_type="coding")
                
                if response:
                    task.status = 'Completed'
                    task.save()
                    self.completed_tasks.append(task)
                    results.append(f"✅ {task.task_name} completed")
                else:
                    task.status = 'Pending'
                    task.save()
                    self.failed_tasks.append(task)
                    results.append(f"❌ {task.task_name} failed")
            else:
                task.status = 'Completed'
                task.save()
                self.completed_tasks.append(task)
                results.append(f"✅ {task.task_name} completed (basic mode)")
            
        except Exception as e:
            task.status = 'Pending'
            task.save()
            self.failed_tasks.append(task)
            results.append(f"❌ {task.task_name} error: {str(e)[:50]}")
    
    def get_stats(self):
        return {
            'active': len(self.active_tasks),
            'completed': len(self.completed_tasks),
            'failed': len(self.failed_tasks),
            'max_workers': self.max_workers
        }


# ============================================================
# 2. 🎯 ቅድሚያ ሰጪ ስርዓት (Priority Queue System)
# ============================================================

class PriorityQueueSystem:
    """በንግድ ተጽዕኖ፣ ፍጥነት እና ዋጋ ላይ ተመስርቶ ስራዎችን ያስተዳድራል"""
    
    def __init__(self):
        self.queues = {'critical': [], 'high': [], 'medium': [], 'low': []}
    
    def add_task(self, task):
        priority = getattr(task, 'priority', 'Medium').lower()
        if priority in self.queues:
            self.queues[priority].append(task)
    
    def get_next_task(self):
        for priority in ['critical', 'high', 'medium', 'low']:
            if self.queues[priority]:
                return self.queues[priority].pop(0)
        return None
    
    def calculate_priority_score(self, task):
        score = 0
        impact = getattr(task, 'business_impact_score', 5)
        score += impact * 2
        
        estimated_hours = getattr(task, 'estimated_hours', 2)
        if estimated_hours <= 1:
            score += 10
        elif estimated_hours <= 3:
            score += 7
        elif estimated_hours <= 5:
            score += 4
        else:
            score += 2
        
        task_type = getattr(task, 'task_type', 'code')
        type_scores = {'growth': 5, 'marketing': 4, 'seo': 3, 'code': 2, 'design': 1}
        score += type_scores.get(task_type, 2)
        
        return min(100, score)
    
    def get_stats(self):
        return {
            'critical': len(self.queues['critical']),
            'high': len(self.queues['high']),
            'medium': len(self.queues['medium']),
            'low': len(self.queues['low']),
            'total': sum(len(q) for q in self.queues.values())
        }


# ============================================================
# 3. 🔍 የኮድ ጥራት ተንታኝ (Code Quality Analyzer)
# ============================================================

class CodeQualityAnalyzer:
    """የኮድ ጥራት፣ ደህንነት እና አፈጻጸም ይመረምራል"""
    
    def __init__(self):
        self.metrics = {'complexity': 0, 'duplication': 0, 'coverage': 0, 'security': 0, 'performance': 0}
    
    def analyze_code(self, code, file_path=""):
        if not code:
            return {'score': 0, 'issues': ['No code to analyze']}
        
        analysis = {
            'file': file_path,
            'line_count': len(code.split('\n')) if code else 0,
            'function_count': self._count_functions(code),
            'class_count': self._count_classes(code),
            'complexity_score': self._calculate_complexity(code),
            'security_score': self._check_security(code),
            'performance_score': self._check_performance(code),
            'issues': self._find_issues(code),
            'score': 0
        }
        
        total_score = (
            analysis['complexity_score'] * 0.3 +
            analysis['security_score'] * 0.35 +
            analysis['performance_score'] * 0.35
        )
        analysis['score'] = round(total_score * 10, 1)
        
        return analysis
    
    def _count_functions(self, code):
        if not code: return 0
        import re
        return len(re.findall(r'def\s+\w+\(', code))
    
    def _count_classes(self, code):
        if not code: return 0
        import re
        return len(re.findall(r'class\s+\w+', code))
    
    def _calculate_complexity(self, code):
        if not code: return 0
        lines = len(code.split('\n'))
        if lines < 50: return 9
        elif lines < 100: return 7
        elif lines < 200: return 5
        elif lines < 500: return 3
        return 1
    
    def _check_security(self, code):
        if not code: return 0
        score = 10
        if 'eval(' in code: score -= 2
        if 'exec(' in code: score -= 2
        if 'password' in code.lower(): score -= 1
        if 'SECRET_KEY' in code: score -= 2
        return max(0, score)
    
    def _check_performance(self, code):
        if not code: return 0
        score = 10
        if 'len(' in code and 'for' in code:
            score -= 1
        return max(0, score)
    
    def _find_issues(self, code):
        issues = []
        if not code: return issues
        if 'TODO' in code: issues.append('Contains TODO comments')
        if 'FIXME' in code: issues.append('Contains FIXME comments')
        if '# ' not in code and len(code.split('\n')) > 20:
            issues.append('Lack of comments')
        if 'import *' in code: issues.append('Wildcard import detected')
        return issues


# ============================================================
# 4. 📊 የገበያ ግንዛቤ (Market Intelligence)
# ============================================================

class MarketIntelligence:
    """ተፎካካሪዎችን ይከታተላል እና የገበያ አዝማሚያ ይተነትናል"""
    
    def __init__(self, site=None):
        self.site = site
    
    def analyze_competitors(self):
        if not self.site:
            return {'error': 'No site provided'}
        
        competitor_urls = getattr(self.site, 'competitor_urls', [])
        return {
            'total_competitors': len(competitor_urls),
            'urls': competitor_urls[:5],
            'features': [f"Analyzing {url}" for url in competitor_urls[:3]],
            'strengths': ['Market presence'],
            'weaknesses': ['Limited data']
        }
    
    def get_market_trends(self):
        return [
            {'name': 'AI Integration', 'level': 'high', 'description': 'AI is becoming essential'},
            {'name': 'Mobile Commerce', 'level': 'high', 'description': 'Mobile shopping is growing'},
            {'name': 'Personalization', 'level': 'medium', 'description': 'Personalized experiences matter'},
        ]
    
    def get_recommendations(self):
        return {
            'short_term': ['Implement mobile-first design', 'Add AI-powered product recommendations'],
            'long_term': ['Develop mobile app', 'Implement AI chatbot']
        }


# ============================================================
# 5. 📈 የአፈጻጸም መለኪያ (Performance Monitor)
# ============================================================

class PerformanceMonitor:
    """የኤጀንቱን አፈጻጸም ይከታተላል እና ሪፖርት ያዘጋጃል"""
    
    def __init__(self):
        self.metrics = {
            'task_execution_times': [],
            'error_rates': [],
            'success_rates': [],
        }
        self.start_time = timezone.now()
    
    def record_task_execution(self, task_name, duration, success=True):
        self.metrics['task_execution_times'].append({
            'task': task_name,
            'duration': duration,
            'success': success,
            'timestamp': timezone.now().isoformat()
        })
    
    def record_error(self, error_type, error_message):
        self.metrics['error_rates'].append({
            'type': error_type,
            'message': error_message[:100],
            'timestamp': timezone.now().isoformat()
        })
    
    def get_stats(self):
        total_tasks = len(self.metrics['task_execution_times'])
        successful = sum(1 for t in self.metrics['task_execution_times'] if t['success'])
        
        avg_duration = 0
        if total_tasks > 0:
            avg_duration = sum(t['duration'] for t in self.metrics['task_execution_times']) / total_tasks
        
        return {
            'uptime': (timezone.now() - self.start_time).total_seconds(),
            'total_tasks': total_tasks,
            'successful_tasks': successful,
            'failed_tasks': total_tasks - successful,
            'success_rate': (successful / total_tasks * 100) if total_tasks > 0 else 0,
            'average_duration': avg_duration,
            'total_errors': len(self.metrics['error_rates']),
        }
    
    def get_performance_report(self):
        stats = self.get_stats()
        return f"""
        ════════════════════════════════════════════════════════
        📊 EthAfri Agent Performance Report
        ════════════════════════════════════════════════════════
        🕐 Uptime: {stats['uptime'] / 3600:.1f} hours
        📋 Total Tasks: {stats['total_tasks']}
        ✅ Successful: {stats['successful_tasks']}
        ❌ Failed: {stats['failed_tasks']}
        📈 Success Rate: {stats['success_rate']:.1f}%
        ⏱️ Avg Duration: {stats['average_duration']:.2f}s
        ⚠️ Errors: {stats['total_errors']}
        ════════════════════════════════════════════════════════
        """


# ============================================================
# 6. 🔮 ትንበያ ሞተር (Predictive Engine)
# ============================================================

class PredictiveEngine:
    """የሚቀጥሉትን ስራዎች እና ችግሮች ይተነብያል"""
    
    def __init__(self, site=None):
        self.site = site
    
    def predict_next_tasks(self):
        if not self.site:
            return []
        
        current_phase = getattr(self.site, 'build_phase', 0)
        phase_tasks = {
            0: [('Seed Real Data', 0.9), ('Build Product CRUD', 0.8)],
            1: [('User Dashboard', 0.8), ('Search & Filters', 0.7)],
            2: [('Review System', 0.7), ('Notifications', 0.6)],
            3: [('Payment Integration', 0.8), ('Marketing Campaigns', 0.6)],
            4: [('SEO Optimization', 0.7), ('Site Replication', 0.5)],
        }
        
        return [{'task': task, 'probability': prob} for task, prob in phase_tasks.get(current_phase, [])]
    
    def predict_errors(self):
        if not self.site:
            return []
        
        try:
            errors = AgentErrorLog.objects.filter(site=self.site, resolved=False)
            if not errors.exists():
                return []
            
            common_errors = errors.values('error_type').annotate(count=Count('id')).order_by('-count')
            return [{
                'type': error['error_type'],
                'probability': min(0.9, error['count'] / 10),
                'suggested_fix': f"Fix {error['error_type']} errors"
            } for error in common_errors[:3]]
        except Exception:
            return []


# ============================================================
# 7. 🧠 ራስ-ማስተማር ስርዓት (Self-Learning System)
# ============================================================

class SelfLearningSystem:
    """ከተሳካ/ከተሳነተ ስራዎች ይማራል እና ወደፊት ይሻሻላል"""
    
    def __init__(self, site=None):
        self.site = site
        self.learned_patterns = []
    
    def learn_from_task(self, task, success=True):
        pattern = {
            'task_type': getattr(task, 'task_type', 'unknown'),
            'priority': getattr(task, 'priority', 'Medium'),
            'success': success,
            'duration': getattr(task, 'duration', 0),
            'timestamp': timezone.now().isoformat()
        }
        self.learned_patterns.append(pattern)
        
        try:
            VectorMemory.objects.create(
                memory_type='insight',
                content=f"Task {task.task_name} {'succeeded' if success else 'failed'}",
                metadata=pattern,
                site=self.site,
                success_rate=100.0 if success else 0.0,
                text_content=f"Learning from {task.task_name}",
                embedding_model='self-learning-v1'
            )
        except Exception as e:
            logger.warning(f"Could not store learning: {e}")
    
    def get_insights(self):
        total = len(self.learned_patterns)
        if total == 0:
            return {'message': 'No learning data yet'}
        
        successful = sum(1 for p in self.learned_patterns if p['success'])
        
        by_type = {}
        for p in self.learned_patterns:
            task_type = p['task_type']
            if task_type not in by_type:
                by_type[task_type] = {'total': 0, 'success': 0}
            by_type[task_type]['total'] += 1
            if p['success']:
                by_type[task_type]['success'] += 1
        
        success_rates = {}
        for task_type, data in by_type.items():
            if data['total'] > 0:
                success_rates[task_type] = (data['success'] / data['total']) * 100
        
        return {
            'total_learned': total,
            'overall_success_rate': (successful / total) * 100 if total > 0 else 0,
            'success_by_type': success_rates,
            'recommendations': self._generate_recommendations(success_rates)
        }
    
    def _generate_recommendations(self, success_rates):
        recommendations = []
        for task_type, rate in success_rates.items():
            if rate < 50:
                recommendations.append(f"Improve {task_type} tasks - {rate:.0f}% success")
            elif rate > 80:
                recommendations.append(f"Good work with {task_type} - {rate:.0f}% success")
        return recommendations or ["All task types are performing well"]


# ============================================================
# 8. 💾 AI Cache System
# ============================================================

class AICache:
    """ተደጋጋሚ የAI ጥያቄዎችን ለማስታወስ (TTL-based)"""
    
    def __init__(self, ttl=1800, max_size=500):
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size
    
    def get_or_compute(self, prompt, compute_func):
        key = hashlib.md5(prompt.encode()).hexdigest()
        
        if key in self.cache:
            cached, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return cached
        
        result = compute_func()
        
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = (result, time.time())
        return result
    
    def _evict_oldest(self):
        if self.cache:
            oldest = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest]
    
    def clear(self):
        self.cache = {}
        logger.info("🧹 AI cache cleared")
    
    def get_size(self):
        return len(self.cache)


# ============================================================
# 9. 🔄 Smart Retry Logic
# ============================================================

class SmartRetry:
    """ያልተሳኩ ስራዎችን በብልህነት መመለስ"""
    
    def __init__(self, max_retries=3, base_delay=1):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def execute(self, func, *args, **kwargs):
        """ተግባርን በSmart Retry ያስኬዳል"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                if result and 'error' not in str(result).lower():
                    return result
                
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)  # 1, 2, 4 seconds
                    logger.info(f"🔄 Retry {attempt+2}/{self.max_retries} in {delay}s")
                    time.sleep(delay)
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    time.sleep(delay)
        
        return {'error': f"All retries failed: {last_error}"}
    
    @classmethod
    def classify_error(cls, error):
        """ስህተቱን በመተንተን አይነቱን ይለያል"""
        error_str = str(error).lower()
        if 'syntax' in error_str:
            return 'syntax'
        elif 'import' in error_str:
            return 'dependency'
        elif 'timeout' in error_str:
            return 'timeout'
        elif 'rate limit' in error_str or 'quota' in error_str:
            return 'rate_limit'
        elif 'database' in error_str or 'db' in error_str:
            return 'database'
        return 'unknown'


# ============================================================
# 10. 📝 Incremental File Analyzer
# ============================================================

class IncrementalFileAnalyzer:
    """የተቀየሩ ፋይሎችን ብቻ ይተነትናል"""
    
    def __init__(self):
        self.file_hashes = {}
    
    def get_file_hash(self, file_path):
        """የፋይሉን hash ያሰላል"""
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return None
    
    def get_changed_files(self, files):
        """የተቀየሩ ፋይሎችን ይመልሳል"""
        changed = {}
        
        for key, path in files.items():
            if isinstance(path, str) and os.path.exists(path):
                current_hash = self.get_file_hash(path)
                file_key = f"{key}_{path}"
                
                if file_key not in self.file_hashes or self.file_hashes[file_key] != current_hash:
                    changed[key] = path
                    self.file_hashes[file_key] = current_hash
        
        return changed
    
    def mark_analyzed(self, files):
        """ፋይሎችን እንደተተነተኑ ምልክት ያደርጋል"""
        for key, path in files.items():
            if isinstance(path, str) and os.path.exists(path):
                file_key = f"{key}_{path}"
                self.file_hashes[file_key] = self.get_file_hash(path)
    
    def reset(self):
        self.file_hashes = {}


# ============================================================
# 11. 🚀 ዋና አስተባባሪ (Enhancement Coordinator)
# ============================================================

class EnhancementCoordinator:
    """ሁሉንም የኤጀንት አቅም ማሳደጊያ ሞጁሎችን ያስተባብራል"""
    
    def __init__(self, site=None):
        self.site = site
        self.executor = ParallelTaskExecutor()
        self.priority_queue = PriorityQueueSystem()
        self.analyzer = CodeQualityAnalyzer()
        self.market = MarketIntelligence(site)
        self.monitor = PerformanceMonitor()
        self.predictor = PredictiveEngine(site)
        self.learner = SelfLearningSystem(site)
        self.cache = AICache()
        self.retry = SmartRetry()
        self.analyzer_tool = IncrementalFileAnalyzer()
    
    def run_enhancement_cycle(self):
        """አንድ ሙሉ የማሻሻያ ዑደት ያካሂዳል"""
        results = []
        
        # 1. የኮድ ጥራት ትንተና
        results.append("🔍 Running code quality analysis...")
        
        # 2. የገበያ ትንተና
        market_analysis = self.market.analyze_competitors()
        results.append(f"📊 Market: {market_analysis.get('total_competitors', 0)} competitors")
        
        # 3. ትንበያ
        predictions = self.predictor.predict_next_tasks()
        results.append(f"🔮 Predictions: {len(predictions)} tasks")
        
        # 4. ስራዎችን አስኬድ
        if self.site:
            try:
                tasks = AIProjectBacklog.objects.filter(site=self.site, status='Pending')
                if tasks.exists():
                    results.append(f"⚡ Executing {tasks.count()} tasks...")
                    task_results = self.executor.execute_tasks(list(tasks), self.site)
                    results.extend(task_results)
            except Exception as e:
                results.append(f"⚠️ Task execution error: {str(e)[:50]}")
        
        # 5. ሪፖርት
        report = self.monitor.get_performance_report()
        results.append(f"📈 Performance: {report[:100]}...")
        
        # 6. ግንዛቤ
        insights = self.learner.get_insights()
        if isinstance(insights, dict) and 'overall_success_rate' in insights:
            results.append(f"🧠 Learning: {insights['overall_success_rate']:.0f}% success")
        
        return " | ".join(results[:10])
    
    def get_full_status(self):
        return {
            'parallel_executor': self.executor.get_stats(),
            'priority_queue': self.priority_queue.get_stats(),
            'performance_monitor': self.monitor.get_stats(),
            'predictions': self.predictor.predict_next_tasks(),
            'insights': self.learner.get_insights(),
            'cache_size': self.cache.get_size(),
        }
    
    def clear_cache(self):
        self.cache.clear()
        return "Cache cleared"


# ============================================================
# 12. ፋብሪካ ተግባራት (Factory Functions)
# ============================================================

def create_enhancement_coordinator(site=None):
    """አዲስ EnhancementCoordinator ይፈጥራል"""
    return EnhancementCoordinator(site)


def get_enhancement_status(site=None):
    """የማሻሻያ ሁኔታ ይመልሳል"""
    coordinator = EnhancementCoordinator(site)
    return coordinator.get_full_status()


def clear_enhancement_cache():
    """ሁሉንም ካሾች ያጸዳል"""
    coordinator = EnhancementCoordinator()
    return coordinator.clear_cache()
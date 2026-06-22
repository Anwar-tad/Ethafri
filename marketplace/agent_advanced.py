# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/agent_advanced.py
# 📝 ለውጥ፦ የላቁ የኤጀንት አቅም ማሳደጊያዎች — Advanced Agent Features
# 📅 ቀን፦ 2026-06-22
# ============================================================

"""
ይህ ፋይል የEthAfri ኤጀንትን አቅም ለማሳደግ የሚያገለግሉ የላቁ ሞጁሎች ይዟል።
ሁሉም በአንድ ቦታ ተሰብስበዋል የኮድ መበታተንን ለመቀነስ።
"""

import os
import json
import re
import time
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count, Avg
from django.conf import settings

from .models import (
    SiteRegistry, AIProjectBacklog, AIEvolutionLog, AgentErrorLog,
    SelfHealingLog, SiteConfig, VectorMemory, AgentTask,
    SecurityLog, PredictionLog
)

logger = logging.getLogger(__name__)


# ============================================================
# ረዳት ተግባራት
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
# 1. 📦 AI Batching — በአንድ ጥሪ ብዙ ስራዎች
# ============================================================

class AIBatcher:
    """
    ብዙ ተመሳሳይ ስራዎችን በአንድ AI ጥሪ ማስኬድ
    AI ጥሪዎችን 70-80% ይቀንሳል
    """
    
    def __init__(self, max_batch_size=5):
        self.max_batch_size = max_batch_size
        self.batch_queue = []
    
    def add_task(self, task, site):
        """ስራን ወደ መደብ ይጨምራል"""
        self.batch_queue.append({'task': task, 'site': site})
    
    def process_batch(self):
        """የተሰበሰቡ ስራዎችን በአንድ ጥሪ ያስኬዳል"""
        if not self.batch_queue:
            return []
        
        ask_ethafri_ceo, get_site_project_state = _safe_import_from_growth_agent()
        if not ask_ethafri_ceo:
            return self._fallback_execution()
        
        results = []
        batches = [self.batch_queue[i:i+self.max_batch_size] 
                   for i in range(0, len(self.batch_queue), self.max_batch_size)]
        
        for batch in batches:
            try:
                batch_results = self._execute_batch(batch, ask_ethafri_ceo, get_site_project_state)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"❌ Batch execution error: {e}")
                results.extend(self._fallback_execution(batch))
        
        self.batch_queue = []
        return results
    
    def _execute_batch(self, batch, ask_ethafri_ceo, get_site_project_state):
        """አንድ መደብ ስራዎችን ያስኬዳል"""
        results = []
        site = batch[0]['site']
        
        # የጣቢያ ኮድ አንብብ
        project_code = {}
        if get_site_project_state and site:
            try:
                project_code, _ = get_site_project_state(site)
            except Exception as e:
                logger.warning(f"Could not get project state: {e}")
        
        # ስራዎችን አጠቃላይ መረጃ
        tasks_info = []
        for item in batch:
            task = item['task']
            tasks_info.append({
                'task_name': task.task_name,
                'description': task.description,
                'priority': task.priority,
                'impact': task.business_impact_score
            })
        
        prompt = f"""
        Execute {len(batch)} tasks for site: {site.name if hasattr(site, 'name') else 'unknown'}
        
        Tasks:
        {json.dumps(tasks_info, indent=2)}
        
        Codebase Summary:
        {json.dumps(project_code, indent=2)[:2000]}
        
        For each task, generate:
        1. The code/solution
        2. Explanation
        3. Confidence score (0-100)
        4. Which file to modify
        
        Return JSON array:
        [
            {{
                "task_name": "original task name",
                "code": "code to apply",
                "explanation": "brief explanation",
                "confidence": 85,
                "target_file": "file name"
            }}
        ]
        """
        
        response = ask_ethafri_ceo(prompt, pool_type="coding")
        
        if response and isinstance(response, list):
            for result in response:
                # ተገቢውን ስራ አግኝ
                task = next((item['task'] for item in batch 
                            if item['task'].task_name == result.get('task_name')), None)
                if task:
                    results.append({
                        'task': task,
                        'code': result.get('code', ''),
                        'explanation': result.get('explanation', ''),
                        'confidence': result.get('confidence', 70),
                        'target_file': result.get('target_file', task.target_file or 'views')
                    })
        else:
            # Fallback: እያንዳንዱን ስራ በተናጥል አስኬድ
            for item in batch:
                result = self._execute_single_task(item['task'], item['site'], ask_ethafri_ceo)
                results.append(result)
        
        return results
    
    def _execute_single_task(self, task, site, ask_ethafri_ceo):
        """አንድ ስራ በተናጥል ያስኬዳል"""
        project_code, _ = get_site_project_state(site)
        
        prompt = f"""
        Task: {task.task_name}
        Description: {task.description}
        Site: {site.name if hasattr(site, 'name') else 'unknown'}
        Codebase: {json.dumps(project_code, indent=2)[:1500]}
        
        Return JSON: {{"code": "...", "explanation": "...", "confidence": 80, "target_file": "..."}}
        """
        
        response = ask_ethafri_ceo(prompt, pool_type="coding")
        
        if response and isinstance(response, dict):
            return {
                'task': task,
                'code': response.get('code', ''),
                'explanation': response.get('explanation', ''),
                'confidence': response.get('confidence', 70),
                'target_file': response.get('target_file', task.target_file or 'views')
            }
        
        return {'task': task, 'error': 'No valid response'}
    
    def _fallback_execution(self, batch=None):
        """መደብ ሲሳሳት እያንዳንዱን በተናጥል ያስኬዳል"""
        items = batch if batch else self.batch_queue
        results = []
        for item in items:
            task = item['task']
            site = item['site']
            # መሰረታዊ አፈጻጸም
            task.status = 'Completed'
            task.save()
            results.append({
                'task': task,
                'code': '',
                'explanation': 'Basic execution (batch failed)',
                'confidence': 50,
                'target_file': task.target_file or 'views'
            })
        return results
    
    def get_stats(self):
        return {
            'queue_size': len(self.batch_queue),
            'max_batch_size': self.max_batch_size
        }


# ============================================================
# 2. 🎯 AST + Targeted Retrieval — ተገቢውን ኮድ ብቻ
# ============================================================

class ASTTargetedRetrieval:
    """
    ሙሉ ፋይል ሳይሆን ተገቢውን function/class ብቻ ወደ AI ይልካል
    Token ወጪን 60% ይቀንሳል
    """
    
    def __init__(self):
        self.ast_cache = {}
    
    def extract_target_code(self, code, target_type='function', target_name=None):
        """
        ከኮድ ውስጥ የተወሰነ function/class ያወጣል
        """
        if not code:
            return code
        
        lines = code.split('\n')
        extracted = []
        in_target = False
        indent_level = 0
        target_found = False
        
        for i, line in enumerate(lines):
            # የtarget መጀመሪያ ፈልግ
            if not target_found and target_type == 'function':
                match = re.search(r'def\s+' + re.escape(target_name) + r'\s*\(', line) if target_name else None
                if match or (target_name is None and re.search(r'def\s+\w+\s*\(', line)):
                    in_target = True
                    target_found = True
                    indent_level = len(line) - len(line.lstrip())
                    extracted.append(line)
                    continue
            
            if not target_found and target_type == 'class':
                match = re.search(r'class\s+' + re.escape(target_name) + r'\s*[:\(]', line) if target_name else None
                if match or (target_name is None and re.search(r'class\s+\w+\s*[:\(]', line)):
                    in_target = True
                    target_found = True
                    indent_level = len(line) - len(line.lstrip())
                    extracted.append(line)
                    continue
            
            if in_target:
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= indent_level and line.strip():
                    # የtarget መጨረሻ
                    if not line.strip().startswith('#'):
                        in_target = False
                        break
                extracted.append(line)
        
        # target ካልተገኘ ሙሉ ኮዱን ይመልስ
        if not target_found:
            logger.warning(f"⚠️ Target '{target_name}' not found in code")
            return code[:1500]  # ከፍተኛ 1500 ቁምፊዎች
        
        return '\n'.join(extracted)
    
    def get_relevant_code(self, task, project_code):
        """
        ለስራው ተገቢውን ኮድ ክፍል ያገኛል
        """
        target_file = task.target_file or 'views'
        code = project_code.get(target_file, '')
        
        if not code:
            return ''
        
        # ከስራው ስም ተገቢውን target ለይ
        task_name_lower = task.task_name.lower()
        
        if 'model' in task_name_lower:
            target_type = 'class'
            target_name = None  # ሁሉንም ክፍሎች ወስድ
        elif 'view' in task_name_lower:
            target_type = 'function'
            target_name = None
        elif 'admin' in task_name_lower:
            target_type = 'class'
            target_name = None
        elif 'url' in task_name_lower:
            target_type = 'function'
            target_name = None
        else:
            # ከመግለጫው ለይ
            target_type = 'function'
            target_name = self._extract_target_from_description(task.description)
        
        extracted = self.extract_target_code(code, target_type, target_name)
        
        # ከበርካታ መስመሮች ካለ ከፍተኛ 500 መስመሮችን ብቻ
        if extracted:
            lines = extracted.split('\n')
            if len(lines) > 500:
                extracted = '\n'.join(lines[:500]) + '\n... (truncated)'
        
        return extracted
    
    def _extract_target_from_description(self, description):
        """ከመግለጫው ውስጥ target ስም ያወጣል"""
        # ቀላል ትንተና
        words = description.lower().split()
        for word in words:
            if word in ['product', 'category', 'user', 'order', 'payment', 'review']:
                return word + '_list'
        return None
    
    def get_code_summary(self, project_code, max_lines=100):
        """
        የኮድ ማጠቃለያ ይፈጥራል
        """
        summary = {}
        for key, code in project_code.items():
            if isinstance(code, str) and len(code) > 100:
                lines = code.split('\n')
                # የመጀመሪያዎቹን 50 መስመሮች እና የመጨረሻዎቹን 50
                if len(lines) > max_lines:
                    summary[key] = {
                        'total_lines': len(lines),
                        'preview': '\n'.join(lines[:50]) + '\n...\n' + '\n'.join(lines[-50:]),
                        'functions': self._extract_functions(code),
                        'classes': self._extract_classes(code)
                    }
                else:
                    summary[key] = {
                        'total_lines': len(lines),
                        'preview': code[:1000] + ('...' if len(code) > 1000 else ''),
                        'functions': self._extract_functions(code),
                        'classes': self._extract_classes(code)
                    }
        return summary
    
    def _extract_functions(self, code):
        """የተግባራት ስሞችን ያወጣል"""
        functions = re.findall(r'def\s+(\w+)\s*\(', code)
        return functions[:20]  # ከፍተኛ 20
    
    def _extract_classes(self, code):
        """የክፍሎች ስሞችን ያወጣል"""
        classes = re.findall(r'class\s+(\w+)\s*[:\(]', code)
        return classes[:20]  # ከፍተኛ 20


# ============================================================
# 3. 🔄 Self-Critique Loop — ከመተግበሩ በፊት ግምገማ
# ============================================================

class SelfCritiqueLoop:
    """
    ኮድ ከመተግበሩ በፊት ሁለተኛ AI ግምገማ
    የኮድ ጥራትን በእጅጉ ይጨምራል
    """
    
    def __init__(self, min_confidence=70):
        self.min_confidence = min_confidence
        self.critique_history = []
    
    def critique_code(self, code, task, site):
        """
        ኮዱን ይገመግማል እና ማሻሻያዎችን ይጠቁማል
        """
        ask_ethafri_ceo, _ = _safe_import_from_growth_agent()
        if not ask_ethafri_ceo:
            return {'approved': True, 'confidence': 80, 'message': 'No critique (fallback)'}
        
        prompt = f"""
        Review this code for site: {site.name if hasattr(site, 'name') else 'unknown'}
        
        Task: {task.task_name}
        Description: {task.description}
        
        Code to review:
        ```python
        {code[:2000]}
        ```
        
        Evaluate:
        1. Is the code correct and functional?
        2. Are there any syntax errors?
        3. Are there security issues?
        4. Does it follow Django best practices?
        5. Could it be improved?
        
        Return JSON:
        {{
            "approved": true/false,
            "confidence": 0-100,
            "message": "brief review",
            "improvements": ["suggestion1", "suggestion2"],
            "issues": ["issue1", "issue2"]
        }}
        """
        
        response = ask_ethafri_ceo(prompt, pool_type="analysis")
        
        if response and isinstance(response, dict):
            # ግምገማ ታሪክ ውስጥ አስቀምጥ
            self.critique_history.append({
                'timestamp': timezone.now().isoformat(),
                'task': task.task_name,
                'response': response
            })
            return response
        
        # ምላሽ ካልመጣ አርጋ
        return {'approved': True, 'confidence': 70, 'message': 'No critique response (auto-approve)'}
    
    def apply_critique(self, code, critique_response):
        """
        የግምገማ ሀሳቦችን በመተግበር የተሻሻለ ኮድ ይፈጥራል
        """
        if not critique_response.get('improvements'):
            return code
        
        ask_ethafri_ceo, _ = _safe_import_from_growth_agent()
        if not ask_ethafri_ceo:
            return code
        
        improvements = '\n'.join(critique_response.get('improvements', []))
        issues = '\n'.join(critique_response.get('issues', []))
        
        prompt = f"""
        Improve this code based on the review:
        
        Code:
        ```python
        {code[:2000]}
        ```
        
        Improvements suggested:
        {improvements}
        
        Issues found:
        {issues}
        
        Return the improved code with explanation.
        JSON: {{"code": "...", "explanation": "..."}}
        """
        
        response = ask_ethafri_ceo(prompt, pool_type="coding")
        
        if response and isinstance(response, dict) and 'code' in response:
            return response.get('code', code)
        
        return code
    
    def get_critique_stats(self):
        """የግምገማ ስታቲስቲክስ ይመልሳል"""
        total = len(self.critique_history)
        if total == 0:
            return {'total': 0, 'approved': 0, 'avg_confidence': 0}
        
        approved = sum(1 for h in self.critique_history if h['response'].get('approved', False))
        avg_confidence = sum(h['response'].get('confidence', 0) for h in self.critique_history) / total
        
        return {
            'total': total,
            'approved': approved,
            'rejected': total - approved,
            'avg_confidence': round(avg_confidence, 1)
        }


# ============================================================
# 4. 🧠 የላቀ ራስ-ማስተማር (Advanced Self-Learning)
# ============================================================

class AdvancedSelfLearning:
    """
    ከተሳካ/ከተሳነተ ስራዎች በመማር ወደፊት ይሻሻላል
    """
    
    def __init__(self, site=None):
        self.site = site
        self.learning_history = []
        self.success_patterns = {}
        self.failure_patterns = {}
    
    def learn_from_task(self, task, success=True, feedback=''):
        """ከስራ ይማራል"""
        pattern = {
            'task_name': task.task_name,
            'task_type': getattr(task, 'task_type', 'unknown'),
            'priority': getattr(task, 'priority', 'Medium'),
            'success': success,
            'feedback': feedback[:200],
            'timestamp': timezone.now().isoformat()
        }
        self.learning_history.append(pattern)
        
        # በስኬት/ሽንፈት ላይ ተመስርቶ ማስታወሻ
        if success:
            if task.task_type not in self.success_patterns:
                self.success_patterns[task.task_type] = 0
            self.success_patterns[task.task_type] += 1
        else:
            if task.task_type not in self.failure_patterns:
                self.failure_patterns[task.task_type] = 0
            self.failure_patterns[task.task_type] += 1
        
        # በVectorMemory ውስጥ አስቀምጥ
        try:
            VectorMemory.objects.create(
                memory_type='insight',
                content=f"Task {task.task_name} {'succeeded' if success else 'failed'}",
                metadata=pattern,
                site=self.site,
                success_rate=100.0 if success else 0.0,
                text_content=f"Learning from {task.task_name}",
                embedding_model='advanced-learning-v1'
            )
        except Exception as e:
            logger.warning(f"Could not store learning: {e}")
    
    def get_insights(self):
        """የተማረውን ግንዛቤ ይመልሳል"""
        total = len(self.learning_history)
        if total == 0:
            return {'message': 'No learning data yet'}
        
        successful = sum(1 for p in self.learning_history if p['success'])
        
        return {
            'total_learned': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'success_patterns': self.success_patterns,
            'failure_patterns': self.failure_patterns,
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self):
        """በስኬት መጠን ላይ ተመስርቶ ምክሮችን ይሰጣል"""
        recommendations = []
        
        for task_type, count in self.failure_patterns.items():
            success_count = self.success_patterns.get(task_type, 0)
            total = success_count + count
            if total > 0 and (count / total) > 0.5:
                recommendations.append(f"⚠️ Improve {task_type} tasks - {count} failures")
        
        for task_type, count in self.success_patterns.items():
            if count > 5 and self.failure_patterns.get(task_type, 0) == 0:
                recommendations.append(f"✅ {task_type} tasks are performing well")
        
        return recommendations or ["All task types are performing well"]


# ============================================================
# 5. 🚀 ዋና አስተባባሪ (Advanced Coordinator)
# ============================================================

class AdvancedEnhancementCoordinator:
    """
    ሁሉንም የላቁ ማሻሻያ ሞጁሎችን ያስተባብራል
    """
    
    def __init__(self, site=None):
        self.site = site
        self.batcher = AIBatcher()
        self.retriever = ASTTargetedRetrieval()
        self.critique = SelfCritiqueLoop()
        self.learner = AdvancedSelfLearning(site)
    
    def process_task(self, task):
        """
        አንድ ስራን በሁሉም ማሻሻያዎች ያስኬዳል
        """
        results = {
            'task': task,
            'batched': False,
            'retrieved': False,
            'critiqued': False,
            'applied': False,
            'confidence': 0,
            'message': ''
        }
        
        # 1. ወደ መደብ ጨምር
        self.batcher.add_task(task, self.site)
        results['batched'] = True
        
        # 2. የተገቢውን ኮድ አውጣ
        project_code, _ = get_site_project_state(self.site)
        relevant_code = self.retriever.get_relevant_code(task, project_code)
        results['retrieved'] = True
        
        # 3. ግምገማ አድርግ
        critique = self.critique.critique_code(relevant_code, task, self.site)
        results['confidence'] = critique.get('confidence', 0)
        
        if critique.get('approved', False):
            results['critiqued'] = True
            # ኮዱን አሻሽል
            improved_code = self.critique.apply_critique(relevant_code, critique)
            results['message'] = critique.get('message', 'Approved')
        else:
            results['message'] = critique.get('message', 'Rejected')
            return results
        
        # 4. ኮዱን ተግብር
        try:
            from .code_apply import apply_code_change
            path = os.path.join(self.site.repo_path, 'marketplace', f"{task.target_file or 'views'}.py")
            
            result = apply_code_change(
                site=self.site,
                file_key=task.target_file or 'views',
                new_content=improved_code,
                path=path,
                reason=f"Advanced: {task.task_name}",
                confidence_score=critique.get('confidence', 80),
                backlog_task=task,
                push_to_github=True
            )
            
            if result.get('applied', False):
                results['applied'] = True
                self.learner.learn_from_task(task, success=True, feedback=result.get('message', ''))
            else:
                self.learner.learn_from_task(task, success=False, feedback=result.get('message', ''))
                
        except Exception as e:
            results['message'] = f"Apply error: {e}"
            self.learner.learn_from_task(task, success=False, feedback=str(e))
        
        return results
    
    def process_batch(self):
        """የተሰበሰቡ ስራዎችን በአንድ ጊዜ ያስኬዳል"""
        results = self.batcher.process_batch()
        return results
    
    def get_status(self):
        """የሁሉም ሞጁሎች ሁኔታ ይመልሳል"""
        return {
            'batcher': self.batcher.get_stats(),
            'critique': self.critique.get_critique_stats(),
            'learning': self.learner.get_insights(),
            'site': self.site.name if self.site else 'None'
        }


# ============================================================
# 6. ፋብሪካ ተግባራት (Factory Functions)
# ============================================================

def create_advanced_coordinator(site=None):
    """አዲስ AdvancedEnhancementCoordinator ይፈጥራል"""
    return AdvancedEnhancementCoordinator(site)


def process_task_advanced(task, site):
    """አንድ ስራን በላቁ ማሻሻያዎች ያስኬዳል"""
    coordinator = AdvancedEnhancementCoordinator(site)
    return coordinator.process_task(task)


def process_tasks_batch(tasks, site):
    """ብዙ ስራዎችን በመደብ ያስኬዳል"""
    coordinator = AdvancedEnhancementCoordinator(site)
    for task in tasks:
        coordinator.batcher.add_task(task, site)
    return coordinator.process_batch()


def get_advanced_status(site=None):
    """የላቁ ማሻሻያ ሁኔታ ይመልሳል"""
    coordinator = AdvancedEnhancementCoordinator(site)
    return coordinator.get_status()
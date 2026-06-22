# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/selector.py
# 📝 ለውጥ፦ Cost-Aware Model Selection — Smart AI Model Router
# 📅 ቀን፦ 2026-06-22
# ============================================================

"""
ይህ ፋይል በስራ ክብደት እና ወጪ ላይ ተመስርቶ
ተገቢውን AI ሞዴል ይመርጣል።
ቀላል ስራዎች ርካሽ ሞዴል ይጠቀማሉ።
"""

import os
import json
import re
import time
import logging
import random
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================
# 1. የሞዴል ቅንብሮች (Model Configurations)
# ============================================================

class ModelRegistry:
    """
    የተለያዩ AI ሞዴሎችን መረጃ ይይዛል
    ወጪ፣ ፍጥነት፣ ጥራት እና አቅም
    """
    
    MODELS = {
        # ርካሽ እና ፈጣን ሞዴሎች (ለቀላል ስራዎች)
        'fast': {
            'name': 'gemini-2.5-flash',
            'provider': 'google',
            'cost_per_1k_tokens': 0.0001,
            'speed_score': 95,  # 0-100
            'quality_score': 70,
            'max_context': 128000,
            'best_for': ['translation', 'simple_analysis', 'quick_fix'],
            'api_key_env': 'GEMINI_API_KEY'
        },
        'groq': {
            'name': 'llama-3.3-70b-versatile',
            'provider': 'groq',
            'cost_per_1k_tokens': 0.0002,
            'speed_score': 90,
            'quality_score': 75,
            'max_context': 128000,
            'best_for': ['quick_code', 'simple_code', 'formatting'],
            'api_key_env': 'GROQ_API_KEY'
        },
        'github': {
            'name': 'meta-llama-3.1-405b-instruct',
            'provider': 'github',
            'cost_per_1k_tokens': 0.0003,
            'speed_score': 80,
            'quality_score': 85,
            'max_context': 128000,
            'best_for': ['medium_code', 'refactoring', 'documentation'],
            'api_key_env': 'GITHUB_TOKEN'
        },
        
        # መካከለኛ ሞዴሎች (ለአብዛኛዎቹ ስራዎች)
        'mistral': {
            'name': 'mistral-large-latest',
            'provider': 'mistral',
            'cost_per_1k_tokens': 0.0008,
            'speed_score': 75,
            'quality_score': 88,
            'max_context': 128000,
            'best_for': ['code', 'analysis', 'moderate_complexity'],
            'api_key_env': 'MISTRAL_API_KEY'
        },
        'openrouter': {
            'name': 'deepseek/deepseek-chat',
            'provider': 'openrouter',
            'cost_per_1k_tokens': 0.0006,
            'speed_score': 78,
            'quality_score': 85,
            'max_context': 128000,
            'best_for': ['code', 'analysis', 'moderate_complexity'],
            'api_key_env': 'OPENROUTER_API_KEY'
        },
        
        # ከፍተኛ ጥራት ሞዴሎች (ለከባድ ስራዎች)
        'premium': {
            'name': 'gemini-2.0-pro',
            'provider': 'google',
            'cost_per_1k_tokens': 0.0025,
            'speed_score': 60,
            'quality_score': 95,
            'max_context': 2000000,
            'best_for': ['complex_code', 'security_audit', 'architecture'],
            'api_key_env': 'GEMINI_API_KEY'
        },
        'huggingface': {
            'name': 'Qwen/Qwen2.5-72B-Instruct',
            'provider': 'huggingface',
            'cost_per_1k_tokens': 0.0020,
            'speed_score': 55,
            'quality_score': 90,
            'max_context': 128000,
            'best_for': ['complex_code', 'large_analysis', 'difficult_tasks'],
            'api_key_env': 'HUGGINGFACE_API_KEY'
        },
    }
    
    @classmethod
    def get_model(cls, model_key: str) -> Dict[str, Any]:
        """የሞዴል መረጃ ይመልሳል"""
        return cls.MODELS.get(model_key, cls.MODELS['mistral'])
    
    @classmethod
    def get_all_models(cls) -> Dict[str, Dict[str, Any]]:
        """ሁሉንም ሞዴሎች ይመልሳል"""
        return cls.MODELS
    
    @classmethod
    def get_available_models(cls) -> Dict[str, Dict[str, Any]]:
        """በአካባቢ ተለዋዋጮች ላይ ተመስርቶ የሚገኙ ሞዴሎችን ይመልሳል"""
        available = {}
        for key, model in cls.MODELS.items():
            env_key = model.get('api_key_env')
            if env_key and os.environ.get(env_key):
                available[key] = model
            elif not env_key:
                available[key] = model
        return available


# ============================================================
# 2. የስራ ክብደት ተንታኝ (Task Complexity Analyzer)
# ============================================================

class TaskComplexityAnalyzer:
    """
    የስራውን ክብደት ይተነትናል
    በዚህ ላይ ተመስርቶ ተገቢውን ሞዴል ይመርጣል
    """
    
    def __init__(self):
        self.complexity_weights = {
            'code_length': 0.15,
            'task_type': 0.25,
            'priority': 0.20,
            'impact': 0.20,
            'dependencies': 0.10,
            'security_sensitivity': 0.10,
        }
    
    def analyze(self, task) -> Dict[str, Any]:
        """
        የስራውን ክብደት ይተነትናል
        ውጤት: {'score': 0-100, 'level': 'low|medium|high|critical', 'details': {...}}
        """
        details = {}
        score = 0
        
        # 1. የኮድ ርዝመት
        code_length_score = self._analyze_code_length(task)
        details['code_length'] = code_length_score
        score += code_length_score * self.complexity_weights['code_length']
        
        # 2. የስራ ዓይነት
        task_type_score = self._analyze_task_type(task)
        details['task_type'] = task_type_score
        score += task_type_score * self.complexity_weights['task_type']
        
        # 3. ቅድሚያ
        priority_score = self._analyze_priority(task)
        details['priority'] = priority_score
        score += priority_score * self.complexity_weights['priority']
        
        # 4. ተጽዕኖ
        impact_score = self._analyze_impact(task)
        details['impact'] = impact_score
        score += impact_score * self.complexity_weights['impact']
        
        # 5. ጥገኞች
        dependency_score = self._analyze_dependencies(task)
        details['dependencies'] = dependency_score
        score += dependency_score * self.complexity_weights['dependencies']
        
        # 6. የደህንነት ስሜታዊነት
        security_score = self._analyze_security_sensitivity(task)
        details['security_sensitivity'] = security_score
        score += security_score * self.complexity_weights['security_sensitivity']
        
        # አጠቃላይ ውጤት (0-100)
        final_score = min(100, score)
        
        # ደረጃ
        if final_score < 25:
            level = 'low'
        elif final_score < 50:
            level = 'medium'
        elif final_score < 75:
            level = 'high'
        else:
            level = 'critical'
        
        return {
            'score': final_score,
            'level': level,
            'details': details
        }
    
    def _analyze_code_length(self, task) -> int:
        """የኮድ ርዝመት ትንተና"""
        # ከስራው መግለጫ ወይም ከተዛማጅ ፋይል ለይ
        description = getattr(task, 'description', '')
        length = len(description)
        
        if length < 100:
            return 10
        elif length < 500:
            return 30
        elif length < 1000:
            return 50
        elif length < 2000:
            return 70
        else:
            return 90
    
    def _analyze_task_type(self, task) -> int:
        """የስራ ዓይነት ትንተና"""
        task_type = getattr(task, 'task_type', 'code')
        
        type_scores = {
            'code': 50,
            'seo': 30,
            'marketing': 40,
            'growth': 45,
            'design': 35,
            'content': 25,
            'acquisition': 40,
        }
        
        return type_scores.get(task_type, 50)
    
    def _analyze_priority(self, task) -> int:
        """ቅድሚያ ትንተና"""
        priority = getattr(task, 'priority', 'Medium')
        
        priority_scores = {
            'Critical': 90,
            'High': 70,
            'Medium': 50,
            'Low': 30,
        }
        
        return priority_scores.get(priority, 50)
    
    def _analyze_impact(self, task) -> int:
        """ተጽዕኖ ትንተና"""
        impact = getattr(task, 'business_impact_score', 5)
        
        # 1-10 ወደ 10-100 ቀይር
        return impact * 10
    
    def _analyze_dependencies(self, task) -> int:
        """ጥገኞች ትንተና"""
        dependency = getattr(task, 'dependency', None)
        if dependency:
            return 70
        return 20
    
    def _analyze_security_sensitivity(self, task) -> int:
        """የደህንነት ስሜታዊነት ትንተና"""
        description = getattr(task, 'description', '').lower()
        task_name = getattr(task, 'task_name', '').lower()
        
        security_keywords = [
            'security', 'auth', 'password', 'secret', 'token',
            'permission', 'access', 'login', 'register', 'admin',
            'encryption', 'hash', 'salt', 'private', 'key'
        ]
        
        combined = description + ' ' + task_name
        
        score = 0
        for keyword in security_keywords:
            if keyword in combined:
                score += 10
        
        return min(100, score)


# ============================================================
# 3. ስማርት ሞዴል መራጭ (Smart Model Selector)
# ============================================================

class SmartModelSelector:
    """
    በስራ ክብደት ላይ ተመስርቶ ተገቢውን AI ሞዴል ይመርጣል
    ወጪን ይቀንሳል እና ጥራትን ያረጋግጣል
    """
    
    def __init__(self):
        self.complexity_analyzer = TaskComplexityAnalyzer()
        self.model_registry = ModelRegistry()
        self.selection_history = []
        self.cost_savings = {
            'total_saved': 0,
            'total_spent': 0,
            'selections': 0
        }
    
    def select_model(self, task, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        ለአንድ ስራ ተገቢውን ሞዴል ይመርጣል
        ውጤት: {'model_key': 'mistral', 'model': {...}, 'confidence': 85, 'reason': '...'}
        """
        # 1. የስራ ክብደት ትንተና
        complexity = self.complexity_analyzer.analyze(task)
        
        # 2. የሚገኙ ሞዴሎች
        available_models = self.model_registry.get_available_models()
        
        if not available_models:
            logger.warning("⚠️ No models available. Using fallback.")
            return {
                'model_key': 'fallback',
                'model': {'name': 'fallback', 'provider': 'local'},
                'confidence': 50,
                'reason': 'No models available'
            }
        
        # 3. በክብደት ላይ ተመስርቶ ሞዴል ምረጥ
        selected_key, selected_model, confidence, reason = self._select_based_on_complexity(
            complexity, available_models, context
        )
        
        # 4. ታሪክ ውስጥ አስቀምጥ
        self.selection_history.append({
            'timestamp': timezone.now().isoformat(),
            'task': getattr(task, 'task_name', 'unknown'),
            'complexity': complexity,
            'selected': selected_key,
            'confidence': confidence,
            'reason': reason
        })
        
        # 5. ወጪ ስታቲስቲክስ አዘምን
        if selected_model:
            self.cost_savings['selections'] += 1
            # ከፍተኛ ጥራት ሞዴል ባንጠቀም የተቀመጠ ወጪ
            premium_cost = ModelRegistry.MODELS.get('premium', {}).get('cost_per_1k_tokens', 0.0025)
            selected_cost = selected_model.get('cost_per_1k_tokens', 0.0005)
            if selected_cost < premium_cost:
                self.cost_savings['total_saved'] += (premium_cost - selected_cost) * 1000  # ግምታዊ
        
        return {
            'model_key': selected_key,
            'model': selected_model,
            'confidence': confidence,
            'reason': reason,
            'complexity': complexity
        }
    
    def _select_based_on_complexity(self, complexity, available_models, context):
        """
        በክብደት ላይ ተመስርቶ ሞዴል ይመርጣል
        """
        score = complexity.get('score', 50)
        level = complexity.get('level', 'medium')
        
        # በክብደት ደረጃ ላይ ተመስርቶ
        if level == 'low' or score < 30:
            # ቀላል ስራ — ፈጣን ሞዴል
            preferred = ['fast', 'groq', 'github']
            confidence = 80
            reason = f"Low complexity task (score: {score:.0f}) — using fast model"
        
        elif level == 'medium' or score < 55:
            # መካከለኛ ስራ — ሚዛናዊ ሞዴል
            preferred = ['mistral', 'openrouter', 'github']
            confidence = 85
            reason = f"Medium complexity task (score: {score:.0f}) — using balanced model"
        
        elif level == 'high' or score < 75:
            # ከባድ ስራ — ጥራት ያለው ሞዴል
            preferred = ['mistral', 'openrouter', 'premium']
            confidence = 88
            reason = f"High complexity task (score: {score:.0f}) — using quality model"
        
        else:
            # ወሳኝ ስራ — ከፍተኛ ጥራት ሞዴል
            preferred = ['premium', 'huggingface', 'mistral']
            confidence = 92
            reason = f"Critical complexity task (score: {score:.0f}) — using premium model"
        
        # የሚገኙትን ሞዴሎች በቅድሚያ ፈልግ
        for key in preferred:
            if key in available_models:
                return key, available_models[key], confidence, reason
        
        # ምንም ካልተገኘ የመጀመሪያውን
        first_key = list(available_models.keys())[0]
        return first_key, available_models[first_key], 60, "Fallback: using first available model"
    
    def get_stats(self) -> Dict[str, Any]:
        """የምርጫ ስታቲስቲክስ ይመልሳል"""
        return {
            'total_selections': len(self.selection_history),
            'cost_savings': self.cost_savings,
            'recent_selections': self.selection_history[-5:] if self.selection_history else [],
        }
    
    def get_recommendation(self, task) -> Dict[str, Any]:
        """ለአንድ ስራ ሞዴል ምክር ይሰጣል (ሳይመርጥ)"""
        complexity = self.complexity_analyzer.analyze(task)
        available = self.model_registry.get_available_models()
        
        # ከፍተኛ ጥራት ያለውን ሞዴል አግኝ
        best_model = None
        best_score = 0
        
        for key, model in available.items():
            quality = model.get('quality_score', 50)
            if quality > best_score:
                best_score = quality
                best_model = key
        
        # ርካሹን ሞዴል አግኝ
        cheapest_model = None
        cheapest_cost = float('inf')
        
        for key, model in available.items():
            cost = model.get('cost_per_1k_tokens', 0.001)
            if cost < cheapest_cost:
                cheapest_cost = cost
                cheapest_model = key
        
        return {
            'task_name': getattr(task, 'task_name', 'unknown'),
            'complexity': complexity,
            'recommended': {
                'best_quality': best_model,
                'cheapest': cheapest_model,
                'balanced': 'mistral' if 'mistral' in available else list(available.keys())[0]
            },
            'available_models': list(available.keys())
        }


# ============================================================
# 4. የተዋሃደ AI ጥሪ (Unified AI Call)
# ============================================================

class UnifiedAICall:
    """
    ስማርት ሞዴል መራጭን በመጠቀም
    ተገቢውን AI ሞዴል ይጠራል
    """
    
    def __init__(self):
        self.selector = SmartModelSelector()
        self.cache = {}
        self.stats = {
            'calls': 0,
            'cached': 0,
            'by_model': {},
            'errors': 0
        }
    
    def call(self, prompt: str, task=None, pool_type="coding", use_cache=True, **kwargs) -> Dict[str, Any]:
        """
        ስማርት ሞዴል መራጭ በመጠቀም AI ን ይጠራል
        """
        # 1. ካሽ ፍተሻ
        if use_cache:
            cache_key = hashlib.md5(prompt.encode()).hexdigest()
            if cache_key in self.cache:
                self.stats['cached'] += 1
                logger.debug("💾 Cache hit for prompt")
                return self.cache[cache_key]
        
        # 2. ስራ ካለ ሞዴል ምረጥ
        selected = None
        if task:
            selected = self.selector.select_model(task)
            logger.info(f"🤖 Selected model: {selected.get('model_key')} - {selected.get('reason')}")
        
        # 3. የሚጠቀመውን ሞዴል ወስን
        model_key = selected.get('model_key') if selected else 'mistral'
        model_config = selected.get('model') if selected else ModelRegistry.get_model('mistral')
        
        # 4. AI ጥሪ አድርግ
        try:
            # ከ growth_agent አስመጣ
            from .growth_agent import ask_ai_with_failover
            
            # በተመረጠው ሞዴል ጥራ
            result = ask_ai_with_failover(prompt, pool_type=pool_type, use_cache=use_cache)
            
            # ስታቲስቲክስ አዘምን
            self.stats['calls'] += 1
            if model_key not in self.stats['by_model']:
                self.stats['by_model'][model_key] = 0
            self.stats['by_model'][model_key] += 1
            
            # ካሽ ላይ አስቀምጥ
            if use_cache and result:
                self.cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"❌ AI call failed: {e}")
            self.stats['errors'] += 1
            
            # ፎልባክ: ሌላ ሞዴል ሞክር
            return self._fallback_call(prompt, pool_type)
    
    def _fallback_call(self, prompt: str, pool_type: str) -> Dict[str, Any]:
        """መደበኛ ፎልባክ ጥሪ"""
        from .growth_agent import ask_ai_with_failover
        return ask_ai_with_failover(prompt, pool_type=pool_type, use_cache=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """የጥሪ ስታቲስቲክስ ይመልሳል"""
        return {
            **self.stats,
            'cache_size': len(self.cache),
            'selector_stats': self.selector.get_stats()
        }
    
    def clear_cache(self):
        """ካሽ ያጸዳል"""
        self.cache = {}
        logger.info("🧹 AI call cache cleared")


# ============================================================
# 5. ፋብሪካ ተግባራት (Factory Functions)
# ============================================================

def create_selector() -> SmartModelSelector:
    """አዲስ SmartModelSelector ይፈጥራል"""
    return SmartModelSelector()


def create_unified_ai_call() -> UnifiedAICall:
    """አዲስ UnifiedAICall ይፈጥራል"""
    return UnifiedAICall()


def get_model_recommendation(task) -> Dict[str, Any]:
    """ለአንድ ስራ የሞዴል ምክር ይሰጣል"""
    selector = SmartModelSelector()
    return selector.get_recommendation(task)


def select_model_for_task(task) -> Dict[str, Any]:
    """ለአንድ ስራ ሞዴል ይመርጣል"""
    selector = SmartModelSelector()
    return selector.select_model(task)


def call_ai_smart(prompt: str, task=None, pool_type="coding", use_cache=True) -> Dict[str, Any]:
    """ስማርት AI ጥሪ"""
    caller = UnifiedAICall()
    return caller.call(prompt, task, pool_type, use_cache)


def get_selector_stats() -> Dict[str, Any]:
    """የመራጭ ስታቲስቲክስ ይመልሳል"""
    selector = SmartModelSelector()
    return selector.get_stats()


def clear_ai_cache():
    """የAI ካሽ ያጸዳል"""
    caller = UnifiedAICall()
    caller.clear_cache()
    return "✅ AI cache cleared"


# ============================================================
# 6. የሙከራ ተግባር
# ============================================================

def test_selector():
    """selector.py ን ለመፈተሽ"""
    print("=" * 50)
    print("🧪 Testing selector.py")
    print("=" * 50)
    
    # 1. ሞዴሎችን ፈትሽ
    models = ModelRegistry.get_available_models()
    print(f"✅ Available models: {list(models.keys())}")
    
    # 2. የስራ ክብደት ትንተና
    class MockTask:
        def __init__(self):
            self.task_name = "Build Product CRUD"
            self.description = "Create full product management system with Create, Read, Update, Delete"
            self.task_type = "code"
            self.priority = "Critical"
            self.business_impact_score = 10
            self.dependency = None
    
    task = MockTask()
    analyzer = TaskComplexityAnalyzer()
    complexity = analyzer.analyze(task)
    print(f"✅ Complexity: {complexity['level']} ({complexity['score']:.0f}%)")
    
    # 3. ሞዴል ምረጥ
    selector = SmartModelSelector()
    selection = selector.select_model(task)
    print(f"✅ Selected model: {selection.get('model_key')} - {selection.get('reason')}")
    
    # 4. ስታቲስቲክስ
    stats = selector.get_stats()
    print(f"✅ Stats: {stats['total_selections']} selections")
    
    print("=" * 50)
    print("✅ selector.py test complete")
    return True
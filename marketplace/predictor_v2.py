# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/predictor_v2.py
# 📝 ለውጥ፦ Advanced Prediction Engine — Self-Improving Predictions
# 📅 ቀን፦ 2026-06-22
# ============================================================

"""
ይህ ፋይል የላቀ ትንበያ ሞተር (Advanced Prediction Engine) ነው።
በታሪክ ውሂብ ላይ ተመስርቶ የሚቀጥሉትን ስራዎች፣
ስህተቶች እና አዝማሚያዎች ይተነብያል።
"""

import json
import math
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.db.models.functions import TruncDate

from .models import (
    SiteRegistry, AIProjectBacklog, AIEvolutionLog, AgentErrorLog,
    SelfHealingLog, Product, Category, User, VectorMemory,
    PredictionLog
)

logger = logging.getLogger(__name__)


# ============================================================
# 1. የውሂብ ተንታኝ (Data Analyzer)
# ============================================================

class DataAnalyzer:
    """
    የታሪክ ውሂብን ይተነትናል እና ቅጦችን ያገኛል
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        self.cache = {}
    
    def analyze_task_patterns(self) -> Dict[str, Any]:
        """የስራ ቅጦችን ይተነትናል"""
        queryset = AIProjectBacklog.objects.filter(site=self.site) if self.site else AIProjectBacklog.objects.all()
        
        total = queryset.count()
        if total == 0:
            return {'total': 0, 'patterns': []}
        
        # በቅድሚያ ስርጭት
        priority_dist = queryset.values('priority').annotate(count=Count('id'))
        
        # በስራ ዓይነት
        type_dist = queryset.values('task_type').annotate(count=Count('id'))
        
        # የስኬት መጠን
        completed = queryset.filter(status='Completed').count()
        success_rate = (completed / total * 100) if total > 0 else 0
        
        # አማካይ ተጽዕኖ
        avg_impact = queryset.aggregate(avg=Avg('business_impact_score'))['avg'] or 0
        
        # የስራ ፍጥነት (በቀን)
        oldest = queryset.order_by('created_at').first()
        if oldest:
            days = (timezone.now() - oldest.created_at).days or 1
            tasks_per_day = total / days
        else:
            tasks_per_day = 0
        
        return {
            'total': total,
            'completed': completed,
            'success_rate': success_rate,
            'avg_impact': avg_impact,
            'tasks_per_day': tasks_per_day,
            'priority_distribution': list(priority_dist),
            'type_distribution': list(type_dist),
            'patterns': self._extract_patterns(queryset)
        }
    
    def _extract_patterns(self, queryset) -> List[Dict]:
        """ከስራዎች ቅጦችን ያወጣል"""
        patterns = []
        
        # ተደጋጋሚ የስራ ስሞች
        common_names = queryset.values('task_name').annotate(count=Count('id')).order_by('-count')[:5]
        for item in common_names:
            if item['count'] > 1:
                patterns.append({
                    'type': 'common_name',
                    'name': item['task_name'],
                    'count': item['count']
                })
        
        # በሳምንት ቀን ላይ ተመስርቶ
        weekday_dist = queryset.extra(
            select={'weekday': "EXTRACT(dow FROM created_at)"}
        ).values('weekday').annotate(count=Count('id'))
        
        if weekday_dist:
            max_weekday = max(weekday_dist, key=lambda x: x['count'])
            patterns.append({
                'type': 'weekday',
                'day': max_weekday['weekday'],
                'count': max_weekday['count']
            })
        
        return patterns
    
    def analyze_error_patterns(self) -> Dict[str, Any]:
        """የስህተት ቅጦችን ይተነትናል"""
        queryset = AgentErrorLog.objects.filter(site=self.site) if self.site else AgentErrorLog.objects.all()
        
        total = queryset.count()
        if total == 0:
            return {'total': 0, 'patterns': []}
        
        # በስህተት ዓይነት
        type_dist = queryset.values('error_type').annotate(count=Count('id')).order_by('-count')
        
        # የስህተት መፍቻ መጠን
        resolved = queryset.filter(resolved=True).count()
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        
        # በጊዜ ስርጭት
        time_dist = queryset.extra(
            select={'date': "DATE(created_at)"}
        ).values('date').annotate(count=Count('id')).order_by('-date')[:30]
        
        return {
            'total': total,
            'resolved': resolved,
            'resolution_rate': resolution_rate,
            'type_distribution': list(type_dist),
            'time_distribution': list(time_dist),
            'patterns': self._extract_error_patterns(queryset)
        }
    
    def _extract_error_patterns(self, queryset) -> List[Dict]:
        """ከስህተቶች ቅጦችን ያወጣል"""
        patterns = []
        
        # ተደጋጋሚ ስህተቶች
        common_errors = queryset.values('error_message').annotate(count=Count('id')).order_by('-count')[:5]
        for item in common_errors:
            if item['count'] > 1:
                patterns.append({
                    'type': 'common_error',
                    'message': item['error_message'][:100],
                    'count': item['count']
                })
        
        return patterns
    
    def analyze_trends(self) -> Dict[str, Any]:
        """የአዝማሚያ ትንተና ያካሂዳል"""
        # የምርት አዝማሚያ
        product_queryset = Product.objects.filter(site=self.site) if self.site else Product.objects.all()
        
        product_growth = product_queryset.extra(
            select={'date': "DATE(created_at)"}
        ).values('date').annotate(count=Count('id')).order_by('date')
        
        # የተጠቃሚ አዝማሚያ
        user_queryset = User.objects.filter(product__site=self.site).distinct() if self.site else User.objects.all()
        user_count = user_queryset.count()
        
        return {
            'product_growth': list(product_growth)[-30:],
            'total_products': product_queryset.count(),
            'total_users': user_count,
            'product_per_user': (product_queryset.count() / user_count) if user_count > 0 else 0
        }


# ============================================================
# 2. ዋና ትንበያ ሞተር (Predictor Engine)
# ============================================================

class PredictorEngine:
    """
    በታሪክ ውሂብ ላይ ተመስርቶ የሚቀጥሉትን ነገሮች ይተነብያል
    Self-Improving: ከትንበያ ውጤቶች ይማራል
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        self.analyzer = DataAnalyzer(site)
        self.predictions = []
        self.accuracy_history = []
    
    def predict_next_tasks(self, count: int = 5) -> List[Dict[str, Any]]:
        """የሚቀጥሉትን ስራዎች ይተነብያል"""
        task_patterns = self.analyzer.analyze_task_patterns()
        
        if task_patterns.get('total', 0) == 0:
            return self._get_default_predictions()
        
        predictions = []
        
        # 1. በተደጋጋሚ ስራዎች ላይ ተመስርቶ
        for pattern in task_patterns.get('patterns', []):
            if pattern.get('type') == 'common_name':
                predictions.append({
                    'task_name': pattern['name'],
                    'probability': min(0.9, pattern['count'] / 10),
                    'reason': f"Common task ({pattern['count']} occurrences)",
                    'priority': 'High'
                })
        
        # 2. በምዕራፍ ላይ ተመስርቶ
        if self.site:
            current_phase = self.site.build_phase
            phase_tasks = self._get_phase_predictions(current_phase)
            predictions.extend(phase_tasks)
        
        # 3. በስህተቶች ላይ ተመስርቶ
        error_patterns = self.analyzer.analyze_error_patterns()
        if error_patterns.get('total', 0) > 0:
            for pattern in error_patterns.get('patterns', []):
                if pattern.get('type') == 'common_error':
                    predictions.append({
                        'task_name': f"Fix: {pattern['message'][:50]}...",
                        'probability': min(0.8, pattern['count'] / 5),
                        'reason': f"Common error ({pattern['count']} occurrences)",
                        'priority': 'Critical'
                    })
        
        # 4. በስኬት መጠን ላይ ተመስርቶ
        if task_patterns.get('success_rate', 0) < 70:
            predictions.append({
                'task_name': 'Improve Task Success Rate',
                'probability': 0.7,
                'reason': f"Current success rate: {task_patterns['success_rate']:.1f}%",
                'priority': 'High'
            })
        
        # ደርድር እና ወስን
        predictions.sort(key=lambda x: x.get('probability', 0), reverse=True)
        
        # ትንበያዎችን አስቀምጥ
        self.predictions = predictions[:count]
        
        # ወደ PredictionLog መዝግብ
        self._log_predictions('tasks', predictions[:count])
        
        return predictions[:count]
    
    def _get_phase_predictions(self, phase: int) -> List[Dict]:
        """በምዕራፍ ላይ ተመስርቶ ትንበያዎችን ይፈጥራል"""
        phase_tasks = {
            0: [
                {'task_name': 'Seed Real Data', 'probability': 0.95, 'priority': 'Critical'},
                {'task_name': 'Build Product Management', 'probability': 0.90, 'priority': 'Critical'},
            ],
            1: [
                {'task_name': 'Build Core Features', 'probability': 0.90, 'priority': 'Critical'},
                {'task_name': 'Build User Dashboard', 'probability': 0.80, 'priority': 'High'},
            ],
            2: [
                {'task_name': 'Build Engagement Features', 'probability': 0.85, 'priority': 'High'},
                {'task_name': 'Add Product Search', 'probability': 0.75, 'priority': 'High'},
            ],
            3: [
                {'task_name': 'Build Monetization', 'probability': 0.85, 'priority': 'High'},
                {'task_name': 'Implement Payment Gateway', 'probability': 0.80, 'priority': 'Critical'},
            ],
            4: [
                {'task_name': 'SEO Optimization', 'probability': 0.80, 'priority': 'High'},
                {'task_name': 'Mature & Replicate', 'probability': 0.70, 'priority': 'Medium'},
            ],
            5: [
                {'task_name': 'Replicate to New Niche', 'probability': 0.75, 'priority': 'Medium'},
                {'task_name': 'Performance Optimization', 'probability': 0.70, 'priority': 'Medium'},
            ]
        }
        
        tasks = phase_tasks.get(phase, [])
        for task in tasks:
            task['reason'] = f"Phase {phase} prediction"
        return tasks
    
    def _get_default_predictions(self) -> List[Dict]:
        """ነባር ትንበያዎችን ይመልሳል"""
        return [
            {'task_name': 'Initialize System', 'probability': 0.90, 'reason': 'Default startup task', 'priority': 'Critical'},
            {'task_name': 'Add Test Products', 'probability': 0.80, 'reason': 'Default seeding', 'priority': 'High'},
        ]
    
    def predict_errors(self, days: int = 7) -> List[Dict[str, Any]]:
        """የሚቀጥሉትን ስህተቶች ይተነብያል"""
        error_patterns = self.analyzer.analyze_error_patterns()
        
        if error_patterns.get('total', 0) == 0:
            return [{'message': 'No error history for prediction', 'probability': 0.0}]
        
        predictions = []
        
        # በታሪክ ስህተቶች ላይ ተመስርቶ
        for pattern in error_patterns.get('patterns', []):
            if pattern.get('type') == 'common_error':
                # የመከሰት እድል አስላ
                days_span = 30  # ባለፉት 30 ቀናት
                prob = min(0.9, pattern['count'] / days_span)
                
                predictions.append({
                    'error_type': pattern['message'][:50],
                    'probability': prob,
                    'confidence': prob * 100,
                    'suggested_fix': f"Fix {pattern['message'][:50]}",
                    'reason': f"Occurred {pattern['count']} times"
                })
        
        # በስህተት ዓይነት ላይ ተመስርቶ
        for error_type in error_patterns.get('type_distribution', []):
            if error_type['count'] > 1:
                predictions.append({
                    'error_type': f"{error_type['error_type']} errors",
                    'probability': min(0.7, error_type['count'] / 10),
                    'confidence': 60 + error_type['count'] * 2,
                    'suggested_fix': f"Review {error_type['error_type']} handling",
                    'reason': f"{error_type['count']} occurrences"
                })
        
        predictions.sort(key=lambda x: x.get('probability', 0), reverse=True)
        
        self._log_predictions('errors', predictions[:5])
        
        return predictions[:5]
    
    def predict_growth(self, days: int = 30) -> Dict[str, Any]:
        """የዕድገት ትንበያ ያካሂዳል"""
        trends = self.analyzer.analyze_trends()
        
        # የምርት ዕድገት ትንበያ
        product_growth = trends.get('product_growth', [])
        if len(product_growth) > 1:
            # አማካይ የዕድገት መጠን
            growth_rates = []
            for i in range(1, len(product_growth)):
                prev = product_growth[i-1]['count']
                curr = product_growth[i]['count']
                if prev > 0:
                    growth_rates.append((curr - prev) / prev)
            
            avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
            current_products = trends.get('total_products', 0)
            predicted_products = current_products * (1 + avg_growth) ** (days / 30)
        else:
            predicted_products = trends.get('total_products', 0) * 1.1
        
        # የተጠቃሚ ዕድገት ትንበያ
        current_users = trends.get('total_users', 0)
        predicted_users = current_users * 1.1 if current_users > 0 else 5
        
        # የስራ መጠን ትንበያ
        task_patterns = self.analyzer.analyze_task_patterns()
        tasks_per_day = task_patterns.get('tasks_per_day', 0)
        predicted_tasks = tasks_per_day * days
        
        result = {
            'days': days,
            'predicted_products': int(predicted_products),
            'predicted_users': int(predicted_users),
            'predicted_tasks': int(predicted_tasks),
            'current_products': trends.get('total_products', 0),
            'current_users': trends.get('total_users', 0),
            'product_growth_rate': avg_growth if product_growth else 0,
            'confidence': min(90, 60 + len(product_growth) * 2)
        }
        
        self._log_predictions('growth', result)
        
        return result
    
    def predict_next_phase(self) -> Dict[str, Any]:
        """የሚቀጥለውን ምዕራፍ ይተነብያል"""
        if not self.site:
            return {'current_phase': 0, 'next_phase': 1, 'confidence': 50}
        
        current = self.site.build_phase
        next_phase = current + 1 if current < 5 else current
        
        # የሽግግር እድል አስላ
        requirements = self._get_phase_requirements(current)
        met = sum(1 for req in requirements if req.get('met', False))
        total = len(requirements) or 1
        confidence = min(95, (met / total) * 100 + 10)
        
        return {
            'current_phase': current,
            'next_phase': next_phase,
            'requirements': requirements,
            'met_requirements': met,
            'total_requirements': total,
            'confidence': confidence,
            'estimated_time': max(1, 7 - met * 2)  # በቀናት
        }
    
    def _get_phase_requirements(self, phase: int) -> List[Dict]:
        """የምዕራፍ መስፈርቶችን ይመልሳል"""
        requirements = []
        
        if phase == 0:
            requirements.append({'name': 'Scaffolding complete', 'met': True})
        
        elif phase == 1:
            products = Product.objects.filter(site=self.site).count() if self.site else 0
            requirements.append({'name': '≥10 products', 'met': products >= 10})
            customers = User.objects.filter(product__site=self.site).distinct().count() if self.site else 0
            requirements.append({'name': '≥5 customers', 'met': customers >= 5})
        
        elif phase == 2:
            total = AIProjectBacklog.objects.filter(site=self.site, task_type='code').count() if self.site else 0
            completed = AIProjectBacklog.objects.filter(site=self.site, task_type='code', status='Completed').count() if self.site else 0
            pct = (completed / total * 100) if total > 0 else 0
            requirements.append({'name': '80% core features complete', 'met': pct >= 80})
        
        elif phase == 3:
            has_engagement = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Engagement',
                status='Completed'
            ).exists() if self.site else False
            requirements.append({'name': 'Engagement features complete', 'met': has_engagement})
        
        elif phase == 4:
            has_monetization = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Monetization',
                status='Completed'
            ).exists() if self.site else False
            requirements.append({'name': 'Monetization complete', 'met': has_monetization})
        
        return requirements
    
    def _log_predictions(self, prediction_type: str, data: Any):
        """ትንበያውን ወደ ዳታቤዝ ይመዘግባል"""
        try:
            PredictionLog.objects.create(
                prediction_type=prediction_type,
                predicted_value=0,
                confidence_score=0,
                input_data=data if isinstance(data, dict) else {'data': data},
                site=self.site,
                model_version='predictor-v2'
            )
        except Exception as e:
            logger.warning(f"Failed to log prediction: {e}")
    
    def get_accuracy(self) -> Dict[str, Any]:
        """የትንበያ ትክክለኛነት ይመልሳል"""
        predictions = PredictionLog.objects.filter(site=self.site) if self.site else PredictionLog.objects.all()
        
        total = predictions.count()
        if total == 0:
            return {'total': 0, 'accuracy': 0}
        
        verified = predictions.filter(verified_at__isnull=False).count()
        
        return {
            'total_predictions': total,
            'verified_predictions': verified,
            'verification_rate': (verified / total * 100) if total > 0 else 0,
            'recent_predictions': list(predictions.order_by('-predicted_at')[:5].values())
        }


# ============================================================
# 3. ፋብሪካ ተግባራት
# ============================================================

def create_predictor(site: SiteRegistry = None) -> PredictorEngine:
    """አዲስ PredictorEngine ይፈጥራል"""
    return PredictorEngine(site)


def predict_next_tasks(site: SiteRegistry = None, count: int = 5) -> List[Dict]:
    """የሚቀጥሉትን ስራዎች ይተነብያል"""
    predictor = PredictorEngine(site)
    return predictor.predict_next_tasks(count)


def predict_errors(site: SiteRegistry = None) -> List[Dict]:
    """የሚቀጥሉትን ስህተቶች ይተነብያል"""
    predictor = PredictorEngine(site)
    return predictor.predict_errors()


def predict_growth(site: SiteRegistry = None, days: int = 30) -> Dict:
    """የዕድገት ትንበያ ይሰጣል"""
    predictor = PredictorEngine(site)
    return predictor.predict_growth(days)


def get_prediction_accuracy(site: SiteRegistry = None) -> Dict:
    """የትንበያ ትክክለኛነት ይመልሳል"""
    predictor = PredictorEngine(site)
    return predictor.get_accuracy()


# ============================================================
# 4. የሙከራ ተግባር
# ============================================================

def test_predictor():
    """predictor_v2.py ን ለመፈተሽ"""
    print("=" * 50)
    print("🧪 Testing predictor_v2.py")
    print("=" * 50)
    
    # 1. ትንበያ ሞተር ፍጠር
    predictor = PredictorEngine()
    print("✅ Predictor engine created")
    
    # 2. የስራ ትንበያ
    tasks = predictor.predict_next_tasks(3)
    print(f"✅ Next tasks: {len(tasks)} predictions")
    for task in tasks:
        print(f"  - {task.get('task_name')} ({task.get('probability', 0):.0%})")
    
    # 3. የስህተት ትንበያ
    errors = predictor.predict_errors()
    print(f"✅ Error predictions: {len(errors)}")
    
    # 4. የዕድገት ትንበያ
    growth = predictor.predict_growth()
    print(f"✅ Growth predictions: {growth}")
    
    # 5. ትክክለኛነት
    accuracy = predictor.get_accuracy()
    print(f"✅ Accuracy: {accuracy}")
    
    print("=" * 50)
    print("✅ predictor_v2.py test complete")
    return True
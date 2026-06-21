# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/trigger_engine.py
# 📝 ለውጥ፦ Data-First, Dependency-Driven Trigger Engine
# 📅 ቀን፦ 2026-06-21
# ============================================================

import logging
from django.utils import timezone
from django.db import models
from .models import (
    SiteRegistry, AIProjectBacklog, Product, User,
    Category, SiteConfig
)

logger = logging.getLogger(__name__)


class TriggerEngine:
    """
    በመረጃ-ተነሳሽነት (data-triggered) ስራዎችን የሚፈጥር ሞተር
    Data-First, Dependency-Driven Organic Growth
    """
    
    # የምዕራፍ ስሞች
    PHASE_NAMES = {
        0: 'Scaffolding',
        1: 'Real Data Seeding',
        2: 'Core Feature Expansion',
        3: 'Engagement Features',
        4: 'Monetization & Growth',
        5: 'Mature / Replicate'
    }
    
    def __init__(self, site: SiteRegistry):
        self.site = site
    
    def evaluate_all_triggers(self):
        """ሁሉንም ትሪገሮች ይገመግማል እና አዲስ ስራዎችን ይፈጥራል"""
        created_tasks = []
        
        # ወቅታዊ ምዕራፍ አግኝ
        current_phase = self.site.build_phase
        
        # በወቅታዊ ምዕራፍ ላይ ያሉ ትሪገሮችን አስኬድ
        phase_triggers = self._get_phase_triggers(current_phase)
        
        for trigger in phase_triggers:
            task = self._evaluate_trigger(trigger)
            if task:
                created_tasks.append(task)
        
        # ተጨማሪ ትሪገሮችን ፈትሽ (ከወቅታዊ ምዕራፍ በላይ)
        if current_phase < 5:
            next_phase_triggers = self._get_phase_triggers(current_phase + 1)
            # ነገር ግን የቀጣይ ምዕራፍ ትሪገሮች በሙሉ አይፈጠሩም
            # ሁኔታዎቹ ከተሟሉ ብቻ
            for trigger in next_phase_triggers:
                if self._check_condition(trigger.get('condition')):
                    task = self._create_task_from_trigger(trigger)
                    if task:
                        created_tasks.append(task)
        
        return created_tasks
    
    def _get_phase_triggers(self, phase):
        """ለአንድ የተወሰነ ምዕራፍ ትሪገሮችን ይመልሳል"""
        triggers = {
            0: self._get_scaffolding_triggers(),
            1: self._get_real_data_triggers(),
            2: self._get_core_features_triggers(),
            3: self._get_engagement_triggers(),
            4: self._get_monetization_triggers(),
            5: self._get_mature_triggers(),
        }
        return triggers.get(phase, [])
    
    def _get_scaffolding_triggers(self):
        """Scaffolding ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'Seed Real Data',
                'description': 'Phase 1: Import/seed real products and customers',
                'priority': 'Critical',
                'business_impact': 10,
                'target_file': 'data_seeding',
                'task_type': 'growth',
                'condition': {
                    'type': 'always',
                    'message': 'Scaffolding complete - starting data seeding'
                }
            }
        ]
    
    def _get_real_data_triggers(self):
        """Real Data Seeding ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'Build Core Features',
                'description': 'Phase 2: Product detail, edit, delete, user dashboard',
                'priority': 'Critical',
                'business_impact': 9,
                'target_file': 'product_views',
                'task_type': 'code',
                'condition': {
                    'type': 'min_products',
                    'value': 10,
                    'message': f'Real products: {self.site.real_product_count}'
                }
            },
            {
                'name': 'Customer Dashboard',
                'description': 'Build customer dashboard and order history',
                'priority': 'High',
                'business_impact': 8,
                'target_file': 'customer_dashboard',
                'task_type': 'code',
                'condition': {
                    'type': 'min_customers',
                    'value': 5,
                    'message': f'Real customers: {self.site.real_customer_count}'
                }
            }
        ]
    
    def _get_core_features_triggers(self):
        """Core Features ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'Build Engagement Features',
                'description': 'Phase 3: Search, filters, reviews, notifications',
                'priority': 'High',
                'business_impact': 8,
                'target_file': 'engagement',
                'task_type': 'seo',
                'condition': {
                    'type': 'core_complete',
                    'value': 0.8,  # 80%
                    'message': 'Core features 80%+ completed'
                }
            },
            {
                'name': 'Add Product Search',
                'description': 'Implement product search with filters',
                'priority': 'High',
                'business_impact': 7,
                'target_file': 'search',
                'task_type': 'code',
                'condition': {
                    'type': 'min_products',
                    'value': 20,
                    'message': '20+ products available for search'
                }
            },
            {
                'name': 'Add Product Reviews',
                'description': 'Implement product review system',
                'priority': 'Medium',
                'business_impact': 6,
                'target_file': 'reviews',
                'task_type': 'code',
                'condition': {
                    'type': 'feature_complete',
                    'feature': 'product_detail',
                    'message': 'Product detail feature complete'
                }
            }
        ]
    
    def _get_engagement_triggers(self):
        """Engagement Features ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'Build Monetization',
                'description': 'Phase 4: Payment integration, marketing campaigns, SEO',
                'priority': 'High',
                'business_impact': 10,
                'target_file': 'monetization',
                'task_type': 'marketing',
                'condition': {
                    'type': 'engagement_complete',
                    'message': 'Engagement phase complete'
                }
            },
            {
                'name': 'Implement Payment Gateway',
                'description': 'Add payment integration for product purchases',
                'priority': 'Critical',
                'business_impact': 10,
                'target_file': 'payment',
                'task_type': 'code',
                'condition': {
                    'type': 'min_products',
                    'value': 30,
                    'message': '30+ products available for payment'
                }
            },
            {
                'name': 'Launch Marketing Campaign',
                'description': 'Create and launch marketing campaign',
                'priority': 'High',
                'business_impact': 9,
                'target_file': 'marketing_campaign',
                'task_type': 'marketing',
                'condition': {
                    'type': 'payment_complete',
                    'message': 'Payment integration complete'
                }
            }
        ]
    
    def _get_monetization_triggers(self):
        """Monetization & Growth ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'Mature & Replicate',
                'description': 'Phase 5: Mature site, replicate to other niches',
                'priority': 'Medium',
                'business_impact': 7,
                'target_file': 'replication',
                'task_type': 'growth',
                'condition': {
                    'type': 'monetization_success',
                    'message': 'Monetization success confirmed'
                }
            },
            {
                'name': 'SEO Optimization',
                'description': 'Comprehensive SEO optimization for site',
                'priority': 'High',
                'business_impact': 8,
                'target_file': 'seo',
                'task_type': 'seo',
                'condition': {
                    'type': 'min_products',
                    'value': 50,
                    'message': '50+ products for SEO'
                }
            }
        ]
    
    def _get_mature_triggers(self):
        """Mature ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'Replicate to New Niche',
                'description': 'Create new site for different niche',
                'priority': 'Medium',
                'business_impact': 6,
                'target_file': 'new_site',
                'task_type': 'growth',
                'condition': {
                    'type': 'site_mature',
                    'message': 'Site is mature and ready for replication'
                }
            }
        ]
    
    def _evaluate_trigger(self, trigger):
        """አንድ ትሪገር ይገመግማል"""
        condition = trigger.get('condition', {})
        
        # ሁኔታውን ፈትሽ
        if not self._check_condition(condition):
            return None
        
        # ስራው ቀድሞ እንዳልተፈጠረ አረጋግጥ
        task_name = trigger.get('name')
        existing = AIProjectBacklog.objects.filter(
            site=self.site,
            task_name=task_name,
            status__in=['Pending', 'Running', 'Completed']
        ).exists()
        
        if existing:
            return None
        
        # አዲስ ስራ ፍጠር
        return self._create_task_from_trigger(trigger)
    
    def _check_condition(self, condition):
        """የትሪገር ሁኔታን ያረጋግጣል"""
        if not condition:
            return False
        
        condition_type = condition.get('type')
        
        if condition_type == 'always':
            return True
        
        elif condition_type == 'min_products':
            return self.site.real_product_count >= condition.get('value', 0)
        
        elif condition_type == 'min_customers':
            return self.site.real_customer_count >= condition.get('value', 0)
        
        elif condition_type == 'core_complete':
            # የCore ስራዎች ስንት ተጠናቀቁ?
            total = AIProjectBacklog.objects.filter(
                site=self.site,
                task_type='code'
            ).count()
            completed = AIProjectBacklog.objects.filter(
                site=self.site,
                task_type='code',
                status='Completed'
            ).count()
            if total == 0:
                return False
            return (completed / total) >= condition.get('value', 0.8)
        
        elif condition_type == 'feature_complete':
            feature = condition.get('feature')
            # የተወሰነ ባህሪ ተጠናቅቋል?
            return AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains=feature,
                status='Completed'
            ).exists()
        
        elif condition_type == 'engagement_complete':
            return AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Engagement',
                status='Completed'
            ).exists()
        
        elif condition_type == 'payment_complete':
            return AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Payment',
                status='Completed'
            ).exists()
        
        elif condition_type == 'monetization_success':
            return AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Monetization',
                status='Completed'
            ).exists()
        
        elif condition_type == 'site_mature':
            return self.site.build_phase >= 5
        
        return False
    
    def _create_task_from_trigger(self, trigger):
        """ከትሪገር አዲስ ስራ ይፈጥራል"""
        try:
            task = AIProjectBacklog.objects.create(
                site=self.site,
                task_name=trigger.get('name'),
                task_type=trigger.get('task_type', 'code'),
                target_file=trigger.get('target_file', 'unknown'),
                priority=trigger.get('priority', 'Medium'),
                status='Pending',
                description=trigger.get('description', ''),
                business_impact_score=trigger.get('business_impact', 5),
                trigger_condition=trigger.get('condition', {}).get('message', ''),
                estimated_hours=trigger.get('estimated_hours', 2.0),
                complexity=trigger.get('complexity', 3)
            )
            logger.info(f"📋 Triggered task: {task.task_name} for {self.site.name}")
            return task
        except Exception as e:
            logger.error(f"Failed to create task from trigger: {e}")
            return None
    
    def update_phase(self):
        """ወቅታዊ የbuild_phase ሁኔታን ያሻሽላል"""
        current = self.site.build_phase
        new_phase = current
        
        if current == 0:
            # Scaffolding → Real Data
            new_phase = 1
            self.site.phase_transition_date = timezone.now()
            logger.info(f"📈 {self.site.name} → Phase 1 (Real Data)")
        
        elif current == 1:
            # Real Data → Core Features
            if self.site.real_product_count >= 10 and self.site.real_customer_count >= 5:
                new_phase = 2
                self.site.phase_transition_date = timezone.now()
                logger.info(f"📈 {self.site.name} → Phase 2 (Core Features)")
        
        elif current == 2:
            # Core Features → Engagement
            total = AIProjectBacklog.objects.filter(
                site=self.site, task_type='code'
            ).count()
            completed = AIProjectBacklog.objects.filter(
                site=self.site, task_type='code', status='Completed'
            ).count()
            if total > 0 and (completed / total) >= 0.8:
                new_phase = 3
                self.site.phase_transition_date = timezone.now()
                logger.info(f"📈 {self.site.name} → Phase 3 (Engagement)")
        
        elif current == 3:
            # Engagement → Monetization
            engagement_complete = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Engagement',
                status='Completed'
            ).exists()
            if engagement_complete:
                new_phase = 4
                self.site.phase_transition_date = timezone.now()
                logger.info(f"📈 {self.site.name} → Phase 4 (Monetization)")
        
        elif current == 4:
            # Monetization → Mature
            monetization_complete = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Monetization',
                status='Completed'
            ).exists()
            if monetization_complete:
                new_phase = 5
                self.site.phase_transition_date = timezone.now()
                logger.info(f"📈 {self.site.name} → Phase 5 (Mature)")
        
        if new_phase != current:
            self.site.build_phase = new_phase
            self.site.save()
        
        return new_phase
    
    def get_phase_status(self):
        """የወቅታዊ ምዕራፍ ሁኔታ ይመልሳል"""
        current = self.site.build_phase
        next_phase = current + 1 if current < 5 else current
        
        return {
            'current_phase': current,
            'current_phase_name': self.PHASE_NAMES.get(current, 'Unknown'),
            'next_phase': next_phase,
            'next_phase_name': self.PHASE_NAMES.get(next_phase, 'Complete'),
            'real_products': self.site.real_product_count,
            'real_customers': self.site.real_customer_count,
            'phase_transition_date': self.site.phase_transition_date,
            'tasks_in_phase': AIProjectBacklog.objects.filter(
                site=self.site,
                trigger_condition__icontains=self.PHASE_NAMES.get(current, '')
            ).count()
        }
    
    def get_next_phase_requirements(self):
        """ወደ ቀጣይ ምዕራፍ ለመሄድ የሚያስፈልጉ መስፈርቶችን ይመልሳል"""
        current = self.site.build_phase
        requirements = []
        
        if current == 0:
            requirements.append("✅ Scaffolding complete - automatic")
        
        elif current == 1:
            requirements.append(f"📦 Real Products: {self.site.real_product_count}/10")
            requirements.append(f"👤 Real Customers: {self.site.real_customer_count}/5")
        
        elif current == 2:
            total = AIProjectBacklog.objects.filter(site=self.site, task_type='code').count()
            completed = AIProjectBacklog.objects.filter(site=self.site, task_type='code', status='Completed').count()
            pct = (completed / total * 100) if total > 0 else 0
            requirements.append(f"📊 Core Features: {pct:.0f}% complete (need 80%)")
        
        elif current == 3:
            has_engagement = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Engagement',
                status='Completed'
            ).exists()
            requirements.append(f"💬 Engagement Features: {'✅' if has_engagement else '❌'}")
        
        elif current == 4:
            has_monetization = AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Monetization',
                status='Completed'
            ).exists()
            requirements.append(f"💰 Monetization: {'✅' if has_monetization else '❌'}")
        
        return requirements
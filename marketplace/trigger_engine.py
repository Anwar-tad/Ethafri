# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/trigger_engine.py
# 📝 ለውጥ፦ ሙሉ በሙሉ የተሻሻለ — Data-First, Self-Learning Trigger Engine
# 📅 ቀን፦ 2026-06-22
# ============================================================

import json
import re
import logging
from django.utils import timezone
from django.db import models
from django.db.models import Count, Q
from .models import (
    SiteRegistry, AIProjectBacklog, Product, Category, 
    User, AgentErrorLog, AIEvolutionLog, SiteConfig,
    SelfHealingLog, VectorMemory
)

logger = logging.getLogger(__name__)


class TriggerEngine:
    """
    በመረጃ-ተነሳሽነት (data-triggered) ስራዎችን የሚፈጥር ሞተር
    Data-First, Dependency-Driven, Self-Learning Organic Growth
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
        self.analysis = None
    
    # ============================================================
    # 1. ዋና ተግባራት
    # ============================================================
    
    def evaluate_all_triggers(self):
        """ሁሉንም ትሪገሮች ይገመግማል እና አዲስ ስራዎችን ይፈጥራል"""
        created_tasks = []
        
        # 1. የጣቢያ ትንተና አካሂድ
        self.analysis = self._analyze_site()
        
        # 2. በምዕራፍ ላይ ተመስርቶ ትሪገሮችን አስኬድ
        current_phase = self.site.build_phase
        phase_triggers = self._get_phase_triggers(current_phase)
        
        for trigger in phase_triggers:
            task = self._evaluate_trigger(trigger)
            if task:
                created_tasks.append(task)
                logger.info(f"📋 Triggered: {task.task_name} for {self.site.name}")
        
        # 3. ተጨማሪ ስማርት ትሪገሮች
        smart_tasks = self._evaluate_smart_triggers()
        created_tasks.extend(smart_tasks)
        
        # 4. ምንም ስራ ካልተፈጠረ — Self-Learning
        if not created_tasks:
            self._trigger_self_learning()
        
        # 5. ምዕራፍ አዘምን
        self.update_phase()
        
        return created_tasks
    
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
    
    # ============================================================
    # 2. የጣቢያ ትንተና
    # ============================================================
    
    def _analyze_site(self):
        """የጣቢያውን ሁኔታ በዝርዝር ይተነትናል"""
        analysis = {
            'products': {
                'total': Product.objects.filter(site=self.site, is_active=True).count(),
                'has_products': Product.objects.filter(site=self.site, is_active=True).exists(),
            },
            'customers': {
                'total': User.objects.filter(product__site=self.site).distinct().count(),
                'has_customers': User.objects.filter(product__site=self.site).exists(),
            },
            'categories': {
                'total': Category.objects.filter(product__site=self.site).distinct().count(),
                'has_categories': Category.objects.filter(product__site=self.site).exists(),
            },
            'code': {
                'has_models': AIEvolutionLog.objects.filter(site=self.site, target_file='models').exists(),
                'has_views': AIEvolutionLog.objects.filter(site=self.site, target_file='views').exists(),
                'has_urls': AIEvolutionLog.objects.filter(site=self.site, target_file='urls').exists(),
                'has_admin': AIEvolutionLog.objects.filter(site=self.site, target_file='admin').exists(),
                'total_changes': AIEvolutionLog.objects.filter(site=self.site).count(),
            },
            'errors': {
                'total': AgentErrorLog.objects.filter(site=self.site, resolved=False).count(),
                'has_errors': AgentErrorLog.objects.filter(site=self.site, resolved=False).exists(),
            },
            'tasks': {
                'total': AIProjectBacklog.objects.filter(site=self.site).count(),
                'pending': AIProjectBacklog.objects.filter(site=self.site, status='Pending').count(),
                'completed': AIProjectBacklog.objects.filter(site=self.site, status='Completed').count(),
                'running': AIProjectBacklog.objects.filter(site=self.site, status='Running').count(),
            },
            'build_phase': self.site.build_phase,
            'growth_level': self.site.growth_level,
        }
        
        # የጎደሉ ባህሪያትን ለይ
        analysis['missing_features'] = self._detect_missing_features(analysis)
        
        return analysis
    
    def _detect_missing_features(self, analysis):
        """የጎደሉ ባህሪያትን ይለያል"""
        missing = []
        
        # በምዕራፍ ላይ ተመስርቶ
        phase = analysis['build_phase']
        
        if phase == 0:
            missing.append('Seed Real Data')
            missing.append('Product Management')
            missing.append('User Authentication')
        
        elif phase == 1:
            if analysis['products']['total'] < 5:
                missing.append('Add More Products')
            if not analysis['categories']['has_categories']:
                missing.append('Add Categories')
            if analysis['customers']['total'] < 3:
                missing.append('Recruit Sellers')
        
        elif phase == 2:
            if not analysis['code']['has_views']:
                missing.append('Build Product Views')
            if not analysis['code']['has_admin']:
                missing.append('Admin Configuration')
            if analysis['products']['total'] < 20:
                missing.append('Expand Product Catalog')
        
        elif phase == 3:
            missing.append('Add Search & Filters')
            missing.append('Build Review System')
            missing.append('Implement Notifications')
        
        elif phase == 4:
            missing.append('Payment Integration')
            missing.append('Marketing Campaigns')
            missing.append('Analytics Dashboard')
        
        elif phase == 5:
            missing.append('Performance Optimization')
            missing.append('Replicate to New Niche')
        
        # ስህተቶች ካሉ
        if analysis['errors']['has_errors']:
            missing.append(f"Fix {analysis['errors']['total']} errors")
        
        return missing
    
    # ============================================================
    # 3. ትሪገር ትውልድ
    # ============================================================
    
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
                'condition': {'type': 'always', 'message': 'Scaffolding complete'}
            },
            {
                'name': 'Build Product Management',
                'description': 'Create product CRUD operations',
                'priority': 'Critical',
                'business_impact': 9,
                'target_file': 'product_views',
                'task_type': 'code',
                'condition': {'type': 'phase_complete', 'phase': 0}
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
                'target_file': 'core_features',
                'task_type': 'code',
                'condition': {
                    'type': 'min_products',
                    'value': 10,
                    'message': f'Real products: {self.site.real_product_count}'
                }
            },
            {
                'name': 'Build User Dashboard',
                'description': 'Customer dashboard and order history',
                'priority': 'High',
                'business_impact': 8,
                'target_file': 'user_dashboard',
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
                'condition': {'type': 'core_complete', 'value': 0.8}
            },
            {
                'name': 'Add Product Search',
                'description': 'Implement product search with filters',
                'priority': 'High',
                'business_impact': 7,
                'target_file': 'search',
                'task_type': 'code',
                'condition': {'type': 'min_products', 'value': 20}
            }
        ]
    
    def _get_engagement_triggers(self):
        """Engagement Features ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'Build Monetization',
                'description': 'Phase 4: Payment integration, marketing campaigns',
                'priority': 'High',
                'business_impact': 10,
                'target_file': 'monetization',
                'task_type': 'marketing',
                'condition': {'type': 'engagement_complete'}
            },
            {
                'name': 'Implement Payment Gateway',
                'description': 'Add payment integration for product purchases',
                'priority': 'Critical',
                'business_impact': 10,
                'target_file': 'payment',
                'task_type': 'code',
                'condition': {'type': 'min_products', 'value': 30}
            }
        ]
    
    def _get_monetization_triggers(self):
        """Monetization & Growth ምዕራፍ ትሪገሮች"""
        return [
            {
                'name': 'SEO Optimization',
                'description': 'Comprehensive SEO optimization for site',
                'priority': 'High',
                'business_impact': 8,
                'target_file': 'seo',
                'task_type': 'seo',
                'condition': {'type': 'monetization_success'}
            },
            {
                'name': 'Mature & Replicate',
                'description': 'Phase 5: Mature site, replicate to other niches',
                'priority': 'Medium',
                'business_impact': 7,
                'target_file': 'replication',
                'task_type': 'growth',
                'condition': {'type': 'phase_complete', 'phase': 4}
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
                'condition': {'type': 'site_mature'}
            },
            {
                'name': 'Performance Optimization',
                'description': 'Optimize database queries and caching',
                'priority': 'Medium',
                'business_impact': 7,
                'target_file': 'performance',
                'task_type': 'seo',
                'condition': {'type': 'site_mature'}
            }
        ]
    
    # ============================================================
    # 4. ስማርት ትሪገሮች
    # ============================================================
    
    def _evaluate_smart_triggers(self):
        """በትንተና ላይ ተመስርቶ አዲስ ስራዎችን ይፈጥራል"""
        created = []
        
        # 1. የጎደሉ ባህሪያት ካሉ
        for feature in self.analysis.get('missing_features', []):
            if not self._task_exists(feature):
                task = self._create_task_from_feature(feature)
                if task:
                    created.append(task)
                    logger.info(f"🧠 Smart trigger: {task.task_name}")
        
        # 2. ስህተቶች ካሉ
        if self.analysis['errors']['has_errors']:
            error_task = self._create_error_fix_task()
            if error_task:
                created.append(error_task)
        
        # 3. የውሂብ ክፍተቶች ካሉ
        if self.analysis['products']['total'] < 3:
            task = self._create_data_seeding_task()
            if task:
                created.append(task)
        
        return created
    
    def _task_exists(self, feature_name):
        """ስራው ቀድሞ እንዳለ ያረጋግጣል"""
        return AIProjectBacklog.objects.filter(
            site=self.site,
            task_name__icontains=feature_name[:30],
            status__in=['Pending', 'Running', 'Completed']
        ).exists()
    
    def _create_task_from_feature(self, feature):
        """ከባህሪ አዲስ ስራ ይፈጥራል"""
        priority = 'Critical' if 'error' in feature.lower() else 'High'
        impact = 9 if 'error' in feature.lower() else 8
        
        task, created = AIProjectBacklog.objects.get_or_create(
            site=self.site,
            task_name=f'Build: {feature}',
            defaults={
                'task_type': 'code',
                'target_file': feature.lower().replace(' ', '_'),
                'priority': priority,
                'status': 'Pending',
                'description': f'Implement {feature} for {self.site.name}',
                'business_impact_score': impact,
                'trigger_condition': f'Smart: Missing {feature}'
            }
        )
        return task if created else None
    
    def _create_error_fix_task(self):
        """የስህተት ጥገና ስራ ይፈጥራል"""
        errors = AgentErrorLog.objects.filter(site=self.site, resolved=False)
        if not errors.exists():
            return None
        
        error_msg = errors.first().error_message[:50]
        task, created = AIProjectBacklog.objects.get_or_create(
            site=self.site,
            task_name=f'Fix: {error_msg}',
            defaults={
                'task_type': 'code',
                'target_file': 'error_fix',
                'priority': 'Critical',
                'status': 'Pending',
                'description': f'Fix error: {error_msg}',
                'business_impact_score': 9,
                'trigger_condition': f'Smart: {errors.count()} errors found'
            }
        )
        return task if created else None
    
    def _create_data_seeding_task(self):
        """የውሂብ መሙያ ስራ ይፈጥራል"""
        task, created = AIProjectBacklog.objects.get_or_create(
            site=self.site,
            task_name='Seed Real Data',
            defaults={
                'task_type': 'growth',
                'target_file': 'data_seeding',
                'priority': 'Critical',
                'status': 'Pending',
                'description': f'Add products and customers to {self.site.name}',
                'business_impact_score': 10,
                'trigger_condition': f'Smart: Only {self.analysis["products"]["total"]} products'
            }
        )
        return task if created else None
    
    # ============================================================
    # 5. Self-Learning
    # ============================================================
    
    def _trigger_self_learning(self):
        """ምንም ስራ ከሌለ ራሱን ያስተምራል"""
        logger.info(f"📚 Self-Learning triggered for {self.site.name}")
        
        # 1. የራስ-ማስተማር መዝግብ
        insight = self._generate_learning_insight()
        
        SelfHealingLog.objects.create(
            error_message=f"Self-Learning: {self.site.name}",
            solution_sql=insight,
            resolved=True
        )
        
        # 2. የቬክተር ትውስታ ውስጥ አስቀምጥ
        try:
            VectorMemory.objects.create(
                memory_type='insight',
                content=f"Site {self.site.name} self-learning: {insight[:200]}",
                site=self.site,
                metadata={'phase': self.site.build_phase},
                text_content=insight,
                embedding_model='self-learning-v1'
            )
        except Exception as e:
            logger.error(f"Failed to save vector memory: {e}")
        
        # 3. አዲስ ስራ ለመፍጠር ሞክር
        if self.site.build_phase < 5:
            # ቀጣይ ምዕራፍ ስራ
            next_phase = self.site.build_phase + 1
            next_tasks = self._get_phase_triggers(next_phase)
            
            for trigger in next_tasks[:1]:  # አንድ ብቻ
                task = self._create_task_from_trigger(trigger)
                if task:
                    logger.info(f"📋 Self-Learning task: {task.task_name}")
                    break
    
    def _generate_learning_insight(self):
        """የራስ-ማስተማር ግንዛቤ ይፈጥራል"""
        analysis = self.analysis
        
        insight = f"""
        📊 Self-Learning Report for {self.site.name}
        
        Current Status:
        - Build Phase: {analysis['build_phase']} ({self.PHASE_NAMES.get(analysis['build_phase'], 'Unknown')})
        - Products: {analysis['products']['total']}
        - Customers: {analysis['customers']['total']}
        - Categories: {analysis['categories']['total']}
        - Code Changes: {analysis['code']['total_changes']}
        - Pending Tasks: {analysis['tasks']['pending']}
        - Completed Tasks: {analysis['tasks']['completed']}
        - Errors: {analysis['errors']['total']}
        
        Missing Features:
        """
        
        for feature in analysis.get('missing_features', []):
            insight += f"\n- {feature}"
        
        if not analysis.get('missing_features'):
            insight += "\n- None! Codebase looks complete."
        
        insight += f"""
        
        Recommendations:
        1. {'Move to next phase' if analysis['build_phase'] < 5 else 'Optimize and replicate'}
        2. {'Add more products' if analysis['products']['total'] < 10 else 'Focus on engagement'}
        3. {'Fix existing errors' if analysis['errors']['has_errors'] else 'Maintain stability'}
        """
        
        return insight
    
    # ============================================================
    # 6. ረዳት ተግባራት
    # ============================================================
    
    def _evaluate_trigger(self, trigger):
        """አንድ ትሪገር ይገመግማል"""
        condition = trigger.get('condition', {})
        
        if not self._check_condition(condition):
            return None
        
        if self._task_exists(trigger.get('name')):
            return None
        
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
            total = AIProjectBacklog.objects.filter(
                site=self.site, task_type='code'
            ).count()
            completed = AIProjectBacklog.objects.filter(
                site=self.site, task_type='code', status='Completed'
            ).count()
            if total == 0:
                return False
            return (completed / total) >= condition.get('value', 0.8)
        
        elif condition_type == 'engagement_complete':
            return AIProjectBacklog.objects.filter(
                site=self.site,
                task_name__icontains='Engagement',
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
        
        elif condition_type == 'phase_complete':
            return self.site.build_phase >= condition.get('phase', 0)
        
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
            logger.info(f"📋 Created task: {task.task_name} for {self.site.name}")
            return task
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None
    
    # ============================================================
    # 7. የሁኔታ መረጃ
    # ============================================================
    
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
    
    def get_analysis_report(self):
        """የሙሉ ትንተና ሪፖርት ይመልሳል"""
        if not self.analysis:
            self.analysis = self._analyze_site()
        
        return {
            'site': self.site.name,
            'analysis': self.analysis,
            'missing_features': self.analysis.get('missing_features', []),
            'phase_status': self.get_phase_status(),
            'requirements': self.get_next_phase_requirements(),
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self):
        """በትንተና ላይ ተመስርቶ ምክሮችን ይፈጥራል"""
        recommendations = []
        analysis = self.analysis
        
        if analysis['products']['total'] < 10:
            recommendations.append("Add more products to attract customers")
        
        if analysis['customers']['total'] < 5:
            recommendations.append("Recruit sellers and customers")
        
        if analysis['errors']['has_errors']:
            recommendations.append(f"Fix {analysis['errors']['total']} errors")
        
        if analysis['tasks']['pending'] > 5:
            recommendations.append("Process pending tasks")
        
        if analysis['build_phase'] < 5:
            recommendations.append(f"Move to phase {analysis['build_phase'] + 1}")
        
        if not recommendations:
            recommendations.append("Site is healthy. Monitor for new opportunities.")
        
        return recommendations
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/feature_evolution.py
# 📝 ዓላማ፦ ኤጀንቱ አዲስ ፊቸሮችን የሚፈጥርበት እና ራሱን የሚያሻሽልበት የተዋሃደ ሞተር
# 📅 ቀን፦ Friday, July 03, 2026
# ============================================================

import logging
import json
from datetime import timedelta
from django.utils import timezone
from django.apps import apps
from .ai_utils import ask_master_ai_smart, clean_and_parse_json
from .code_apply import apply_code_change

logger = logging.getLogger(__name__)


def get_model(model_name):
    """ሞዴሎችን በዳይናሚክ መጫኛ"""
    try:
        return apps.get_model('marketplace', model_name)
    except Exception:
        return None


class FeatureEvolutionEngine:
    """
    ኤጀንቱ አዲስ ፊቸሮችን የሚፈጥርበት እና ራሱን የሚያሻሽልበት 
    የተዋሃደ ራስ-እድገት ሞተር
    """
    
    def __init__(self, site):
        self.site = site
        self.pending_features = []
        self.completed_features = []
        
        # የሚፈለጉ ሞዴሎችን አስቀድመን መጫን
        self.SiteConfig = get_model('SiteConfig')
        self.SelfHealingLog = get_model('SelfHealingLog')
        
    def evolve(self):
        """ሙሉ የራስ-እድገት ዑደት ያካሂዳል"""
        logger.info(f"🧬 Starting self-evolution cycle for {self.site.name}...")
        
        try:
            # 1. የጎደሉትን ፊቸሮች ይለያል
            self.discover_missing_features()
            
            if not self.pending_features:
                logger.info("✅ No missing features found. System is complete!")
                return
            
            # 2. ቅድሚያ ይሰጣል
            self.prioritize_features()
            
            # 3. ከፍተኛ ቅድሚያ ያላቸውን 3 ፊቸሮች ይፈጥራል
            created = 0
            for feature in self.pending_features[:3]:
                logger.info(f"🚀 Creating high-priority feature: {feature['name']}")
                if self.create_feature(feature):
                    self.completed_features.append(feature)
                    self.pending_features.remove(feature)
                    created += 1
                    logger.info(f"✅ Created feature: {feature['name']}")
                else:
                    logger.error(f"❌ Failed to create feature: {feature['name']}")
            
            # 4. የራስ-እድገት ሪፖርት ያዘጋጃል
            self._generate_evolution_report(created)
            
        except Exception as e:
            logger.error(f"❌ Self-evolution failed: {e}")
    
    def discover_missing_features(self):
        """የትኞቹ ፊቸሮች እንደጎደሉ ይለያል"""
        prompt = """
        Analyze the current EthAfri marketplace system and identify 10 missing advanced features.
        
        Current capabilities:
        - Self-healing, Autonomous coding, Multi-AI consensus
        - Web scraping, Competitive intelligence, Multi-site management
        - A/B testing, SEO optimization
        
        Return JSON with key 'features' containing list of objects with:
        - 'name': feature name (with emoji)
        - 'description': what it does
        - 'priority': 1-10 (10 = highest)
        - 'file': proposed file name
        - 'business_impact': 1-10
        - 'implementation_complexity': 1-10
        """
        
        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))
        
        if data and 'features' in data:
            self.pending_features = data['features']
            logger.info(f"✅ Discovered {len(self.pending_features)} missing features")
            self._save_to_db('pending', self.pending_features)
        
        return self.pending_features
    
    def prioritize_features(self):
        """ፊቸሮችን በደረጃ ይደረድራል"""
        self.pending_features.sort(
            key=lambda x: (
                x.get('priority', 0) * 2 + 
                x.get('business_impact', 0) * 1.5 - 
                x.get('implementation_complexity', 0) * 0.5
            ),
            reverse=True
        )
        return self.pending_features
    
    def create_feature(self, feature):
        """አንድ የተወሰነ ፊቸር ይፈጥራል"""
        logger.info(f"🔨 Creating feature: {feature['name']}")
        
        code = self._generate_code(feature)
        if not code:
            return False
        
        file_name = feature.get('file', 'views')
        result = apply_code_change(
            site=self.site,
            file_key=file_name,
            new_content=code,
            reason=f"Self-created: {feature['name']}",
            target_name=feature.get('target_name')
        )
        
        self._log_creation(feature, result.get('success', False))
        return result.get('success', False)
    
    def _generate_code(self, feature):
        """ለፊቸር ኮድ ያመነጫል"""
        prompt = f"""
        Create complete Django 4/5 Python implementation for:
        
        Feature: {feature['name']}
        Description: {feature['description']}
        
        Requirements:
        - Proper error handling and logging
        - Docstrings
        - Production-ready code
        """
        return ask_master_ai_smart(prompt, task_type="coding")
    
    def _save_to_db(self, key, data):
        """መረጃን በዳታቤዝ ውስጥ ያስቀምጣል"""
        if not self.SiteConfig:
            return
        try:
            self.SiteConfig.objects.update_or_create(
                key=f"FEATURES_{key.upper()}_{self.site.name}",
                defaults={'value': {
                    'data': data,
                    'last_updated': timezone.now().isoformat()
                }}
            )
        except Exception as e:
            logger.error(f"Failed to save: {e}")
    
    def _log_creation(self, feature, success):
        """የፊቸር ፍጠር ይመዘግባል"""
        if not self.SelfHealingLog:
            return
        try:
            self.SelfHealingLog.objects.create(
                site=self.site,
                error_message=f"Feature: {feature['name']} - {'✅' if success else '❌'}",
                solution_sql=json.dumps(feature),
                resolved=success
            )
        except Exception as e:
            logger.error(f"Failed to log: {e}")
    
    def _generate_evolution_report(self, created):
        """ሪፖርት ያዘጋጃል"""
        report = {
            'timestamp': timezone.now().isoformat(),
            'created': created,
            'pending': len(self.pending_features),
            'completed': len(self.completed_features)
        }
        
        if self.SiteConfig:
            try:
                self.SiteConfig.objects.update_or_create(
                    key=f"EVOLUTION_REPORT_{self.site.name}",
                    defaults={'value': report}
                )
                logger.info(f"📊 Report: {report}")
            except Exception as e:
                logger.error(f"Failed to save report: {e}")
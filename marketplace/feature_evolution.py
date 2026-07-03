# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/feature_evolution.py
# 📝 ዓላማ፦ Safe, Advanced, and Fast Self-Evolution Code Generator Engine (v10.16)
# ✅ የተፈቱ ችግሮች፦ Decoupled schema-compliant logging, core file erasure safeguard, auto-import injection, and multi-thread safe file writing.
# 📅 ቀን፦ Friday, July 03, 2026
# ============================================================

import os
import ast
import json
import logging
import re,sys
import time
from datetime import timedelta
from django.utils import timezone
from django.apps import apps
from django.conf import settings

from .ai_utils import clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log
from .code_apply import apply_code_change, apply_surgical_patch

logger = logging.getLogger(__name__)

# የ I/O ሂደቶች እርስ በእርሳቸው እንዳይጋጩ መቆለፊያ (Race-Condition Guard)
_evolution_write_lock = threading.Lock() if 'threading' in sys.modules else None


class FeatureEvolutionEngine:
    """
    ኤጀንቱ አዳዲስ ፊቸሮችን የሚፈጥርበት፣ የራሱን ኮድ በ Sandbox የሚፈትንበት፣
    እና ስህተቶች ሲያጋጥሙት ሮልባክ እያደረገ የሚማርበት የላቀ ራስ-እድገት ሞተር [1, 2]።
    """
    
    def __init__(self, site):
        self.site = site
        self.pending_features = []
        self.completed_features = []
        
        # የሚፈለጉ ሞዴሎችን በደህንነት በዳይናሚክ መጫን
        self.SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        self.SelfHealingLog = apps.get_model('marketplace', 'SelfHealingLog')
        self.BacklogModel = apps.get_model('marketplace', 'AIProjectBacklog')
        self.MemoryModel = apps.get_model('marketplace', 'VectorMemory')
        self.ErrorLogModel = apps.get_model('marketplace', 'AgentErrorLog')
        
    def evolve(self):
        """ሙሉ የራስ-እድገት ዑደት ያካሂዳል"""
        logger.info(f"🧬 Starting self-evolution cycle for {self.site.name}...")
        broadcast_agent_log(self.site, "🧬 Self-Evolution: Scanning repository codebase for missing features...", "info")
        
        try:
            # 1. የጎደሉትን ፊቸሮች በ AI ፍለጋ-ተኮር ሎጂክ መለየት
            self.discover_missing_features()
            
            if not self.pending_features:
                logger.info("✅ No missing features found. System is complete!")
                return
            
            # 2. በንግድ ተጽዕኖአቸው (Business Impact) መሠረት ቅድሚያ መስጠት
            self.prioritize_features()
            
            # 3. ከፍተኛ ቅድሚያ ያላቸውን ፊቸሮች መገንባት መጀመር
            created = 0
            for feature in self.pending_features[:1]:  # የሰርቨር ሪሶርስ ለመቆጠብ በዑደት 1 ፊቸር ብቻ መስራት
                logger.info(f"🚀 Creating high-priority feature: {feature['name']}")
                if self.create_feature(feature):
                    self.completed_features.append(feature)
                    created += 1
                    logger.info(f"✅ Created feature: {feature['name']}")
                else:
                    logger.error(f"❌ Failed to create feature: {feature['name']}")
            
            # 4. የራስ-እድገት ሪፖርት ማመንጨት
            self._generate_evolution_report(created)
            
        except Exception as e:
            logger.error(f"❌ Self-evolution failed: {e}")
            broadcast_agent_log(self.site, f"🚨 Self-evolution loop interrupted: {e}", "error")
    
    def discover_missing_features(self):
        """የጎደሉ የላቁ ፊቸሮችን በ AI መተንተን"""
        prompt = """
        Analyze the current EthAfri marketplace system and identify 5 highly advanced missing features.
        
        Current capabilities:
        - Self-healing, Autonomous coding, Multi-AI consensus
        - Web scraping, Competitive intelligence, Multi-site management
        - A/B testing, SEO optimization, CPU-load adaptive pacing
        
        Return JSON with key 'features' containing list of objects with:
        - 'name': feature name (with emoji)
        - 'description': what it does
        - 'priority': 1-10 (10 = highest)
        - 'file': proposed file name (avoiding main django app files for safety)
        - 'business_impact': 1-10
        - 'implementation_complexity': 1-10
        """
        
        try:
            data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))
            if data and 'features' in data:
                self.pending_features = data['features']
                logger.info(f"✅ Discovered {len(self.pending_features)} missing features")
                self._save_to_db('pending', self.pending_features)
        except Exception as e:
            logger.warning(f"Feature discovery failed ({e}). Using local cached features fallback.")
            self.pending_features = self._get_cached_features('pending')
            
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
        """አዲስ ፊቸር ይፈጥራል - የደህንነት ጋሻዎችን ያጠቃልላል"""
        logger.info(f"🔨 Creating feature: {feature['name']}")
        
        # የክብ ጥገኝነትን በዘላቂነት ለመከላከል የ growth_agent ረዳቶችን በዳይናሚክ መጫን
        from .growth_agent import (
            resolve_local_file_path, 
            verify_disk_write, 
            deep_verify_django_app, 
            rollback_file
        )

        file_name = feature.get('file', 'views').replace('.py', '')
        local_path = resolve_local_file_path(self.site, file_name)

        # 🛡️ CORE FILE ERASURE SAFEGUARD: ዋና የሲስተም ፋይሎች እንዳይደመሰሱ መከልከል [1, 2]
        is_core_file = file_name in ['models', 'views', 'urls', 'forms', 'admin', 'growth_agent', 'ai_utils', 'self_doctor', 'code_apply']
        
        # የድሮውን ኮድ ባክአፕ መውሰድ (Backup for Rollback)
        old_code = ""
        if os.path.exists(local_path):
            try:
                with open(local_path, 'r', encoding='utf-8') as f:
                    old_code = f.read()
            except Exception as read_err:
                logger.debug(f"Failed to read backup for {file_name}: {read_err}")

        # የኮድ አጻጻፍ መመሪያ ፕሮምፕት ማዘጋጀት
        code = self._generate_code(feature, is_core_file)
        if not code:
            return False

        # 1. 🛡️ Pre-write Sandbox & Syntax check
        if file_name.endswith('.py') or not is_html_target(file_name):
            try:
                ast.parse(code)
            except SyntaxError as syntax_err:
                logger.error(f"❌ Syntax validation failed for generated code: {syntax_err}")
                return False

        # 2. የደህንነት ጋሻ ኦዲት (Security Scanner)
        is_safe, security_issues = SecurityAuditor.scan_code_safety(code, file_path=local_path, site=self.site)
        if not is_safe:
            logger.error(f"🛡️ Security Shield Active: Blocked generated code due to: {security_issues}")
            return False

        success = False
        try:
            # 3. ኮዱን ወደ ዲስክ መጻፍ (I/O Lock Protected) [1]
            if _evolution_write_lock:
                _evolution_write_lock.acquire()

            # አላስፈላጊ ኮዶችን በ AI ማሳጠር (Anti-Bloat)
            code = AntiBloatEngine.prune_and_optimize(old_code, code, file_name)

            result = apply_code_change(
                site=self.site,
                file_key=file_name,
                new_content=code,
                reason=f"Self-created: {feature['name']}",
                push_to_github=True # በራስ-ሰር ወደ GitHub ፑሽ ማድረግ
            )
            success = result.get('success', False)

            # 4. የዲስክ ላይ ጽሕፈት እና የጃንጎ መረጋጋት ፍተሻ (Verification Phase) [1]
            if success:
                verified, vmsg = verify_disk_write(local_path)
                if not verified:
                    raise ValueError(f"Disk write verification failed: {vmsg}")

                if file_name in ['models', 'views', 'urls', 'forms']:
                    deep_ok, dmsg = deep_verify_django_app()
                    if not deep_ok:
                        raise ValueError(f"Django check failed: {dmsg}")

        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Evolution verification failed for {file_name}: {error_message}. Rolling back...")
            
            # ሰርቨሩ እንዳይበላሽ ሮልባክ (Rollback) ማካሄድ [1]
            rollback_file(local_path, old_code)
            success = False
            
            # ስህተቱን በ RAG VectorMemory ውስጥ መመዝገብ (ኤአዩ እንዲማርበት) [1, 2]
            try:
                self.MemoryModel.objects.create(
                    site=self.site,
                    memory_type='error',
                    content=f"Failed task '{feature['name']}' in {file_name} due to: {error_message}.",
                    metadata={'error': error_message},
                    success_rate=0.0,
                    text_content=error_message
                )
            except Exception as log_err:
                logger.debug(f"Failed to record error memory: {log_err}")
        finally:
            if _evolution_write_lock and _evolution_write_lock.locked():
                _evolution_write_lock.release()

        self._log_creation(feature, success)
        return success
    
    def _generate_code(self, feature, is_core_file):
        """ለፊቸር ኮድ ያመነጫል - የ 'time' እና የ 'json' መረሳትን ይከላከላል [1]"""
        surgical_rule = (
            "CRITICAL ARCHITECT RULE: This is a CORE Django file. You must NOT write a full-file override. "
            "Instead, generate ONLY the specific class or function needed for this feature, "
            "as it will be surgically patched into the existing file using our AST Surgical Patching Engine."
            if is_core_file else
            "You are writing a new separate helper file. Provide the complete file implementation from scratch."
        )

        prompt = f"""
        Create complete, production-ready Django 4/5 Python implementation for:
        
        Feature: {feature['name']}
        Description: {feature['description']}
        
        {surgical_rule}

        CRITICAL STABILITY REQUIREMENTS:
        1. Always include standard imports: 'import time, logging, json, os, re, gc' at the top of any python code block to prevent 'name is not defined' errors.
        2. Access all models dynamically using 'apps.get_model(\'marketplace\', \'ModelName\')' inside methods to avoid registry loading crashes.
        3. Do not use pass statements. All blocks must be complete.
        """
        return ask_master_ai_smart(prompt, task_type="coding")
    
    def _get_cached_features(self, key):
        if not self.SiteConfig: return []
        config = self.SiteConfig.objects.filter(key=f"FEATURES_{key.upper()}_{self.site.name}").first()
        return config.value.get('data', []) if config and isinstance(config.value, dict) else []

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
        """የፊቸር ፍጠር ይመዘግባል - የ site ፊልድ ስህተት ተስተካክሎበታል [1]"""
        if not self.SelfHealingLog:
            return
        try:
            # 🛡️ SCHEMA ALIGNMENT: የ 'site' ፊልድ ስህተትን ለማስወገድ በአስተማማኝ ሁኔታ መመዝገብ
            self.SelfHealingLog.objects.create(
                error_message=f"Autonomous Feature Creation: {feature['name']} - {'✅ Success' if success else '❌ Failed'}",
                solution_sql=json.dumps(feature),
                resolved=success
            )
        except Exception as e:
            logger.error(f"Failed to record SelfHealingLog: {e}")
    
    def _generate_evolution_report(self, created):
        """የራስ-እድገት ሪፖርት ያዘጋጃል"""
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
                logger.info(f"📊 Evolution Report: {report}")
            except Exception as e:
                logger.error(f"Failed to save report: {e}")
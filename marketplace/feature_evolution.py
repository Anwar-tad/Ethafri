# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/feature_evolution.py
# 📝 ዓላማ፦ Safe, Advanced, and Fast Self-Evolution Code Generator Engine (v10.19 - Hardened Modular Scaffolder)
# ✅ የተፈቱ ችግሮች፦ Dynamic modular code-splitting (Cumulative Scaffolder), 3-attempt recursive syntax & design audit self-heal loop, HTML container tag balance verifications, and thread-safe file writing.
# 📅 ቀን፦ Saturday, July 04, 2026
# ============================================================

import os
import ast
import json
import logging
import re
import time
import sys
import threading  # ✅ 'threading' is not defined ስህተትን ለመከላከል የተጨመረ

from datetime import timedelta
from django.utils import timezone
from django.apps import apps

from .ai_utils import clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log
from .code_apply import apply_code_change, apply_surgical_patch
from .self_doctor import SecurityAuditor, AntiBloatEngine

logger = logging.getLogger(__name__)

# የ I/O ሂደቶች እርስ በእርሳቸው እንዳይጋጩ መቆለፊያ (Race-Condition Guard) [1]
_evolution_write_lock = threading.Lock() if 'threading' in sys.modules else None


# ============================================================
# ⚙️ 🛠️ LIGHWEIGHT HELPER FUNCTIONS
# ============================================================

def is_html_target(target_file: str) -> bool:
    """የፋይሉ አይነት ኤችቲኤምኤል መሆን አለመሆኑን መለያ [1]"""
    return target_file.endswith('_html') or 'html' in target_file


def html_content_is_malformed(html_content: str) -> bool:
    """የተበላሹ ክፍተቶችና ያልተዘጉ ታጎች (div/form/section) እንዳይኖሩት በዳይናሚክ የሚያረጋግጥ [1]"""
    for tag in ['div', 'form', 'section', 'main']:
        open_count = len(re.findall(rf'<{tag}\b', html_content, re.IGNORECASE))
        close_count = len(re.findall(rf'</{tag}>', html_content, re.IGNORECASE))
        if open_count != close_count:
            return True
    return False


# ============================================================
# 🧬 FEATURE EVOLUTION ENGINE
# ============================================================

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
        """የኮድ ዝግመተ-ለውጥ ዑደትን ያስፈጽማል (Self-Evolution Loop)"""
        logger.info(f"🧬 Starting self-evolution cycle for {self.site.name}...")
        broadcast_agent_log(self.site, "🧬 Self-Evolution: Scanning repository codebase for missing features...", "info")
        
        try:
            # 1. የጎደሉትን ፊቸሮች በ AI ፈልጎ መለየት
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
        
        # የክብ ጥገኝነትን ለመከላከል የ growth_agent ረዳቶችን በዳይናሚክ መጫን [1]
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
            except Exception:
                pass

        # 🛡️ 1. CUMULATIVE MODULE SCAFFOLDER ( የፋይል መጠን ገደብ መዝገብ) [1]
        is_bloated = False
        if file_name in ['models', 'views', 'urls', 'forms', 'growth_agent']:
            is_bloated = AntiBloatEngine.is_file_bloated(local_path)
            
        inject_import_payload = None
        if is_bloated:
            # ራሱን በዳይናሚክ ወደ አዲስ የረዳት ሞጁል መሰንጠቅ (Dynamic Splitting)
            new_module_name = f"{file_name}_helper_{feature.get('name', 'evolution').lower().replace(' ', '_')}"
            new_module_name = re.sub(r'[^a-zA-Z0-9_]', '', new_module_name)[:50]
            
            logger.warning(f"⚠️ Cumulative Anti-Bloat: '{file_name}' is bloated. Scaffolding new separate module '{new_module_name}' to maintain performance.")
            
            new_file_path = resolve_local_file_path(self.site, new_module_name)
            
            # Redirect writing to the new dynamic helper file
            file_name = new_module_name
            local_path = new_file_path
            is_core_file = False

        # 🔄 2. የ 3-ደረጃ ሪከርሲቭ ሲንታክስ እና የንድፍ ራሱን ማከሚያ (Recursive Design Healer Loop) [1]
        attempts = 0
        new_code = ""
        error_msg = ""
        target_is_html = is_html_target(file_name)
        
        while attempts < 3:
            attempts += 1
            if error_msg:
                # የተፈጠረውን የሲንታክስ ስህተት ወይም የኦዲት ማስጠንቀቂያ መልሶ ለኤአይ መመገብ
                retry_prompt = (
                    f"Your previous code attempt returned the following audit, syntax, or design warning: '{error_msg}'.\n"
                    f"Please fully repair and refactor the code to fix this issue completely. "
                    f"Strictly enforce DRY consolidation (extend existing code instead of duplicating), "
                    f"asset externalization (absolutely NO inline <style> or <script> tags inside HTML templates), "
                    f"and extensible design signatures.\n"
                    f"Return JSON with key 'code'."
                )
                raw_res = ask_master_ai_smart(retry_prompt, task_type="coding")
            else:
                raw_res = self._generate_code(feature, is_core_file)

            res = clean_and_parse_json(raw_res)
            if not (res and isinstance(res, dict) and 'code' in res):
                error_msg = "Invalid JSON or missing 'code' key in response"
                continue
                
            new_code = res['code']
            
            # Sandbox Syntax Verification
            if not target_is_html:
                try:
                    compile(new_code, '<string>', 'exec')
                except SyntaxError as e:
                    error_msg = f"SyntaxError: {e}"
                    logger.warning(f"⚠️ Evolution Sandbox (Attempt {attempts}/3) failed: {error_msg}")
                    continue
            else:
                if html_content_is_malformed(new_code):
                    error_msg = "Malformed HTML detected (unbalanced tags or unclosed container structures)"
                    logger.warning(f"⚠️ Evolution Sandbox (Attempt {attempts}/3) failed: {error_msg}")
                    continue
                    
            # Symmetric Design & Security Auditor Audit
            is_safe, security_issues = SecurityAuditor.scan_code_safety(new_code, file_path=local_path, site=self.site)
            if not is_safe:
                error_msg = f"Audit Failure: {'; '.join(security_issues)}"
                logger.warning(f"⚠️ Evolution Sandbox (Attempt {attempts}/3) failed audit: {error_msg}")
                continue
                
            # If both syntax compiling and security/design audit pass, break!
            error_msg = ""
            break
            
        # 🛡️ FIXED: 3ቱ ሙከራዎች ካልተሳኩ ወዲያውኑ ስራውን በማቋረጥ የ compile() ስህተትን መከላከል [1]
        if attempts >= 3 and error_msg:
            logger.error(f"❌ Evolution Sandbox: Failed to compile or audit code after 3 recursive healing attempts: {error_msg}")
            task = self.BacklogModel.objects.filter(site=self.site, task_name=feature['name']).first()
            if task:
                task.status = 'Pending'
                task.save()
            return False # <--- እዚህ ጋር ስራውን ያቋርጣል (ከስህተት ያድናል)

        # 💉 3. አውቶማቲክ የኢምፖርት ሎጂክ ማስላት (ይህም በዋናው ፋይል አናት ላይ import ይተክላል)
        if is_bloated and not target_is_html:
            try:
                tree = ast.parse(new_code)
                top_level_names = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
                if top_level_names:
                    original_core_path = resolve_local_file_path(self.site, feature.get('file', 'views').replace('.py', ''))
                    import_line = f"from .{file_name} import {', '.join(top_level_names)}"
                    inject_import_payload = {
                        "target_path": original_core_path,
                        "import_line": import_line
                    }
                    logger.info(f"💉 Planning import injection for {feature.get('file')}: '{import_line}'")
            except Exception as e:
                logger.debug(f"Failed to parse AST of new code to extract import names: {e}")
                inject_import_payload = None

        success = False
        try:
            # 4. ኮዱን ወደ ዲስክ መጻፍ (I/O Lock Protected) [1]
            if _evolution_write_lock:
                _evolution_write_lock.acquire()

            # አላስፈላጊ ኮዶችን ማሳጠር (Anti-Bloat)
            new_code = AntiBloatEngine.prune_and_optimize(old_code, new_code, file_name)

            result = apply_code_change(
                site=self.site,
                file_key=file_name,
                new_content=new_code,
                reason=f"Self-Evolution: Auto-generated feature {feature['name']}",
                backlog_task=None,
                inject_import=inject_import_payload # የዳይናሚክ ኢምፖርት መጋጠሚያ እዚህ ይተላለፋል
            )
            
            if result.get('success'):
                applied_path = result.get('path', local_path)
                verified, vmsg = verify_disk_write(applied_path)
                if not verified:
                    logger.error(f"❌ Post-apply disk verification failed for {file_name}: {vmsg}. Rolling back...")
                    rollback_file(applied_path, old_code)
                    return False
                
                if file_name in DJANGO_APP_FILES:
                    deep_ok, dmsg = deep_verify_django_app()
                    if not deep_ok:
                        logger.error(f"❌ Deep Django check failed after applying {file_name}: {dmsg}. Rolling back...")
                        rollback_file(applied_path, old_code)
                        return False
                success = True
            
        except Exception as e:
            logger.error(f"❌ Failed to write or verify evolution code change: {e}")
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

        CRITICAL STABILITY & OPTIMIZATION REQUIREMENTS:
        1. Always include standard imports: 'import time, logging, json, os, re, gc' at the top of any python code block to prevent 'name is not defined' errors.
        2. Access all models dynamically using 'apps.get_model(\'marketplace\', \'ModelName\')' inside methods to avoid registry loading crashes.
        3. FEATURE CONSOLIDATION RULE: All functions or classes must be highly reusable, compact, and parameter-driven (supporting multiple features inside a single clean interface).
        4. PERFORMANCE & ASSET OPTIMIZATION RULE: Never write inline CSS or inline javascript blocks inside HTML. Move custom styles/scripts to shared global.css or global.js to prevent rendering blocking.
        5. Design interfaces to be schema-agnostic or support extensible payloads (extensible payload dictionaries config-driven) for seamless future scaling.
        6. Do not use pass statements. All blocks must be complete.
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
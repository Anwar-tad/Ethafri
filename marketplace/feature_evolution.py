# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/feature_evolution.py
# 📝 ስሪት፦ v11.00 (Dynamic Self-Evolution Engine - Spy-to-Evolution Edition)
# ✅ የተፈቱ ችግሮች፦ Dynamic app model registry loading to prevent AppRegistryNotReady,
#                    and robust JSONField type checking added to evolution cooldown to prevent parsing crashes (v11.00).
# 📅 ቀን፦ Friday, July 24, 2026
# ============================================================

import os
import re
import ast
import json
import logging
import hashlib
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.db import connections
from django.apps import apps
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger(__name__)


# ============================================================
# 🛡️ 1. TOKEN-OPTIMIZED CODEBASE CONTEXT SCANNER
# ============================================================
def _scan_local_marketplace_code(site) -> Dict[str, str]:
    """
    የስርዓቱን አሁናዊ የኮድ ይዘት በከፊል በመቃኘት (ቶከን ለመቆጠብ ለእያንዳንዱ ፋይል ቢበዛ 
    የመጀመሪያዎቹን 2000 ፊደላት ብቻ በመውሰድ) ለ AI CTO አርክቴክት መረጃ ያዘጋጃል
    """
    base_dir = str(settings.BASE_DIR)
    app_name = 'marketplace'
    
    if site and site.name != 'primary':
        if site.repo_path:
            if site.repo_path.startswith('http') or 'github.com' in site.repo_path:
                base = os.path.join('/tmp', 'ethafri_agent', site.name)
            else:
                base = site.repo_path
        else:
            base = os.path.join('/tmp', 'ethafri_agent', site.name)
    else:
        base = base_dir

    target_files = {
        'models': 'models.py',
        'views': 'views.py',
        'urls': 'urls.py',
        'forms': 'forms.py',
        'admin': 'admin.py'
    }
    
    code_state = {}
    for key, relative_name in target_files.items():
        full_path = os.path.join(base, app_name, relative_name)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    code_state[key] = f.read()[:2000]
            except Exception:
                code_state[key] = "❌ ERROR_READING"
        else:
            code_state[key] = "❌ MISSING_FILE"
            
    return code_state


# ============================================================
# 🧬 2. FEATURE EVOLUTION ENGINE (THE PLANNER)
# ============================================================
class FeatureEvolutionEngine:
    """የኤጀንቱን የኮድ ይዘት እና ብቃት በ AI አማካኝነት በዳይናሚክ መንገድ የሚያሳድግ ዋና ሎጂክ"""

    def __init__(self, site):
        self.site = site

    def evolve(self):
        """የእድገት ዑደቱን ያስፈጽማል (የተፎካካሪ ስለላ ታሪክን ከአሁኑ ኮድ ጋር በማወዳደር ክፍተቶችን ይለያል)"""
        logger.info(f"🧬 FeatureEvolution: Initializing R&D evolution cycle for site '{self.site.name}'...")
        
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
        Product = apps.get_model('marketplace', 'Product')
        VectorMemory = apps.get_model('marketplace', 'VectorMemory')
        
        if not SiteConfig or not AIProjectBacklog:
            return

        cooldown_key = f"LAST_SELF_EVOLUTION_GEN_{self.site.name}"
        last_gen = SiteConfig.objects.filter(key=cooldown_key).first()
        
        # 🛡️ ቶከን መቆጠቢያ፦ አዲስ የራስ-ዕድገት ፊቸር ታስክ በየ 12 ሰዓቱ ቢበዛ 1 ጊዜ ብቻ እንዲፈጠር መገደብ
        if last_gen and last_gen.value:
            try:
                # 🛡️ FIXED: JSONField String/Dict Parsing safety checks across DB drivers
                val_data = last_gen.value
                if isinstance(val_data, str):
                    val_data = json.loads(val_data)
                
                if isinstance(val_data, dict):
                    last_time_str = val_data.get('time', '')
                    if last_time_str:
                        last_time = datetime.fromisoformat(last_time_str)
                        if timezone.is_naive(last_time):
                            last_time = timezone.make_aware(last_time)
                        if timezone.now() - last_time < timedelta(hours=12):
                            logger.info(f"🧬 FeatureEvolution: Engine is on 12-hour cooldown. Skipping generation to save API tokens.")
                            return
            except Exception as e:
                logger.warning(f"Error parsing evolution timestamp: {e}")

        existing_pending = AIProjectBacklog.objects.filter(
            site=self.site, 
            status='Pending',
            task_name__icontains="SELF-EVOLUTION"
        ).exists()
        
        if existing_pending:
            logger.info("🧬 FeatureEvolution: Active pending evolution tasks exist in queue. Postponing new feature research.")
            return

        code_context = _scan_local_marketplace_code(self.site)
        
        try:
            products_count = Product.objects.filter(site=self.site, is_active=True).count() if Product else 0
        except Exception:
            products_count = 0

        competitor_insights = []
        if VectorMemory:
            try:
                insights = VectorMemory.objects.filter(site=self.site, memory_type='insight').order_by('-id')[:5]
                competitor_insights = [i.content for i in insights]
            except Exception as e:
                logger.debug(f"Failed to query competitor insights: {e}")

        if not competitor_insights:
            competitor_insights = [
                "Trending features from Jumia: Advanced product filtering by category/price.",
                "Competitor benchmark: Secure seller panel to edit and deactivate listings dynamically.",
                "Local trend: Instant search suggestions in Amharic on home page."
            ]
            
        system_summary = {
            "niche": self.site.niche or "general",
            "build_phase": self.site.build_phase,
            "product_count": products_count,
            "code_summary": {k: "Present" if "❌" not in v else "Missing" for k, v in code_context.items()}
        }

        logger.info(f"🧠 FeatureEvolution: Asking Master AI CTO to architect the next optimal feature...")

        prompt = f"""
        Act as an Enterprise AI Chief Technology Officer (CTO). 
        Our dynamic Django 4/5 marketplace system state is: {json.dumps(system_summary, ensure_ascii=False)}
        
        Here are code snippet summaries for context (imports and class definitions):
        {json.dumps(code_context, ensure_ascii=False)}

        We recently scraped competitors and discovered these highly requested features:
        {json.dumps(competitor_insights, ensure_ascii=False)}
        
        Your task is to identify exactly ONE missing business feature in our codebase from the scraped list. 
        Rank the missing features by strict priority guidelines:
        1. Priority 1 (Critical): Core product and seller operations (e.g. Seller panel to edit/deactivate listings).
        2. Priority 2 (High): Search, advanced filters (price range, region), categories, or UX optimizations.
        3. Priority 3 (Medium): Secondary marketing or social share tools.
        
        Check the current codebase context. If we already have a class or view that satisfies Priority 1, organically move to Priority 2, and so on. Never generate a task for a feature that is already present in our code.
        
        Format Requirement: Return strictly in JSON format with exactly one key 'architected_feature':
        {{
            "task_name": "🧠 SELF-EVOLUTION: [A short descriptive name of the advanced feature]",
            "target_file": "[The file to insert the code, e.g. 'views', 'models', 'urls', 'forms']",
            "priority": "High",
            "description": "[A highly detailed technical specification explaining exactly what code functions/classes the builder should write and append inside the target file. Write the complete prompt guidelines for the builder.]",
            "business_impact_score": [An integer from 1 to 10]
        }}
        """

        from .ai_utils import ask_master_ai_smart, clean_and_parse_json, broadcast_agent_log
        try:
            response = ask_master_ai_smart(prompt, task_type="self_evolution")
            data = clean_and_parse_json(response)
            
            feature = data.get('architected_feature') if data else None
            
            if feature and isinstance(feature, dict) and feature.get('task_name'):
                task_name = feature['task_name'][:200]
                
                task_exists = AIProjectBacklog.objects.filter(site=self.site, task_name=task_name).exists()
                if not task_exists:
                    AIProjectBacklog.objects.create(
                        site=self.site,
                        task_name=task_name,
                        target_file=feature.get('target_file', 'views'),
                        priority=feature.get('priority', 'High'),
                        status='Pending',
                        description=f"Self-Architected Feature Spec: {feature.get('description', '')}",
                        business_impact_score=int(feature.get('business_impact_score', 8)),
                        trigger_condition='Autonomous R&D Self-Evolution Loop'
                    )
                    
                    SiteConfig.objects.update_or_create(
                        key=cooldown_key,
                        defaults={'value': {'time': timezone.now().isoformat(), 'status': 'success'}}
                    )
                    
                    broadcast_agent_log(
                        self.site, 
                        f"🧬 Self-Evolution: Organically identified missing feature task: '{task_name}' based on competitor spy and codebase gap analysis!", 
                        "success"
                    )
                else:
                    logger.info(f"🧬 FeatureEvolution: Feature task '{task_name}' already exists in backlog.")
            else:
                logger.warning("🧬 FeatureEvolution: AI returned invalid or empty feature architecture schema.")
                
        except Exception as e:
            logger.error(f"❌ FeatureEvolution Engine failed: {e}", exc_info=True)
        finally:
            try:
                connections.close_all()
            except Exception:
                pass
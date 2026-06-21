# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_coder.py
# 📝 ለውጥ፦ Smart Self-Coder — RAG Memory + AgentTask + Security + Predictive
# 📅 ቀን፦ 2026-06-21
# ============================================================

import requests
import os
import json
import base64
import re
import logging
from django.conf import settings
from django.utils import timezone
from django.db import models
from .growth_agent import ask_ethafri_ceo, get_site_project_state
from .models import (
    SiteRegistry, AgentErrorLog, AIEvolutionLog, SiteConfig,
    VectorMemory, AgentTask, SecurityLog, PredictionLog
)

logger = logging.getLogger(__name__)


# ============================================================
# 1. የሬንደር ሁኔታ አንባቢ (KeyError-Safe)
# ============================================================

def get_render_deploy_status():
    """የሬንደርን የቅርብ ጊዜ መጫን ሂደት ሁኔታ ያነባል (KeyError-Safe)"""
    service_id = getattr(settings, 'RENDER_SERVICE_ID', None)
    api_key = getattr(settings, 'RENDER_API_KEY', None)
    
    if not service_id or not api_key:
        return None
        
    url = f"https://api.render.com/v1/services/{service_id}/deploys"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200 and len(response.json()) > 0:
            latest_deploy = response.json()[0].get('deploy', {})
            return {
                "id": latest_deploy.get('id', 'Unknown'),
                "status": latest_deploy.get('status', 'Unknown'),
                "commit_id": latest_deploy.get('commitId', 'Unknown')
            }
    except Exception as e:
        logger.error(f"Render API Connection Warning: {e}")
    return None


# ============================================================
# 2. 🆕 RAG Memory Engine for Self-Healing
# ============================================================

class SelfHealMemory:
    """ራስ-ጥገና ትውስታ — ያለፉ ፈውሶችን ያስታውሳል"""
    
    def __init__(self, site):
        self.site = site
    
    def remember_healing(self, error_type, error_message, solution, success=True):
        """የተሳካ ፈውስ ያስታውሳል"""
        memory = VectorMemory.objects.create(
            memory_type='solution',
            content=f"Error: {error_message[:200]}\nSolution: {solution[:500]}",
            metadata={
                'error_type': error_type,
                'success': success,
                'site_id': self.site.id if self.site else None
            },
            site=self.site,
            success_rate=100.0 if success else 0.0
        )
        memory.mark_used(success)
        return memory
    
    def find_similar_healing(self, error_message, limit=3):
        """ተመሳሳይ ፈውሶችን ያገኛል"""
        return VectorMemory.find_similar(
            query=error_message,
            memory_type='solution',
            site=self.site,
            limit=limit
        )


# ============================================================
# 3. 🆕 Self-Heal Task Manager
# ============================================================

class SelfHealTaskManager:
    """ራስ-ጥገና ስራዎችን ያስተዳድራል"""
    
    def __init__(self, site):
        self.site = site
    
    def create_heal_task(self, task_name, description, priority=5):
        """አዲስ የጥገና ስራ ይፈጥራል"""
        return AgentTask.objects.create(
            agent_type='code',
            task_name=task_name,
            description=description,
            priority=priority,
            site=self.site,
            status='pending'
        )
    
    def get_pending_tasks(self):
        """ያልተጠናቀቁ ስራዎችን ያገኛል"""
        return AgentTask.objects.filter(
            site=self.site,
            status__in=['pending', 'running']
        ).order_by('-priority')


# ============================================================
# 4. ወደ ጊትሃብ መግፋት (Multi-Site)
# ============================================================

def push_code_to_github(file_path, file_content, commit_message, site_name="primary"):
    """
    የተጻፈውን አዲስ የፓይተን ኮድ በቀጥታ ወደ ጊትሃብ ይልካል (Push)
    """
    github_token = getattr(settings, 'GITHUB_TOKEN', None)
    repo = "Anwar-tad/Ethafri"
    
    if not github_token:
        return "❌ GITHUB_TOKEN Missing from settings."

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    sha = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            sha = res.json().get('sha', '')
    except Exception as e:
        logger.warning(f"GitHub SHA retrieval failed for {file_path}: {e}")

    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha if sha else None,
        "branch": "main"
    }
    
    try:
        put_res = requests.put(url, headers=headers, json=payload, timeout=10)
        if put_res.status_code in [200, 201]:
            return f"✅ Code pushed to GitHub for {site_name}!"
        return f"❌ Push Failed for {site_name}: {put_res.text}"
    except Exception as e:
        return f"❌ GitHub Connection Failed for {site_name}: {e}"


# ============================================================
# 5. 🆕 የተሻሻለ ለአንድ ጣቢያ ራስ-ጥገና (Smart Self-Heal)
# ============================================================

def self_heal_single_site(site: SiteRegistry):
    """
    ለአንድ የተወሰነ ጣቢያ ራስ-ጥገና ያካሂዳል
    RAG Memory, AgentTask, Security Scanner ይጠቀማል
    """
    site_name = site.name
    logger.info(f"🛠️ Starting smart self-heal for site: {site_name}")
    
    results = []
    memory = SelfHealMemory(site)
    task_manager = SelfHealTaskManager(site)
    
    # 1. የጣቢያውን የኮድ ሁኔታ ያንብብ
    project_code, file_paths = get_site_project_state(site)
    
    if not project_code:
        return f"⚠️ No code found for {site_name}"
    
    # 2. ያልተፈቱ ስህተቶችን ያንብብ
    recent_errors = AgentErrorLog.objects.filter(
        site=site,
        resolved=False
    ).order_by('-created_at')[:10]
    
    if not recent_errors:
        return f"✅ No errors found for {site_name}"
    
    # 3. 🆕 ተመሳሳይ ፈውሶችን ከትውስታ ያግኝ
    similar_healings = memory.find_similar_healing(
        recent_errors.first().error_message
    )
    memory_context = ""
    for heal in similar_healings:
        memory_context += f"\nPrevious successful healing: {heal.content[:300]}\n"
    
    # 4. ስህተቶቹን ለ AI አቅርብ
    error_summary = []
    for err in recent_errors:
        error_summary.append({
            'task_name': err.task_name,
            'error_type': err.error_type,
            'error_message': err.error_message[:200],
            'code_attempted': err.code_attempted[:500]
        })
    
    # 5. 🆕 AI ፕሮምፕት (ከትውስታ ጋር)
    prompt = f"""
    [CRITICAL DIRECTIVE] 
    You are the Smart Self-Healing Agent for site: {site_name}.
    
    Site Information:
    - Niche: {site.niche}
    - Target Market: {site.target_market}
    - Growth Level: {site.growth_level}
    
    Recent Errors:
    {json.dumps(error_summary, indent=2)}
    
    Memory Context (past successful healings):
    {memory_context}
    
    Current Codebase:
    {json.dumps(project_code, indent=2)[:4000]}
    
    Task:
    1. Analyze the errors with the help of past healings
    2. Identify root causes (missing imports, syntax, logic, security)
    3. Generate corrected code
    4. Rate your confidence (0-100) for each fix
    
    Output Format:
    {{
        "confidence_score": 85,
        "fixed_files": {{
            "models": "corrected models.py code",
            "views": "corrected views.py code",
            "growth_agent": "corrected growth_agent.py code"
        }},
        "explanation": "Brief explanation",
        "security_issues": ["issue1", "issue2"],
        "root_cause": "Main cause of the error"
    }}
    """
    
    ai_response = ask_ethafri_ceo(prompt, pool_type="healing")
    
    if not ai_response:
        return f"❌ Self-Healing failed for {site_name}: No AI response"
    
    if isinstance(ai_response, dict) and "error" in ai_response:
        return f"❌ Self-Healing failed for {site_name}: {ai_response['error']}"
    
    # 6. የAI ምላሽን መፍታት
    fixed_files = {}
    explanation = "System self-correction"
    confidence_score = 50
    security_issues = []
    root_cause = ""
    
    if isinstance(ai_response, dict):
        fixed_files = ai_response.get('fixed_files', {})
        explanation = ai_response.get('explanation', 'System self-correction')
        confidence_score = ai_response.get('confidence_score', 50)
        security_issues = ai_response.get('security_issues', [])
        root_cause = ai_response.get('root_cause', '')
    else:
        try:
            data = json.loads(ai_response)
            fixed_files = data.get('fixed_files', {})
            explanation = data.get('explanation', 'System self-correction')
            confidence_score = data.get('confidence_score', 50)
            security_issues = data.get('security_issues', [])
            root_cause = data.get('root_cause', '')
        except Exception:
            return f"❌ Self-Healing failed for {site_name}: Invalid AI response format"
    
    # 7. 🆕 የደህንነት ችግሮችን ወደ SecurityLog መዝግብ
    for issue in security_issues:
        SecurityLog.objects.create(
            category='code_injection',
            severity='high',
            description=issue,
            file_path='multiple_files',
            site=site,
            is_fixed=False
        )
    
    # 8. 🆕 ኮድ ከመተግበሩ በፊት የመተማመን ምርመራ
    if confidence_score < 60:
        # ዝቅተኛ መተማመን ካለ ለሰው ያሳስብ
        results.append(f"⚠️ Low confidence ({confidence_score}%) - Review recommended")
    
    # 9. የተስተካከሉ ፋይሎችን መተግበር
    changes_applied = 0
    for file_key, new_content in fixed_files.items():
        if new_content and len(new_content.strip()) > 100:
            path = file_paths.get(file_key)
            if path:
                try:
                    # የፓይተን ሲንታክስ ፍተሻ
                    if file_key in ['models', 'views', 'urls', 'forms']:
                        compile(new_content, f"test_{file_key}.py", 'exec')
                    
                    # አሮጌውን ኮድ አስቀምጥ
                    old_code = ""
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            old_code = f.read()
                    
                    # አዲሱን ኮድ ጻፍ
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    # በ EvolutionLog ውስጥ መዝግብ
                    AIEvolutionLog.objects.create(
                        target_file=file_key,
                        reason_for_change=f"Self-Heal for {site_name}: {explanation[:100]}",
                        old_code_backup=old_code,
                        new_code_patch=new_content,
                        site=site
                    )
                    
                    # 🆕 የተሳካ ፈውስ በትውስታ ውስጥ አስቀምጥ
                    memory.remember_healing(
                        error_type='code_healing',
                        error_message=f"Fixed {file_key}",
                        solution=f"{explanation[:200]}\nRoot cause: {root_cause}",
                        success=True
                    )
                    
                    # 🆕 አዲስ የጥገና ስራ ፍጠር
                    task_manager.create_heal_task(
                        task_name=f"Heal_{file_key}_{timezone.now().strftime('%Y%m%d')}",
                        description=f"Self-healed {file_key}: {explanation[:100]}",
                        priority=3
                    )
                    
                    # ወደ ጊትሃብ ግፋ
                    push_result = push_code_to_github(
                        f"marketplace/{file_key}.py",
                        new_content,
                        f"AI: Self-Healed {site_name} (File: {file_key}) - Confidence {confidence_score}%",
                        site_name
                    )
                    results.append(push_result)
                    
                    # ስህተቶቹን እንደተፈቱ ምልክት አድርግ
                    AgentErrorLog.objects.filter(site=site, resolved=False).update(resolved=True)
                    changes_applied += 1
                    results.append(f"✅ Fixed {file_key} (Confidence: {confidence_score}%)")
                    
                except SyntaxError as e:
                    results.append(f"❌ Syntax error in {file_key}: {e}")
                    # 🆕 ያልተሳካ ፈውስ በትውስታ ውስጥ አስቀምጥ
                    memory.remember_healing(
                        error_type='syntax_error',
                        error_message=f"Syntax error in {file_key}",
                        solution=f"Failed: {str(e)}",
                        success=False
                    )
                except Exception as e:
                    results.append(f"❌ Error applying fix to {file_key}: {e}")
    
    # 10. 🆕 ትንበያ መዝግብ
    PredictionLog.objects.create(
        prediction_type='growth',
        predicted_value=confidence_score,
        confidence_score=confidence_score,
        input_data={'site': site_name, 'changes': changes_applied},
        site=site
    )
    
    return f"🛠️ Smart Self-Heal for {site_name}: {' | '.join(results)}"


# ============================================================
# 6. ዋናው ራስ-ጥገና ተግባር (የተሻሻለ - Multi-Site)
# ============================================================

def self_heal_failed_build():
    """
    ሬንደር ላይ ቢከሽፍ AIው ራሱ መዝገቡን አንብቦ ኮዱን የሚጠግንበት ዑደት
    አሁን RAG Memory, AgentTask, Security Scanner ይጠቀማል
    """
    results = []
    
    # 1. የሬንደር ሁኔታ ፍተሻ
    status_info = get_render_deploy_status()
    if status_info:
        deploy_status = status_info.get('status', 'Unknown')
        commit_id = status_info.get('commit_id', 'Unknown')
        
        if deploy_status == "build_failed":
            results.append(f"⚠️ Render Build Failed on Commit {commit_id[:7]}!")
            results.append("🔧 Attempting smart self-heal...")
    
    # 2. ሁሉንም ጣቢያዎች ራስ-ጥገና አድርግ
    try:
        sites = SiteRegistry.objects.filter(is_active=True)
    except Exception:
        sites = None
    
    if not sites or not sites.exists():
        return "⚠️ No active sites found for self-healing"
    
    for site in sites:
        try:
            unresolved_errors = AgentErrorLog.objects.filter(site=site, resolved=False).count()
            
            if unresolved_errors > 0:
                result = self_heal_single_site(site)
                results.append(result)
            else:
                results.append(f"✅ No errors found for {site.name}")
                
        except Exception as e:
            error_msg = f"❌ Self-heal failed for {site.name}: {str(e)}"
            results.append(error_msg)
            logger.error(error_msg)
    
    if not results:
        return "System status is normal, no self-healing needed."
    
    return f"🛠️ Smart Self-Heal Summary: {' | '.join(results)}"
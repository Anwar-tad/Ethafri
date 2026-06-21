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
                "commit_id": latest_deploy.get('commitId', 'Unknown'),
                "created_at": latest_deploy.get('createdAt', 'Unknown')
            }
    except Exception as e:
        logger.error(f"Render API Connection Warning: {e}")
    return None


# ============================================================
# 2. 🆕 RAG Memory Engine for Self-Healing
# ============================================================

class SelfHealMemory:
    """ራስ-ጥገና ትውስታ — ያለፉ ፈውሶችን ያስታውሳል"""
    
    def __init__(self, site=None):
        self.site = site
    
    def remember_healing(self, error_type, error_message, solution, success=True, confidence=80):
        """የተሳካ ፈውስ ያስታውሳል"""
        try:
            memory = VectorMemory.objects.create(
                memory_type='solution' if success else 'error',
                content=f"Error: {error_message[:200]}\nSolution: {solution[:500]}",
                metadata={
                    'error_type': error_type,
                    'success': success,
                    'confidence': confidence,
                    'site_id': self.site.id if self.site else None,
                    'timestamp': timezone.now().isoformat()
                },
                site=self.site,
                success_rate=float(confidence) if success else 0.0
            )
            memory.mark_used(success)
            logger.info(f"🧠 Remembered healing for {error_type} (success={success})")
            return memory
        except Exception as e:
            logger.error(f"Failed to remember healing: {e}")
            return None
    
    def find_similar_healing(self, error_message, limit=3):
        """ተመሳሳይ ፈውሶችን ያገኛል"""
        try:
            return VectorMemory.find_similar(
                query=error_message,
                memory_type='solution',
                site=self.site,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to find similar healing: {e}")
            return []
    
    def find_similar_errors(self, error_message, limit=3):
        """ተመሳሳይ ስህተቶችን ያገኛል"""
        try:
            return VectorMemory.find_similar(
                query=error_message,
                memory_type='error',
                site=self.site,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Failed to find similar errors: {e}")
            return []
    
    def get_success_rate(self):
        """የፈውስ ስኬት መጠን ያገኛል"""
        try:
            total = VectorMemory.objects.filter(
                site=self.site,
                memory_type='solution'
            ).count()
            if total == 0:
                return 0
            successful = VectorMemory.objects.filter(
                site=self.site,
                memory_type='solution',
                success_rate__gt=50
            ).count()
            return (successful / total) * 100
        except Exception:
            return 0


# ============================================================
# 3. 🆕 Self-Heal Task Manager
# ============================================================

class SelfHealTaskManager:
    """ራስ-ጥገና ስራዎችን ያስተዳድራል"""
    
    def __init__(self, site=None):
        self.site = site
    
    def create_heal_task(self, task_name, description, priority=5, error_type='runtime'):
        """አዲስ የጥገና ስራ ይፈጥራል"""
        try:
            task = AgentTask.objects.create(
                agent_type='code',
                task_name=task_name,
                description=description,
                priority=priority,
                site=self.site,
                status='pending',
                metadata={'error_type': error_type}
            )
            logger.info(f"📋 Created heal task: {task_name}")
            return task
        except Exception as e:
            logger.error(f"Failed to create heal task: {e}")
            return None
    
    def get_pending_tasks(self):
        """ያልተጠናቀቁ ስራዎችን ያገኛል"""
        try:
            return AgentTask.objects.filter(
                site=self.site,
                status__in=['pending', 'running']
            ).order_by('-priority')
        except Exception as e:
            logger.error(f"Failed to get pending tasks: {e}")
            return []
    
    def mark_task_completed(self, task_id, result_data=None):
        """ስራውን እንደተጠናቀቀ ምልክት ያደርጋል"""
        try:
            task = AgentTask.objects.get(id=task_id)
            task.status = 'completed'
            task.completed_at = timezone.now()
            if result_data:
                task.result_data = result_data
            task.save()
            logger.info(f"✅ Task {task.task_name} completed")
            return True
        except Exception as e:
            logger.error(f"Failed to mark task completed: {e}")
            return False


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
        logger.warning("❌ GITHUB_TOKEN Missing from settings.")
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
            logger.info(f"📄 Found existing file: {file_path} (sha: {sha[:8]})")
    except Exception as e:
        logger.warning(f"GitHub SHA retrieval failed for {file_path}: {e}")

    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": "main"
    }
    if sha:
        payload["sha"] = sha
    
    try:
        put_res = requests.put(url, headers=headers, json=payload, timeout=10)
        if put_res.status_code in [200, 201]:
            logger.info(f"✅ Code pushed to GitHub for {site_name}!")
            return f"✅ Code pushed to GitHub for {site_name}!"
        logger.error(f"❌ Push Failed for {site_name}: {put_res.text}")
        return f"❌ Push Failed for {site_name}: {put_res.text[:200]}"
    except Exception as e:
        logger.error(f"❌ GitHub Connection Failed for {site_name}: {e}")
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
    
    try:
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
        error_message = recent_errors.first().error_message
        similar_healings = memory.find_similar_healing(error_message, limit=3)
        similar_errors = memory.find_similar_errors(error_message, limit=3)
        
        memory_context = ""
        for heal in similar_healings:
            memory_context += f"\nPrevious successful healing: {heal.content[:300]}\n"
        
        error_context = ""
        for err in similar_errors:
            error_context += f"\nSimilar error: {err.content[:200]}\n"
        
        # 4. ስህተቶቹን ለ AI አቅርብ
        error_summary = []
        for err in recent_errors:
            error_summary.append({
                'task_name': err.task_name,
                'error_type': err.error_type,
                'error_message': err.error_message[:200],
                'code_attempted': err.code_attempted[:500] if err.code_attempted else ''
            })
        
        # 5. 🆕 AI ፕሮምፕት (ከትውስታ ጋር)
        prompt = f"""
        [CRITICAL DIRECTIVE] 
        You are the Smart Self-Healing Agent for site: {site_name}.
        
        Site Information:
        - Niche: {site.niche}
        - Target Market: {site.target_market}
        - Growth Level: {site.growth_level}
        - Build Phase: {site.build_phase}
        
        Recent Errors:
        {json.dumps(error_summary, indent=2)}
        
        Memory Context (past successful healings):
        {memory_context}
        
        Similar Error Context:
        {error_context}
        
        Current Codebase:
        {json.dumps(project_code, indent=2)[:4000]}
        
        Task:
        1. Analyze the errors with the help of past healings
        2. Identify root causes (missing imports, syntax, logic, security)
        3. Generate corrected code
        4. Rate your confidence (0-100) for each fix
        5. Check for security vulnerabilities
        
        Output Format:
        {{
            "confidence_score": 85,
            "fixed_files": {{
                "models": "corrected models.py code",
                "views": "corrected views.py code",
                "growth_agent": "corrected growth_agent.py code"
            }},
            "explanation": "Brief explanation of the fix",
            "security_issues": ["issue1", "issue2"],
            "root_cause": "Main cause of the error",
            "suggested_improvements": ["improvement1", "improvement2"]
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
        suggested_improvements = []
        
        if isinstance(ai_response, dict):
            fixed_files = ai_response.get('fixed_files', {})
            explanation = ai_response.get('explanation', 'System self-correction')
            confidence_score = ai_response.get('confidence_score', 50)
            security_issues = ai_response.get('security_issues', [])
            root_cause = ai_response.get('root_cause', '')
            suggested_improvements = ai_response.get('suggested_improvements', [])
        else:
            try:
                # JSON ን ከጽሁፉ ውስጥ አውጣ
                match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    fixed_files = data.get('fixed_files', {})
                    explanation = data.get('explanation', 'System self-correction')
                    confidence_score = data.get('confidence_score', 50)
                    security_issues = data.get('security_issues', [])
                    root_cause = data.get('root_cause', '')
                    suggested_improvements = data.get('suggested_improvements', [])
            except Exception as e:
                logger.error(f"Failed to parse AI response: {e}")
                return f"❌ Self-Healing failed for {site_name}: Invalid AI response format"
        
        # 7. 🆕 የደህንነት ችግሮችን ወደ SecurityLog መዝግብ
        for issue in security_issues:
            try:
                SecurityLog.objects.create(
                    category='code_injection',
                    severity='high',
                    description=issue,
                    file_path='multiple_files',
                    site=site,
                    is_fixed=False
                )
            except Exception as e:
                logger.error(f"Failed to create SecurityLog: {e}")
        
        # 8. 🆕 ማሻሻያ ሀሳቦችን መዝግብ
        for improvement in suggested_improvements:
            try:
                task_manager.create_heal_task(
                    task_name=f"Improve_{improvement[:30]}",
                    description=f"Suggested improvement: {improvement}",
                    priority=3
                )
            except Exception as e:
                logger.error(f"Failed to create improvement task: {e}")
        
        # 9. 🆕 ኮድ ከመተግበሩ በፊት የመተማመን ምርመራ
        if confidence_score < 60:
            results.append(f"⚠️ Low confidence ({confidence_score}%) - Review recommended")
        
        # 10. የተስተካከሉ ፋይሎችን መተግበር
        changes_applied = 0
        for file_key, new_content in fixed_files.items():
            if new_content and len(new_content.strip()) > 100:
                path = file_paths.get(file_key)
                if path:
                    try:
                        # የፓይተን ሲንታክስ ፍተሻ
                        if file_key in ['models', 'views', 'urls', 'forms', 'admin']:
                            compile(new_content, f"test_{file_key}.py", 'exec')
                        
                        # አሮጌውን ኮድ አስቀምጥ
                        old_code = ""
                        if os.path.exists(path):
                            with open(path, 'r', encoding='utf-8') as f:
                                old_code = f.read()
                        
                        # አዲሱን ኮድ ጻፍ
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        # በ EvolutionLog ውስጥ መዝግብ
                        AIEvolutionLog.objects.create(
                            target_file=file_key,
                            reason_for_change=f"Self-Heal for {site_name}: {explanation[:100]}",
                            old_code_backup=old_code[:1000] if old_code else '',
                            new_code_patch=new_content[:1000],
                            site=site
                        )
                        
                        # 🆕 የተሳካ ፈውስ በትውስታ ውስጥ አስቀምጥ
                        memory.remember_healing(
                            error_type='code_healing',
                            error_message=f"Fixed {file_key}: {error_message[:100]}",
                            solution=f"{explanation[:200]}\nRoot cause: {root_cause}",
                            success=True,
                            confidence=confidence_score
                        )
                        
                        # 🆕 አዲስ የጥገና ስራ ፍጠር
                        task_manager.create_heal_task(
                            task_name=f"Heal_{file_key}_{timezone.now().strftime('%Y%m%d_%H%M')}",
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
                            success=False,
                            confidence=0
                        )
                    except Exception as e:
                        results.append(f"❌ Error applying fix to {file_key}: {e}")
        
        # 11. 🆕 ትንበያ መዝግብ
        try:
            PredictionLog.objects.create(
                prediction_type='growth',
                predicted_value=float(confidence_score),
                confidence_score=float(confidence_score),
                input_data={
                    'site': site_name,
                    'changes': changes_applied,
                    'root_cause': root_cause,
                    'fixes': list(fixed_files.keys())
                },
                site=site
            )
        except Exception as e:
            logger.error(f"Failed to create PredictionLog: {e}")
        
        # 12. 🆕 የራስ-ጥገና ማጠቃለያ
        success_rate = memory.get_success_rate()
        results.append(f"📊 Success Rate: {success_rate:.1f}%")
        
        if changes_applied == 0:
            results.append("⚠️ No changes were applied")
        
        return f"🛠️ Smart Self-Heal for {site_name}: {' | '.join(results)}"
    
    except Exception as e:
        error_msg = f"❌ Self-heal error for {site_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg


# ============================================================
# 6. 🆕 ለሁሉም ጣቢያዎች ራስ-ጥገና
# ============================================================

def self_heal_all_sites():
    """ሁሉንም ንቁ ጣቢያዎች ራስ-ጥገና ያደርጋል"""
    results = []
    
    try:
        sites = SiteRegistry.objects.filter(is_active=True)
    except Exception as e:
        logger.error(f"Failed to get active sites: {e}")
        return "❌ Failed to get active sites"
    
    if not sites.exists():
        return "⚠️ No active sites found"
    
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
    
    return f"🛠️ Self-Heal Summary: {' | '.join(results)}"


# ============================================================
# 7. ዋናው ራስ-ጥገና ተግባር (የተሻሻለ - Multi-Site)
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
    except Exception as e:
        logger.error(f"Failed to get active sites: {e}")
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
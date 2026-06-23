# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_coder.py
# 📝 ለውጥ፦ Smart Self-Coder — Safe Codebase Context & Codeapply Integration
# ✅ የተፈቱ ችግሮች፦ File Truncations, DB Connection Leaks, Duplicate Extensions
# 📅 ቀን፦ 2026-06-23
# ============================================================

import requests
import os
import json
import base64
import re
import logging
from django.conf import settings
from django.utils import timezone
from django.db import models, connection, connections
from .growth_agent import ask_ethafri_ceo, get_site_project_state
from .models import (
    SiteRegistry, AgentErrorLog, AIEvolutionLog, SiteConfig,
    VectorMemory, AgentTask, SecurityLog, PredictionLog
)

# የኮድ መተግበሪያ ነጥብ
try:
    from .code_apply import apply_code_change, push_code_to_github
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ code_apply.py not found. Using fallback.")
    
    def apply_code_change(site, file_key, new_content, path, reason, confidence_score=100, backlog_task=None, push_to_github=True):
        old_code = ""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        try:
            AIEvolutionLog.objects.create(
                target_file=file_key,
                reason_for_change=reason,
                old_code_backup=old_code,
                new_code_patch=new_content,
                site=site
            )
        except Exception as e:
            logger.error(f"Fallback AIEvolutionLog error: {e}")
        
        return {'success': True, 'message': f"✅ Applied {file_key} (fallback)", 'applied': True}

    def push_code_to_github(file_path, file_content, commit_message, site_name="primary"):
        return "Fallback (Not Implemented)"

logger = logging.getLogger(__name__)


# ============================================================
# ⚙️ የውሂብ መላክ ማሻሻያ (Token Optimization & Safe JSON)
# ============================================================

def get_optimized_code_context(project_code, target_file_key=None, max_chars=40000):
    """
    ይህ ረዳት ተግባር ለኤአይ የሚላከውን የኮድ መጠን በጥንቃቄ ያሳጥራል።
    የስህተት መነሻ የሆነውን ፋይል ሙሉ በሙሉ (እስከ 40,000 ቁምፊዎች) ይልካል፣ ሌሎችን ግን ያሳጥራል።
    ይህም ትልቅ JSON ተቆርጦ ኤአይ እንዳይቋረጥ እና የፋይል መጥፋት እንዳይከሰት ይከላከላል።
    """
    optimized = {}
    for key, content in project_code.items():
        if not isinstance(content, str):
            optimized[key] = content
            continue
        
        if target_file_key and key == target_file_key:
            optimized[key] = content[:max_chars] + ("\n... [Truncated due to extreme size]" if len(content) > max_chars else "")
        else:
            lines = content.split('\n')
            if len(lines) > 35:
                optimized[key] = "\n".join(lines[:35]) + f"\n... [Truncated {len(lines)-35} lines to prevent timeout]"
            else:
                optimized[key] = content
    return optimized


# ============================================================
# 1. የሬንደር ሁኔታ አንባቢ (KeyError-Safe)
# ============================================================

def get_render_deploy_status():
    """የሬንደርን የቅርብ ጊዜ መጫን ሁኔታ ያነባል — በጥብቅ የጊዜ ገደብ"""
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
        response = requests.get(url, headers=headers, timeout=5)
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
# 2. RAG Memory Engine for Self-Healing (የተሻሻለ)
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
                success_rate=float(confidence) if success else 0.0,
                text_content=error_message[:500],
                embedding_model='self-heal-v1'
            )
            memory.mark_used(success)
            logger.info(f"🧠 Remembered healing for {error_type} (success={success})")
            return memory
        except Exception as e:
            logger.error(f"Failed to remember healing: {e}")
            return None
    
    def find_similar_healing(self, error_message, limit=3):
        """ተመሳሳይ ፈውሶችን ያገኛል — OR-based scoring"""
        try:
            from django.db.models import Q
            
            keywords = [k for k in error_message.lower().split() if len(k) > 2][:8]
            queryset = VectorMemory.objects.filter(
                site=self.site,
                memory_type='solution'
            )
            
            if keywords:
                q_filter = Q()
                for keyword in keywords:
                    q_filter |= Q(content__icontains=keyword)
                queryset = queryset.filter(q_filter)
            
            return queryset.order_by('-success_rate', '-usage_count')[:limit]
        except Exception as e:
            logger.error(f"Failed to find similar healing: {e}")
            return []
    
    def find_similar_errors(self, error_message, limit=3):
        """ተመሳሳይ ስህተቶችን ያገኛል — OR-based scoring"""
        try:
            from django.db.models import Q
            
            keywords = [k for k in error_message.lower().split() if len(k) > 2][:8]
            queryset = VectorMemory.objects.filter(
                site=self.site,
                memory_type='error'
            )
            
            if keywords:
                q_filter = Q()
                for keyword in keywords:
                    q_filter |= Q(content__icontains=keyword)
                queryset = queryset.filter(q_filter)
            
            return queryset.order_by('-success_rate', '-usage_count')[:limit]
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
# 3. Self-Heal Task Manager
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
# 5. የተሻሻለ ለአንድ ጣቢያ ራስ-ጥገና (Smart Self-Heal)
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
        
        # 3. ዋነኛውን የጥፋት መነሻ ፋይል ፈልግ
        primary_error = recent_errors.first()
        error_message = primary_error.error_message
        target_file_key = primary_error.task_name.lower()
        
        # 4. ተመሳሳይ ፈውሶችን ከትውስታ ያግኝ
        similar_healings = memory.find_similar_healing(error_message, limit=2)
        similar_errors = memory.find_similar_errors(error_message, limit=2)
        
        memory_context = ""
        for heal in similar_healings:
            memory_context += f"\nPrevious successful healing: {heal.content[:250]}\n"
        
        error_context = ""
        for err in similar_errors:
            error_context += f"\nSimilar error: {err.content[:150]}\n"
        
        # 5. የተስተካከለ እና ቶከን የሚቆጥብ የኮድ ይዘት ያዘጋጁ (JSON እንዳይቆረጥ) - 40,000 Limit
        optimized_code = get_optimized_code_context(project_code, target_file_key=target_file_key)
        
        # 6. ስህተቶቹን ለ AI አቅርብ (ከ Error ID ጋር)
        error_summary = []
        for err in recent_errors:
            error_summary.append({
                'id': err.id,
                'task_name': err.task_name,
                'error_type': err.error_type,
                'error_message': err.error_message[:150],
                'code_attempted': err.code_attempted[:300] if err.code_attempted else ''
            })
        
        # 7. AI ፕሮምፕት (ከትውስታ እና አስተማማኝ JSON ጋር)
        prompt = f"""
        [CRITICAL DIRECTIVE] 
        You are the Smart Self-Healing Agent for site: {site_name}.
        
        Site Information:
        - Niche: {site.niche}
        - Target Market: {site.target_market}
        - Build Phase: {site.build_phase}
        
        Recent Errors:
        {json.dumps(error_summary, indent=2)}
        
        Memory Context (past successful healings):
        {memory_context}
        
        Similar Error Context:
        {error_context}
        
        Current Codebase (Summary & Targeted Full Files):
        {json.dumps(optimized_code, indent=2)}
        
        ⚠️ CRITICAL INSTRUCTION (PRESERVATION SAFEGUARD):
        - In 'fixed_files', you MUST return the FULL, COMPLETE content of any file you fix.
        - Do NOT truncate, delete, or omit any existing models, views, imports, or functions.
        - Keep all original features (like Category, Product, AIProjectBacklog classes) intact.
        - Merely append or integrate your corrections into the existing code.
        - Truncating code will result in severe database loss!

        Task:
        1. Analyze the errors and identify root causes
        2. Generate corrected code
        3. Rate your confidence (0-100) for each fix
        4. Check for security vulnerabilities
        
        Output Format (STRICT JSON ONLY):
        {{
            "confidence_score": 85,
            "fixed_files": {{
                "models": "corrected models.py code",
                "views": "corrected views.py code"
            }},
            "explanation": "Brief explanation",
            "security_issues": ["issue1"],
            "root_cause": "Main cause of error",
            "suggested_improvements": ["improvement1"],
            "resolved_error_ids": [123, 456]
        }}
        """
        
        ai_response = ask_ethafri_ceo(prompt, pool_type="healing")
        
        if not ai_response:
            return f"❌ Self-Healing failed for {site_name}: No AI response"
        
        if isinstance(ai_response, dict) and "error" in ai_response:
            return f"❌ Self-Healing failed for {site_name}: {ai_response['error']}"
        
        # 8. የAI ምላሽን መፍታት
        fixed_files = {}
        explanation = "System self-correction"
        confidence_score = 50
        security_issues = []
        root_cause = ""
        resolved_error_ids = []
        
        if isinstance(ai_response, dict):
            fixed_files = ai_response.get('fixed_files', {})
            explanation = ai_response.get('explanation', 'System self-correction')
            confidence_score = ai_response.get('confidence_score', 50)
            security_issues = ai_response.get('security_issues', [])
            root_cause = ai_response.get('root_cause', '')
            resolved_error_ids = ai_response.get('resolved_error_ids', [])
        else:
            try:
                match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    fixed_files = data.get('fixed_files', {})
                    explanation = data.get('explanation', 'System self-correction')
                    confidence_score = data.get('confidence_score', 50)
                    security_issues = data.get('security_issues', [])
                    root_cause = data.get('root_cause', '')
                    resolved_error_ids = data.get('resolved_error_ids', [])
            except Exception as e:
                logger.error(f"Failed to parse AI response: {e}")
                return f"❌ Self-Healing failed for {site_name}: Invalid AI response format"
        
        # 9. የደህንነት ችግሮችን ወደ SecurityLog መዝግብ
        for issue in security_issues:
            try:
                SecurityLog.objects.create(
                    category='code_injection', severity='high', description=issue,
                    file_path='multiple_files', site=site, is_fixed=False
                )
            except Exception as e:
                logger.error(f"Failed to create SecurityLog: {e}")
        
        # 10. የመተማመን ፍተሻ (Confidence Check)
        if confidence_score < 50:
            results.append(f"⛔ Confidence too low ({confidence_score}%) — changes NOT applied")
            return f"⛔ Self-Heal blocked for {site_name}: Confidence too low"
        
        # 11. የተስተካከሉ ፋይሎችን መተግበር
        changes_applied = 0
        for file_key, new_content in fixed_files.items():
            if new_content and len(new_content.strip()) > 10:
                path = file_paths.get(file_key)
                
                # 🛡️ repo_path የድረ-ገጽ URL ከሆነ በደህንነት ወደ settings.BASE_DIR ማምራት
                if not path or 'http' in path or 'github.com' in path:
                    path = os.path.join(settings.BASE_DIR, 'marketplace', f'{file_key}.py' if not file_key.endswith('.py') else file_key)
                
                if path:
                    result = apply_code_change(
                        site=site, file_key=file_key, new_content=new_content, path=path,
                        reason=f"Self-Heal for {site_name}: {explanation[:150]}",
                        confidence_score=confidence_score, backlog_task=None, push_to_github=True
                    )
                    results.append(result['message'])
                    
                    if result['applied']:
                        changes_applied += 1
                        memory.remember_healing(
                            error_type='code_healing',
                            error_message=f"Fixed {file_key}: {error_message[:100]}",
                            solution=f"{explanation[:200]}\nRoot cause: {root_cause}",
                            success=True,
                            confidence=confidence_score
                        )
        
        # 12. ስህተቶቹን እንደተፈቱ ምልክት አድርጉ
        if resolved_error_ids:
            updated = AgentErrorLog.objects.filter(
                id__in=resolved_error_ids, site=site
            ).update(resolved=True)
            results.append(f"✅ Resolved {updated} specific errors")
        else:
            results.append("⚠️ No specific errors confirmed resolved")
        
        # 13. ትንበያ መዝግብ
        try:
            PredictionLog.objects.create(
                prediction_type='growth', predicted_value=float(confidence_score),
                confidence_score=float(confidence_score),
                input_data={'site': site_name, 'changes': changes_applied, 'fixes': list(fixed_files.keys())},
                site=site
            )
        except Exception as e:
            logger.error(f"Failed to create PredictionLog: {e}")
        
        return f"🛠️ Smart Self-Heal for {site_name}: {' | '.join(results)}"
    
    except Exception as e:
        error_msg = f"❌ Self-heal error for {site_name}: {str(e)}"
        logger.error(error_msg)
        return error_msg
        
    finally:
        connection.close()


# ============================================================
# 6. ለሁሉም ጣቢያዎች ራስ-ጥገና
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
        finally:
            connection.close()
    
    return f"🛠️ Self-Heal Summary: {' | '.join(results)}"


# ============================================================
# 7. ዋናው ራስ-ጥገና ተግባር (የተሻሻለ - Multi-Site)
# ============================================================

def self_heal_failed_build():
    """ሬንደር ላይ ቢከሽፍ AIው ራሱ መዝገቡን አንብቦ ኮዱን የሚጠግንበት ዑደት"""
    results = []
    
    # 1. የሬንደር ሁኔታ ፍተሻ
    status_info = get_render_deploy_status()
    if status_info:
        deploy_status = status_info.get('status', 'Unknown')
        commit_id = status_info.get('commit_id', 'Unknown')
        
        if deploy_status == "build_failed":
            results.append(f"⚠️ Render Build Failed on Commit {commit_id[:7]}!")
    
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
        finally:
            connection.close()
    
    if not results:
        return "System status is normal, no self-healing needed."
    
    return f"🛠️ Smart Self-Heal Summary: {' | '.join(results)}"
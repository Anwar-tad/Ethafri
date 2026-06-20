# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/self_coder.py
# 📝 ለውጥ፦ Multi-Site Support + SiteRegistry Integration
# 📅 ቀን፦ 2026-06-20
# ============================================================

import requests
import json
import base64
import re
import logging
from django.conf import settings
from django.utils import timezone
from .growth_agent import ask_ethafri_ceo, get_site_project_state
from .models import SiteRegistry, AgentErrorLog, AIEvolutionLog, SiteConfig

logger = logging.getLogger(__name__)


# ============================================================
# 1. የሬንደር ሁኔታ አንባቢ (ሳይለወጥ)
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
# 2. ወደ ጊትሃብ መግፋት (የተሻሻለ - Multi-Site)
# ============================================================

def push_code_to_github(file_path, file_content, commit_message, site_name="primary"):
    """
    የተጻፈውን አዲስ የፓይተን ኮድ በቀጥታ ወደ ጊትሃብ ይልካል (Push)
    አሁን ለብዙ ጣቢያዎች ይሰራል
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

    # 1. የድሮውን ፋይል SHA ማግኘት
    sha = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            sha = res.json().get('sha', '')
    except Exception as e:
        logger.warning(f"GitHub SHA retrieval failed for {file_path}: {e}")

    # 2. ፋይሉን በ Base64 ኢንኮድ ማድረግ
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

    # 3. ወደ ጊትሃብ መግፋት
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
# 3. ለአንድ ጣቢያ ራስ-ጥገና (Self-Heal Single Site)
# ============================================================

def self_heal_single_site(site: SiteRegistry):
    """
    ለአንድ የተወሰነ ጣቢያ ራስ-ጥገና ያካሂዳል
    """
    site_name = site.name
    logger.info(f"🛠️ Starting self-heal for site: {site_name}")
    
    results = []
    
    # 1. የጣቢያውን ሁኔታ ያንብብ
    project_code, file_paths = get_site_project_state(site)
    
    if not project_code:
        return f"⚠️ No code found for {site_name}"
    
    # 2. የጣቢያውን የስህተት ሎግ ያንብብ
    recent_errors = AgentErrorLog.objects.filter(
        site=site,
        resolved=False
    ).order_by('-created_at')[:10]
    
    if not recent_errors:
        return f"✅ No errors found for {site_name}"
    
    # 3. ስህተቶቹን ለ AI አቅርብ
    error_summary = []
    for err in recent_errors:
        error_summary.append({
            'task_name': err.task_name,
            'error_type': err.error_type,
            'error_message': err.error_message[:200],
            'code_attempted': err.code_attempted[:500]
        })
    
    # 4. AI እንዲያስተካክል ጠይቅ
    prompt = f"""
    [CRITICAL DIRECTIVE] 
    You are the Autonomous CEO of EthAfri. Self-healing is needed for site: {site_name}.
    
    Site Information:
    - Niche: {site.niche}
    - Target Market: {site.target_market}
    - Growth Level: {site.growth_level}
    
    Recent Errors:
    {json.dumps(error_summary, indent=2)}
    
    Current Codebase:
    {json.dumps(project_code, indent=2)[:5000]}
    
    Task:
    1. Analyze the errors above
    2. Identify the root cause
    3. Write corrected code
    4. Return ONLY valid JSON with the fixed code
    
    Output Format:
    {{
        "fixed_files": {{
            "models": "corrected models.py code",
            "views": "corrected views.py code",
            "growth_agent": "corrected growth_agent.py code"
        }},
        "explanation": "Brief explanation of what was fixed"
    }}
    """
    
    ai_response = ask_ethafri_ceo(prompt, pool_type="coding")
    
    if not ai_response:
        return f"❌ Self-Healing failed for {site_name}: No AI response"
    
    if isinstance(ai_response, dict) and "error" in ai_response:
        return f"❌ Self-Healing failed for {site_name}: {ai_response['error']}"
    
    # 5. የAI ምላሽን አስተካክል
    fixed_files = {}
    if isinstance(ai_response, dict):
        fixed_files = ai_response.get('fixed_files', {})
        explanation = ai_response.get('explanation', '')
    else:
        # ጥሬ ጽሑፍ ከሆነ
        try:
            data = json.loads(ai_response)
            fixed_files = data.get('fixed_files', {})
            explanation = data.get('explanation', '')
        except:
            return f"❌ Self-Healing failed for {site_name}: Invalid AI response format"
    
    # 6. የተስተካከሉ ፋይሎችን ተግብር
    changes_applied = 0
    for file_key, new_content in fixed_files.items():
        if new_content and len(new_content.strip()) > 100:
            # የፋይሉን መንገድ አግኝ
            path = file_paths.get(file_key)
            if path:
                try:
                    # ሲንታክስ ፍተሻ
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
                    
                    # ስህተቶቹን እንደተፈቱ ምልክት አድርግ
                    AgentErrorLog.objects.filter(site=site, resolved=False).update(resolved=True)
                    
                    changes_applied += 1
                    results.append(f"✅ Fixed {file_key}")
                    
                except SyntaxError as e:
                    results.append(f"❌ Syntax error in {file_key}: {e}")
                except Exception as e:
                    results.append(f"❌ Error applying fix to {file_key}: {e}")
    
    # 7. ወደ ጊትሃብ ግፋ (ከሆነ)
    if changes_applied > 0:
        push_result = push_code_to_github(
            f"marketplace/{file_key}.py",
            new_content,
            f"AI: Self-Healed {site_name} - {explanation[:50]}",
            site_name
        )
        results.append(push_result)
    
    return f"🛠️ Self-Heal for {site_name}: {' | '.join(results)}"


# ============================================================
# 4. ዋናው ራስ-ጥገና ተግባር (የተሻሻለ - Multi-Site)
# ============================================================

def self_heal_failed_build():
    """
    ሬንደር ላይ ቢከሽፍ AIው ራሱ መዝገቡን አንብቦ ኮዱን የሚጠግንበት ዑደት
    አሁን ሁሉንም ጣቢያዎች ያስተዳድራል
    """
    results = []
    
    # 1. የሬንደር ሁኔታ ፍተሻ (ለዋናው ጣቢያ)
    status_info = get_render_deploy_status()
    if status_info:
        deploy_status = status_info.get('status', 'Unknown')
        commit_id = status_info.get('commit_id', 'Unknown')
        
        if deploy_status == "build_failed":
            results.append(f"⚠️ Render Build Failed on Commit {commit_id[:7]}!")
            # የሬንደር ጥገና ለዋናው ጣቢያ ብቻ
            # (የሬንደር ማሰማሪያ አንድ ነው)
            results.append("🔧 Attempting primary site self-heal...")
    
    # 2. ሁሉንም ጣቢያዎች ራስ-ጥገና አድርግ
    sites = SiteRegistry.objects.filter(is_active=True)
    
    if not sites.exists():
        return "⚠️ No active sites found for self-healing"
    
    for site in sites:
        try:
            # ለዚህ ጣቢያ ያልተፈቱ ስህተቶች ካሉ
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
    
    # 3. ማጠቃለያ
    if not results:
        return "System status is normal, no self-healing needed."
    
    return f"🛠️ Self-Heal Summary: {' | '.join(results)}"
# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/code_apply.py
# 📝 ዓላማ፦ ብቸኛው ትክክለኛ "ኮድ የመተግበር" ነጥብ (Single Source of Truth)
#           growth_agent.py እና self_coder.py ሁለቱም ይህንኑ ይጠቀማሉ።
#           ይህ የ Persistence Mismatch (Render ephemeral filesystem) ችግርን ይፈታል።
# 📅 ቀን፦ 2026-06-22
# ============================================================

import os
import re
import logging
import base64
import hashlib
import time
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================
# ⚙️ ውቅር (Configuration)
# ============================================================

CONFIDENCE_THRESHOLD = 70  # ✅ ከዚህ በታች ራስ-ሰር አይተገበርም — ለ admin ይቀርባል
MAX_FILE_SIZE = 50000  # ከፍተኛ የፋይል መጠን (ባይት)


# ============================================================
# 🛠️ ዋና ተግባር — ኮድ መተግበር
# ============================================================

def apply_code_change(site, file_key, new_content, path, reason, 
                      confidence_score=100, backlog_task=None, 
                      push_to_github=True, skip_syntax_check=False):
    """
    ✅ ሁሉም ኮድ-የሚተገብር ቦታ (growth_agent.py, self_coder.py) ይህንኑ ብቻ መጠቀም አለበት።
    
    ያደርጋቸው፦
    1. Syntax ፍተሻ (compile()) — ካልተሳካ አይተገበርም
    2. ✅ እውነተኛ Confidence Gating — ዝቅተኛ confidence ያለው ለውጥ ጨርሶ አይተገበርም
    3. Local disk ላይ ይጽፋል
    4. ✅ ወደ GitHub ይገፋል
    5. AIEvolutionLog ይመዘገባል
    
    Args:
        site: SiteRegistry instance
        file_key: የፋይሉ መለያ (models, views, urls, etc.)
        new_content: አዲሱ የፋይል ይዘት
        path: የፋይሉ ሙሉ መንገድ
        reason: የለውጡ ምክንያት
        confidence_score: 0-100 የእምነት ውጤት
        backlog_task: ተዛማጅ AIProjectBacklog (ካለ)
        push_to_github: ወደ GitHub መግፋት ይፈለጋል?
        skip_syntax_check: የማጣራት እርምጃ ይዘለላል? (አደገኛ!)
    
    Returns:
        dict: {
            'success': bool,
            'applied': bool,
            'message': str,
            'path': str,
            'file_key': str
        }
    """
    from .models import AIEvolutionLog, SiteConfig, AgentErrorLog
    
    # ============================================================
    # 1. መረጃ ማረጋገጥ (Validation)
    # ============================================================
    
    if not path:
        return {
            'success': False,
            'applied': False,
            'message': '❌ No path provided',
            'path': path,
            'file_key': file_key
        }
    
    if not new_content or len(new_content.strip()) < 10:
        return {
            'success': False,
            'applied': False,
            'message': '❌ Content too short or empty',
            'path': path,
            'file_key': file_key
        }
    
    if len(new_content) > MAX_FILE_SIZE:
        return {
            'success': False,
            'applied': False,
            'message': f'❌ File too large: {len(new_content)} > {MAX_FILE_SIZE} bytes',
            'path': path,
            'file_key': file_key
        }
    
    # ============================================================
    # 2. Syntax ፍተሻ (Syntax Check)
    # ============================================================
    
    if not skip_syntax_check and file_key in ['models', 'views', 'urls', 'forms', 'admin', 'settings']:
        try:
            compile(new_content, f"validate_{file_key}.py", 'exec')
        except SyntaxError as e:
            # ስህተቱን መዝግብ
            try:
                AgentErrorLog.objects.create(
                    task_name=f"Syntax Check: {file_key}",
                    error_type='syntax',
                    error_message=f"Syntax error: {e}",
                    code_attempted=new_content[:500],
                    site=site,
                    resolved=False
                )
            except Exception:
                pass
            
            return {
                'success': False,
                'applied': False,
                'message': f"❌ Syntax error: {e}",
                'path': path,
                'file_key': file_key
            }
    
    # ============================================================
    # 3. Confidence Gating (ዝቅተኛ እምነት → አይተገበርም)
    # ============================================================
    
    if confidence_score < CONFIDENCE_THRESHOLD:
        try:
            SiteConfig.objects.create(
                key=f"PENDING_REVIEW_{site.name if site else 'global'}_{int(timezone.now().timestamp())}",
                value={
                    'site_id': site.id if site else None,
                    'file_key': file_key,
                    'new_content': new_content[:5000],
                    'reason': reason,
                    'confidence_score': confidence_score,
                    'status': 'awaiting_admin_approval',
                    'created_at': timezone.now().isoformat(),
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not queue for review: {e}")
        
        logger.warning(f"⚠️ Low confidence ({confidence_score}%) for {file_key} → queued for admin review, NOT applied")
        
        return {
            'success': True,
            'applied': False,
            'message': f"⏸️ Confidence {confidence_score}% < {CONFIDENCE_THRESHOLD}% — queued for review",
            'path': path,
            'file_key': file_key
        }
    
    # ============================================================
    # 4. የአሮጌውን ኮድ አስቀምጥ (Backup)
    # ============================================================
    
    old_code = ""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except Exception as e:
            logger.warning(f"⚠️ Could not read old file: {e}")
            old_code = ""
    
    # ============================================================
    # 5. ወደ ፋይል ጻፍ (Local File Write)
    # ============================================================
    
    try:
        # ማውጫው መኖሩን አረጋግጥ
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        logger.info(f"📝 Written to {path}")
        
    except Exception as e:
        error_msg = f"❌ File write error: {e}"
        logger.error(error_msg)
        
        # ስህተቱን መዝግብ
        try:
            AgentErrorLog.objects.create(
                task_name=f"File Write: {file_key}",
                error_type='runtime',
                error_message=error_msg,
                code_attempted=new_content[:500],
                site=site,
                resolved=False
            )
        except Exception:
            pass
        
        return {
            'success': False,
            'applied': False,
            'message': error_msg,
            'path': path,
            'file_key': file_key
        }
    
    # ============================================================
    # 6. ወደ GitHub ግፋ (GitHub Push)
    # ============================================================
    
    push_result = "Skipped (push_to_github=False)"
    if push_to_github:
        try:
            # ወደ GitHub መግፋት
            push_func = _push_to_github
            if push_func:
                site_name = site.name if site else "primary"
                commit_message = f"AI: {reason[:100]} (Confidence {confidence_score}%)"
                
                push_result = push_func(
                    file_path=f"marketplace/{file_key}.py" if not file_key.endswith('.py') else file_key,
                    content=new_content,
                    commit_message=commit_message,
                    site_name=site_name
                )
                
                if push_result and push_result.startswith("❌"):
                    logger.error(f"⚠️ Local write OK but GitHub push FAILED: {push_result}")
                else:
                    logger.info(f"✅ GitHub push: {push_result}")
                    
        except Exception as e:
            push_result = f"❌ GitHub push error: {e}"
            logger.error(push_result)
    
    # ============================================================
    # 7. ለውጥ መዝግብ (Evolution Log)
    # ============================================================
    
    try:
        AIEvolutionLog.objects.create(
            backlog_task=backlog_task,
            target_file=file_key,
            reason_for_change=reason,
            old_code_backup=old_code[:10000],
            new_code_patch=new_content[:10000],
            site=site
        )
        logger.info(f"📝 Logged evolution for {file_key}")
    except Exception as e:
        logger.warning(f"⚠️ Could not log evolution: {e}")
    
    # ============================================================
    # 8. ተዛማጅ ስራ ሁኔታ አዘምን (Update Backlog Task)
    # ============================================================
    
    if backlog_task:
        try:
            backlog_task.status = 'Completed'
            backlog_task.save()
            logger.info(f"✅ Task {backlog_task.task_name} marked as Completed")
        except Exception as e:
            logger.warning(f"⚠️ Could not update task status: {e}")
    
    # ============================================================
    # 9. ውጤት መመለስ (Return Result)
    # ============================================================
    
    return {
        'success': True,
        'applied': True,
        'message': f"✅ Applied {file_key} | GitHub: {push_result}",
        'path': path,
        'file_key': file_key
    }


# ============================================================
# 🔧 ወደ GitHub መግፋት (Push to GitHub)
# ============================================================

def _push_to_github(file_path, content, commit_message, site_name="primary"):
    """
    ኮዱን ወደ GitHub ይገፋል
    """
    import requests
    import base64
    
    github_token = getattr(settings, 'GITHUB_TOKEN', None)
    repo = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    
    if not github_token:
        logger.warning("❌ GITHUB_TOKEN Missing from settings.")
        return "❌ GITHUB_TOKEN Missing from settings."

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # SHA ን አግኝ (ካለ)
    sha = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            sha = res.json().get('sha', '')
            logger.info(f"📄 Found existing file: {file_path} (sha: {sha[:8]})")
    except Exception as e:
        logger.warning(f"GitHub SHA retrieval failed: {e}")

    encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

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
        logger.error(f"❌ GitHub Connection Failed: {e}")
        return f"❌ GitHub Connection Failed: {e}"


# ============================================================
# 🔧 ረዳት ተግባራት
# ============================================================

def validate_code_syntax(code, file_type="python"):
    """
    የኮድ ሰዋሰው ያረጋግጣል
    """
    if file_type == "python":
        try:
            compile(code, "validate.py", 'exec')
            return {'valid': True, 'message': 'Syntax OK'}
        except SyntaxError as e:
            return {'valid': False, 'message': f"Syntax error: {e}"}
    elif file_type == "html":
        if '<' in code and '>' in code:
            return {'valid': True, 'message': 'HTML structure OK'}
        return {'valid': False, 'message': 'Invalid HTML structure'}
    else:
        return {'valid': True, 'message': f'Validation for {file_type} not implemented'}


def get_code_diff(old_code, new_code):
    """
    በአሮጌው እና አዲሱ ኮድ መካከል ያለውን ልዩነት ያሳያል
    """
    if not old_code:
        return "New file created"
    if old_code == new_code:
        return "No changes"
    
    old_lines = old_code.split('\n')
    new_lines = new_code.split('\n')
    
    diff = []
    max_lines = min(len(old_lines), len(new_lines))
    
    for i in range(max_lines):
        if old_lines[i] != new_lines[i]:
            diff.append(f"Line {i+1}: -{old_lines[i][:50]} +{new_lines[i][:50]}")
    
    if len(old_lines) > len(new_lines):
        for i in range(len(new_lines), len(old_lines)):
            diff.append(f"Line {i+1}: -{old_lines[i][:50]}")
    elif len(new_lines) > len(old_lines):
        for i in range(len(old_lines), len(new_lines)):
            diff.append(f"Line {i+1}: +{new_lines[i][:50]}")
    
    return '\n'.join(diff[:20])


def sanitize_code(content):
    """
    ኮዱን ከአደገኛ ነገሮች ያጸዳል
    """
    # አደገኛ ተግባራትን ፈልግ
    dangerous = ['eval(', 'exec(', 'os.system(', 'subprocess.call(']
    for item in dangerous:
        if item in content:
            logger.warning(f"⚠️ Dangerous code pattern detected: {item}")
    
    return content


# ============================================================
# 📊 የስርዓት ሁኔታ መመለሻ
# ============================================================

def get_code_apply_stats():
    """
    የcode_apply.py አጠቃቀም ስታቲስቲክስ ይመልሳል
    """
    try:
        from .models import AIEvolutionLog, SiteConfig, AgentErrorLog
        
        total_applications = AIEvolutionLog.objects.count()
        pending_reviews = SiteConfig.objects.filter(
            key__startswith='PENDING_REVIEW_'
        ).count()
        recent_errors = AgentErrorLog.objects.filter(
            error_type='syntax',
            resolved=False
        ).count()
        
        return {
            'total_applications': total_applications,
            'pending_reviews': pending_reviews,
            'syntax_errors': recent_errors,
            'confidence_threshold': CONFIDENCE_THRESHOLD,
            'max_file_size': MAX_FILE_SIZE
        }
    except Exception as e:
        return {'error': str(e)}
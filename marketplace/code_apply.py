# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/code_apply.py
# 📝 ዓላማ፦ ብቸኛው ትክክለኛ "ኮድ የመተግበሪያ" ነጥብ (Single Source of Truth)
#           ይህ የ Persistence Mismatch (Render ephemeral filesystem) ችግርን ይፈታል።
# ✅ የተፈቱ ችግሮች፦ Circular Imports, Thread Safety, Duplicate Extensions (.py.py), HTTP Path Safeguard
# 📅 ቀን፦ 2026-06-23
# ============================================================

import os
import ast
import logging
import base64
import requests
import threading
import subprocess
from django.utils import timezone
from django.conf import settings
from django.db import connection, connections

logger = logging.getLogger(__name__)

# ============================================================
# ⚙️ ውቅር (Configuration)
# ============================================================

CONFIDENCE_THRESHOLD = 70  # ከዚህ በታች ራስ-ሰር አይተገበርም — ለ review ይቀርባል
MAX_FILE_SIZE = 50000  # ከፍተኛ የፋይል መጠን (ባይት)

# ፋይሎች በብዙ ክሮች በአንድ ጊዜ ተጽፈው እንዳይበላሹ የሚከላከል መቆለፊያ (Thread Lock)
_file_lock = threading.Lock()


# ============================================================
# 🛠️ ዋና ተግባር — ኮድ መተግበር
# ============================================================

def apply_code_change(site, file_key, new_content, path, reason, 
                      confidence_score=100, backlog_task=None, 
                      push_to_github=True, skip_syntax_check=False):
    """
    ኮድን በደህንነት ወደ ፋይል ይጽፋል፣ ስህተቶችን አስቀድሞ ይፈትሻል፣ እና ወደ GitHub ይገፋል
    """
    from .models import AIEvolutionLog, SiteConfig, AgentErrorLog
    
    # ============================================================
    # 🛡️ ራስ-ሰር የጥበቃ ሎጂክ (Path Safeguard)
    # የጣቢያው repo_path የድረ-ገጽ ሊንክ (HTTP) ሆኖ ከተገኘ በራስ-ሰር ወደ ትክክለኛው የሰርቨር ማህደር ይቀይረዋል
    # ============================================================
    # ============================================================
    # 🛡️ ራስ-ሰር የጥበቃ ሎጂክ (Path Safeguard)
    # የውጭ ጣቢያዎች ኮድ በስህተት የፕራይመሪውን እንዳያጠፉ በተናጠል ማህደር ውስጥ ማዞር
    # ============================================================
    site_name = site.name if site else "primary"
    if not path or 'http' in path or 'github.com' in path:
        if site_name == "primary":
            path = os.path.join(settings.BASE_DIR, 'marketplace', f'{file_key}.py' if not file_key.endswith('.py') else file_key)
        else:
            # ✅ የውጭ ሳይቶች ኮድ በሰርቨር ላይ በተለየ ማህደር ውስጥ እንዲጻፍ ማዞር
            path = os.path.join('/tmp', 'ethafri_agent', site_name, 'marketplace', f'{file_key}.py' if not file_key.endswith('.py') else file_key)
            logger.warning(f"🛡️ Safeguard: Redirected remote site {site_name} path to sandbox: {path}")

    # 1. መረጃ ማረጋገጥ (Validation)
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
    
    # 2. Syntax ፍተሻ (Syntax Check)
    if not skip_syntax_check and file_key in ['models', 'views', 'urls', 'forms', 'admin', 'settings']:
        try:
            compile(new_content, f"validate_{file_key}.py", 'exec')
        except SyntaxError as e:
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
            finally:
                connection.close()
            
            return {
                'success': False,
                'applied': False,
                'message': f"❌ Syntax error: {e}",
                'path': path,
                'file_key': file_key
            }
    
    # 3. Confidence Gating
    if confidence_score < CONFIDENCE_THRESHOLD:
        try:
            SiteConfig.objects.update_or_create(
                key=f"PENDING_REVIEW_{site.name if site else 'global'}_{int(timezone.now().timestamp())}",
                defaults={
                    'value': {
                        'site_id': site.id if site else None,
                        'file_key': file_key,
                        'new_content': new_content[:5000],
                        'reason': reason,
                        'confidence_score': confidence_score,
                        'status': 'awaiting_admin_approval',
                        'created_at': timezone.now().isoformat(),
                    }
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Could not queue for review: {e}")
        finally:
            connection.close()
        
        logger.warning(f"⚠️ Low confidence ({confidence_score}%) for {file_key} → queued for admin review, NOT applied")
        
        return {
            'success': True,
            'applied': False,
            'message': f"⏸️ Confidence {confidence_score}% < {CONFIDENCE_THRESHOLD}% — queued for review",
            'path': path,
            'file_key': file_key
        }
    
    # 4. የአሮጌውን ኮድ አስቀምጥ (Backup)
    old_code = ""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except Exception as e:
            logger.warning(f"⚠️ Could not read old file: {e}")
            old_code = ""
    
    # 5. ወደ ፋይል ጻፍ (Local File Write - Thread Safe)
    with _file_lock:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.info(f"📝 Written to {path}")
        except Exception as e:
            error_msg = f"❌ File write error: {e}"
            logger.error(error_msg)
            
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
            finally:
                connection.close()
            
            return {
                'success': False,
                'applied': False,
                'message': error_msg,
                'path': path,
                'file_key': file_key
            }
    
    # 6. ወደ GitHub ግፋ (GitHub Push - Decoupled & Exact Paths)
    push_result = "Skipped (push_to_github=False)"
    if push_to_github:
        try:
            site_name = site.name if site else "primary"
            commit_message = f"AI: {reason[:100]} (Confidence {confidence_score}%)"
            
            # ✅ የ GitHub አንጻራዊ ማውጫ ፈላጊ (የ .py.py መደጋገም እንዳይፈጠር ያደርጋል)
            if site_name == "primary":
                relative_path = os.path.relpath(path, settings.BASE_DIR)
            else:
                # የሩቅ ሳይት ከሆነ በሪፖዚተሪው ውስጥ ያለውን ትክክለኛ ማህደር ለይቶ ማውጣት
                match = re.search(r"marketplace/.*$", path.replace('\\', '/'))
                if match:
                    relative_path = match.group(0)
                else:
                    relative_path = f"marketplace/{file_key}.py" if not file_key.endswith('.py') else file_key
            
            push_result = push_code_to_github(
                file_path=relative_path,
                file_content=new_content,
                commit_message=commit_message,
                site_name=site_name
            )
                    
        except Exception as e:
            push_result = f"❌ GitHub push error: {e}"
            logger.error(push_result)
    
    # 7. ለውጥ መዝግብ (Evolution Log)
    try:
        AIEvolutionLog.objects.create(
            backlog_task=backlog_task,
            target_file=file_key,
            reason_for_change=reason,
            old_code_backup=old_code[:10000],  # ከፍተኛ 10k ቁምፊዎች
            new_code_patch=new_content[:10000],
            site=site
        )
        logger.info(f"📝 Logged evolution for {file_key}")
    except Exception as e:
        logger.warning(f"⚠️ Could not log evolution: {e}")
    finally:
        connection.close()
    
    # 8. ተዛማጅ ስራ ሁኔታ አዘምን
    if backlog_task:
        try:
            backlog_task.status = 'Completed'
            backlog_task.save()
            logger.info(f"✅ Task {backlog_task.task_name} marked as Completed")
        except Exception as e:
            logger.warning(f"⚠️ Could not update task status: {e}")
        finally:
            connection.close()
    
    return {
        'success': True,
        'applied': True,
        'message': f"✅ Applied {file_key} | GitHub: {push_result}",
        'path': path,
        'file_key': file_key
    }


# ============================================================
# 🚀 ጊትሃብ መግፊያ ሎጂክ (Decoupled & Complete)
# ============================================================

def push_code_to_github(file_path, file_content, commit_message, site_name="primary"):
    """
    የተጻፈውን አዲስ ኮድ በቀጥታ ወደ ጊትሃብ ይልካል
    """
    github_token = getattr(settings, 'GITHUB_TOKEN', None)
    repo = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    
    if not github_token:
        logger.warning("❌ GITHUB_TOKEN Missing from settings. Trying subprocess fallback...")
        return _simple_git_push(file_path, file_content, commit_message)

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    sha = ""
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            sha = res.json().get('sha', '')
            logger.info(f"📄 Found existing file in GitHub: {file_path}")
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
        put_res = requests.put(url, headers=headers, json=payload, timeout=6)
        if put_res.status_code in [200, 201]:
            return "✅ Pushed successfully!"
        return f"❌ Push Failed: {put_res.text[:100]}"
    except Exception as e:
        return f"❌ Connection Failed: {e}"


# ============================================================
# 10. ውጫዊ ጊት መግፊያ (Subprocess with Timeout)
# ============================================================

def _simple_git_push(file_path, content, commit_message, site_name="primary"):
    """
    ቀላል git push — Subprocess ከ 8 ሰከንድ ከፍተኛ የመጠበቂያ ጊዜ ጋር (Timeout)
    """
    try:
        base_dir = settings.BASE_DIR
        full_path = os.path.join(base_dir, file_path)
        
        commands = [
            ['git', 'add', file_path],
            ['git', 'commit', '-m', commit_message],
            ['git', 'push', 'origin', 'main']
        ]
        
        for cmd in commands:
            result = subprocess.run(cmd, cwd=base_dir, capture_output=True, text=True, timeout=8)
            if result.returncode != 0 and 'nothing to commit' not in result.stderr:
                return f"⚠️ Git error: {result.stderr[:100]}"
        
        return f"✅ Git push for {file_path}"
        
    except subprocess.TimeoutExpired:
        return f"❌ Git push timeout (8 seconds exceeded)"
    except Exception as e:
        return f"❌ Git error: {e}"


def validate_code_syntax(code, file_type="python"):
    if file_type == "python":
        try:
            compile(code, "validate.py", 'exec')
            return {'valid': True, 'message': 'Syntax OK'}
        except SyntaxError as e:
            return {'valid': False, 'message': f"Syntax error: {e}"}
    return {'valid': True, 'message': f'Validation for {file_type} not implemented'}


def get_code_diff(old_code, new_code):
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
            diff.append(f"Line {i+1}: -{old_lines[i][:40]} +{new_lines[i][:40]}")
    
    return '\n'.join(diff[:10])


def sanitize_code(content):
    dangerous = ['eval(', 'exec(', 'os.system(', 'subprocess.call(']
    for item in dangerous:
        if item in content:
            logger.warning(f"⚠️ Dangerous code pattern detected: {item}")
    return content


# ============================================================
# 📊 የስርዓት ሁኔታ መመለሻ
# ============================================================

def get_code_apply_stats():
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
    finally:
        connection.close()
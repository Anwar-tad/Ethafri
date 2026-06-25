# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/code_apply.py
# 📝 ዓላማ፦ Safe & Precise Code Application — Guardian Standard (Fixed)
# ✅ የተፈቱ ችግሮች፦ AST check on HTML files, 'home_html' mapping bug, Path Traversal vulnerability
# 📅 ቀን፦ 2026-06-25
# ============================================================

import os
import ast
import logging
import requests
import base64
from django.conf import settings
from .models import AIEvolutionLog

logger = logging.getLogger(__name__)

# ============================================================
# 🛠️ ዋናው የኮድ መተግበሪያ ተግባር (apply_code_change)
# ============================================================

def apply_code_change(site, file_key, new_content, reason="", path=None, 
                      confidence_score=100, backlog_task=None, push_to_github=True):
    """
    ኮድን በደህንነት ይተገብራል፣ የፓይተን ሲንታክስ ብቻ ይፈትሻል፣ እና ወደ GitHub ይገፋል (Sync)
    """
    
    # 1. 🛡️ የፋይል ስም እና ማውጫ መፍቻ (Smarter Path & Extension Resolver)
    base_dir = str(settings.BASE_DIR)
    
    if not path:
        # 'home_html' የሚለውን ቁልፍ ወደ ትክክለኛው የ HTML ፋይል መለወጥ (home_html.py መደጋገምን ያስቀራል)
        if file_key == 'home_html':
            file_name = 'templates/marketplace/home.html'
        else:
            file_name = f"{file_key}.py" if not file_key.endswith(('.py', '.html')) else file_key
            
        path = os.path.join(base_dir, 'marketplace', file_name)
    
    # 2. 🛡️ የደህንነት ጥበቃ አጥር (Path Traversal Gating - 100% Secure)
    # AIው ከ base_dir ውጪ በስህተትም ሆነ በቅንነት ኮድ እንዳይጽፍ ይከላከላል
    real_path = os.path.abspath(path)
    real_base = os.path.abspath(base_dir)
    if not real_path.startswith(real_base):
        error_msg = f"❌ Security Block: Path Traversal Attempted for path {path}"
        logger.error(error_msg)
        return {
            'success': False,
            'applied': False,
            'message': error_msg,
            'path': path,
            'file_key': file_key
        }

    # 3. 🛡️ የሲንታክስ (Syntax) ፍተሻ - ለፓይተን ፋይሎች ብቻ!
    # ይህ ማስተካከያ HTML ገጾች (templates) ያለ ምንም እንቅፋት እንዲሻሻሉ በር ይከፍታል
    if path.endswith('.py'):
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return {
                'success': False, 
                'applied': False, 
                'message': f"❌ Python Syntax Error blocked: {e}",
                'path': path,
                'file_key': file_key
            }

    # 4. የአሮጌውን ኮድ አስቀምጥ (Backup for Rollback)
    old_code = ""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except Exception as e:
            logger.warning(f"⚠️ Could not read old file for backup: {e}")

    # 5. ወደ ፋይል ጻፍ (Local File Write)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        logger.info(f"💾 Written successfully to: {path}")
    except Exception as e:
        error_msg = f"❌ File write error: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'applied': False,
            'message': error_msg,
            'path': path,
            'file_key': file_key
        }

    # 6. ወደ GitHub ግፋ (GitHub Push - Decoupled)
    push_status = "Skipped"
    if push_to_github:
        try:
            # ለ GitHub የሚሆን አንጻራዊ መንገድ (Relative Path)
            rel_path = os.path.relpath(path, settings.BASE_DIR).replace('\\', '/')
            push_status = push_to_github_raw(rel_path, new_content, reason)
        except Exception as e:
            push_status = f"GitHub Error: {e}"
            logger.error(push_status)

    # 7. ለውጥ መዝግብ (Evolution Log)
    try:
        AIEvolutionLog.objects.create(
            site=site,
            target_file=file_key,
            reason_for_change=reason,
            old_code_backup=old_code[:10000],  # ከፍተኛ 10k ፊደላት
            new_code_patch=new_content[:10000],
            backlog_task=backlog_task
        )
    except Exception as e:
        logger.warning(f"⚠️ Could not log evolution entry: {e}")

    # 8. ተዛማጅ ስራ ሁኔታ አዘምን
    if backlog_task:
        try:
            backlog_task.status = 'Completed'
            backlog_task.save()
        except Exception as e:
            logger.warning(f"⚠️ Could not update task status: {e}")

    return {
        'success': True,
        'applied': True,
        'message': f"✅ Applied {file_key} | GitHub: {push_status}",
        'path': path,
        'file_key': file_key
    }


# ============================================================
# 🚀 ጊትሃብ መግፊያ ሎጂክ (Raw API)
# ============================================================

def push_to_github_raw(file_path, content, message):
    """GitHub API በመጠቀም ኮድን በቀጥታ ወደ ሪፖዚተሪ መግፋት"""
    token = getattr(settings, 'GITHUB_TOKEN', None)
    repo = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    if not token: 
        return "Local only (No Token)"

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"token {token}", 
        "Accept": "application/vnd.github.v3+json"
    }

    # የፋይሉን SHA ማግኘት (ለመተካት አስፈላጊ ነው)
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None

    payload = {
        "message": f"AI: {message[:100]}",
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "branch": "main"
    }
    if sha: 
        payload["sha"] = sha

    try:
        put_res = requests.put(url, headers=headers, json=payload, timeout=8)
        if put_res.status_code in [200, 201]:
            return "Sync OK"
        return f"Error {put_res.status_code}"
    except Exception as e:
        return f"Connection Error: {e}"
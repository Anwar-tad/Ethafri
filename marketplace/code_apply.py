# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/code_apply.py
# 📝 ዓላማ፦ Safe & Precise Code Application — Guardian Standard (v9.5)
# ✅ የተፈቱ ችግሮች፦ Multi-site SaaS Sandboxing, Path Commonpath Defense, Site-Specific Repo Routing
# 📅 ቀን፦ 2026-06-27
# ============================================================

import os
import ast
import re
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
                      confidence_score=100, backlog_task=None, push_to_github=False):
    """
    ኮድን በደህንነት ይተገብራል፣ የፓይተን ሲንታክስ ብቻ ይፈትሻል፣ 
    እና በአስተዳዳሪው ትዕዛዝ መሠረት ብቻ ወደ GitHub ያመሳስላል (Sync)
    """
    
    # 1. የፋይል ስም እና ማውጫ በዳይናሚክ መፍታት (SaaS Sandboxed Workspaces)
    base_dir = str(settings.BASE_DIR)
    app_name = 'marketplace'
    
    # የሳይቱን ቤዝ ማህደር መወሰን (የሳይቶች ዳታ እንዳይደባለቅ መከላከያ)
    if site and site.name != 'primary':
        if site.repo_path:
            if site.repo_path.startswith('http') or 'github.com' in site.repo_path:
                # ሪሞት ሪፖዚተሪ ከሆነ በጊዚያዊ የሥራ ማህደር ውስጥ ማስቀመጥ
                base = os.path.join('/tmp', 'ethafri_agent', site.name)
            else:
                # ሎካል ማህደር ከሆነ የራሱን ማውጫ መጠቀም
                base = site.repo_path
        else:
            base = os.path.join('/tmp', 'ethafri_agent', site.name)
    else:
        base = base_dir

    if not path:
        if file_key.endswith('_html') or 'html' in file_key:
            clean_name = file_key.replace('_html', '').replace('.html', '') + '.html'
            file_path_relative = os.path.join('templates', app_name, clean_name)
        else:
            clean_name = file_key.replace('.py', '') + '.py'
            file_path_relative = clean_name
            
        path = os.path.join(base, app_name, file_path_relative)
    
    # 2. 🛡️ የደህንነት ጥበቃ አጥር (Path Traversal Gating - Commonpath Check)
    real_path = os.path.abspath(path)
    real_base = os.path.abspath(base)
    
    # ከየራሱ ደንበኛ workspace ውጪ ለመፃፍ ሲሞከር ወዲያውኑ ማገድ (ለሁሉም ሳይቶች ይሰራል)
    try:
        if os.path.commonpath([real_path, real_base]) != real_base:
            raise ValueError("Path Traversal Blocked")
    except (ValueError, Exception):
        error_msg = f"❌ Security Block: Path Traversal Attempted for path {path}"
        logger.error(error_msg)
        return {
            'success': False, 'applied': False, 'message': error_msg,
            'path': path, 'file_key': file_key
        }

    # 3. የሲንታክስ (Syntax) ፍተሻ - ለፓይተን ፋይሎች ብቻ!
    if path.endswith('.py'):
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return {
                'success': False, 'applied': False, 
                'message': f"❌ Python Syntax Error blocked: {e}",
                'path': path, 'file_key': file_key
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
            'success': False, 'applied': False, 'message': error_msg,
            'path': path, 'file_key': file_key
        }

    # 6. ወደ GitHub ግፋ (GitHub Push - Decoupled Guardrail)
    push_status = "Skipped (Local Only)"
    if push_to_github:
        try:
            # ሪፖዚተሪ-አንጻራዊ አቅጣጫን በሳይቱ ማህደር መሰረት በትክክል ማስላት
            rel_path = os.path.relpath(path, base).replace('\\', '/')
            push_status = push_to_github_raw(rel_path, new_content, reason, site=site)
        except Exception as e:
            push_status = f"GitHub Error: {e}"
            logger.error(push_status)

    # 7. ለውጥ መዝግብ (Evolution Log)
    try:
        AIEvolutionLog.objects.create(
            site=site,
            target_file=file_key,
            reason_for_change=reason,
            old_code_backup=old_code[:10000],
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

def push_to_github_raw(file_path, content, message, site=None):
    """GitHub API በመጠቀም ኮድን በቀጥታ ወደየሳይቱ ሪፖዚተሪ መግፋት"""
    token = getattr(settings, 'GITHUB_TOKEN', None)
    
    # ጊትሃብ ሪፖን በሳይት ደረጃ በዳይናሚክ መወሰን (የማከማቻ አድራሻ መዛባትን ይከላከላል)
    repo = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    if site and site.repo_path and ('github.com' in site.repo_path or site.repo_path.startswith('http')):
        match = re.search(r"github\.com/([^/]+/[^/]+)", site.repo_path)
        if match:
            repo = match.group(1).replace('.git', '')

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
            return f"Sync OK ({repo})"
        return f"Error {put_res.status_code}"
    except Exception as e:
        return f"Connection Error: {e}"
import os
import ast
import logging
import requests
import base64
from django.conf import settings
from .models import AIEvolutionLog

logger = logging.getLogger(__name__)

def apply_code_change(site, file_key, new_content, reason, confidence_score=100, backlog_task=None):
    """ኮድን በደህንነት ይተገብራል"""
    
    # 1. የሲንታክስ (Syntax) ፍተሻ - ኮዱ ሳይቱን እንዳያቆመው
    try:
        ast.parse(new_content)
    except SyntaxError as e:
        logger.error(f"❌ Syntax Error Blocked: {e}")
        return {'success': False, 'applied': False, 'message': f"❌ Syntax Error: {e}"}

    try:
        # 2. ፋይልን መፈለጊያ (Path Resolver - የደህንነት ማጠናከሪያ)
        base_dir = str(settings.BASE_DIR)
        
        # የ file_key አጻጻፍን ማስተካከል
        if not file_key.endswith(('.py', '.html')):
            file_name = f"{file_key}.py"
        else:
            file_name = file_key
            
        # በማርኬትፕሌይስ ዙሪያ የሚፈጠርን የፓዝ መደጋገም መከላከል
        if 'marketplace' in file_name:
            path = os.path.normpath(os.path.join(base_dir, file_name))
        else:
            path = os.path.normpath(os.path.join(base_dir, 'marketplace', file_name))
        
        # 3. የአሮጌውን ኮድ Backup መያዝ
        old_code = ""
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()

        # 4. ወደ ፋይል መጻፍ (Local Write)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # 5. ወደ GitHub መግፋት (Sync)
        # ማሳሰቢያ፦ ይህ የሚሰራው የ GITHUB_TOKEN በ settings/env ላይ ሲገኝ ብቻ ነው
        github_status = push_to_github_raw(path, new_content, reason)
        
        # 6. ለውጡን መመዝገብ (Evolution Log)
        AIEvolutionLog.objects.create(
            site=site, 
            target_file=file_key, 
            reason_for_change=reason,
            old_code_backup=old_code[:5000], 
            new_code_patch=new_content[:5000],
            backlog_task=backlog_task
        )
        
        return {'success': True, 'applied': True, 'message': f"✅ Applied & Sync: {github_status}"}
    except Exception as e:
        logger.critical(f"❌ Fatal Write Error in apply_code_change: {e}")
        return {'success': False, 'applied': False, 'message': f"❌ Write Error: {e}"}

def push_to_github_raw(file_path, content, message):
    """GitHub API በመጠቀም ኮድን በቀጥታ መግፋት"""
    token = getattr(settings, 'GITHUB_TOKEN', None)
    repo = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    
    # 👑 የደህንነት መከላከያ፦ ቶክን ከሌለ ወይም ፑሽ እንዲደረግ ትዕዛዝ ካልተሰጠ ወደ 깃ሃብ አይገፋም
    if not token: 
        return "Local only (No Token System)"

    try:
        # ለ GitHub የሚሆን አንጻራዊ መንገድ (Relative Path)
        rel_path = os.path.relpath(file_path, settings.BASE_DIR).replace('\\', '/')
        url = f"https://api.github.com/repos/{repo}/contents/{rel_path}"
        headers = {
            "Authorization": f"token {token}", 
            "Accept": "application/vnd.github.v3+json"
        }

        # የፋይሉን SHA ማግኘት (ለመተካት ወሳኝ ነው)
        res = requests.get(url, headers=headers, timeout=10)
        sha = None
        if res.status_code == 200:
            sha = res.json().get('sha')
        elif res.status_code == 404:
            # ፋይሉ በ GitHub ላይ አዲስ ከሆነ SHA አያስፈልገውም
            sha = None
        else:
            logger.warning(f"⚠️ Unexpected GitHub SHA response: {res.status_code}")
            return f"GitHub Link Issue ({res.status_code})"

        payload = {
            "message": f"AI: {message[:50]}",
            "content": base64.b64encode(content.encode()).decode('utf-8'),
            "branch": "main"
        }
        if sha: 
            payload["sha"] = sha

        put_res = requests.put(url, headers=headers, json=payload, timeout=15)
        if put_res.status_code in [200, 201]:
            return "GitHub Sync OK"
        else:
            logger.error(f"❌ GitHub Put Error {put_res.status_code}: {put_res.text}")
            return f"GitHub Error {put_res.status_code}"
            
    except Exception as e:
        logger.error(f"🚨 Exception in push_to_github_raw: {e}")
        return "GitHub Timeout/Error"

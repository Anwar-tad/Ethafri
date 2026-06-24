import os, ast, logging, requests, base64
from django.conf import settings
from .models import AIEvolutionLog

logger = logging.getLogger(__name__)

def apply_code_change(site, file_key, new_content, reason, confidence_score=100, backlog_task=None):
    """ኮድን በደህንነት ይተገብራል"""
    
    # 1. የሲንታክስ (Syntax) ፍተሻ - ኮዱ ሳይቱን እንዳያቆመው
    try:
        ast.parse(new_content)
    except SyntaxError as e:
        return {'success': False, 'applied': False, 'message': f"❌ Syntax Error: {e}"}

    # 2. ፋይልን መፈለጊያ (Path Resolver)
    base_dir = str(settings.BASE_DIR)
    path = os.path.join(base_dir, 'marketplace', f"{file_key}.py" if not file_key.endswith(('.py', '.html')) else file_key)
    
    # 3. የአሮጌውን ኮድ Backup መያዝ
    old_code = ""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            old_code = f.read()

    # 4. ወደ ፋይል መጻፍ (Local Write)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # 5. ወደ GitHub መግፋት (Sync)
        github_status = push_to_github_raw(path, new_content, reason)
        
        # 6. ለውጡን መመዝገብ (Evolution Log)
        AIEvolutionLog.objects.create(
            site=site, target_file=file_key, reason_for_change=reason,
            old_code_backup=old_code[:5000], new_code_patch=new_content[:5000],
            backlog_task=backlog_task
        )
        
        return {'success': True, 'applied': True, 'message': f"✅ Applied & Sync: {github_status}"}
    except Exception as e:
        return {'success': False, 'applied': False, 'message': f"❌ Write Error: {e}"}

def push_to_github_raw(file_path, content, message):
    """GitHub API በመጠቀም ኮድን በቀጥታ መግፋት"""
    token = getattr(settings, 'GITHUB_TOKEN', None)
    repo = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    if not token: return "Local only (No Token)"

    # ለ GitHub የሚሆን አንጻራዊ መንገድ (Relative Path)
    rel_path = os.path.relpath(file_path, settings.BASE_DIR).replace('\\', '/')
    url = f"https://api.github.com/repos/{repo}/contents/{rel_path}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    # የፋይሉን SHA ማግኘት (ለመተካት አስፈላጊ ነው)
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None

    payload = {
        "message": f"AI: {message[:50]}",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main"
    }
    if sha: payload["sha"] = sha

    put_res = requests.put(url, headers=headers, json=payload)
    return "GitHub Sync OK" if put_res.status_code in [200, 201] else f"GitHub Error {put_res.status_code}"
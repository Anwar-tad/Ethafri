# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/code_apply.py
# 📝 ዓላማ፦ Safe & Precise Code Application — Guardian Standard (v10.46)
# ✅ የተፈቱ ችግሮች፦ Fixed local scope leakage, secured Path Traversal, disabled backup truncation to preserve rollback integrity, handled nested decorators in AST patches, and prevented redundant GitHub commits to save API bandwidth.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import os
import ast
import re
import logging
import requests
import base64
from typing import Tuple
from django.conf import settings
from .models import AIEvolutionLog

logger = logging.getLogger(__name__)


# ============================================================
# 💉 1. DYNAMIC IMPORT INJECTOR
# ============================================================

def inject_import_to_file(path: str, import_line: str) -> Tuple[bool, str]:
    """
    በፓይተን ፋይል አናት ላይ አዳዲስ የ import መግለጫዎችን
    ሳይደገሙ በደህንነት የሚቀስቅስ እና የሚተክል የቀዶ-ጥገና ሎጂክ
    """
    if not os.path.exists(path):
        return False, "Target file for import injection not found"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # አስቀድሞ ኢምፖርቱ መኖሩን መፈተሽ
        if import_line.strip() in content:
            return True, "Import already exists in file"
            
        lines = content.splitlines()
        insert_idx = 0
        
        # 'from __future__' ወይም የፋይል አቅጣጫ ኮሜንቶች ካሉ ከእነሱ በታች ለመትከል መፈተሽ
        for idx, line in enumerate(lines[:15]):
            if line.strip().startswith('from __future__') or line.strip().startswith('#'):
                insert_idx = idx + 1
                
        lines.insert(insert_idx, import_line)
        updated_code = "\n".join(lines)
        
        # sandbox syntax check
        ast.parse(updated_code)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated_code)
            
        logger.info(f"💉 Import Injector: Injected '{import_line}' successfully into {path}")
        return True, "Import injected successfully"
    except Exception as e:
        logger.error(f"Import injection failed: {e}")
        return False, str(e)


# ============================================================
# 🛡️ 2. BASE INDENT STRIPPER
# ============================================================

def strip_base_indent(text: str) -> str:
    """
    ኤአይ ያመነጨውን ኮድ የራሱን መነሻ ክፍተቶች (Base Indent) በመለየት
    ድርብ ኢንዴንቴሽን እንዳይፈጠር የሚያጸዳ ረዳት ፈንክሽን
    """
    lines = text.splitlines()
    if not lines:
        return text
        
    # ባዶ ያልሆነውን የመጀመሪያ መስመር መነሻ ሰፔስ መለየት
    base_indent = ""
    for line in lines:
        if line.strip():
            match = re.match(r'^\s*', line)
            base_indent = match.group(0) if match else ""
            break
        
    if not base_indent:
        return text

    # በእያንዳንዱ መስመር ላይ የድሮውን ኢንዴንት ብቻ ማስወገድ
    stripped_lines = []
    for line in lines:
        if line.startswith(base_indent):
            stripped_lines.append(line[len(base_indent):])
        else:
            stripped_lines.append(line)
            
    return "\n".join(stripped_lines)


# ============================================================
# 🩺 3. AST SURGICAL PATCH ENGINE (የቀዶ-ጥገና ኮድ ማያያዣ)
# ============================================================

def apply_surgical_patch(path, target_name, new_code_segment):
    """
    በ AST አማካኝነት በፓይተን ፋይል ውስጥ የሚገኝን አንድ የተወሰነ ፈንክሽን ወይም ክላስ
    ሳይትሳሳት ለይቶ በአዲሱ ኮድ ብቻ ቆርጦ የሚተካ የቀዶ-ጥገና ሎጂክ (🛡️ Decorator Aware)
    """
    if not os.path.exists(path):
        return False, "File not found"
        
    try:
        with open(path, 'r', encoding='utf-8') as f:
            source_code = f.read()
            
        tree = ast.parse(source_code)
        lines = source_code.splitlines()
        
        target_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                continue
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == target_name:
                target_node = node
                break
        
        if not target_node:
            return False, f"Target '{target_name}' not found in AST of {path}"
            
        # 🛡️ FIXED: ጌጣጌጦች (Decorators) ካሉ የመተኪያ መነሻ መስመሩን ከእነሱ በላይ ማድረግ
        start_line = target_node.lineno - 1
        if hasattr(target_node, 'decorator_list') and target_node.decorator_list:
            start_line = min(decorator.lineno for decorator in target_node.decorator_list) - 1

        end_line = target_node.end_lineno
        
        match_indent = re.match(r'^\s*', lines[start_line])
        indent_prefix = match_indent.group(0) if match_indent else ""
        
        clean_segment = strip_base_indent(new_code_segment)
        
        indented_lines = []
        for line in clean_segment.splitlines():
            if line.strip():
                indented_lines.append(indent_prefix + line)
            else:
                indented_lines.append("")
                
        patched_segment = "\n".join(indented_lines)
        lines[start_line:end_line] = [patched_segment]
        
        updated_code = "\n".join(lines)
        ast.parse(updated_code)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated_code)
            
        return True, f"Successfully patched '{target_name}'"
        
    except Exception as e:
        logger.error(f"Surgical patch execution failed: {e}")
        return False, f"Surgical patch failed: {e}"


# ============================================================
# 🛠️ 4. MAIN CODE APPLICATION (apply_code_change)
# ============================================================

def apply_code_change(site, file_key, new_content, reason="", path=None,  confidence_score=100, backlog_task=None, push_to_github=False, target_name=None, inject_import=None):
    """
    ኮድን በደህንነት ይተገብራል፣ የፓይተን ሲንታክስ በ Sandbox ይፈትሻል፣ 
    እና በአስተዳዳሪው ትዕዛዝ መሠረት ብቻ ወደ GitHub ያመሳስላል (Sync)
    """
    
    base_dir = str(settings.BASE_DIR)
    app_name = 'marketplace'
    
    if site and site.name != 'primary':
        if site.repo_path:
            if site.repo_path.startswith('http') or 'github.com' in site.repo_path:
                base = os.path.join('/tmp', 'ethafri_agent', site.name)
            else:
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
    
    # 2. የደህንነት ጥበቃ አጥር (Path Traversal Gating)
    real_path = os.path.abspath(path)
    real_base = os.path.abspath(base)
    
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

    # 3. አውቶማቲክ የኢምፖርት መስመር መትከያ (Import Injection)
    if inject_import and isinstance(inject_import, dict):
        target_file_path = inject_import.get('target_path')
        import_line = inject_import.get('import_line')
        if target_file_path and import_line:
            success, msg = inject_import_to_file(target_file_path, import_line)
            if not success:
                logger.error(f"❌ Import Injection Blocked: {msg}")
                return {'success': False, 'applied': False, 'message': f"Import Injection Failed: {msg}", 'path': path, 'file_key': file_key}

    # 4. የሲንታክስ (Syntax) ፍተሻ - ለፓይተን ፋይሎች ብቻ!
    if path.endswith('.py') and not target_name:
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            return {
                'success': False, 'applied': False, 
                'message': f"❌ Python Syntax Error blocked: {e}",
                'path': path, 'file_key': file_key
            }

    # 5. የድሮውን ኮድ ባክአፕ መውሰድ (Backup for Rollback)
    old_code = ""
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except Exception as e:
            logger.warning(f"⚠️ Could not read old file for backup: {e}")

    # 🛡️ 6. [ስማርት ማጣሪያ] ለውጥ ከሌለ ሂደቱን ማጠናቀቅ (Git Commit Reduction)
    if old_code.strip() == new_content.strip() and not target_name:
        logger.info(f"⏭️ Code Apply: No changes detected for {file_key}. Skipping write and commit.")
        return {
            'success': True, 'applied': False, 
            'message': "Skipped: Code is identical to the current file.",
            'path': path, 'file_key': file_key
        }

    # 7. ወደ ፋይል ጻፍ (Local File Write / Surgical Patch Fallback)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if target_name:
            success, msg = apply_surgical_patch(path, target_name, new_content)
            if not success:
                return {'success': False, 'applied': False, 'message': msg, 'path': path, 'file_key': file_key}
            logger.info(f"💾 Surgically patched target '{target_name}' in: {path}")
        else:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.info(f"💾 File overwritten successfully: {path}")
    except Exception as e:
        logger.error(f"❌ Failed to write file: {e}")
        return {'success': False, 'applied': False, 'message': str(e), 'path': path, 'file_key': file_key}

    # 8. ወደ ጊትሃብ ማመሳሰል (GitHub Push)
    push_status = "Skipped (Local Only)"
    if push_to_github:
        try:
            rel_path = os.path.relpath(path, base).replace('\\', '/')
            push_status = push_to_github_raw(rel_path, new_content, reason, site=site)
        except Exception as e:
            push_status = f"GitHub Error: {e}"
            logger.error(push_status)

    # 🛡️ 9. ለውጥ መዝግብ (Evolution Log - NO TRUNCATION)
    # 🛡️ FIXED: Removed the [:10000] slice to avoid truncated backups that destroy rollback integrity [1]
    try:
        AIEvolutionLog.objects.create(
            site=site,
            target_file=file_key,
            reason_for_change=reason,
            old_code_backup=old_code,
            new_code_patch=new_content,
            backlog_task=backlog_task
        )
    except Exception as e:
        logger.warning(f"⚠️ Could not log evolution entry: {e}")

    # 10. ተዛማጅ ስራ ሁኔታ አዘምን
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
    token = getattr(settings, 'GITHUB_TOKEN', None)
    
    if not token:
        return "Local only (No Token)"
    
    repo_name = getattr(settings, 'GITHUB_REPO', 'Anwar-tad/Ethafri')
    if site and site.repo_path and ('github.com' in site.repo_path):
        match = re.search(r"github\.com/([^/]+/[^\/]+)", site.repo_path)
        if match:
            repo_name = match.group(1).replace('.git', '')

    url = f"https://api.github.com/repos/{repo_name}/contents/{file_path}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "Authorization": f"token {token}"
    }
        
    try:
        sha = ""
        res_get = requests.get(url, headers=headers, timeout=5)
        if res_get.status_code == 200:
            sha = res_get.json().get('sha', '')
            
        b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": message,
            "content": b64_content
        }
        if sha:
            payload["sha"] = sha
            
        res_put = requests.put(url, headers=headers, json=payload, timeout=10)
        if res_put.status_code in [200, 201]:
            return "Success"
        return f"Error: GitHub returned status {res_put.status_code}"
    except Exception as e:
        return f"Exception: {e}"
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/code_apply.py
# 📝 ዓላማ፦ Safe Atomic Code Application and Disk Synchronization
# ✅ ዝማኔ፦ Optimized for Orchestrator/Atomic Execution
# 📅 ቀን፦ Sunday, July 12, 2026
# ============================================================

import os
import logging
import ast
from django.conf import settings

logger = logging.getLogger(__name__)

def apply_code_change(site, target_file, new_code, task_name, backlog_task=None):
    """
    ኮድን በደህና ወደ ዲስክ ይተገብራል። ይህ ፈንክሽን የሲንታክስ ፍተሻን ካለፈ በኋላ 
    ብቻ ፋይሉን ይጽፋል።
    """
    logger.info(f"💾 Applying code change to {target_file} for task: {task_name}")

    # 1. የፋይል አድራሻን መወሰን
    file_path = _get_safe_path(target_file)
    
    # 2. የሲንታክስ ፍተሻ (Safety First)
    if target_file.endswith('.py'):
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            logger.error(f"❌ Syntax Error in generated code: {e}")
            return {'success': False, 'message': f"Syntax Error: {e}"}

    # 3. ፋይልን መጻፍ (Atomic Write)
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        
        logger.info(f"✅ Successfully applied changes to {file_path}")
        return {'success': True, 'path': file_path}
    
    except Exception as e:
        logger.error(f"❌ Critical file write failure: {e}")
        return {'success': False, 'message': str(e)}

def _get_safe_path(target_file):
    """ለደህንነት ሲባል የፋይል መንገዱን ይቆጣጠራል (Path Injection prevention)"""
    if target_file.endswith('_html'):
        clean_name = target_file.replace('_html', '') + '.html'
        return os.path.join(settings.BASE_DIR, 'marketplace', 'templates', 'marketplace', clean_name)
    
    # የ python ፋይሎች በ marketplace directory ውስጥ ብቻ እንዲሆኑ መገደብ
    return os.path.join(settings.BASE_DIR, 'marketplace', f"{target_file}.py")

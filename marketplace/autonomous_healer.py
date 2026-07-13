# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/autonomous_healer.py
# 📝 ዓላማ፦ Autonomous Healing Orchestrator (v10.49)
# ✅ የተፈቱ ችግሮች፦ Dynamic path resolution for all target files, markdown code-fence sanitization, circular reference safety via django.apps dynamic model loader, and prevention of infinite retry loops to save AI tokens.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import os
import re
import ast
import logging
from django.conf import settings
from django.apps import apps # 🛡️ FIXED: dynamic model loader to prevent circular imports
from .code_apply import apply_code_change
from .ai_utils import ask_master_ai_smart

logger = logging.getLogger(__name__)

def resolve_target_file_path(site, target_file: str) -> str:
    """
    በጣቢያው አይነት እና በፋይል ቁልፍ መሰረት ትክክለኛውን የፋይል አቅጣጫ በዳይናሚክ መንገድ ይወስናል
    """
    base_dir = str(settings.BASE_DIR)
    app_name = 'marketplace'
    
    # የባለብዙ ጣቢያ (Multi-site Tenant) አቅጣጫን ማስተካከያ (Dynamic Resolution)
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

    # የኤችቲኤምኤል ቴምፕሌቶችን መለየት
    if target_file.endswith('_html') or 'html' in target_file:
        clean_name = target_file.replace('_html', '').replace('.html', '') + '.html'
        return os.path.join(base, app_name, 'templates', app_name, clean_name)
    
    # የፓይተን ፋይሎችን መለየት
    clean_name = target_file.replace('.py', '') + '.py'
    return os.path.join(base, app_name, clean_name)


def extract_pure_code(text: str) -> str:
    """
    ኤአይ የሚያመነጨውን ኮድ ከማርክዳውን ፌንሶች (```python ... ```)
    ለይቶ ንጹሕ ኮድ ብቻ የሚያወጣ ረዳት ፈንክሽን
    """
    if not text:
        return ""
    
    # የማርክዳውን ኮድ መክፈቻዎችን (Fences) መፈለግ
    match = re.search(r'```python\s*([\s\S]*?)```', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    match_generic = re.search(r'```\s*([\s\S]*?)```', text)
    if match_generic:
        return match_generic.group(1).strip()
        
    return text.strip()


def execute_autonomous_healing_cycle(site):
    """
    ይህ ሞጁል በስርዓቱ የተመዘገቡ ስህተቶችን በዳይናሚክ መንገድ ይለያል፣ በ AI መፍትሄ ያመነጫል፣ 
    እና ኮዱን በደህንነት ለመተግበር ወደ code_apply.py ይልካል።
    """
    # 🛡️ FIXED: Django Apps Registry በመጠቀም ሞዴሉን በዳይናሚክ መንገድ መጫን (Circular import safety)
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')

    # 1. አዳዲስ መፍትሄ የሚጠይቁ ሁሉንም ታስኮች ለይ (🛡️ Dynamic File Scope)
    # scrapper_engine ብቻ ሳይሆን ማንኛውንም የተበላሸ ፋይል (views, models, urls, etc.) እንዲያስተካክል ተደርጓል
    pending_tasks = AIProjectBacklog.objects.filter(
        site=site, 
        status="Pending", 
        task_name__icontains="EMERGENCY" # ወይም critical የሆኑ የጥገና ታስኮችን ለይቶ ለማስኬድ
    ) | AIProjectBacklog.objects.filter(
        site=site, 
        status="Pending", 
        task_type="code_repair" # የጥገና ስራዎችን ለመለየት
    ) | AIProjectBacklog.objects.filter(
        site=site, 
        status="Pending", 
        target_file="scrapper_engine" # ለተኳሃኝነት ሲባል
    )

    pending_tasks = pending_tasks.distinct()
    
    if not pending_tasks.exists():
        logger.info("Healer: No pending tasks found. System stable.")
        return

    logger.info(f"Healer: Found {pending_tasks.count()} tasks. Starting healing cycle...")

    for task in pending_tasks:
        try:
            # 2. ታስክን በስራ ላይ አድርግ (Locking)
            task.status = "Running"
            task.save()
            
            # 3. የፋይል አቅጣጫውን በዳይናሚክ መንገድ መወሰን (Dynamic File Resolver)
            target_file = task.target_file or "scrapper_engine"
            target_path = resolve_target_file_path(site, target_file)
            
            current_code = ""
            if os.path.exists(target_path):
                with open(target_path, "r", encoding="utf-8") as f:
                    current_code = f.read()
            else:
                logger.warning(f"Healer: Target file {target_path} not found. Creating a fresh file...")

            # 4. መፍትሄ በ AI አመንጭ
            prompt = f"""
            CRITICAL REPAIR TASK: {task.task_name}
            File to modify: {target_file} (Full Path: {target_path})
            Requirement: {task.description}. 
            
            Below is the current content of the file:
            {current_code}
            
            Please rewrite/fix this file. Write the complete, syntactically valid code.
            """
            ai_response = ask_master_ai_smart(prompt, task_type="code_repair")
            
            # 🛡️ 5. ኮዱን ከማርክዳውን ማጽዳት (Markdown Code-fence Stripper)
            fixed_code = extract_pure_code(ai_response)

            # 6. መፍትሄውን ወደ code_apply.py ላክ (የመጨረሻው እና ብቸኛው መተግበሪያ)
            if fixed_code and len(fixed_code.strip()) > 10:
                result = apply_code_change(
                    site=site,
                    file_key=target_file,
                    new_content=fixed_code,
                    reason=f"Auto-Heal Task ID: {task.id} - {task.description}",
                    path=target_path,
                    backlog_task=task,
                    push_to_github=True # አውቶማቲክ Deployment እንዲቀሰቀስ
                )
                
                if result.get('success'):
                    logger.info(f"✅ Healer: Task {task.id} successfully healed and applied to {target_file}.")
                else:
                    # 🛡️ ቶከን መቆጠቢያ፦ ጥገናው ካልተሳካ ታስክን ወደ Blocked በመቀየር ድጋሚ የማይቆም ሉፕ (Infinite loop) ውስጥ እንዳይገባ መከላከል
                    task.status = "Blocked"
                    task.save()
                    logger.error(f"❌ Healer: Application failed: {result.get('message')}")
            else:
                raise Exception("AI response was empty or invalid.")

        except Exception as e:
            logger.error(f"Healer: Critical error in task {task.id}: {e}")
            # አደገኛ ስህተት ሲፈጠር ታስክን ወደ Blocked በመቀየር የቁልፍ ቶከኖችን መባከን መከላከል
            task.status = "Blocked"
            task.save()
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/autonomous_healer.py
# 📝 ዓላማ፦ Autonomous Healing Coordinator (The Planner)
# ✅ ዝማኔ፦ Code deployment delegated to code_apply.py, prompt mutation enabled, 
#          and FieldError reflection check added to execute_autonomous_healing_cycle (v11.00).
# 📅 ቀን፦ Friday, July 24, 2026
# ============================================================

import os
import re
import logging
import json
from django.conf import settings
from django.apps import apps
from django.db.models import Q

logger = logging.getLogger(__name__)


def resolve_target_file_path(site, target_file: str) -> str:
    """
    በጣቢያው አይነት እና በፋይል ቁልፍ መሰረት ትክክለኛውን የፋይል አቅጣጫ በዳይናሚክ መንገድ ይወስናል
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

    if target_file.endswith('_html') or 'html' in target_file:
        clean_name = target_file.replace('_html', '').replace('.html', '') + '.html'
        return os.path.join(base, app_name, 'templates', app_name, clean_name)
    
    clean_name = target_file.replace('.py', '') + '.py'
    return os.path.join(base, app_name, clean_name)


def extract_pure_code(text: str) -> str:
    """
    ኤአይ የሚያመነጨውን ኮድ ከማርክዳውን ፌንሶች (```python ... ```)
    ለይቶ ንጹሕ ኮድ ብቻ የሚያወጣ ረዳት ፈንክሽን
    """
    if not text:
        return ""
    
    match = re.search(r'```python\s*([\s\S]*?)```', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    match_generic = re.search(r'```\s*([\s\S]*?)```', text)
    if match_generic:
        return match_generic.group(1).strip()
        
    return text.strip()


def execute_autonomous_healing_cycle(site):
    """
    በስርዓቱ የተመዘገቡ ስህተቶችን በዳይናሚክ መንገድ ይለያል፣ በ RAG ታሪክ መሠረት ፕሮምፕቱን ያዘጋጃል፣ 
    እና ኮዱን በደህንነት ለመተግበር 100% ወደ code_apply.py በውክልና ያስተላልፋል (The Planner)።
    """
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    VectorMemory = apps.get_model('marketplace', 'VectorMemory')
    
    if not AIProjectBacklog:
        return

    from .ai_utils import ask_master_ai_smart, clean_and_parse_json
    from .code_apply import apply_code_change

    # 1. አዳዲስ መፍትሄ የሚጠይቁ የጥገና ታስኮችን ለይቶ ማውጣት
    try:
        pending_tasks = AIProjectBacklog.objects.filter(
            site=site, 
            status="Pending"
        ).filter(Q(task_name__icontains="EMERGENCY") | Q(target_file="scrapper_engine"))

        # 🛡️ FIELDERROR REFLECTION CHECK: የ task_type መሬት በስኬማው ውስጥ መኖሩን በዳይናሚክ ማረጋገጥ
        task_fields = [f.name for f in AIProjectBacklog._meta.get_fields()]
        if 'task_type' in task_fields:
            pending_tasks = pending_tasks | AIProjectBacklog.objects.filter(
                site=site, 
                status="Pending", 
                task_type="code_repair"
            )
        pending_tasks = pending_tasks.distinct()
    except Exception as query_err:
        logger.warning(f"Healer query optimization bypassed due to error: {query_err}. Running fallback query.")
        pending_tasks = AIProjectBacklog.objects.filter(
            site=site,
            status="Pending"
        ).filter(Q(task_name__icontains="EMERGENCY") | Q(target_file="scrapper_engine"))

    if not pending_tasks.exists():
        logger.info("Healer Coordinator: No pending repair tasks found. System stable.")
        return

    logger.info(f"Healer Coordinator: Found {pending_tasks.count()} tasks. Starting planning cycle...")

    for task in pending_tasks:
        try:
            task.status = "Running"
            task.save()
            
            target_file = task.target_file or "scrapper_engine"
            target_path = resolve_target_file_path(site, target_file)
            
            current_code = ""
            if os.path.exists(target_path):
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        current_code = f.read()
                except Exception as r_err:
                    logger.warning(f"Healer could not read target file: {r_err}")

            past_failed_patches = []
            if VectorMemory:
                try:
                    failures = VectorMemory.objects.filter(site=site, memory_type='failed_attempt').order_by('-id')[:2]
                    past_failed_patches = [f.content for f in failures]
                except Exception:
                    pass

            attempts = 0
            success = False
            last_error_msg = ""

            while attempts < 2 and not success:
                attempts += 1
                
                if attempts > 1 and last_error_msg:
                    prompt = (
                        f"REPAIR RETRY LOOP (Attempt {attempts}/2):\n"
                        f"Task: {task.task_name}\n"
                        f"File to modify: {target_file} (Full Path: {target_path})\n"
                        f"Our previous attempt failed with compile or runtime error: '{last_error_msg}'.\n"
                        f"Please fully repair and refactor the code to fix this issue completely.\n"
                        f"Return JSON with key 'code' containing only the corrected and tested python snippet."
                    )
                else:
                    prompt = (
                        f"CRITICAL REPAIR TASK:\n"
                        f"Task: {task.task_name}\n"
                        f"File to modify: {target_file} (Full Path: {target_path})\n"
                        f"Requirement: {task.description}.\n\n"
                        f"Current File Content:\n{current_code}\n\n"
                        f"CRITICAL (Do not generate code that matches these past failed approaches): {json.dumps(past_failed_patches, ensure_ascii=False)}\n"
                        f"Write the optimal, syntactically valid code. Return JSON with key 'code' containing only the code."
                    )

                try:
                    ai_response = ask_master_ai_smart(prompt, task_type="coding", task=task)
                    res_data = clean_and_parse_json(ai_response)
                    fixed_code = res_data.get('code', '') if res_data else ""
                    if not fixed_code:
                        fixed_code = extract_pure_code(ai_response)
                except Exception as ai_err:
                    last_error_msg = f"AI response generation failed: {ai_err}"
                    continue

                if fixed_code and len(fixed_code.strip()) > 10:
                    logger.info(f"Healer Coordinator: Delegating code deployment of {target_file} to code_apply...")
                    
                    surgical_target = None
                    match_node = re.search(r'(?:class|def)\s+([a-zA-Z0-9_]+)', task.description)
                    if match_node:
                        surgical_target = match_node.group(1)

                    result = apply_code_change(
                        site=site,
                        file_key=target_file,
                        new_content=fixed_code,
                        reason=f"Healer Task ID: {task.id} - {task.task_name}",
                        backlog_task=task,
                        target_name=surgical_target
                    )

                    if result.get('success'):
                        success = True
                        logger.info(f"✅ Healer Coordinator: Task {task.id} successfully healed on {target_file}.")
                    else:
                        last_error_msg = result.get('message', 'Unknown application failure')
                        logger.warning(f"⚠️ Healer Coordinator: Application attempt {attempts} failed: {last_error_msg}")
                else:
                    last_error_msg = "Generated code was empty or invalid"

            if not success:
                if VectorMemory:
                    try:
                        VectorMemory.objects.create(
                            site=site,
                            memory_type='failed_attempt',
                            content=f"File: {target_file} failed to heal. Last error: {last_error_msg}",
                            success_rate=0.0
                        )
                    except Exception: pass

                task.status = "Blocked"
                task.save()
                logger.error(f"❌ Healer Coordinator: Task {task.id} is blocked after exhaustively failing retries. Error: {last_error_msg}")

        except Exception as e:
            logger.error(f"Healer: Critical error in task {task.id}: {e}")
            task.status = "Blocked"
            task.save()
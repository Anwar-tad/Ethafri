# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/autonomous_healer.py
# 📝 ዓላማ፦ Autonomous Healing Orchestrator (v10.47)
# ✅ የተፈቱ ችግሮች፦ Decoupled from GitHub CLI, Centralized code application, and Optimized task management.
# 📅 ቀን፦ Sunday, July 12, 2026
# ============================================================

import logging
from .models import AIProjectBacklog
from .code_apply import apply_code_change
from .ai_utils import ask_master_ai_smart

logger = logging.getLogger(__name__)

def execute_autonomous_healing_cycle(site):
    """
    ይህ ሞጁል ችግሮችን ይለያል፣ በ AI መፍትሄ ያመነጫል፣ 
    እና ኮዱን ለመተግበር ወደ code_apply.py ይልካል።
    """
    # 1. አዳዲስ መፍትሄ የሚጠይቁ ታስኮችን ለይ
    pending_tasks = AIProjectBacklog.objects.filter(site=site, status="Pending", target_file="scrapper_engine")
    
    if not pending_tasks.exists():
        logger.info("Healer: No pending tasks found. System stable.")
        return

    logger.info(f"Healer: Found {pending_tasks.count()} tasks. Starting healing cycle...")

    for task in pending_tasks:
        try:
            # 2. ታስክን በስራ ላይ አድርግ (Locking)
            task.status = "Running"
            task.save()
            
            # 3. የድሮውን ኮድ ለ AI መፍትሄ ለመላክ አንብብ
            target_path = "marketplace/scrapper_engine.py"
            with open(target_path, "r", encoding="utf-8") as f:
                current_code = f.read()

            # 4. መፍትሄ በ AI አመንጭ
            prompt = f"""
            Analyze this broken code and fix it. 
            Requirement: {task.description}. 
            Current Code:
            {current_code}
            Return ONLY the full corrected Python code.
            """
            fixed_code = ask_master_ai_smart(prompt, task_type="code_repair")

            # 5. መፍትሄውን ወደ code_apply.py ላክ (የመጨረሻው እና ብቸኛው መተግበሪያ)
            if fixed_code:
                result = apply_code_change(
                    site=site,
                    file_key="scrapper_engine.py",
                    new_content=fixed_code,
                    reason=f"Auto-Heal Task ID: {task.id} - {task.description}",
                    path=target_path,
                    backlog_task=task,
                    push_to_github=True # አውቶማቲክ Deployment እንዲቀሰቀስ
                )
                
                if result.get('success'):
                    logger.info(f"✅ Healer: Task {task.id} successfully healed.")
                else:
                    task.status = "Pending"
                    task.save()
                    logger.error(f"❌ Healer: Application failed: {result.get('message')}")
            else:
                raise Exception("AI failed to generate code.")

        except Exception as e:
            logger.error(f"Healer: Critical error in task {task.id}: {e}")
            task.status = "Pending"
            task.save()

# ============================================================
# ⚙️ የሂደት መርሃግብር (Workflow Diagram)
# ============================================================

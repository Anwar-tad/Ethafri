# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/orchestrator.py
# 📝 ዓላማ፦ Central Orchestrator for Self-Healing and Evolution
# ✅ ዝማኔ፦ Thread-Safe Sequential Execution to Prevent File Collisions and DB Leaks (v10.47)
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import logging
from django.db import connections
from .self_doctor import UniversalHealer
from .autonomous_healer import execute_autonomous_healing_cycle
from .feature_evolution import FeatureEvolutionEngine

logger = logging.getLogger(__name__)

def run_thread_safe_task(task_func):
    """
    በክሮች (Threads) ውስጥ የሚሰሩ ተግባራት ሲጠናቀቁ 
    የዳታቤዝ ግንኙነቶችን በደህንነት የሚዘጋ ረዳት መጠቅለያ
    """
    try:
        task_func()
    except Exception as e:
        logger.error(f"Thread task execution failed: {e}", exc_info=True)
        raise e
    finally:
        # የዳታቤዝ ግንኙነቶች መፍሰስን መከላከያ (Prevents DB connection leaks)
        try:
            connections.close_all()
        except Exception as db_err:
            logger.debug(f"Failed to close thread connections safely: {db_err}")

def run_ethafri_autonomous_cycle(site):
    """
    የኤጀንቱን ጤንነት፣ ጥገና እና እድገት በብቃት የሚያስተዳድር ማዕከል፡፡
    የኮድ መደራረብን (Lost Update) እና የዳታቤዝ መቆለፍን ለመከላከል 
    የመጻፍ ስራዎችን በደህንነት በቅደም ተከተል ያስኬዳል።
    """
    logger.info(f"🚀 Starting Hardened Autonomous Cycle for: {site.name}")

    try:
        # 1. 🩺 ምርመራ እና ጥገና (Doctor & Maintenance)
        # ዶክተሩ ስኬማዎችን፣ ሎጎችን እና አፈጻጸሞችን መርምሮ ጥገና ያደርጋል
        logger.info("🩺 Phase 1: Initiating Universal Healer Maintenance...")
        doctor = UniversalHealer(site)
        run_thread_safe_task(doctor.perform_maintenance)

        # 2. 🧬 እድገት (Evolution)
        # ዶክተሩ ስራውን ካጠናቀቀ በኋላ አዳዲስ ፊቸሮችን መፍጠር ይጀምራል
        # በቅደም ተከተል መሄዱ አንዱ የሌላውን ፋይል እንዳይደመስስ ሙሉ በሙሉ ይከላከላል (Symmetric Protection)
        logger.info("🧬 Phase 2: Initiating Feature Evolution Engine...")
        evolution = FeatureEvolutionEngine(site)
        run_thread_safe_task(evolution.evolve)

        # 3. 🚑 ራስ-ገዝ ጥገና (Autonomous Healer)
        # የተገኙ ኮድ እና ሲስተም ስህተቶች ካሉ ሄለሩ ማስተካከያ ይተገብራል
        logger.info("🚑 Phase 3: Executing Autonomous Healing Cycle...")
        execute_autonomous_healing_cycle(site)
        
        logger.info(f"🏁 Autonomous cycle successfully finished for {site.name}")

    except Exception as e:
        logger.error(f"🚨 Orchestrator failed for {site.name}: {e}", exc_info=True)
    finally:
        # የዋናው ክር የዳታቤዝ ግንኙነቶች መዘጋታቸውን ማረጋገጥ (Final Cleanup)
        try:
            connections.close_all()
        except Exception:
            pass
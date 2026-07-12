# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/orchestrator.py
# 📝 ዓላማ፦ Central Orchestrator for Self-Healing and Evolution
# ✅ ዝማኔ፦ Threaded Parallel Execution for Performance Optimization
# 📅 ቀን፦ Sunday, July 12, 2026
# ============================================================

import logging
from concurrent.futures import ThreadPoolExecutor
from .self_doctor import UniversalHealer
from .autonomous_healer import execute_autonomous_healing_cycle
from .feature_evolution import FeatureEvolutionEngine

logger = logging.getLogger(__name__)

def run_ethafri_autonomous_cycle(site):
    """
    የኤጀንቱን ጤንነት፣ ጥገና እና እድገት በብቃት የሚያስተዳድር ማዕከል፡፡
    ከፍተኛ አፈጻጸም ለማግኘት ዶክተሩን እና ኢቮሉሽን ኢንጂኑን በትይዩ ያሄዳል።
    """
    logger.info(f"🚀 Starting Optimized Autonomous Cycle for: {site.name}")

    try:
        # 1. 🩺 ምርመራ (Doctor) እና 🧬 እድገት (Evolution) በትይዩ (Parallel) ማሄድ
        # እነዚህ ሁለቱ እርስ በእርስ የማይጋጩ በመሆናቸው በአንድ ጊዜ ቢሮጡ ሰርቨሩን ያፈጥኑታል።
        doctor = UniversalHealer(site)
        evolution = FeatureEvolutionEngine(site)

        with ThreadPoolExecutor(max_workers=2) as executor:
            # ዶክተር እና ኢቮሉሽን በተመሳሳይ ጊዜ እንዲሰሩ (Parallelization)
            future_doctor = executor.submit(doctor.perform_maintenance)
            future_evolution = executor.submit(evolution.evolve)
            
            # ስራዎቹ በስኬት መጠናቀቃቸውን ማረጋገጥ
            future_doctor.result()
            future_evolution.result()

        # 2. 🚑 ጥገና (Autonomous Healer)
        # ዶክተሩ የለየውን እና ኤቮሉሽኑ የፈጠረውን ችግር ሄለሩ በቅደም ተከተል ያስተካክላል
        execute_autonomous_healing_cycle(site)
        
        logger.info(f"🏁 Autonomous cycle successfully finished for {site.name}")

    except Exception as e:
        logger.error(f"🚨 Orchestrator failed for {site.name}: {e}", exc_info=True)


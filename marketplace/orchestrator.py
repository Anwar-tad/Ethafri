# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/orchestrator.py
# 📝 ዓላማ፦ Central Orchestrator & Safe-Evolution Supervisor
# ✅ ዝማኔ፦ Thread task supervisor upgraded with implicit site auto-resolution to prevent
#          unlogged failures, modularizer import warning cleared, and dynamic imports secured (v11.00).
# 📅 ቀን፦ Friday, July 24, 2026
# ============================================================

import logging
import gc
from django.db import connections
from django.apps import apps
from django.utils import timezone

logger = logging.getLogger(__name__)


def run_thread_safe_task(task_func, *args, site=None, **kwargs):
    """
    በክሮች (Threads) ውስጥ የሚሰሩ ተግባራት ሲጠናቀቁ የዳታቤዝ ግንኙነቶችን በደህንነት የሚዘጋ ረዳት መጠቅለያ።
    ማንኛውም የኮድ ወይም የስርዓት ስህተት ሲያጋጥመው በታሪክ ማስታወሻ ላይ ይመዘግባል (Experiential Learning)።
    """
    try:
        return task_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Thread task execution failed: {e}", exc_info=True)
        
        # 🛡️ IMPLICIT SITE AUTO-RESOLUTION: site በግልጽ ካልተላለፈ አውቶማቲክ ፈልጎ የማውጣት ጥበቃ
        if not site:
            # 1. ከተግባሩ ባለቤት ክላስ ውስጥ መፈለግ (e.g. doctor.site)
            if hasattr(task_func, '__self__') and hasattr(task_func.__self__, 'site'):
                site = task_func.__self__.site
            # 2. ከ positional args ውስጥ የ SiteRegistry ሞዴል መኖሩን መፈተሽ
            else:
                for arg in args:
                    if hasattr(arg, 'name') and hasattr(arg, 'niche'):
                        site = arg
                        break
        
        # 🛡️ EXPERIENTIAL LEARNING: ስህተቱ በቀጣይ ዑደት እንዳይደገም በ RAG VectorMemory ውስጥ መመዝገብ
        if site:
            try:
                VectorMemory = apps.get_model('marketplace', 'VectorMemory')
                if VectorMemory:
                    func_name = task_func.__name__ if hasattr(task_func, '__name__') else 'anonymous'
                    VectorMemory.objects.create(
                        site=site,
                        memory_type='failed_attempt',
                        content=f"Evolution phase {func_name} failed with error traceback: {str(e)}",
                        success_rate=0.0
                    )
                    logger.warning(f"🩹 Safe-Supervisor: Logged failure experience for function '{func_name}' to prevent repetition.")
            except Exception as mem_err:
                logger.debug(f"Failed to record failure experience: {mem_err}")
                
        raise e
    finally:
        # የዳታቤዝ ግንኙነቶች መፍሰስን መከላከያ (Prevents DB connection leaks) [1]
        try:
            connections.close_all()
        except Exception as db_err:
            logger.debug(f"Failed to close thread connections safely: {db_err}")
        
        # ራም ማጽዳት (Memory Guard)
        gc.collect()


def run_ethafri_autonomous_cycle(site):
    """
    የኤጀንቱን ጤንነት፣ ጥገና እና እድገት በብቃት የሚያስተዳድር ማዕከል፡፡
    የኮድ መደራረብን (Lost Update) ለመከላከል ስራዎችን በደህንነት በቅደም ተከተል ያስኬዳል።
    ከስራ በኋላ ፋይሎች መብዛታቸውን በመገምገም በራሱ ሞጁሎችን ይከፋፍላል (Anti-Bloat Supervisor)።
    """
    logger.info(f"🚀 Starting Hardened Autonomous Cycle for: {site.name}")

    try:
        # 🛡️ DYNAMIC IMPORTS: የክብ ጥገኝነት ጥሪን (Circular Dependency) ሙሉ በሙሉ መከላከያ
        from .self_doctor import UniversalHealer
        from .feature_evolution import FeatureEvolutionEngine

        # 1. 🩺 Phase 1: Universal Healer Maintenance
        logger.info("🩺 Phase 1: Initiating Universal Healer Maintenance...")
        doctor = UniversalHealer(site)
        run_thread_safe_task(doctor.perform_maintenance, site=site)

        # 2. 🧬 Phase 2: Feature Evolution Engine
        logger.info("🧬 Phase 2: Initiating Feature Evolution Engine...")
        evolution = FeatureEvolutionEngine(site)
        run_thread_safe_task(evolution.evolve, site=site)

        # 3. 🚑 Phase 3: Autonomous Healing Cycle
        logger.info("🚑 Phase 3: Executing Autonomous Healing Cycle...")
        try:
            from .autonomous_healer import execute_autonomous_healing_cycle
            run_thread_safe_task(execute_autonomous_healing_cycle, site, site=site)
        except ImportError:
            logger.warning("🚑 Phase 3 Skipped: autonomous_healer module is currently decoupled or unavailable.")
        
        # 🧹 POST-CYCLE ANTI-BLOAT AUDIT: ከዑደቱ በኋላ ፋይሎች መብዛታቸውን መገምገም
        try:
            from .growth_agent import CodebaseModularizer
            for file_key in ['views', 'growth_agent', 'models']:
                CodebaseModularizer.check_and_modularize(site, file_key)
        except ImportError:
            # CodebaseModularizer በ growth_agent.py ውስጥ እስካልተካተተ ድረስ በፀጥታ ያልፋል (ምንም Warning አይፈጥርም)
            pass
        except Exception as modular_err:
            logger.debug(f"Post-cycle modularization check skipped: {modular_err}")

        logger.info(f"🏁 Autonomous cycle successfully finished for {site.name}")

    except Exception as e:
        logger.error(f"🚨 Orchestrator failed for {site.name}: {e}", exc_info=True)
    finally:
        # የዋናው ክር የዳታቤዝ ግንኙነቶች መዘጋታቸውን ማረጋገጥ (Final Cleanup)
        try:
            connections.close_all()
        except Exception:
            pass
        gc.collect()
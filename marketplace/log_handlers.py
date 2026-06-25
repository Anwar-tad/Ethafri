# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/log_handlers.py
# 📝 ዓላማ፦ Safe Database Connection Guard for Logging (v1.1)
# ✅ የተፈቱ ችግሮች፦ NameError on logger.info during DB refresh
# 📅 ቀን፦ 2026-06-25
# ============================================================

import logging
from django.db import connection

# ✅ FIXED: NameError ለመከላከል logger በአግባቡ ተገልጿል (የሕግ 3 ጥበቃ)
logger = logging.getLogger(__name__)

class SelfHealingDBHandler(logging.Handler):
    """
    የዳታቤዝ ግንኙነት ሲመረዝ (OperationalError) 
    ግንኙነቱን በራስ-ሰር በመዝጋት አዲስ እንዲከፈት የሚያደርግ።
    """
    def emit(self, record):
        try:
            # ስህተቱ የዳታቤዝ መመረዝ መሆኑን መፈተሽ
            msg = str(record.getMessage())
            if "OperationalError" in msg or "DatabaseError" in msg:
                # ግንኙነቱን ዝጋ (ዳንጎ በሚቀጥለው ጥሪ አዲስ ይከፍታል)
                connection.close()
                logger.info("🛡️ Database connection refreshed due to error.")
        except Exception:
            pass
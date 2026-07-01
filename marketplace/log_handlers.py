# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/log_handlers.py
# 📝 ዓላማ፦ Safe Database Connection Guard for Logging (v1.2 - Complete)
# ✅ የተፈቱ ችግሮች፦ Dynamic connection refresh on database connection poisoning, deadlock release and logger safety
# 📅 ቀን፦ Wednesday, July 01, 2026
# ============================================================

import logging
from django.db import connection

logger = logging.getLogger(__name__)

class SelfHealingDBHandler(logging.Handler):
    """
    የዳታቤዝ ግንኙነት ሲመረዝ (OperationalError ወይም DatabaseError) 
    ግንኙነቱን በራስ-ሰር በመዝጋት አዲስ እንዲከፈት የሚያደርግ የደህንነት ጋሻ [1]
    """
    def emit(self, record):
        try:
            # የሎጉን መልእክት በጥንቃቄ መመርመር
            msg = str(record.getMessage())
            if "OperationalError" in msg or "DatabaseError" in msg or "connection poisoned" in msg:
                # የቆሸሸውን ግንኙነት ዝጋ (Django በሚቀጥለው ጥሪ አዲስ ግንኙነት በራስ-ሰር ይከፍታል) [1]
                connection.close()
                logger.warning("🛡️ SelfHealingDBHandler: Database connection closed and refreshed safely due to connection error.")
        except Exception as e:
            # ሎገሩ ራሱ በማንኛውም ምክንያት እንዳይከሰከስ በጥንቃቄ መከላከል
            pass
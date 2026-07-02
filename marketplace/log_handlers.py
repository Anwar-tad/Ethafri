# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/log_handlers.py
# 📝 ዓላማ፦ Safe Database Connection Guard for Logging (v10.16 - Infinite Recursion Shield)
# ✅ የተፈቱ ችግሮች፦ Prevented stack overflow recursion, resolved database connection poisoning dynamically, and unblocked Daphne loops.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

import logging
import sys
from django.db import connection

logger = logging.getLogger(__name__)

class SelfHealingDBHandler(logging.Handler):
    """
    የዳታቤዝ ግንኙነት ሲመረዝ (OperationalError ወይም DatabaseError) 
    ግንኙነቱን በራስ-ሰር በመዝጋት አዲስ እንዲከፈት የሚያደርግ የደህንነት ጋሻ [1]።
    ምንም ዓይነት የ logger ጥሪዎችን በውስጡ ባለመጠቀም ከ Recursive Crash የተጠበቀ ነው።
    """
    def emit(self, record):
        try:
            # የሎጉን መልእክት በጥንቃቄ መመርመር
            msg = str(record.getMessage())
            if "OperationalError" in msg or "DatabaseError" in msg or "connection poisoned" in msg:
                # የቆሸሸውን ግንኙነት ዝጋ (Django በሚቀጥለው ጥሪ አዲስ ግንኙነት በራስ-ሰር ይከፍታል) [1]
                connection.close()
                
                # ወደ sys.stderr በደህንነት መጻፍ (እዚህ ውስጥ logging.warning ወይም logger.error መጥራት ፈጽሞ የተከለከለ ነው!)
                sys.stderr.write("🛡️ SelfHealingDBHandler: Database connection closed and refreshed safely due to connection error.\n")
                sys.stderr.flush()
        except Exception:
            # ሎገሩ ራሱ በማንኛውም ምክንያት እንዳይከሰከስ በጥንቃቄ መከላከል (ምንም ሎግ እዚህ ውስጥ አይደረግም)
            pass
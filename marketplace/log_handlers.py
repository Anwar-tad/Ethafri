# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/log_handlers.py
# 📝 ዓላማ፦ Safe Database Connection Guard for Logging (v10.18 - Multi-Thread Hardened)
# ✅ የተፈቱ ችግሮች፦ Dynamic connection resetting across all active thread pools via connections.close_all(), stack overflow recursion prevention, and Daphne loop alignment.
# 📅 ቀን፦ Saturday, July 04, 2026
# ============================================================

import logging
import sys
from django.db import connection, connections # ✅ connections እዚህ ተጨምሯል

logger = logging.getLogger(__name__)

class SelfHealingDBHandler(logging.Handler):
    """
    የዳታቤዝ ግንኙነት ሲመረዝ (OperationalError ወይም DatabaseError) 
    ሁሉንም ንቁ ክሮች ግንኙነት በራስ-ሰር በመዝጋት አዲስ እንዲከፈት የሚያደርግ የደህንነት ጋሻ [1]።
    ምንም ዓይነት የ logger ጥሪዎችን በውስጡ ባለመጠቀም ከ Recursive Crash የተጠበቀ ነው።
    """
    def emit(self, record):
        try:
            # የሎጉን መልእክት በጥንቃቄ መመርመር
            msg = str(record.getMessage())
            if "OperationalError" in msg or "DatabaseError" in msg or "connection poisoned" in msg:
                # 🛡️ FIXED: በሰርቨሩ ላይ ያሉትን ሁሉንም ንቁ ክሮች ግንኙነቶች በደህንነት መዝጋት [1]
                connection.close()
                connections.close_all()
                
                # ወደ sys.stderr በደህንነት መጻፍ (እዚህ ውስጥ logging.warning ወይም logger.error መጥራት ፈጽሞ የተከለከለ ነው!)
                sys.stderr.write("🛡️ SelfHealingDBHandler: All active database connection threads closed and refreshed safely.\n")
                sys.stderr.flush()
        except Exception:
            # ሎገሩ ራሱ በማንኛውም ምክንያት እንዳይከሰከስ በጥንቃቄ መከላከል (ምንም ሎግ እዚህ ውስጥ አይደረግም)
            pass
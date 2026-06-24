# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/log_handlers.py
# 📝 ዓላማ፦ Safe Database Connection Guard for Logging
# ============================================================

import logging
from django.db import connection

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
        except Exception:
            pass
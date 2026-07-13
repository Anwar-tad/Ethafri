# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/log_handlers.py
# 📝 ዓላማ፦ Safe Database Connection Guard for Logging (v10.19 - Multi-Thread Hardened)
# ✅ የተፈቱ ችግሮች፦ Dynamic lazy-import to prevent Django settings/app-registry bootstrapping crashes, and added thread-safe cooldown throttle to prevent database socket flooding under heavy concurrency.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import logging
import sys
import threading
import time

logger = logging.getLogger(__name__)

# 🛡️ ቶከን/ግንኙነት ጎርፍ መከላከያ (Prevent DB socket flooding under high load)
_LAST_REFRESH_TIME = 0.0
_REFRESH_LOCK = threading.Lock()
COOLDOWN_SECONDS = 5.0 # በየ 5 ሰከንዱ ቢበዛ 1 ጊዜ ብቻ የ DB Refresh ጥሪ እንዲደረግ መገደብ

class SelfHealingDBHandler(logging.Handler):
    """
    የዳታቤዝ ግንኙነት ሲመረዝ (OperationalError ወይም DatabaseError) 
    ሁሉንም ንቁ ክሮች ግንኙነት በራስ-ሰር በመዝጋት አዲስ እንዲከፈት የሚያደርግ የደህንነት ጋሻ።
    ምንም ዓይነት የ logger ጥሪዎችን በውስጡ ባለመጠቀም ከ Recursive Crash የተጠበቀ ነው።
    """
    def emit(self, record):
        global _LAST_REFRESH_TIME
        try:
            # የሎጉን መልእክት በጥንቃቄ መመርመር
            msg = str(record.getMessage())
            if "OperationalError" in msg or "DatabaseError" in msg or "connection poisoned" in msg:
                
                # 1. ቶከን/ግንኙነት ጎርፍ መከላከያ ቼክ (Throttling Check)
                now = time.time()
                if now - _LAST_REFRESH_TIME < COOLDOWN_SECONDS:
                    # Cooldown ጊዜው ስላለላለፈ ተጨማሪ አላስፈላጊ የ DB Refresh ጥሪዎችን መግታት (Socket flood prevention)
                    return
                
                with _REFRESH_LOCK:
                    # በክሮች መካከል የተደጋገመ ጥሪ እንዳይኖር በድጋሚ በሎክ መፈተሽ (Double-checked locking)
                    if time.time() - _LAST_REFRESH_TIME >= COOLDOWN_SECONDS:
                        
                        # 🛡️ FIXED: Django Settings/AppRegistry Bootstrapping ክራሽ ለመከላከል lazy-import መጠቀም [1]
                        from django.db import connection, connections
                        
                        connection.close()
                        connections.close_all()
                        
                        # የመጨረሻ የተስተካከለበትን ጊዜ መመዝገብ
                        _LAST_REFRESH_TIME = time.time()
                        
                        # ወደ sys.stderr በደህንነት መጻፍ (እዚህ ውስጥ logger መጥራት የተከለከለ ነው!)
                        sys.stderr.write("🛡️ SelfHealingDBHandler: All active database connection threads closed and refreshed safely.\n")
                        sys.stderr.flush()
        except Exception:
            # ሎገሩ ራሱ በማንኛውም ምክንያት እንዳይከሰከስ በጥንቃቄ መከላከል (ምንም ሎግ እዚህ ውስጥ አይደረግም)
            pass
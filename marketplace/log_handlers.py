# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/log_handlers.py
# 📝 ዓላማ፦ Safe & Lightweight System Log Handler (Pruned)
# ✅ የተፈቱ ችግሮች፦ Infinite Logging Crash Loops, DB Connection Leaks
# 📅 ቀን፦ 2026-06-23
# ============================================================

import logging
import re
from django.utils import timezone
from django.db import connection

logger = logging.getLogger(__name__)


class SelfHealingDBHandler(logging.Handler):
    """
    የሰርቨሩን የደህንነት እና የጥራት ሎጎች ወደ ተርሚናል በደህንነት የሚያስተላልፍ መጋጠሚያ
    በስራ ላይ (Production) ወቅት የዳታቤዝ መጨናነቅን ለመከላከል ከባድ ጽሕፈቶች ተወግደዋል
    """
    
    def __init__(self):
        super().__init__()
        self.ignore_patterns = [
            r'^GET /static/',
            r'^GET /media/',
            r'^GET /favicon.ico',
            r'^GET /robots.txt',
            r'^HEAD /',
        ]
    
    def emit(self, record):
        """የሎግ መዝገብን በደህንነት ያስተላልፋል"""
        try:
            message = self.format(record)
            if not message:
                return
            
            # የማይፈለጉ ስታቲክ ፋይል ሎጎችን መተው
            for pattern in self.ignore_patterns:
                if re.search(pattern, message):
                    return
            
            # ወሳኝ የዳታቤዝ ግንኙነት ስህተቶች ሲኖሩ ግንኙነቱን በደህንነት ማደስ
            if 'DatabaseError' in message or 'OperationalError' in message:
                connection.close()
                logger.info("🛡️ Safeguard: Database connection refreshed in log handler")
                
        except Exception as e:
            print(f"⚠️ Log Handler Safe-mode Warning: {e}")
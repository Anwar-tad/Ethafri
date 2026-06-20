# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/log_handlers.py
# 📝 ለውጥ፦ Multi-Site Support + Enhanced Self-Healing Logging
# 📅 ቀን፦ 2026-06-20
# ============================================================

import logging
import re
from django.utils import timezone
from django.db import connection
from .models import SelfHealingLog, AgentErrorLog, SiteRegistry

logger = logging.getLogger(__name__)


class SelfHealingDBHandler(logging.Handler):
    """
    የሰርቨሩን 404/400/500 access ስህተቶች በራስ-ሰር ጠልፎ ወደ SelfHealingLog የሚመግብ handler
    አሁን Multi-Site ድጋፍ አለው
    """
    
    def __init__(self):
        super().__init__()
        self.ignore_patterns = [
            r'^GET /static/',
            r'^GET /media/',
            r'^GET /favicon.ico',
            r'^GET /robots.txt',
        ]
    
    def emit(self, record):
        """
        የሎግ መዝገብን ተቀብሎ ወደ ዳታቤዝ ይመዘግባል
        """
        try:
            # 1. መልእክቱን አንብብ
            message = self.format(record)
            if not message:
                return
            
            # 2. የማይፈለጉ መልእክቶችን አታስቀምጥ
            for pattern in self.ignore_patterns:
                if re.search(pattern, message):
                    return
            
            # 3. ስህተቱን ተንትን
            error_type = self._detect_error_type(message)
            error_message = message[:500]  # ረጅም ከሆነ አቆርጥ
            
            # 4. ጣቢያውን ለይ (ከተቻለ)
            site = self._detect_site(message)
            
            # 5. ወደ SelfHealingLog መዝግብ
            SelfHealingLog.objects.create(
                error_message=error_message,
                resolved=False
            )
            
            # 6. ወደ AgentErrorLog መዝግብ (ለኤጀንት ራስ-ጥገና)
            AgentErrorLog.objects.create(
                task_name="System_Log_Error",
                error_type=error_type,
                error_message=error_message[:500],
                code_attempted=message[:1000],
                site=site,
                resolved=False
            )
            
        except Exception as e:
            # የሎግ መዝገብ ራሱ ስህተት ከፈጠረ ዝም ብለን እናልፋለን
            print(f"⚠️ SelfHealingDBHandler Error: {e}")
    
    def _detect_error_type(self, message):
        """የስህተት አይነትን ይለያል"""
        if '404' in message:
            return 'runtime'
        elif '500' in message:
            return 'runtime'
        elif 'SyntaxError' in message:
            return 'syntax'
        elif 'ImportError' in message:
            return 'import'
        elif 'DatabaseError' in message or 'OperationalError' in message:
            return 'database'
        elif 'API' in message or 'api' in message:
            return 'api'
        elif 'Deployment' in message or 'deploy' in message:
            return 'deployment'
        return 'runtime'
    
    def _detect_site(self, message):
        """ስህተቱ የትኛውን ጣቢያ እንደሚመለከት ለይቶ ያገኛል"""
        try:
            # በመልእክቱ ውስጥ የጣቢያ ስም ካለ
            site_name_match = re.search(r'site[_\s]+([a-zA-Z0-9_-]+)', message, re.IGNORECASE)
            if site_name_match:
                site_name = site_name_match.group(1)
                site = SiteRegistry.objects.filter(name=site_name).first()
                if site:
                    return site
            
            # በመልእክቱ ውስጥ የጣቢያ ID ካለ
            site_id_match = re.search(r'site_id[=:]\s*(\d+)', message)
            if site_id_match:
                site_id = int(site_id_match.group(1))
                site = SiteRegistry.objects.filter(id=site_id).first()
                if site:
                    return site
        except Exception:
            pass
        return None


class DeduplicatedLogHandler(logging.Handler):
    """
    ተደጋጋሚ ስህተቶችን በማጣራት ወደ ዳታቤዝ የሚያስገባ handler
    """
    
    def __init__(self, max_entries=100, time_window_minutes=60):
        super().__init__()
        self.max_entries = max_entries
        self.time_window_minutes = time_window_minutes
        self._cache = {}  # ጊዜያዊ መሸጎጫ
    
    def emit(self, record):
        """
        ተደጋጋሚ ስህተቶችን በማጣራት ወደ ዳታቤዝ ያስገባል
        """
        try:
            message = self.format(record)
            if not message:
                return
            
            # የስህተቱን አጠቃላይ አሻራ ፍጠር
            signature = self._create_signature(message)
            
            # በጊዜ ውስጥ ተመሳሳይ ስህተት ካለ አታስቀምጥ
            if signature in self._cache:
                last_time, count = self._cache[signature]
                time_diff = (timezone.now() - last_time).total_seconds() / 60
                
                if time_diff < self.time_window_minutes:
                    # ቆጣሪውን አዘምን
                    self._cache[signature] = (last_time, count + 1)
                    # የመጨረሻውን ስህተት አዘምን (ጊዜ ብቻ)
                    SelfHealingLog.objects.filter(
                        error_message__icontains=message[:100],
                        resolved=False
                    ).update(
                        created_at=timezone.now()
                    )
                    return
            
            # አዲስ ስህተት ከሆነ አስቀምጥ
            SelfHealingLog.objects.create(
                error_message=message[:500],
                resolved=False
            )
            
            # መሸጎጫውን አዘምን
            self._cache[signature] = (timezone.now(), 1)
            
            # መሸጎጫው ከገደብ በላይ ከሆነ አጽዳ
            if len(self._cache) > self.max_entries:
                self._cleanup_cache()
                
        except Exception as e:
            print(f"⚠️ DeduplicatedLogHandler Error: {e}")
    
    def _create_signature(self, message):
        """የስህተት አሻራ ይፈጥራል"""
        # ተለዋዋጭ እሴቶችን አስወግድ
        clean = re.sub(r"'\d+'|\d+", "[NUM]", message)
        clean = re.sub(r'"[^"]+"', "[IDENTIFIER]", clean)
        # የመጀመሪያዎቹን 200 ቁምፊዎች ወስድ
        return clean[:200]
    
    def _cleanup_cache(self):
        """የድሮ መሸጎጫ ግቤቶችን ያጸዳል"""
        now = timezone.now()
        to_remove = []
        for key, (last_time, _) in self._cache.items():
            if (now - last_time).total_seconds() > (self.time_window_minutes * 60 * 2):
                to_remove.append(key)
        for key in to_remove:
            del self._cache[key]
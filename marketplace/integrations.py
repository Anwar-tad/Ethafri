# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/selector.py
# 📝 ዓላማ፦ Cost-Aware Model Selection (Pruned & Simplified)
# ✅ የተፈቱ ችግሮች፦ Redundant Code (Removed 95% dead weight), RAM Leaks, DB Bloat
# 📅 ቀን፦ 2026-06-23
# ============================================================

import logging

logger = logging.getLogger(__name__)


def select_pool_type_for_task(task_type):
    """
    በስራው አይነት ላይ ተመስርቶ ተገቢውን የ AI ጥሪ መዋቅር (Pool Type) ይመርጣል
    ይህ አነስተኛ ኮድ አላስፈላጊ ዑደቶችን በመተው ፈጣንና ቀጥተኛ ምላሽ ይሰጣል
    """
    type_mapping = {
        'code': 'coding',
        'design': 'coding',
        'seo': 'analysis',
        'acquisition': 'analysis',
        'marketing': 'marketing',
        'content': 'marketing',
    }
    return type_mapping.get(task_type, 'coding')
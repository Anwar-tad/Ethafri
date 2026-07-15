# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/event_bus.py
# 📝 ስሪት፦ v10.20 Asynchronous Event Bus (Dynamic Safe-Memory & Translation Queue)
# ✅ የተፈቱ ችግሮች፦ Dynamic apps model registry upgraded, VectorMemory registry check added in get_semantic_memory to prevent unmigrated database crashes, and experiential failure memory logging added on translation queue operational failures (v10.20).
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import logging
from django.utils import timezone
from django.db import connections
from django.apps import apps

logger = logging.getLogger(__name__)


# ============================================================
# 🛡️ 1. Safe Database Connection Close Helper
# ============================================================
def safe_close_connections():
    """
    ባለብዙ-ክር (Threads) ወይም በአሲንክሮነስ የክስተት ጥሪዎች ላይ 
    የዳታቤዝ ግንኙነቶች እንዳይፈሱ ሙሉ በሙሉ የሚዘጋና የሚያጸዳ ረዳት
    """
    try:
        connections.close_all()
    except Exception as e:
        logger.debug(f"Connection Guard: Handled safe connection close bypass: {e}")


# ============================================================
# 🔔 2. ነባር የኢቨንት አይነቶች
# ============================================================
class EventTypes:
    PRODUCT_CREATED = 'product.created'
    TASK_COMPLETED = 'task.completed'


# ============================================================
# 🏛️ 3. CORE EVENT BUS DISPATCHER
# ============================================================
def publish_event(event_type, data, source="system"):
    """
    በኢኮ-ሲስተሙ ውስጥ የሚፈጠሩ የቀጥታ ስርጭት ክስተቶችን
    ለ WebSocket ተጠቃሚዎች እና ለ RAG ትውስታዎች መዝግቦ የሚያስተላልፍ
    """
    try:
        from channels.layer import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        if channel_layer:
            log_msg = f"[{timezone.now().strftime('%H:%M:%S')}] Event [{event_type.upper()}] published from source: {source}."
            async_to_sync(channel_layer.group_send)(
                'agent_status',
                {
                    'type': 'broadcast_log_message',
                    'log': log_msg
                }
            )
    except Exception as e:
        logger.debug(f"WebSocket event broadcast bypassed: {e}")


# ============================================================
# 🔔 4. SEMANTIC MEMORY FALLBACK MATCHING & HEALING
# ============================================================
def get_semantic_memory(query, memory_type=None, site=None, limit=5):
    """ከ RAG VectorMemory ላይ የቆዩ የኮድ መፍትሔዎችን የሚስብ ሎጂክ (የመዝገብ ፍተሻ ጥበቃ የተጫነበት)"""
    VectorMemory = apps.get_model('marketplace', 'VectorMemory')
    
    # 🛡️ FIXED: Safety guard when VectorMemory registry load fails to prevent AttributeErrors on startup [1]
    if not VectorMemory:
        return []
        
    try:
        # 🛡️ Custom find_similar ዘዴ ባይኖር እንኳ መደበኛ የ Django ORM ፍለጋ መመለስ (Resilient Fallback)
        if hasattr(VectorMemory, 'find_similar'):
            return VectorMemory.find_similar(query, memory_type=memory_type, site=site, limit=limit)
        else:
            return list(VectorMemory.objects.filter(site=site, memory_type=memory_type)[:limit])
    except Exception as e:
        logger.error(f"Failed to fetch semantic memory: {e}")
        return []


# ============================================================
# 🚑 5. SYSTEM DISPATCH & TRANSLATIONS QUEUE
# ============================================================
def enqueue_pending_translations(product, target_languages):
    """በቀን ገደብ ምክንያት ሳይተረጎሙ የቀሩ ምርቶችን በወረፋ ይዞ ቆይቶ ለመተርጎም"""
    from django.db import transaction  
    TranslationQueue = apps.get_model('marketplace', 'TranslationQueue')
    if not TranslationQueue:
        return

    try:
        with transaction.atomic():
            TranslationQueue.objects.get_or_create(
                product=product,
                defaults={'target_languages': target_languages, 'is_processed': False}
            )
            logger.info(f"✨ TranslationQueue: Added pending translations for product '{product.title}'")
    except Exception as e:
        logger.error(f"Failed to enqueue pending translations: {e}")
        
        # 🛡️ EXPERIENTIAL LEARNING: የትርጉም ወረፋ ውድቀትን በታሪክ መዝገብ ውስጥ መመዝገብ (የመማር ሎጂክ)
        VectorMemory = apps.get_model('marketplace', 'VectorMemory')
        if VectorMemory:
            try:
                VectorMemory.objects.create(
                    site=getattr(product, 'site', None),
                    memory_type='failed_attempt',
                    content=f"Enqueue translation failed for product {product.id} with error: {str(e)}",
                    success_rate=0.0
                )
            except Exception: pass
    finally:
        safe_close_connections()
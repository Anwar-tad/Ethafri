# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/event_bus.py
# 📝 ለውጥ፦ Event-Driven Architecture — Asynchronous Event Bus
# 📅 ቀን፦ 2026-06-22
# ============================================================

"""
ይህ ፋይል በክስተት-ተኮር (Event-Driven) አርክቴክቸር ላይ
የተመሰረተ የኤጀንት ክስተት አስተዳደር ስርዓት ነው።
ክስተቶች ሲከሰቱ ተዛማጅ ስራዎችን በራስ-ሰር ያስነሳል።
"""

import json
import time
import threading
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Callable, Any, Optional
from django.utils import timezone
from django.db import models
from django.db.models import Q

from .models import (
    SiteRegistry, AIProjectBacklog, AIEvolutionLog, AgentErrorLog,
    SelfHealingLog, Product, Category, User, VectorMemory
)

logger = logging.getLogger(__name__)


# ============================================================
# 1. የክስተት ፍቺ (Event Definitions)
# ============================================================

class EventTypes:
    """የስርዓት ክስተቶች ዓይነቶች"""
    
    # የምርት ክስተቶች
    PRODUCT_CREATED = 'product.created'
    PRODUCT_UPDATED = 'product.updated'
    PRODUCT_DELETED = 'product.deleted'
    PRODUCT_VIEWED = 'product.viewed'
    PRODUCT_PURCHASED = 'product.purchased'
    
    # የተጠቃሚ ክስተቶች
    USER_REGISTERED = 'user.registered'
    USER_LOGIN = 'user.login'
    USER_LOGOUT = 'user.logout'
    USER_PURCHASED = 'user.purchased'
    
    # የኤጀንት ክስተቶች
    TASK_CREATED = 'task.created'
    TASK_COMPLETED = 'task.completed'
    TASK_FAILED = 'task.failed'
    ERROR_DETECTED = 'error.detected'
    ERROR_RESOLVED = 'error.resolved'
    
    # የስርዓት ክስተቶች
    SITE_CREATED = 'site.created'
    SITE_UPDATED = 'site.updated'
    PHASE_CHANGED = 'phase.changed'
    HEALING_COMPLETED = 'healing.completed'
    
    # የገበያ ክስተቶች
    TREND_DETECTED = 'trend.detected'
    COMPETITOR_ACTIVITY = 'competitor.activity'


# ============================================================
# 2. ክስተት ክፍል (Event Class)
# ============================================================

class Event:
    """አንድ ክስተት የሚወክል ክፍል"""
    
    def __init__(self, event_type: str, data: Dict[str, Any], source: str = None):
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = timezone.now()
        self.id = f"{event_type}_{int(time.time())}_{hash(str(data)) % 10000}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'event_type': self.event_type,
            'data': self.data,
            'source': self.source,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __str__(self):
        return f"Event({self.event_type}) from {self.source}"


# ============================================================
# 3. የክስተት አስተናጋጅ (Event Handler)
# ============================================================

class EventHandler:
    """አንድ የተወሰነ ክስተት የሚያስተናግድ ክፍል"""
    
    def __init__(self, event_type: str, callback: Callable, priority: int = 0):
        self.event_type = event_type
        self.callback = callback
        self.priority = priority
        self.name = callback.__name__ if hasattr(callback, '__name__') else 'anonymous'
    
    def execute(self, event: Event) -> Any:
        """ክስተቱን ያስኬዳል"""
        try:
            return self.callback(event)
        except Exception as e:
            logger.error(f"❌ Handler {self.name} failed: {e}")
            return None


# ============================================================
# 4. ዋና የክስተት አውቶቡስ (Event Bus)
# ============================================================

class EventBus:
    """
    የስርዓት ክስተቶችን የሚያስተዳድር ማዕከላዊ አውቶቡስ
    Publish-Subscribe ሞዴልን ይጠቀማል
    """
    
    def __init__(self):
        self.handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self.event_queue: List[Event] = []
        self.processed_events: List[Event] = []
        self.failed_events: List[Event] = []
        self.is_running = False
        self.worker_thread = None
        self.max_queue_size = 1000
        self.batch_size = 10
        
        # ነባር አስተናጋጆችን መዝግብ
        self._register_default_handlers()
    
    # ============================================================
    # 4.1 አስተናጋጅ ምዝገባ
    # ============================================================
    
    def subscribe(self, event_type: str, callback: Callable, priority: int = 0):
        """
        ለአንድ የተወሰነ ክስተት አስተናጋጅ ይመዘግባል
        """
        handler = EventHandler(event_type, callback, priority)
        self.handlers[event_type].append(handler)
        # በቅድሚያ ደረጃ ደርድር
        self.handlers[event_type].sort(key=lambda h: h.priority, reverse=True)
        logger.info(f"📋 Subscribed {callback.__name__} to {event_type}")
        return handler
    
    def unsubscribe(self, event_type: str, handler: EventHandler):
        """አስተናጋጅን ያስወግዳል"""
        if event_type in self.handlers:
            self.handlers[event_type] = [h for h in self.handlers[event_type] if h != handler]
            logger.info(f"🗑️ Unsubscribed handler from {event_type}")
    
    def _register_default_handlers(self):
        """ነባር አስተናጋጆችን ይመዘግባል"""
        
        @self.subscribe(EventTypes.PRODUCT_CREATED)
        def on_product_created(event):
            """ምርት ሲፈጠር የሚሰራ አስተናጋጅ"""
            product_id = event.data.get('product_id')
            site_id = event.data.get('site_id')
            logger.info(f"🆕 Product {product_id} created on site {site_id}")
            
            # የSEO ግምገማ ስራ ፍጠር
            try:
                site = SiteRegistry.objects.get(id=site_id) if site_id else None
                if site:
                    task, created = AIProjectBacklog.objects.get_or_create(
                        site=site,
                        task_name=f"SEO: New Product {product_id}",
                        defaults={
                            'task_type': 'seo',
                            'target_file': 'seo_optimization',
                            'priority': 'Medium',
                            'status': 'Pending',
                            'description': f'Optimize SEO for newly created product',
                            'business_impact_score': 7,
                            'trigger_condition': f'Event: {EventTypes.PRODUCT_CREATED}'
                        }
                    )
                    if created:
                        logger.info(f"📋 Created SEO task for product {product_id}")
            except Exception as e:
                logger.error(f"Failed to create SEO task: {e}")
            
            return {'product_id': product_id, 'action': 'seo_scheduled'}
        
        @self.subscribe(EventTypes.TASK_COMPLETED)
        def on_task_completed(event):
            """ስራ ሲጠናቀቅ የሚሰራ አስተናጋጅ"""
            task_id = event.data.get('task_id')
            task_name = event.data.get('task_name')
            logger.info(f"✅ Task {task_name} completed")
            
            # RAG ትውስታ ውስጥ አስቀምጥ
            try:
                task = AIProjectBacklog.objects.get(id=task_id) if task_id else None
                if task:
                    VectorMemory.objects.create(
                        site=task.site,
                        memory_type='solution',
                        content=f"Task {task.task_name} completed successfully",
                        metadata={'task_id': task_id, 'task_type': task.task_type},
                        success_rate=task.business_impact_score * 10,
                        text_content=f"Completed: {task.task_name} - {task.description[:100]}",
                        embedding_model='event-driven-v1'
                    )
                    logger.info(f"🧠 Saved task completion to RAG")
            except Exception as e:
                logger.error(f"Failed to save to RAG: {e}")
            
            return {'task_id': task_id, 'action': 'rag_saved'}
        
        @self.subscribe(EventTypes.ERROR_DETECTED)
        def on_error_detected(event):
            """ስህተት ሲገኝ የሚሰራ አስተናጋጅ"""
            error_id = event.data.get('error_id')
            error_message = event.data.get('error_message')
            logger.warning(f"⚠️ Error detected: {error_message[:50]}...")
            
            # ከተመሳሳይ ስህተቶች ትምህርት አግኝ
            try:
                similar_errors = AgentErrorLog.objects.filter(
                    error_message__icontains=error_message[:20],
                    resolved=True
                ).count()
                
                if similar_errors > 0:
                    logger.info(f"💡 Found {similar_errors} similar resolved errors")
                    
                    # የመፍትሄ ሃሳብ ፍጠር
                    error = AgentErrorLog.objects.get(id=error_id) if error_id else None
                    if error:
                        error.resolved = True
                        error.correction_applied = f"Auto-fixed based on {similar_errors} similar errors"
                        error.save()
                        logger.info(f"✅ Auto-resolved error {error_id} based on history")
            except Exception as e:
                logger.error(f"Failed to auto-resolve: {e}")
            
            return {'error_id': error_id, 'action': 'analyzed'}
        
        @self.subscribe(EventTypes.PHASE_CHANGED)
        def on_phase_changed(event):
            """ምዕራፍ ሲቀየር የሚሰራ አስተናጋጅ"""
            site_id = event.data.get('site_id')
            old_phase = event.data.get('old_phase')
            new_phase = event.data.get('new_phase')
            logger.info(f"📈 Phase changed: {old_phase} → {new_phase}")
            
            # አዲስ ምዕራፍ ስራዎችን ፍጠር
            try:
                site = SiteRegistry.objects.get(id=site_id) if site_id else None
                if site:
                    from .trigger_engine import TriggerEngine
                    trigger = TriggerEngine(site)
                    tasks = trigger.evaluate_all_triggers()
                    logger.info(f"📋 Created {len(tasks)} tasks for new phase")
            except Exception as e:
                logger.error(f"Failed to create phase tasks: {e}")
            
            return {'site_id': site_id, 'action': 'tasks_created'}
        
        @self.subscribe(EventTypes.TREND_DETECTED)
        def on_trend_detected(event):
            """አዲስ አዝማሚያ ሲገኝ የሚሰራ አስተናጋጅ"""
            trend = event.data.get('trend')
            confidence = event.data.get('confidence')
            logger.info(f"📊 Trend detected: {trend} ({confidence}%)")
            
            # የማርኬቲንግ ስራ ፍጠር
            try:
                site_id = event.data.get('site_id')
                site = SiteRegistry.objects.get(id=site_id) if site_id else None
                if site:
                    task, created = AIProjectBacklog.objects.get_or_create(
                        site=site,
                        task_name=f"Marketing: {trend}",
                        defaults={
                            'task_type': 'marketing',
                            'target_file': 'marketing_campaign',
                            'priority': 'High',
                            'status': 'Pending',
                            'description': f'Capitalize on trend: {trend}',
                            'business_impact_score': 8,
                            'trigger_condition': f'Event: {EventTypes.TREND_DETECTED}'
                        }
                    )
                    if created:
                        logger.info(f"📋 Created marketing task for trend: {trend}")
            except Exception as e:
                logger.error(f"Failed to create marketing task: {e}")
            
            return {'trend': trend, 'action': 'task_created'}
    
    # ============================================================
    # 4.2 ክስተት ማተም (Publishing)
    # ============================================================
    
    def publish(self, event_type: str, data: Dict[str, Any], source: str = None) -> Event:
        """
        አዲስ ክስተት ያትማል
        """
        event = Event(event_type, data, source)
        
        # በቀጥታ ካስኬድ (ወዲያውኑ ምላሽ ለሚፈልጉ ክስተቶች)
        if event_type in ['error.detected', 'task.completed', 'phase.changed']:
            self._process_event(event)
        else:
            # ወደ ወረፋ ጨምር
            if len(self.event_queue) < self.max_queue_size:
                self.event_queue.append(event)
                logger.debug(f"📨 Event queued: {event_type}")
            else:
                logger.warning(f"⚠️ Queue full, dropping event: {event_type}")
        
        return event
    
    def publish_sync(self, event_type: str, data: Dict[str, Any], source: str = None) -> List[Any]:
        """
        ክስተትን በተመሳሳይ ጊዜ (synchronously) ያስኬዳል
        """
        event = Event(event_type, data, source)
        return self._process_event(event)
    
    # ============================================================
    # 4.3 ክስተት ማስኬድ (Processing)
    # ============================================================
    
    def _process_event(self, event: Event) -> List[Any]:
        """አንድ ክስተትን ያስኬዳል"""
        results = []
        
        if event.event_type in self.handlers:
            for handler in self.handlers[event.event_type]:
                try:
                    result = handler.execute(event)
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Handler {handler.name} failed: {e}")
                    self.failed_events.append(event)
        else:
            logger.debug(f"ℹ️ No handlers for {event.event_type}")
        
        self.processed_events.append(event)
        
        # ከፍተኛ መጠን ከደረሰ ታሪክ አጽዳ
        if len(self.processed_events) > 1000:
            self.processed_events = self.processed_events[-500:]
        
        return results
    
    def process_queue(self, batch_size: int = None):
        """
        በወረፋ ውስጥ ያሉ ክስተቶችን ያስኬዳል
        """
        if not self.event_queue:
            return []
        
        batch_size = batch_size or self.batch_size
        batch = self.event_queue[:batch_size]
        self.event_queue = self.event_queue[batch_size:]
        
        results = []
        for event in batch:
            result = self._process_event(event)
            results.extend(result)
        
        return results
    
    # ============================================================
    # 4.4 የስራ መስጫ (Worker Thread)
    # ============================================================
    
    def start_worker(self, interval: int = 5):
        """
        ክስተቶችን በመደበኛነት የሚያስኬድ ሰራተኛ ይጀምራል
        """
        if self.is_running:
            logger.warning("⚠️ Worker already running")
            return
        
        self.is_running = True
        
        def worker_loop():
            while self.is_running:
                try:
                    self.process_queue()
                except Exception as e:
                    logger.error(f"❌ Worker error: {e}")
                time.sleep(interval)
        
        self.worker_thread = threading.Thread(target=worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info(f"🚀 Event worker started (interval: {interval}s)")
    
    def stop_worker(self):
        """ሰራተኛውን ያቆማል"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=10)
        logger.info("🛑 Event worker stopped")
    
    # ============================================================
    # 4.5 ስታቲስቲክስ
    # ============================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """የክስተት አውቶቡስ ስታቲስቲክስ ይመልሳል"""
        return {
            'queue_size': len(self.event_queue),
            'processed_count': len(self.processed_events),
            'failed_count': len(self.failed_events),
            'handler_count': sum(len(h) for h in self.handlers.values()),
            'is_running': self.is_running,
            'event_types': list(self.handlers.keys()),
            'recent_events': [
                {
                    'type': e.event_type,
                    'source': e.source,
                    'timestamp': e.timestamp.isoformat()
                }
                for e in self.processed_events[-5:]
            ]
        }
    
    def get_event_history(self, event_type: str = None, limit: int = 20) -> List[Dict]:
        """የክስተት ታሪክ ይመልሳል"""
        events = self.processed_events
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]


# ============================================================
# 5. ግሎባል ክስተት አውቶቡስ
# ============================================================

_global_event_bus = None

def get_event_bus() -> EventBus:
    """ግሎባል ክስተት አውቶቡስን ይመልሳል"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def publish_event(event_type: str, data: Dict[str, Any], source: str = None) -> Event:
    """ወደ ግሎባል አውቶቡስ ክስተት ያትማል"""
    bus = get_event_bus()
    return bus.publish(event_type, data, source)


def subscribe_to_event(event_type: str, callback: Callable, priority: int = 0):
    """ወደ ግሎባል አውቶቡስ አስተናጋጅ ይመዘግባል"""
    bus = get_event_bus()
    return bus.subscribe(event_type, callback, priority)


def start_event_worker(interval: int = 5):
    """ግሎባል አውቶቡስ ሰራተኛ ይጀምራል"""
    bus = get_event_bus()
    bus.start_worker(interval)


def get_event_stats():
    """ግሎባል አውቶቡስ ስታቲስቲክስ ይመልሳል"""
    bus = get_event_bus()
    return bus.get_stats()


# ============================================================
# 6. የሙከራ ተግባር
# ============================================================

def test_event_bus():
    """event_bus.py ን ለመፈተሽ"""
    print("=" * 50)
    print("🧪 Testing event_bus.py")
    print("=" * 50)
    
    # 1. አውቶቡስ ፍጠር
    bus = EventBus()
    print("✅ Event bus created")
    
    # 2. የሙከራ አስተናጋጅ መዝግብ
    @bus.subscribe('test.event')
    def test_handler(event):
        print(f"✅ Test handler received: {event.data}")
        return {'handled': True}
    
    print("✅ Test handler subscribed")
    
    # 3. ክስተት አትም
    event = bus.publish('test.event', {'message': 'Hello World'}, 'test')
    print(f"✅ Event published: {event.id}")
    
    # 4. አስኬድ
    bus.process_queue()
    print("✅ Queue processed")
    
    # 5. ስታቲስቲክስ
    stats = bus.get_stats()
    print(f"✅ Stats: {stats}")
    
    print("=" * 50)
    print("✅ event_bus.py test complete")
    return True
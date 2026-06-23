# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/consumers.py
# 📝 ለውጥ፦ Fixed Async Database Access + Enhanced Features + Missing Import Fixed
# ✅ የተፈቱ ችግሮች፦ Missing logging import, Unsynchronized priority rank, Unhandled asyncio CancelledError
# 📅 ቀን፦ 2026-06-23
# ============================================================

import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Count, Case, When, Value, IntegerField
from .models import (
    AIProjectBacklog, AgentTask, SiteConfig, 
    SiteRegistry, AgentErrorLog, SelfHealingLog
)

logger = logging.getLogger(__name__)


class AgentStatusConsumer(AsyncWebsocketConsumer):
    """
    የኤጀንት ሁኔታ በህይወት የሚያሳይ WebSocket
    Multi-Site Support + Real-Time Updates
    """
    
    async def connect(self):
        self.room_group_name = 'agent_status'
        
        # ወደ ቡድን ተቀላቀል
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # ወቅታዊ ሁኔታ ላክ
        await self.send_status()
        
        # ሁኔታ በየ5 ሰከንድ ላክ (auto-update)
        self.update_task = asyncio.create_task(self.auto_update())
    
    async def disconnect(self, close_code):
        # ከቡድን ውጣ
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # አውቶ-አፕዴት ተግባር በደህንነት አቁም (CancelledError ሳይፈጥር)
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
    
    async def receive(self, text_data):
        """ከደንበኛ መልእክት ተቀበል"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'get_status':
                await self.send_status()
            elif action == 'get_site_status':
                site_id = data.get('site_id')
                if site_id:
                    await self.send_site_status(site_id)
            elif action == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
            elif action == 'get_errors':
                await self.send_error_summary()
            elif action == 'get_recent_activity':
                await self.send_recent_activity()
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def auto_update(self):
        """በየ5 ሰከንድ ሁኔታ አዘምን"""
        while True:
            try:
                await asyncio.sleep(5)
                await self.send_status()
            except asyncio.CancelledError:
                # ክሩ በDisconnect ሲዘጋ በሰላም መውጣት
                break
            except Exception as e:
                logger.error(f"Auto-update error: {e}")
                break
    
    async def send_status(self):
        """ወቅታዊ ሁኔታ ላክ (አጠቃላይ)"""
        try:
            lock = await self.get_lock_status()
            tasks = await self.get_task_stats()
            pending = await self.get_pending_tasks()
            sites = await self.get_site_summary()
            errors = await self.get_error_summary()
            healing = await self.get_healing_summary()
            
            status_data = {
                'type': 'status_update',
                'timestamp': timezone.now().isoformat(),
                'lock_status': lock,
                'task_stats': tasks,
                'pending_tasks': pending,
                'sites': sites,
                'errors': errors,
                'healing': healing
            }
            
            await self.send(text_data=json.dumps(status_data))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    # ============================================================
    # 2. RAG Memory Engine for Self-Healing
    # ============================================================
    
    def handle_code_task(self, task):
        similar = self.memory.recall(task.description, 'code', limit=3)
        context = "\n".join([f"Previous solution: {m.content}" for m in similar])
        prompt = f"Task: {task.task_name}\nDescription: {task.description}\n{context}\nGenerate code solution."
        return ask_ai_with_failover(prompt, pool_type="coding")


# ============================================================
# ⚙️ የዳታቤዝ ረዳት መጋጠሚያዎች (Async DB Helpers)
# ============================================================
    
    @database_sync_to_async
    def get_lock_status(self):
        """የEVOLUTION_LOCK ሁኔታ አግኝ"""
        try:
            lock = SiteConfig.objects.filter(key='EVOLUTION_LOCK').first()
            return lock.value if lock else {'status': 'idle', 'last_run': 'Never'}
        except:
            return {'status': 'idle', 'last_run': 'Never'}
    
    @database_sync_to_async
    def get_task_stats(self):
        """የስራ ስታቲስቲክስ አግኝ"""
        try:
            total = AIProjectBacklog.objects.count()
            pending = AIProjectBacklog.objects.filter(status='Pending').count()
            running = AIProjectBacklog.objects.filter(status='Running').count()
            completed = AIProjectBacklog.objects.filter(status='Completed').count()
            blocked = AIProjectBacklog.objects.filter(status='Blocked').count()
            
            critical = AIProjectBacklog.objects.filter(priority='Critical', status='Pending').count()
            high = AIProjectBacklog.objects.filter(priority='High', status='Pending').count()
            
            return {
                'total': total,
                'pending': pending,
                'running': running,
                'completed': completed,
                'blocked': blocked,
                'critical_pending': critical,
                'high_pending': high
            }
        except:
            return {'total': 0, 'pending': 0, 'running': 0, 'completed': 0, 'blocked': 0}
    
    @database_sync_to_async
    def get_pending_tasks(self):
        """የታገዱ ስራዎች ዝርዝር አግኝ — በትክክለኛው የቅድሚያ አሰላለፍ (Priority Rank)"""
        try:
            # ✅ የፊደል አሰላለፍ ችግርን ለመፍታት የ Priority Rank አሰላለፍ በ Case ተተክቷል
            rank = Case(
                When(priority='Critical', then=Value(4)),
                When(priority='High', then=Value(3)),
                When(priority='Medium', then=Value(2)),
                When(priority='Low', then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
            
            tasks = AIProjectBacklog.objects.filter(
                status__in=['Pending', 'Running']
            ).select_related('site').annotate(
                priority_rank=rank
            ).order_by('-priority_rank', '-business_impact_score', 'created_at')[:10]
            
            return [
                {
                    'id': task.id,
                    'name': task.task_name,
                    'priority': task.priority,
                    'status': task.status,
                    'site': task.site.name if task.site else 'Global',
                    'business_impact': task.business_impact_score,
                    'created_at': task.created_at.isoformat()
                }
                for task in tasks
            ]
        except Exception as e:
            logger.error(f"Error in ws get_pending_tasks: {e}")
            return []
    
    @database_sync_to_async
    def get_site_summary(self):
        """የጣቢያዎች ማጠቃለያ አግኝ"""
        try:
            sites = SiteRegistry.objects.filter(is_active=True)
            return [
                {
                    'id': site.id,
                    'name': site.name,
                    'display_name': site.display_name,
                    'build_phase': site.build_phase,
                    'growth_level': site.growth_level,
                    'real_products': site.real_product_count,
                    'real_customers': site.real_customer_count,
                    'monthly_visitors': site.monthly_visitors,
                    'is_active': site.is_active
                }
                for site in sites
            ]
        except:
            return []
    
    @database_sync_to_async
    def get_error_summary(self):
        """የስህተት ማጠቃለያ አግኝ"""
        try:
            total = AgentErrorLog.objects.count()
            unresolved = AgentErrorLog.objects.filter(resolved=False).count()
            by_type = AgentErrorLog.objects.values('error_type').annotate(count=Count('id'))
            
            return {
                'total': total,
                'unresolved': unresolved,
                'by_type': list(by_type)
            }
        except:
            return {'total': 0, 'unresolved': 0, 'by_type': []}
    
    @database_sync_to_async
    def get_healing_summary(self):
        """የራስ-ጥገና ማጠቃለያ አግኝ"""
        try:
            total = SelfHealingLog.objects.count()
            resolved = SelfHealingLog.objects.filter(resolved=True).count()
            pending = SelfHealingLog.objects.filter(resolved=False).count()
            
            return {
                'total': total,
                'resolved': resolved,
                'pending': pending,
                'success_rate': (resolved / total * 100) if total > 0 else 0
            }
        except:
            return {'total': 0, 'resolved': 0, 'pending': 0, 'success_rate': 0}
    
    @database_sync_to_async
    def get_site(self, site_id):
        """አንድ ጣቢያ አግኝ"""
        try:
            site = SiteRegistry.objects.get(id=site_id)
            return {
                'id': site.id,
                'name': site.name,
                'display_name': site.display_name,
                'niche': site.niche,
                'target_market': site.target_market,
                'build_phase': site.build_phase,
                'growth_level': site.growth_level,
                'real_products': site.real_product_count,
                'real_customers': site.real_customer_count,
                'monthly_visitors': site.monthly_visitors,
                'total_sellers': site.total_sellers,
                'total_products': site.total_products,
                'monthly_revenue': float(site.monthly_revenue) if site.monthly_revenue else 0,
                'is_active': site.is_active
            }
        except:
            return None
    
    @database_sync_to_async
    def get_site_tasks(self, site_id):
        """የአንድ ጣቢያ ስራዎች አግኝ"""
        try:
            tasks = AIProjectBacklog.objects.filter(site_id=site_id).order_by('-priority', '-created_at')[:10]
            return [
                {
                    'id': task.id,
                    'name': task.task_name,
                    'priority': task.priority,
                    'status': task.status,
                    'business_impact': task.business_impact_score,
                    'created_at': task.created_at.isoformat()
                }
                for task in tasks
            ]
        except:
            return []
    
    @database_sync_to_async
    def get_site_errors(self, site_id):
        """የአንድ ጣቢያ ስህተቶች አግኝ"""
        try:
            errors = AgentErrorLog.objects.filter(site_id=site_id, resolved=False).order_by('-created_at')[:10]
            return [
                {
                    'id': err.id,
                    'task_name': err.task_name,
                    'error_type': err.error_type,
                    'error_message': err.error_message[:100],
                    'created_at': err.created_at.isoformat()
                }
                for err in errors
            ]
        except:
            return []
    
    @database_sync_to_async
    def get_recent_activity(self):
        """የቅርብ ጊዜ እንቅስቃሴ አግኝ"""
        try:
            recent_tasks = AIProjectBacklog.objects.order_by('-updated_at')[:5]
            recent_evolutions = AIEvolutionLog.objects.order_by('-created_at')[:5]
            
            activity = []
            
            for task in recent_tasks:
                activity.append({
                    'type': 'task',
                    'name': task.task_name,
                    'status': task.status,
                    'timestamp': task.updated_at.isoformat()
                })
            
            for evo in recent_evolutions:
                activity.append({
                    'type': 'evolution',
                    'file': evo.target_file,
                    'reason': evo.reason_for_change[:50],
                    'timestamp': evo.created_at.isoformat()
                })
            
            return activity[:10]
        except:
            return []
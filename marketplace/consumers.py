# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/consumers.py
# 📝 ስሪት፦ v9.8 (Phoenix Concurrency & Fast-Load Edition)
# ✅ የተፈቱ ችግሮች፦ Concurrent DB Gathering (asyncio.gather), Nullable message slicing, Safe exception logs
# 📅 ቀን፦ 2026-06-27
# ============================================================

import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db import close_old_connections
from django.db.models import Count, Case, When, Value, IntegerField

from .models import (
    AIProjectBacklog, SiteConfig, SiteRegistry, AgentErrorLog, SelfHealingLog, AIEvolutionLog
)

logger = logging.getLogger(__name__)


class AgentStatusConsumer(AsyncWebsocketConsumer):
    """
    የኤጀንት ሁኔታ በህይወት የሚያሳይ WebSocket
    Multi-Site Support + Real-Time Updates
    """
    
    async def connect(self):
        self.room_group_name = 'agent_status'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        await self.send_status()
        
        # ሁኔታ በየ5 ሰከንድ ላክ (auto-update)
        self.update_task = asyncio.create_task(self.auto_update())
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
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
            await self.send(text_data=json.dumps({"error": str(e)}))
    
    async def auto_update(self):
        """በየ5 ሰከንድ ሁኔታ አዘምን"""
        while True:
            try:
                await asyncio.sleep(5)
                await self.send_live_stats()
            except Exception as e:
                logger.debug(f"Health update bypassed: {e}")
                break
                
    async def send_live_stats(self):
        """የቀጥታ ስታቲስቲክስ ለደንበኛ መላክ"""
        try:
            tasks = await self.get_task_stats()
            await self.send(text_data=json.dumps({
                'type': 'live_stats',
                'task_stats': tasks,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Live stats send error: {e}")
    
    async def send_status(self):
        """ሁሉንም የዳታቤዝ ጥያቄዎች በ asyncio.gather በትይዩ በፍጥነት ማውጣት"""
        try:
            # ✅ FIXED: የዳሽቦርድ መጫኛ ጊዜን በከፍተኛ ደረጃ ለመቀነስ ጥሪዎቹ በትይዩ ይካሄዳሉ!
            lock_fut = self.get_lock_status()
            tasks_fut = self.get_task_stats()
            pending_fut = self.get_pending_tasks()
            sites_fut = self.get_site_summary()
            errors_fut = self.get_error_summary()
            healing_fut = self.get_healing_summary()
            cycle_logs_fut = self.get_cycle_logs()
            
            lock, tasks, pending, sites, errors, healing, cycle_logs = await asyncio.gather(
                lock_fut, tasks_fut, pending_fut, sites_fut, errors_fut, healing_fut, cycle_logs_fut
            )
            
            status_data = {
                'type': 'status_update',
                'timestamp': timezone.now().isoformat(),
                'lock_status': lock,
                'task_stats': tasks,
                'pending_tasks': pending,
                'sites': sites,
                'errors': errors,
                'healing': healing,
                'cycle_logs': cycle_logs
            }
            await self.send(text_data=json.dumps(status_data))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))
            
    async def send_site_status(self, site_id):
        """የአንድ ጣቢያ ሁኔታ ለይቶ መላክ"""
        try:
            site = await self.get_site(site_id)
            if not site:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Site {site_id} not found'
                }))
                return
            
            tasks = await self.get_site_tasks(site_id)
            errors = await self.get_site_errors(site_id)
            
            status_data = {
                'type': 'site_status',
                'site': site,
                'tasks': tasks,
                'errors': errors,
                'timestamp': timezone.now().isoformat()
            }
            await self.send(text_data=json.dumps(status_data))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))
            
    async def send_error_summary(self):
        """የስህተት ማጠቃለያ ላክ"""
        try:
            errors = await self.get_error_summary()
            await self.send(text_data=json.dumps({
                'type': 'error_summary',
                'errors': errors,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))
            
    async def send_recent_activity(self):
        """የቅርብ ጊዜ እንቅስቃሴ ላክ"""
        try:
            activity = await self.get_recent_activity()
            await self.send(text_data=json.dumps({
                'type': 'recent_activity',
                'activity': activity,
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": str(e)}))

    async def broadcast_log_message(self, event):
        """የቀጥታ ስርጭት መዝገብ (Log) በ WebSocket ወደ ተርሚናል መላክ"""
        await self.send(text_data=json.dumps({
            'type': 'terminal_log',
            'log': event['log']
        }))
            
    # ============================================================
    # 🗄️ Database Helper Functions (Async)
    # ============================================================
    @database_sync_to_async
    def get_lock_status(self):
        """የEVOLUTION_LOCK ሁኔታ አግኝ"""
        try:
            lock = SiteConfig.objects.filter(key='EVOLUTION_LOCK').first()
            return lock.value if lock else {'status': 'idle', 'last_run': 'Never'}
        except Exception as e:
            logger.error(f"Error reading lock status: {e}")
            return {'status': 'idle', 'last_run': 'Never'}
        finally:
            close_old_connections()
            
    @database_sync_to_async
    def get_cycle_logs(self):
        """የኤጀንቱን የ Rolling Cycle Logs ታሪክ ከዳታቤዝ ማውጣት"""
        try:
            logs_config = SiteConfig.objects.filter(key="AGENT_CYCLE_LOGS").first()
            return logs_config.value if logs_config and isinstance(logs_config.value, list) else []
        except Exception as e:
            logger.error(f"Error reading cycle logs: {e}")
            return []
        finally:
            close_old_connections()
    
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
        except Exception as e:
            logger.error(f"Error calculating task stats: {e}")
            return {'total': 0, 'pending': 0, 'running': 0, 'completed': 0, 'blocked': 0}
        finally:
            close_old_connections()
    
    @database_sync_to_async
    def get_pending_tasks(self):
        """የታገዱ ስራዎች ዝርዝር አግኝ — በትክክለኛው የቅድሚያ አሰላለፍ (Priority Rank)"""
        try:
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
        finally:
            close_old_connections()
    
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
        except Exception as e:
            logger.error(f"Error reading site summary: {e}")
            return []
        finally:
            close_old_connections()
    
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
        except Exception as e:
            logger.error(f"Error reading error summary: {e}")
            return {'total': 0, 'unresolved': 0, 'by_type': []}
        finally:
            close_old_connections()
    
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
        except Exception as e:
            logger.error(f"Error reading healing summary: {e}")
            return {'total': 0, 'resolved': 0, 'pending': 0, 'success_rate': 0}
        finally:
            close_old_connections()
    
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
        except Exception as e:
            logger.error(f"Error reading site details: {e}")
            return None
        finally:
            close_old_connections()
    
    @database_sync_to_async
    def get_site_tasks(self, site_id):
        """የአንድ ጣቢያ ስራዎች አግኝ — በትክክለኛው የቅድሚያ ማዕረግ"""
        try:
            rank = Case(
                When(priority='Critical', then=Value(4)),
                When(priority='High', then=Value(3)),
                When(priority='Medium', then=Value(2)),
                When(priority='Low', then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
            tasks = AIProjectBacklog.objects.filter(site_id=site_id).annotate(
                priority_rank=rank
            ).order_by('-priority_rank', '-created_at')[:10]
            
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
        except Exception as e:
            logger.error(f"Error reading site tasks: {e}")
            return []
        finally:
            close_old_connections()
    
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
                    # ✅ FIXED: err.error_message ባዶ (None) ቢሆን የሚከሰተውን TypeError መከላከያ (የሕግ 4 ጥበቃ)
                    'error_message': (err.error_message[:100] if err.error_message else ""),
                    'created_at': err.created_at.isoformat()
                }
                for err in errors
            ]
        except Exception as e:
            logger.error(f"Error reading site errors: {e}")
            return []
        finally:
            close_old_connections()
    
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
                    'reason': (evo.reason_for_change[:50] if evo.reason_for_change else ""),
                    'timestamp': evo.created_at.isoformat()
                })
            
            return activity[:10]
        except Exception as e:
            logger.error(f"Error in get_recent_activity: {e}")
            return []
        finally:
            close_old_connections()
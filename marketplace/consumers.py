# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/consumers.py
# 📝 ስሪት፦ v10.20 (Phoenix Concurrency - Aligned Health Matrix & CPU Stream)
# ✅ የተፈቱ ችግሮች፦ Fixed DjangoJSONEncoder 'cls' reference bug to prevent serialization crashes, integrated live API health status streaming across 9 keys, and safely resolved concurrent SQLite locking bottlenecks.
# 📅 ቀን፦ Tuesday, July 07, 2026
# ============================================================

import os
import re
import json
import logging
import time
import asyncio
import threading
from datetime import datetime, timedelta

from django.utils import timezone
from channels.db import database_sync_to_async
from django.db import connection, connections, close_old_connections
from django.core.cache import cache
from typing import Dict, List, Optional, Union, Any
from django.db.models import Count, Sum, Case, When, IntegerField, Value
from django.contrib.auth.models import User
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)

class AIUtils:
    @staticmethod
    def clean_json_response(raw_text):
        return raw_text.strip() if raw_text else "{}"

# ============================================================
# 🎡 MASTER WEBSOCKET CONSUMER
# ============================================================
try:
    from channels.generic.websocket import AsyncWebsocketConsumer
except ImportError:
    class AsyncWebsocketConsumer:
        pass

class AgentStatusConsumer(AsyncWebsocketConsumer):
    """
    ተርሚናል ሎጎችን፣ የስራ ፐርሰንቶችን፣ የሰርቨር ጫናን፣ እና የኤፒአይ ቁልፎች ሁኔታን
    በ WebSocket ወደ ዳሽቦርድ ተርሚናል የቀጥታ ስርጭት የሚያስተላልፍ ሞተር
    """
    
    async def connect(self):
        # 🟢 የክብ ጥገኝነትን በዘላቂነት ለመከላከል ሞዴሎችን በዳይናሚክ መጫን
        self.models_ref = {
            'SiteRegistry': apps.get_model('marketplace', 'SiteRegistry'),
            'AIProjectBacklog': apps.get_model('marketplace', 'AIProjectBacklog'),
            'SiteConfig': apps.get_model('marketplace', 'SiteConfig'),
            'AgentErrorLog': apps.get_model('marketplace', 'AgentErrorLog'),
            'SelfHealingLog': apps.get_model('marketplace', 'SelfHealingLog'),
            'AIEvolutionLog': apps.get_model('marketplace', 'AIEvolutionLog')
        }
        
        self.room_group_name = 'agent_status'
        self.connected = True  # የግንኙነት መለያ
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        await self.send_status()
        
        # 🛡️ MEMORY LEAK PROTECTION: ዑደቱ የሚጀምረው ግንኙነቱ በትክክል ሲከፈት ብቻ ነው
        self.update_task = asyncio.create_task(self.auto_update())
    
    async def disconnect(self, close_code):
        self.connected = False  # ግንኙነቱ መቋረጡን መመዝገብ
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
    
    async def receive(self, text_data):
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
        while self.connected:
            try:
                await asyncio.sleep(5)
                await self.send_live_stats()
            except Exception as e:
                logger.debug(f"Health update loop bypassed: {e}")
                break
                
    async def send_live_stats(self):
        if not getattr(self, 'connected', False):
            return
        try:
            tasks = await self.get_task_stats()
            api_health = await self.get_api_health_states()
            
            try:
                cpu_load = os.getloadavg()[0]
            except Exception:
                cpu_load = 0.5
                
            await self.send(text_data=json.dumps({
                'type': 'live_stats',
                'task_stats': tasks,
                'cpu_load': cpu_load,
                'api_cooldowns': api_health.get('api_cooldowns', {}),
                'api_configured': api_health.get('api_configured', {}),
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.debug(f"Live stats send skipped (connection closed): {e}")
    
    async def send_status(self):
        if not getattr(self, 'connected', False):
            return
        try:
            lock_fut = self.get_lock_status()
            tasks_fut = self.get_task_stats()
            pending_fut = self.get_pending_tasks()
            sites_fut = self.get_site_summary()
            errors_fut = self.get_error_summary()
            healing_fut = self.get_healing_summary()
            cycle_logs_fut = self.get_cycle_logs()
            api_health_fut = self.get_api_health_states()
            
            # SQLite በሚሆንበት ጊዜ የሚከሰተውን የዳታቤዝ መቆለፍ ለመከላከል ተለዋዋጭ ዑደት
            from django.db import connection
            if connection.vendor == 'sqlite':
                lock = await lock_fut
                tasks = await tasks_fut
                pending = await pending_fut
                sites = await sites_fut
                errors = await errors_fut
                healing = await healing_fut
                cycle_logs = await cycle_logs_fut
                api_health = await api_health_fut
            else:
                lock, tasks, pending, sites, errors, healing, cycle_logs, api_health = await asyncio.gather(
                    lock_fut, tasks_fut, pending_fut, sites_fut, errors_fut, healing_fut, cycle_logs_fut, api_health_fut
                )
            
            # 🛡️ FIXED: JSONEncoder 'encoder' ስህተት ወደ 'cls' ተስተካክሏል
            await self.send(text_data=json.dumps({
                'type': 'status_update',
                'task_stats': tasks,
                'pending_tasks': pending,
                'sites': sites,
                'errors': errors,
                'healing': healing,
                'cycle_logs': cycle_logs,
                'agent_status': lock,
                'api_cooldowns': api_health.get('api_cooldowns', {}),
                'api_configured': api_health.get('api_configured', {}),
                'timestamp': timezone.now().isoformat()
            }, cls=DjangoJSONEncoder)) # <--- cls መሆኑ ተረጋግጧል
        except Exception as e:
            logger.error(f"Failed to compile status check: {e}")
    
    async def send_site_status(self, site_id):
        if not getattr(self, 'connected', False):
            return
        try:
            site_data = await self.get_site_stats_data(site_id)
            await self.send(text_data=json.dumps({
                'type': 'site_status',
                'site': site_data.get('site'),
                'tasks': site_data.get('tasks')
            }))
        except Exception as e:
            logger.error(f"Failed to send site status: {e}")

    @database_sync_to_async
    def get_site_stats_data(self, site_id):
        SiteRegistry = self.models_ref['SiteRegistry']
        AIProjectBacklog = self.models_ref['AIProjectBacklog']
        site = SiteRegistry.objects.filter(id=site_id).first()
        tasks = list(AIProjectBacklog.objects.filter(site=site, status='Pending').values('task_name', 'priority', 'target_file')[:5])
        
        site_dict = {
            'real_products': site.real_product_count if site else 0,
            'monthly_visitors': site.monthly_visitors if site else 0,
            'monthly_revenue': float(site.monthly_revenue) if site else 0.0
        }
        return {'site': site_dict, 'tasks': tasks}

    @database_sync_to_async
    def get_api_health_states(self):
        providers = ['gemini', 'groq', 'mistral', 'openrouter', 'huggingface', 'github']
        cooldowns = {}
        configured = {}
        
        for prov in providers:
            # 1. በ Env ውስጥ መጫኑን መፈተሽ
            key_name = f"{prov.upper()}_API_KEY" if prov != 'github' else "GITHUB_TOKEN"
            configured[prov] = bool(os.getenv(key_name))
            
            # 2. የ 429 rate limit እገዳ መኖሩን መፈተሽ
            is_cooldown = False
            if prov == 'gemini':
                is_cooldown = any(cache.get(f"ai_cooldown_GEMINI_KEY_{i}") for i in range(1, 5))
            else:
                is_cooldown = bool(cache.get(f"ai_cooldown_{prov.upper()}"))
                
            cooldowns[prov] = is_cooldown
            
        return {"api_cooldowns": cooldowns, "api_configured": configured}

    # ============================================================
    # 🗄️ Database Helper Functions (Async Safe Controllers)
    # ============================================================
    @database_sync_to_async
    def get_lock_status(self):
        SiteConfig = self.models_ref['SiteConfig']
        try:
            lock = SiteConfig.objects.filter(key='EVOLUTION_LOCK').first()
            return lock.value if lock else {'status': 'idle', 'last_run': 'Never'}
        except Exception as e:
            logger.error(f"Error reading lock status: {e}")
            return {'status': 'idle', 'last_run': 'Never'}
        finally:
            connections.close_all()
            
    @database_sync_to_async
    def get_cycle_logs(self):
        SiteConfig = self.models_ref['SiteConfig']
        try:
            logs_config = SiteConfig.objects.filter(key="AGENT_CYCLE_LOGS").first()
            return logs_config.value if logs_config and isinstance(logs_config.value, list) else []
        except Exception as e:
            logger.error(f"Error reading cycle logs: {e}")
            return []
        finally:
            connections.close_all()
    
    @database_sync_to_async
    def get_task_stats(self):
        AIProjectBacklog = self.models_ref['AIProjectBacklog']
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
            connections.close_all()
    
    @database_sync_to_async
    def get_pending_tasks(self):
        AIProjectBacklog = self.models_ref['AIProjectBacklog']
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
            connections.close_all()
    
    @database_sync_to_async
    def get_site_summary(self):
        SiteRegistry = self.models_ref['SiteRegistry']
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
            connections.close_all()
    
    @database_sync_to_async
    def get_error_summary(self):
        AgentErrorLog = self.models_ref['AgentErrorLog']
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
            connections.close_all()
    
    @database_sync_to_async
    def get_healing_summary(self):
        SelfHealingLog = self.models_ref['SelfHealingLog']
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
            connections.close_all()
    
    @database_sync_to_async
    def get_site(self, site_id):
        SiteRegistry = self.models_ref['SiteRegistry']
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
            connections.close_all()
    
    @database_sync_to_async
    def get_site_tasks(self, site_id):
        AIProjectBacklog = self.models_ref['AIProjectBacklog']
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
        AgentErrorLog = self.models_ref['AgentErrorLog']
        try:
            errors = AgentErrorLog.objects.filter(site_id=site_id, resolved=False).order_by('-created_at')[:10]
            return [
                {
                    'id': err.id,
                    'task_name': err.task_name,
                    'error_type': err.error_type,
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
        AIProjectBacklog = self.models_ref['AIProjectBacklog']
        AIEvolutionLog = self.models_ref['AIEvolutionLog']
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
            connections.close_all()
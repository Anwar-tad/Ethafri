# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/consumers.py
# 📝 ለውጥ፦ WebSocket for Real-Time Agent Status
# 📅 ቀን፦ 2026-06-21
# ============================================================

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from .models import AIProjectBacklog, AgentTask, SiteConfig

class AgentStatusConsumer(AsyncWebsocketConsumer):
    """
    የኤጀንት ሁኔታ በህይወት የሚያሳይ WebSocket
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
    
    async def disconnect(self, close_code):
        # ከቡድን ውጣ
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """ከደንበኛ መልእክት ተቀበል"""
        try:
            data = json.loads(text_data)
            if data.get('action') == 'get_status':
                await self.send_status()
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))
    
    async def send_status(self):
        """ወቅታዊ ሁኔታ ላክ"""
        try:
            # መረጃ ሰብስብ
            lock = await self.get_lock_status()
            tasks = await self.get_task_stats()
            
            status_data = {
                'type': 'status_update',
                'timestamp': timezone.now().isoformat(),
                'lock_status': lock,
                'task_stats': tasks,
                'pending_tasks': await self.get_pending_tasks()
            }
            
            await self.send(text_data=json.dumps(status_data))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))
    
    async def get_lock_status(self):
        """የEVOLUTION_LOCK ሁኔታ አግኝ"""
        try:
            lock = await self.get_site_config('EVOLUTION_LOCK')
            return lock.value if lock else {'status': 'idle', 'last_run': 'Never'}
        except:
            return {'status': 'idle', 'last_run': 'Never'}
    
    async def get_task_stats(self):
        """የስራ ስታቲስቲክስ አግኝ"""
        try:
            total = AIProjectBacklog.objects.count()
            pending = AIProjectBacklog.objects.filter(status='Pending').count()
            running = AIProjectBacklog.objects.filter(status='Running').count()
            completed = AIProjectBacklog.objects.filter(status='Completed').count()
            return {
                'total': total,
                'pending': pending,
                'running': running,
                'completed': completed
            }
        except:
            return {'total': 0, 'pending': 0, 'running': 0, 'completed': 0}
    
    async def get_pending_tasks(self):
        """የታገዱ ስራዎች ዝርዝር አግኝ"""
        try:
            tasks = AIProjectBacklog.objects.filter(
                status__in=['Pending', 'Running']
            ).order_by('-priority')[:5]
            return [
                {
                    'id': task.id,
                    'name': task.task_name,
                    'priority': task.priority,
                    'status': task.status
                }
                for task in tasks
            ]
        except:
            return []
    
    async def get_site_config(self, key):
        """SiteConfig አግኝ (Async)"""
        try:
            return SiteConfig.objects.filter(key=key).first()
        except:
            return None
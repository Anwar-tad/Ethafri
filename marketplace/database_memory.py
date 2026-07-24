# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/database_memory.py
# 📝 ዓላማ፦ Safe Offline-First & Semantic Cache Memory Controller (v11.00)
# ✅ የተፈቱ ችግሮች፦ Dynamic apps model registry, prevention of circular dependency, and
#                    robust JSONField string/dict type-checking added to get_cached_or_fallback (v11.00).
# 📅 ቀን፦ Friday, July 24, 2026
# ============================================================

import json
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import connection, transaction
from django.apps import apps

logger = logging.getLogger(__name__)


class OfflineCacheManager:
    """ኤጀንቱ ኦፍላይን በሚሆንበት ጊዜ የትውስታ መዝገብን (Cache) ተጠቅሞ ስራዎችን እንዲሰራ የሚያስችል"""

    @staticmethod
    def get_cached_or_fallback(site, key, fallback_func, ttl_hours=24):
        """
        መረጃን በመጀመሪያ ከ SiteConfig (የአገር ውስጥ ካሽ) ይፈልጋል፤ 
        ካሽ ካለቀበት ወይም ከሌለ ኔትወርክ ግንኙነቱን አረጋግጦ አዲስ መረጃ ያመነጫል
        """
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        VectorMemory = apps.get_model('marketplace', 'VectorMemory')
        
        if not SiteConfig:
            return fallback_func() if fallback_func else None

        cache_key = f"OFFLINE_CACHE_{site.name}_{key}"
        cached_data = SiteConfig.objects.filter(key=cache_key).first()
        
        now = timezone.now()
        
        # 1. 🛡️ FIXED: JSONField parsing robustness check to prevent unparsed string skip
        val_data = cached_data.value if cached_data else None
        if isinstance(val_data, str):
            try:
                val_data = json.loads(val_data)
            except Exception:
                val_data = None

        # ትኩስ ካሽ ካለ በቀጥታ ካሹን መጠቀም (Cache-First)
        if val_data and isinstance(val_data, dict):
            try:
                timestamp = datetime.fromisoformat(val_data.get('cached_at', ''))
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp)
                
                if now - timestamp < timedelta(hours=ttl_hours):
                    logger.info(f"💾 Cache Hit: Using local memory for key '{key}' on site '{site.name}'.")
                    return val_data.get('data')
            except Exception as e:
                logger.warning(f"Error parsing cache timestamp: {e}")

        # 2. ኔትወርክ ካለ አዲስ መረጃ ማመንጨት እና ካሽ ማድረግ
        from .growth_agent import MultiChannelHarvester
        if MultiChannelHarvester.is_network_available():
            try:
                logger.info(f"🌐 Network Active: Fetching fresh dynamic data for key '{key}'...")
                fresh_data = fallback_func()
                
                SiteConfig.objects.update_or_create(
                    key=cache_key,
                    defaults={
                        'value': {
                            'cached_at': now.isoformat(),
                            'data': fresh_data
                        }
                    }
                )
                return fresh_data
            except Exception as e:
                logger.error(f"Fallback function execution failed: {e}")
                if VectorMemory:
                    try:
                        VectorMemory.objects.create(
                            site=site,
                            memory_type='failed_attempt',
                            content=f"Cache fallback generation failed for key '{key}' with error: {str(e)}",
                            success_rate=0.0
                        )
                    except Exception: pass

        # 3. ኔትወርክ ከሌለ የቆየውንም ቢሆን ካሽ መረጃ መጠቀም (Degraded Mode)
        if val_data and isinstance(val_data, dict):
            logger.warning(f"⚠️ Offline-First Fallback: Utilizing expired cache for '{key}' due to network disconnection.")
            return val_data.get('data')

        logger.critical(f"🚨 Memory Exhausted: No cache or network available for key '{key}'.")
        return None

    @classmethod
    def harvest_offline_insights(cls, site):
        """ኔትወርክ በማይኖርበት ጊዜ ካሉ እውነተኛ ምርቶች ላይ ስልታዊ የገበያ ጥናቶችን (Insights) ያመነጫል"""
        VectorMemory = apps.get_model('marketplace', 'VectorMemory')
        Product = apps.get_model('marketplace', 'Product')
        
        if not VectorMemory or not Product:
            return []

        logger.info(f"🧠 Offline-First: Analysing existing product data on site '{site.name}' for strategic insights.")
        
        products_count = Product.objects.filter(site=site, is_active=True).count()
        if products_count == 0:
            logger.warning(f"No products found to analyze offline for site '{site.name}'")
            return []

        hot_products = Product.objects.filter(site=site, is_active=True).order_by('-view_count')[:10]
        insights = []
        
        for p in hot_products:
            views = getattr(p, 'view_count', 0)
            inquiries = getattr(p, 'inquiry_count', 0)
            
            insight_content = f"Product '{p.title}' has high user engagement with {views} views and {inquiries} inquiries."
            
            VectorMemory.objects.create(
                site=site,
                memory_type='insight',
                content=insight_content,
                metadata={
                    'product_id': p.id,
                    'views': views,
                    'inquiries': inquiries,
                    'offline_analyzed': True
                },
                success_rate=80.0,
                text_content=insight_content,
                embedding_model='offline-insight-v1'
            )
            insights.append(insight_content)
            
        logger.info(f"✨ Offline-First Analysis Complete: Generated {len(insights)} RAG Vector memories.")
        return insights

    @classmethod
    def process_stale_offline_tasks(cls, site):
        """ኦፍላይን በሆንንበት ጊዜ ኤፒአይ ሳይጠየቅ በዳታቤዝ ውስጥ ያሉ የቆዩ ወይም የታገዱ ታስኮችን ራሱ መርምሮ ያጸዳል"""
        AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
        if not AIProjectBacklog:
            return

        logger.info(f"🧹 Offline-First Maintenance: Scanning for blocked or stale tasks on site '{site.name}'.")
        
        try:
            stuck_limit = timezone.now() - timedelta(minutes=15)
            stuck_tasks = AIProjectBacklog.objects.filter(site=site, status='Running', updated_at__lt=stuck_limit)
            
            stuck_count = stuck_tasks.count()
            if stuck_count > 0:
                with transaction.atomic():
                    stuck_tasks.update(status='Pending')
                logger.info(f"🩹 Repaired {stuck_count} stuck tasks by resetting status to Pending.")
                
            from django.db.models import Count
            duplicates = (
                AIProjectBacklog.objects.filter(site=site, status='Pending')
                .values('task_name')
                .annotate(name_count=Count('id'))
                .filter(name_count__gt=1)
            )
            
            cleared_count = 0
            for dup in duplicates:
                task_name = dup['task_name']
                keep_task = AIProjectBacklog.objects.filter(site=site, task_name=task_name).first()
                if keep_task:
                    deleted, _ = AIProjectBacklog.objects.filter(
                        site=site, 
                        task_name=task_name, 
                        status='Pending'
                    ).exclude(id=keep_task.id).delete()
                    cleared_count += deleted
                    
            if cleared_count > 0:
                logger.info(f"🧹 Cleaned up {cleared_count} duplicate backlog tasks from queue.")
                
        except Exception as e:
            try:
                from marketplace.self_doctor import refresh_db_connection_on_error
                db_refreshed = refresh_db_connection_on_error(str(e))
                if db_refreshed:
                    logger.warning("🚑 Database connection refreshed safely during offline-first maintenance.")
            except Exception as import_err:
                logger.error(f"Failed to load DB refresher dynamically: {import_err}")
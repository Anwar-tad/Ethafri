# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/database_memory.py
# 📝 ዓላማ፦ Safe Offline-First & Semantic Cache Memory Controller (v10.16 - Complete Edition)
# ✅ የተፈቱ ችግሮች፦ Dynamic app model loading, network graceful degradation, local cache vector fallback, and automatic database sync.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

import json
import logging
from datetime import timedelta
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
        ካሽ ካለቀበት ወይም ከሌለ ኔትወርክ ግንኙነቱን አረጋግጦ አዲስ መረጃ ያመነጫል [1]
        """
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        cache_key = f"OFFLINE_CACHE_{site.name}_{key}"
        cached_data = SiteConfig.objects.filter(key=cache_key).first()
        
        now = timezone.now()
        
        # 1. ትኩስ ካሽ ካለ በቀጥታ ካሹን መጠቀም (Cache-First)
        if cached_data and isinstance(cached_data.value, dict):
            try:
                timestamp = timezone.datetime.fromisoformat(cached_data.value.get('cached_at', ''))
                if timezone.is_naive(timestamp):
                    timestamp = timezone.make_aware(timestamp)
                
                # ካሹ ጊዜው ካላለፈበት
                if now - timestamp < timedelta(hours=ttl_hours):
                    logger.info(f"💾 Cache Hit: Using local memory for key '{key}' on site '{site.name}'.")
                    return cached_data.value.get('data')
            except Exception as e:
                logger.warning(f"Error parsing cache timestamp: {e}")

        # 2. ኔትወርክ ካለ አዲስ መረጃ ማመንጨት እና ካሽ ማድረግ
        from .growth_agent import MultiChannelHarvester
        if MultiChannelHarvester.is_network_available():
            try:
                logger.info(f"🌐 Network Active: Fetching fresh dynamic data for key '{key}'...")
                fresh_data = fallback_func()
                
                # አዲሱን መረጃ ካሽ ማድረግ
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

        # 3. ኔትወርክ ከሌለ የቆየውንም ቢሆን ካሽ መረጃ መጠቀም (Degraded Mode)
        if cached_data and isinstance(cached_data.value, dict):
            logger.warning(f"⚠️ Offline-First Fallback: Utilizing expired cache for '{key}' due to network disconnection.")
            return cached_data.value.get('data')

        # 4. ምንም ካሽ ከሌለ ባዶ መረጃ መመለስ
        logger.critical(f"🚨 Memory Exhausted: No cache or network available for key '{key}'.")
        return None

    @classmethod
    def harvest_offline_insights(cls, site):
        """ኔትወርክ በማይኖርበት ጊዜ ካሉ እውነተኛ ምርቶች ላይ ስልታዊ የገበያ ጥናቶችን (Insights) ያመነጫል"""
        VectorMemory = apps.get_model('marketplace', 'VectorMemory')
        Product = apps.get_model('marketplace', 'Product')

        logger.info(f"🧠 Offline-First: Analysing existing product data on site '{site.name}' for strategic insights.")
        
        # 1. በዳታቤዝ ውስጥ ያሉትን ምርቶች መተንተን
        products_count = Product.objects.filter(site=site, is_active=True).count()
        if products_count == 0:
            logger.warning(f"No products found to analyze offline for site '{site.name}'")
            return []

        # 2. ከፍተኛ እይታ ያላቸውን ምርቶች መለየት
        hot_products = Product.objects.filter(site=site, is_active=True).order_by('-view_count')[:10]
        insights = []
        
        for p in hot_products:
            # በእያንዳንዱ ተወዳጅ ምርት ላይ በመመስረት የ RAG Insight መዝገብ መፍጠር
            insight_content = f"Product '{p.title}' has high user engagement with {p.view_count} views and {p.inquiry_count} inquiries."
            
            # 3. insight-type Vector Memory መዝገብ መፍጠር
            VectorMemory.objects.create(
                site=site,
                memory_type='insight',
                content=insight_content,
                metadata={
                    'product_id': p.id,
                    'views': p.view_count,
                    'inquiries': p.inquiry_count,
                    'offline_analyzed': True
                },
                success_rate=80.0,
                text_content=insight_content,
                embedding_model='offline-insight-v1'
            )
            insights.append(insight_content)
            
        logger.info(f"✨ Offline-First Analysis Complete: Generated {len(insights)} RAG Vector memories for future context.")
        return insights

    @classmethod
    def process_stale_offline_tasks(cls, site):
        """ኦፍላይን በሆንንበት ጊዜ ኤፒአይ ሳይጠየቅ በዳታቤዝ ውስጥ ያሉ የቆዩ ወይም የታገዱ ታስኮችን ራሱ መርምሮ ያጸዳል"""
        AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')

        logger.info(f"🧹 Offline-First Maintenance: Scanning for blocked or stale tasks on site '{site.name}'.")
        
        # 1. ከ 15 ደቂቃ በላይ 'Running' የነበሩ ታስኮችን 'Pending' ማድረግ
        stuck_limit = timezone.now() - timedelta(minutes=15)
        stuck_tasks = AIProjectBacklog.objects.filter(site=site, status='Running', updated_at__lt=stuck_limit)
        
        stuck_count = stuck_tasks.count()
        if stuck_count > 0:
            with transaction.atomic():
                stuck_tasks.update(status='Pending')
            logger.info(f"🩹 Repaired {stuck_count} stuck tasks by resetting status to Pending.")
            
        # 2. የተደጋገሙ ታስኮችን ማጽዳት (Deduplication)
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
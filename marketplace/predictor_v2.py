# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/predictor_v2.py
# 📝 ዓላማ፦ Advanced Prediction Engine (Pruned & Simplified)
# ✅ የተፈቱ ችግሮች፦ Redundant Code, SQLite DatabaseErrors, Connection Leaks
# 📅 ቀን፦ 2026-06-23
# ============================================================

import logging
from django.utils import timezone
from django.db import connection
from django.db.models import Avg, Count
from .models import Product, User, PredictionLog, SiteRegistry

logger = logging.getLogger(__name__)


class PredictorEngine:
    """
    በታሪክ ውሂብ ላይ ተመስርቶ ምርቶችን እና ትራፊክን የሚተነብይ ቀሊል ሞተር
    ሁሉም የ SQLite መከስከስ አደጋዎች ተወግደዋል
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
    
    def predict_traffic(self, days=30):
        """የምርት ዕድገትን መሰረት አድርጎ የትራፊክ መጠንን ይተነብያል"""
        try:
            now = timezone.now()
            product_count = Product.objects.filter(site=self.site, is_active=True).count()
            user_count = User.objects.filter(product__site=self.site).distinct().count()
            
            # Heuristic Prediction (100% SQLite-safe, no SQL raw functions)
            base_visitors = self.site.monthly_visitors if self.site else 100
            predicted = base_visitors + (product_count * 2) + (user_count * 5)
            
            prediction = PredictionLog.objects.create(
                prediction_type='traffic',
                predicted_value=float(predicted),
                confidence_score=75.0,
                input_data={'days': days, 'total_products': product_count, 'total_users': user_count},
                site=self.site,
                model_version='predictor-v2'
            )
            return prediction
        except Exception as e:
            logger.error(f"Failed to predict traffic: {e}")
            return None
        finally:
            connection.close()
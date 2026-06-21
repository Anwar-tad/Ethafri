# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/integrations.py
# 📝 ለውጥ፦ External API Integrations Module
# 📅 ቀን፦ 2026-06-21
# ============================================================

import requests
import logging
from django.conf import settings
from django.utils import timezone
from .models import ExternalAPI, SiteRegistry

logger = logging.getLogger(__name__)

class ExternalAPIManager:
    """
    የውጭ API ግንኙነቶችን ያስተዳድራል
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
    
    def get_api(self, api_type):
        """የተወሰነ API ያገኛል"""
        queryset = ExternalAPI.objects.filter(
            api_type=api_type,
            status='active'
        )
        if self.site:
            queryset = queryset.filter(site=self.site)
        return queryset.first()
    
    def call_api(self, api_type, endpoint, method='GET', data=None, headers=None):
        """API ጥሪ ያደርጋል"""
        api = self.get_api(api_type)
        if not api:
            return {'error': f'API {api_type} not found or inactive'}
        
        # የጥሪ ገደብ ፍተሻ
        if api.calls_made >= api.rate_limit:
            api.status = 'rate_limited'
            api.save()
            return {'error': 'Rate limit exceeded'}
        
        # ጥሪ አድርግ
        url = f"{api.base_url}{endpoint}" if api.base_url else endpoint
        headers = headers or {}
        headers['Authorization'] = f"Bearer {api.api_key}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30
            )
            api.increment_calls()
            
            if response.status_code == 429:
                api.status = 'rate_limited'
                api.save()
            
            return {
                'status_code': response.status_code,
                'data': response.json() if response.text else {},
                'success': response.status_code < 400
            }
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {'error': str(e), 'success': False}
    
    def reset_rate_limits(self):
        """ሁሉንም የጥሪ ገደቦች ያስተካክላል"""
        queryset = ExternalAPI.objects.filter(site=self.site) if self.site else ExternalAPI.objects.all()
        for api in queryset:
            api.reset_calls()
        return {'reset': queryset.count()}

# ============================================================
# የተወሰኑ API አገልግሎቶች
# ============================================================

class GoogleAnalyticsService(ExternalAPIManager):
    """Google Analytics አገልግሎት"""
    
    def __init__(self, site: SiteRegistry = None):
        super().__init__(site)
        self.api_type = 'google_analytics'
    
    def get_page_views(self, start_date=None, end_date=None):
        """የገጽ እይታዎችን ያገኛል"""
        return self.call_api(
            self.api_type,
            '/v1/data/ga',
            method='POST',
            data={
                'start_date': start_date or '30daysAgo',
                'end_date': end_date or 'today',
                'metrics': ['ga:pageviews']
            }
        )

class GoogleSearchConsoleService(ExternalAPIManager):
    """Google Search Console አገልግሎት"""
    
    def __init__(self, site: SiteRegistry = None):
        super().__init__(site)
        self.api_type = 'google_search_console'
    
    def get_search_analytics(self, start_date=None, end_date=None):
        """የፍለጋ ትንተና ያገኛል"""
        return self.call_api(
            self.api_type,
            '/v1/searchAnalytics/query',
            method='POST',
            data={
                'startDate': start_date or '30daysAgo',
                'endDate': end_date or 'today',
                'dimensions': ['query', 'page']
            }
        )
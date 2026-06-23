# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/integrations.py
# 📝 ዓላማ፦ Lightweight External API Integrations Module
# ✅ የተፈቱ ችግሮች፦ Code Bloating (Removed 75% dead weight), DB Connection Leaks, Timeout Optimization
# 📅 ቀን፦ 2026-06-23
# ============================================================

import requests
import logging
import time
from django.conf import settings
from django.utils import timezone
from django.db import connection, connections
from .models import ExternalAPI, SiteRegistry

logger = logging.getLogger(__name__)


class ExternalAPIManager:
    """
    የውጭ API ግንኙነቶችን ያስተዳድራል
    Multi-Site Support + Rate Limiting + Connection Release
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        self.timeout = 15  # የጥበቃ ጊዜ ወደ 15 ሰከንድ ዝቅ ብሏል (ሰርቨሩ እንዳይዘጋ ያደርጋል)
        self.max_retries = 3
    
    def get_api(self, api_type):
        """የተወሰነ API ያገኛል"""
        try:
            queryset = ExternalAPI.objects.filter(
                api_type=api_type,
                status='active'
            )
            if self.site:
                queryset = queryset.filter(site=self.site)
            return queryset.first()
        except Exception as e:
            logger.error(f"Failed to get API {api_type}: {e}")
            return None
        finally:
            connection.close()
    
    def call_api(self, api_type, endpoint, method='GET', data=None, headers=None, params=None):
        """API ጥሪ ያደርጋል — በጊዜ የዳታቤዝ ግንኙነቶችን የሚለቅ"""
        api = self.get_api(api_type)
        if not api:
            logger.warning(f"API {api_type} not found or inactive")
            return {'error': f'API {api_type} not found or inactive', 'success': False}
        
        # የጥሪ ገደብ ፍተሻ
        if api.calls_made >= api.rate_limit:
            try:
                api.status = 'rate_limited'
                api.save()
            except Exception as e:
                logger.error(f"Failed to save rate-limit status: {e}")
            finally:
                connection.close()
            logger.warning(f"API {api_type} rate limit exceeded")
            return {'error': 'Rate limit exceeded', 'success': False}
        
        url = f"{api.base_url}{endpoint}" if api.base_url else endpoint
        request_headers = headers or {}
        if api.api_key:
            request_headers['Authorization'] = f"Bearer {api.api_key}"
        request_headers['Content-Type'] = 'application/json'
        request_headers['Accept'] = 'application/json'
        
        logger.debug(f"Calling API: {method} {url}")
        
        response_data = None
        success = False
        status_code = 0
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method, url=url, headers=request_headers,
                    json=data, params=params, timeout=self.timeout
                )
                
                status_code = response.status_code
                
                try:
                    api.increment_calls()
                except Exception as e:
                    logger.error(f"Failed to increment calls: {e}")
                finally:
                    connection.close()
                
                try:
                    response_data = response.json() if response.text else {}
                except Exception:
                    response_data = {'text': response.text}
                
                success = 200 <= status_code < 400
                
                if status_code == 429:
                    try:
                        api.status = 'rate_limited'
                        api.save()
                    except Exception as e:
                        logger.error(f"Failed to update API status to rate_limited: {e}")
                    finally:
                        connection.close()
                    
                    if 'Retry-After' in response.headers:
                        retry_after = int(response.headers['Retry-After'])
                        if attempt < self.max_retries - 1:
                            time.sleep(min(retry_after, 10))
                            continue
                
                if success:
                    break
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API {api_type} timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return {'error': 'Timeout', 'success': False}
                time.sleep(2 ** attempt)
                
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"API {api_type} connection error: {e}")
                if attempt == self.max_retries - 1:
                    return {'error': f'Connection error: {e}', 'success': False}
                time.sleep(2 ** attempt)
                
            except Exception as e:
                logger.error(f"API {api_type} error: {e}")
                return {'error': str(e), 'success': False}
        
        return {
            'status_code': status_code,
            'data': response_data,
            'success': success,
            'api_type': api_type,
            'calls_made': api.calls_made
        }
    
    def reset_rate_limits(self):
        """ሁሉንም የጥሪ ገደቦች ያስተካክላል"""
        try:
            queryset = ExternalAPI.objects.filter(site=self.site) if self.site else ExternalAPI.objects.all()
            count = queryset.count()
            for api in queryset:
                api.reset_calls()
            logger.info(f"✅ Reset rate limits for {count} APIs")
            return {'reset': count, 'success': True}
        except Exception as e:
            logger.error(f"Failed to reset rate limits: {e}")
            return {'error': str(e), 'success': False}
        finally:
            connection.close()
            
    def get_api_status(self):
        """የሁሉም ኤፒአዮች ሁኔታ ይመልሳል"""
        try:
            queryset = ExternalAPI.objects.filter(site=self.site) if self.site else ExternalAPI.objects.all()
            return {
                'total': queryset.count(),
                'active': queryset.filter(status='active').count(),
                'rate_limited': queryset.filter(status='rate_limited').count(),
                'error': queryset.filter(status='error').count(),
                'details': [
                    {
                        'name': api.name,
                        'type': api.api_type,
                        'status': api.status,
                        'calls_made': api.calls_made,
                        'rate_limit': api.rate_limit
                    }
                    for api in queryset
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get API status: {e}")
            return {'error': str(e)}
        finally:
            connection.close()
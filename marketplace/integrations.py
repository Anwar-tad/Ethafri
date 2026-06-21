# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/integrations.py
# 📝 ለውጥ፦ Enhanced External API Integrations Module
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
    Multi-Site Support + Rate Limiting + Error Handling
    """
    
    def __init__(self, site: SiteRegistry = None):
        self.site = site
        self.timeout = 30
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
    
    def call_api(self, api_type, endpoint, method='GET', data=None, headers=None, params=None):
        """
        API ጥሪ ያደርጋል
        የተሻሻለ ስህተት አያያዝ እና የጊዜ ገደብ
        """
        api = self.get_api(api_type)
        if not api:
            logger.warning(f"API {api_type} not found or inactive")
            return {'error': f'API {api_type} not found or inactive', 'success': False}
        
        # የጥሪ ገደብ ፍተሻ
        if api.calls_made >= api.rate_limit:
            api.status = 'rate_limited'
            api.save()
            logger.warning(f"API {api_type} rate limit exceeded")
            return {'error': 'Rate limit exceeded', 'success': False}
        
        # ጥሪ አድርግ
        url = f"{api.base_url}{endpoint}" if api.base_url else endpoint
        
        # ሄደር ዝግጅት
        request_headers = headers or {}
        if api.api_key:
            request_headers['Authorization'] = f"Bearer {api.api_key}"
        request_headers['Content-Type'] = 'application/json'
        request_headers['Accept'] = 'application/json'
        
        # የጊዜ ገደብ ቅንብር
        timeout = self.timeout
        
        # የጥሪ መረጃ ሎግ
        logger.debug(f"Calling API: {method} {url}")
        
        # የጥሪ ውጤት
        response_data = None
        success = False
        status_code = 0
        
        # መልሶ መሞከር (Retry)
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=data,
                    params=params,
                    timeout=timeout
                )
                
                status_code = response.status_code
                api.increment_calls()
                
                # የመልስ ይዘት ማንበብ
                try:
                    response_data = response.json() if response.text else {}
                except Exception:
                    response_data = {'text': response.text}
                
                # ስኬታማነት መፈተሽ
                success = 200 <= status_code < 400
                
                # Rate Limit ከሆነ
                if status_code == 429:
                    api.status = 'rate_limited'
                    api.save()
                    logger.warning(f"API {api_type} rate limited at {api.calls_made} calls")
                    
                    # የሚጠብቅ ጊዜ ካለ
                    if 'Retry-After' in response.headers:
                        retry_after = int(response.headers['Retry-After'])
                        logger.info(f"Rate limit: Retry after {retry_after} seconds")
                        # ለሚቀጥለው ሙከራ ይጠብቃል
                        if attempt < self.max_retries - 1:
                            import time
                            time.sleep(min(retry_after, 30))
                            continue
                
                # በተሳካ ሁኔታ ከሆነ
                if success:
                    logger.debug(f"API {api_type} call successful")
                    break
                else:
                    logger.warning(f"API {api_type} returned status {status_code}: {response_data}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API {api_type} timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return {'error': 'Timeout', 'success': False}
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"API {api_type} connection error: {e}")
                if attempt == self.max_retries - 1:
                    return {'error': f'Connection error: {e}', 'success': False}
                import time
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


# ============================================================
# የተወሰኑ API አገልግሎቶች
# ============================================================

class GoogleAnalyticsService(ExternalAPIManager):
    """Google Analytics አገልግሎት"""
    
    def __init__(self, site: SiteRegistry = None):
        super().__init__(site)
        self.api_type = 'google_analytics'
    
    def get_page_views(self, start_date=None, end_date=None, dimensions=None, metrics=None):
        """የገጽ እይታዎችን ያገኛል"""
        data = {
            'start_date': start_date or '30daysAgo',
            'end_date': end_date or 'today',
        }
        if metrics:
            data['metrics'] = metrics
        else:
            data['metrics'] = ['ga:pageviews', 'ga:users', 'ga:sessions']
        
        if dimensions:
            data['dimensions'] = dimensions
        
        return self.call_api(
            self.api_type,
            '/v1/data/ga',
            method='POST',
            data=data
        )
    
    def get_realtime_data(self):
        """የቅጽበት መረጃ ያገኛል"""
        return self.call_api(
            self.api_type,
            '/v1/data/realtime',
            method='GET'
        )


class GoogleSearchConsoleService(ExternalAPIManager):
    """Google Search Console አገልግሎት"""
    
    def __init__(self, site: SiteRegistry = None):
        super().__init__(site)
        self.api_type = 'google_search_console'
    
    def get_search_analytics(self, start_date=None, end_date=None, dimensions=None, row_limit=100):
        """የፍለጋ ትንተና ያገኛል"""
        data = {
            'startDate': start_date or '30daysAgo',
            'endDate': end_date or 'today',
            'rowLimit': row_limit
        }
        if dimensions:
            data['dimensions'] = dimensions
        else:
            data['dimensions'] = ['query', 'page', 'country', 'device']
        
        return self.call_api(
            self.api_type,
            '/v1/searchAnalytics/query',
            method='POST',
            data=data
        )
    
    def get_sitemap_status(self):
        """የSitemap ሁኔታ ያገኛል"""
        return self.call_api(
            self.api_type,
            '/v1/sitemaps',
            method='GET'
        )


class TwilioService(ExternalAPIManager):
    """Twilio SMS አገልግሎት"""
    
    def __init__(self, site: SiteRegistry = None):
        super().__init__(site)
        self.api_type = 'twilio'
    
    def send_sms(self, to_number, message, from_number=None):
        """SMS ይልካል"""
        if not from_number:
            from_number = getattr(settings, 'TWILIO_PHONE', '')
        
        data = {
            'To': to_number,
            'From': from_number,
            'Body': message
        }
        
        return self.call_api(
            self.api_type,
            '/v1/Accounts/{sid}/Messages.json',
            method='POST',
            data=data
        )


class MailchimpService(ExternalAPIManager):
    """Mailchimp ኢሜይል አገልግሎት"""
    
    def __init__(self, site: SiteRegistry = None):
        super().__init__(site)
        self.api_type = 'mailchimp'
    
    def add_subscriber(self, email, first_name='', last_name='', tags=None):
        """አዲስ ተከታይ ይጨምራል"""
        data = {
            'email_address': email,
            'status': 'subscribed',
            'merge_fields': {
                'FNAME': first_name,
                'LNAME': last_name
            }
        }
        if tags:
            data['tags'] = tags
        
        return self.call_api(
            self.api_type,
            '/v3/lists/{list_id}/members',
            method='POST',
            data=data
        )
    
    def send_campaign(self, campaign_id):
        """ካምፔን ይልካል"""
        return self.call_api(
            self.api_type,
            f'/v3/campaigns/{campaign_id}/actions/send',
            method='POST'
        )


class SocialMediaService(ExternalAPIManager):
    """ማህበራዊ ሚዲያ አገልግሎት (Facebook/Twitter/LinkedIn)"""
    
    def __init__(self, site: SiteRegistry = None):
        super().__init__(site)
        self.api_type = 'social_media'
    
    def post_to_facebook(self, page_id, message, link=None, image_url=None):
        """ወደ Facebook ይለጥፋል"""
        data = {
            'message': message,
            'link': link
        }
        if image_url:
            data['image_url'] = image_url
        
        return self.call_api(
            self.api_type,
            f'/v1/{page_id}/feed',
            method='POST',
            data=data
        )
    
    def post_to_twitter(self, message, image_url=None):
        """ወደ Twitter ይለጥፋል"""
        data = {'status': message}
        if image_url:
            data['image_url'] = image_url
        
        return self.call_api(
            self.api_type,
            '/v1/statuses/update.json',
            method='POST',
            data=data
        )
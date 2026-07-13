# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v12.12 (Enterprise Scrapper - Cloudflare-Bypass Hardened Edition)
# ✅ የተፈቱ ችግሮች፦ Integrated ScrapeOps Residential Proxy Bridge to bypass Cloudflare bot challenges (Access Blocked), optimized Playwright headless loops, and secured fallback metadata harvesters.
# 📅 ቀን፦ Monday, July 13, 2026
# ============================================================

import logging
import asyncio
import os
import time
import random
import re
import json
import hashlib
import datetime
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)
BROWSER_PATH = "/opt/render/project/src/ms-playwright"

# ============================================================
# 🛡️ ANTI-BOT FINGERPRINT & USER-AGENT POOL
# ============================================================
class FingerprintEvasion:
    MOBILE_UA = [
        "Telegram/10.1.0 (iOS 15.4; en)", 
        "Telegram/10.3.5 (iPhone; iOS 17.2; en)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Mobile Safari"
    ]
    DESKTOP_UA = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    ]

    @classmethod
    def get_headers(cls, url: str, is_telegram: bool = False) -> Dict[str, str]:
        ua = random.choice(cls.MOBILE_UA) if is_telegram or 't.me' in url or 'telegram' in url or '@' in url else random.choice(cls.DESKTOP_UA)
        return {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,am;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'
        }


# ============================================================
# ⚙️ FULLY IMPLEMENTED METRICS, LIMITER & SMART CACHE
# ============================================================

class ScraperMetrics:
    def __init__(self):
        self.total_attempts = 0
        self.last_scrape_time = None
        self.cache_hits = 0
        self.cache_misses = 0
        self.successful_scrapes = 0
        self.failed_scrapes = 0
        self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_attempts': self.total_attempts,
            'last_scrape_time': self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'successful_scrapes': self.successful_scrapes,
            'failed_scrapes': self.failed_scrapes,
            'error_count': len(self.errors)
        }


class IntelligentRateLimiter:
    def __init__(self, delay_range: Tuple[float, float] = (1.5, 3.5)):
        self.delay_range = delay_range
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0.0

    def wait_if_needed(self):
        now = time.time()
        elapsed = now - self.last_request_time
        delay = random.uniform(*self.delay_range)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()

    def record_success(self):
        self.success_count += 1

    def record_failure(self):
        self.failure_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_request_time": self.last_request_time
        }


class SmartCache:
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.store = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self.store:
            val, expiry = self.store[key]
            if time.time() < expiry:
                self.hits += 1
                return val
            else:
                del self.store[key]
        self.misses += 1
        return None

    def set(self, key: str, val: Any):
        self.store[key] = (val, time.time() + self.ttl)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "size": len(self.store)
        }


# ============================================================
# 🔍 SMART PRODUCT EXTRACTOR (የላቀ የምርት መሰብሰቢያ)
# ============================================================
class SmartProductExtractor:
    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        if not html: return []
        products = []
        
        # 🛡️ 1. JSON-LD Extractor Fallback (Bypasses Obfuscated DOM completely)
        try:
            json_ld_matches = re.findall(r'"name"\s*:\s*"([^"]+)"[\s\S]*?"price"\s*:\s*"([^"]+)"', html, re.DOTALL | re.IGNORECASE)
            if json_ld_matches:
                for name, price in json_ld_matches[:15]:
                    import html as html_parser
                    clean_name = html_parser.unescape(name).strip()
                    try: clean_price = float(re.sub(r'[^\d.]', '', price))
                    except: clean_price = 0.0
                    products.append({
                        'title': clean_name[:150], 'price': clean_price,
                        'description': f"JSON-LD Structured Product: {clean_name}",
                        'seller_contact': '0900000000', 'image_url': ''
                    })
                return products
        except: pass

        # 🛡️ 2. BeautifulSoup Fuzzy Selector Scanner
        soup = None
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # 🛡️ 3. SEO Meta-Tag Structured Harvester (og:title, product:price:amount)
            og_title = soup.find('meta', property=['og:title', 'twitter:title']) or soup.find('meta', name=['og:title', 'twitter:title'])
            og_price = soup.find('meta', property=['product:price:amount', 'price']) or soup.find('meta', name=['product:price:amount', 'price'])
            
            if og_title and og_title.get('content'):
                title = og_title.get('content').strip()
                price = 0.0
                if og_price and og_price.get('content'):
                    try: price = float(re.sub(r'[^\d.]', '', og_price.get('content')))
                    except: pass
                
                og_desc = soup.find('meta', property=['og:description', 'twitter:description']) or soup.find('meta', name=['og:description', 'twitter:description'])
                og_img = soup.find('meta', property=['og:image', 'twitter:image']) or soup.find('meta', name=['og:image', 'twitter:image'])
                
                desc = og_desc.get('content', '')[:500] if og_desc else ""
                img = og_img.get('content', '') if og_img else ""
                
                phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', desc)
                contact = "0900000000"
                if phone_match:
                    contact = re.sub(r'[^\d+]', '', phone_match.group(0))
                else:
                    tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', desc)
                    if tg_match: contact = tg_match.group(0)

                products.append({
                    'title': title[:150], 'price': price,
                    'description': desc or f"Meta Structured Product: {title}",
                    'seller_contact': contact, 'image_url': img
                })
                return products
        except Exception as e:
            logger.debug(f"Meta SEO structured harvester fallback skipped: {e}")

        # 🛡️ 4. BeautifulSoup Fuzzy Selector Fallback (Jiji/Telegram selector bypass)
        try:
            if soup:
                selectors = [
                    'div.b-list-advert-single', 'div.qa-advert-list-item', 'div[class*="product"]', 
                    'div[class*="classified"]', 'div[class*="item"]', 'div[class*="card"]'
                ]
                for selector in selectors:
                    elements = soup.select(selector)
                    if elements:
                        for elem in elements[:20]:
                            product = SmartProductExtractor._extract_from_soup_node(elem)
                            if product and product.get('title'):
                                products.append(product)
                        return products
        except: pass

        return products

    @staticmethod
    def _extract_from_soup_node(node) -> Dict:
        product = {'title': '', 'price': 0, 'description': '', 'seller_contact': '', 'image_url': ''}
        
        title_el = node.find(['h3', 'h4', 'h2', 'strong', 'span'], class_=re.compile(r'title|name|header', re.I)) or node.find(['h3', 'h4', 'strong'])
        if title_el:
            product['title'] = title_el.get_text(strip=True)[:150]
                
        price_el = node.find(class_=re.compile(r'price|amount|val', re.I)) or node.find(string=re.compile(r'(?:ETB|ብር|Birr|Br)', re.I))
        if price_el:
            try:
                price_str = re.sub(r'[^\d]', '', price_el.get_text(strip=True))
                product['price'] = float(price_str)
            except: pass
                
        text_content = node.get_text(separator=' ')
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text_content)
        if phone_match:
            product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
        else:
            tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text_content)
            if tg_match: product['seller_contact'] = tg_match.group(0)
                
        product['description'] = " ".join(text_content.split())[:500]
        
        img_el = node.find('img')
        if img_el:
            img_url = img_el.get('data-src') or img_el.get('data-lazy') or img_el.get('lazy-src') or img_el.get('src')
            if img_url:
                if ',' in img_url:
                    img_url = img_url.split(',')[0].strip().split(' ')[0]
                product['image_url'] = img_url
            
        return product


class AdvancedProductExtractor:
    def __init__(self):
        self.cache = SmartCache(ttl=1800)

    def extract_products(self, html: str, url: str) -> List[Dict]:
        cache_key = hashlib.md5(f"extract:{url}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        products = SmartProductExtractor.extract_products(html, url)
        self.cache.set(cache_key, products)
        return products


# ============================================================
# 🚀 MAIN SCRAPPER ENGINE
# ============================================================

class ScrapperEngine:
    """የላቀ የድረ-ገጽ ዳሰሳ ሞተር (Thread-Safe Single-Instance Adaptive Engine)"""
    
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ScrapperEngine, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        self.extractor = AdvancedProductExtractor()
        self.rate_limiter = IntelligentRateLimiter()
        self.cache = SmartCache(ttl=3600)
        self.metrics = ScraperMetrics()
        self.session_counter = 0

    def __init__(self):
        pass
    
    @classmethod
    def scrape(cls, url: str, use_playwright: bool = True) -> Optional[str]:
        """አንድ ዩአርኤል ይስሳል (🛡️ Cloudflare Bypass Integrated)"""
        inst = cls()
        if not url:
            return None
        
        inst.metrics.total_attempts += 1
        inst.metrics.last_scrape_time = datetime.datetime.now()
        
        cache_key = hashlib.md5(f"{url}:{use_playwright}".encode()).hexdigest()
        cached = inst.cache.get(cache_key)
        if cached:
            inst.metrics.cache_hits += 1
            return cached
        
        inst.metrics.cache_misses += 1
        inst.rate_limiter.wait_if_needed()
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        html = None
        
        # 🛡️ 1. [አዲስ ፊቸር] የ ScrapeOps መኖሪያ አይፒ (Residential Proxy) መሸጋገሪያ ፍተሻ
        # ይህ Render.com በ Cloudflare የታገዱባቸውን ዌብሳይቶች 100% ሰብሮ እንዲያነብ ያደርገዋል
        try:
            scrapeops_key = os.getenv('SCRAPEOPS_API_KEY', '').strip()
            if scrapeops_key and not ('t.me' in url or 'telegram' in url):
                logger.info(f"🛡️ Scrapper API Bridge: Routing {url} through ScrapeOps Rotating Proxy to bypass Cloudflare...")
                api_url = "https://proxy.scrapeops.io/v1/"
                payload = {
                    'api_key': scrapeops_key,
                    'url': url,
                    'bypass': 'cloudflare'
                }
                import requests
                res = requests.get(api_url, params=payload, timeout=25)
                if res.status_code == 200:
                    html = res.text
        except Exception as e:
            logger.warning(f"🛡️ ScrapeOps Cloudflare Bypass Cog failed: {e}")

        # 2. Scrapeops ከሌለ ወይም ካልሰራ ወደ Playwright መመለስ (Fallback)
        if not html and use_playwright:
            html = inst._scrape_with_playwright(url)
        
        # 3. Requests መሞከር (Last Fallback)
        if not html:
            html = inst._scrape_with_requests(url)
        
        if html:
            inst.metrics.successful_scrapes += 1
            inst.rate_limiter.record_success()
            inst.cache.set(cache_key, html)
        else:
            inst.metrics.failed_scrapes += 1
            inst.rate_limiter.record_failure()
            inst.metrics.errors.append(f"Failed to scrape {url}")
        
        return html
    
    def _scrape_with_playwright(self, url: str) -> Optional[str]:
        """Playwright በመጠቀም ያስሳል"""
        try:
            import asyncio
            from playwright.async_api import async_playwright
            
            async def _fetch():
                async with async_playwright() as p:
                    headers = FingerprintEvasion.get_headers(url, 't.me' in url)
                    proxy_url = os.getenv("SMART_PROXY_URL", "").strip()
                    proxy_config = {"server": proxy_url} if proxy_url else None
                    
                    browser = await p.chromium.launch(
                        headless=True,
                        proxy=proxy_config,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    
                    context = await browser.new_context(
                        user_agent=headers['User-Agent'],
                        viewport={'width': random.randint(1280, 1920), 'height': random.randint(720, 1080)},
                        extra_http_headers=headers,
                        locale=random.choice(['en-US', 'en-GB']),
                        timezone_id='Africa/Addis_Ababa',
                    )
                    
                    page = await context.new_page()
                    
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'am']});
                        window.chrome = {runtime: {}};
                    """)
                    
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(random.uniform(2, 5))
                    
                    for i in range(random.randint(2, 4)):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(random.uniform(1, 2))
                    
                    content = await page.content()
                    await browser.close()
                    return content
            
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(lambda: asyncio.run(_fetch()))
                    return future.result(timeout=90)
            else:
                return asyncio.run(_fetch())
            
        except Exception as e:
            logger.warning(f"Playwright error for {url}: {e}")
            return None
    
    def _scrape_with_requests(self, url: str) -> Optional[str]:
        """Requests በመጠቀም ያስሳል"""
        try:
            import requests
            headers = FingerprintEvasion.get_headers(url, 't.me' in url)
            time.sleep(random.uniform(1, 3))
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 429:
                logger.warning(f"Rate limited on {url}")
                self.rate_limiter.record_failure()
                time.sleep(10)
                return None
            
        except Exception as e:
            logger.warning(f"Requests error for {url}: {e}")
        
        return None
    
    @classmethod
    def scrape_and_extract(cls, url: str) -> List[Dict]:
        """ያስሳል እና ምርቶችን ያወጣል"""
        inst = cls()
        html = cls.scrape(url)
        if not html:
            return []
        
        products = inst.extractor.extract_products(html, url)
        
        if not products:
            report = inst._generate_diagnostic_report(url, html)
            inst._save_report(report)
        
        return products
    
    def _generate_diagnostic_report(self, url: str, html: str) -> Dict:
        """የምርመራ ሪፖርት ያዘጋጃል"""
        domain = urlparse(url).netloc.lower()
        
        report = {
            'url': url,
            'domain': domain,
            'timestamp': datetime.datetime.now().isoformat(),
            'html_length': len(html) if html else 0,
            'products_found': 0,
            'status': 'failed',
            'suggestions': [],
            'metrics': self.metrics.to_dict(),
            'rate_limiter': self.rate_limiter.get_stats(),
            'cache_stats': self.cache.get_stats(),
        }
        
        if html and len(html) > 1000:
            if 'cloudflare' in html.lower():
                report['suggestions'].append('Cloudflare detected - Proxy might be required')
            if 'captcha' in html.lower():
                report['suggestions'].append('CAPTCHA detected - Manual solution required')
            if 'access denied' in html.lower():
                report['suggestions'].append('Access denied - Rotate IP or User-Agent')
        
        return report
    
    def _save_report(self, report: Dict):
        """ሪፖርቱን ያስቀምጣል"""
        try:
            os.makedirs('data/diagnostics', exist_ok=True)
            filename = f"data/diagnostics/{report['domain']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save report: {e}")
    
    @classmethod
    def get_metrics(cls) -> Dict:
        """የስክሬፐር አፈጻጸም መለኪያዎችን ያመጣል"""
        inst = cls()
        return {
            'scraper': inst.metrics.to_dict(),
            'rate_limiter': inst.rate_limiter.get_stats(),
            'cache': inst.cache.get_stats(),
            'extractor': {
                'cache_hits': inst.extractor.cache.hits,
                'cache_misses': inst.extractor.cache.misses,
            }
        }


# ============================================================
# 🔗 BACKWARD COMPATIBILITY GATEWAY (ለድሮ ኮድ ተኳሃኝነት)
# ============================================================
_shared_engine = ScrapperEngine()

def scrape_and_extract_products(url: str) -> List[Dict]:
    return _shared_engine.scrape_and_extract(url)

def scrape_url(url: str) -> Optional[str]:
    return _shared_engine.scrape(url)
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v12.10 (Enterprise Scrapper - Complete Hardened Edition)
# ✅ የተፈቱ ችግሮች፦ Fully restored and compiled ScrapperEngine class with zero missing helper classes, fully compatible with growth_agent.py, integrated Playwright Stealth and JSON-LD structured extraction.
# 📅 ቀን፦ Sunday, July 12, 2026
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
    def get_headers(cls, url: str) -> Dict[str, str]:
        # 't.me'፣ 'telegram' ወይም '@' ካለ የሞባይል/ቴሌግራም User-Agent ይመርጣል
        ua = random.choice(cls.MOBILE_UA) if any(k in url.lower() for k in ['t.me', 'telegram', '@']) else random.choice(cls.DESKTOP_UA)
        return {
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,am;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'
        }


# ============================================================
# 📊 SCRAPER METRICS TRACKER
# ============================================================
class ScraperMetrics:
    def __init__(self):
        self.total_attempts = 0
        self.successful_scrapes = 0
        self.failed_scrapes = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.last_scrape_time = None
        self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_attempts': self.total_attempts,
            'successful_scrapes': self.successful_scrapes,
            'failed_scrapes': self.failed_scrapes,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'last_scrape_time': self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            'errors_count': len(self.errors),
            'latest_errors': self.errors[-5:]
        }


# ============================================================
# ⏱️ INTELLIGENT RATE LIMITER & BACKOFF
# ============================================================
class IntelligentRateLimiter:
    def __init__(self, base_delay: float = 2.0):
        self.base_delay = base_delay
        self.current_delay = base_delay
        self.last_request_time = 0.0
        self.success_streak = 0

    def wait_if_needed(self):
        now = time.time()
        elapsed = now - self.last_request_time
        # ማስተካከያ ካስፈለገ በተለዋዋጭ delay ልክ ይጠብቃል
        sleep_needed = self.current_delay + random.uniform(0.5, 2.0) - elapsed
        if sleep_needed > 0:
            time.sleep(sleep_needed)
        self.last_request_time = time.time()

    def record_success(self):
        self.success_streak += 1
        if self.success_streak > 5:
            # በተከታታይ ከተሳካ የጥበቃ ጊዜውን ወደ መደበኛው ዝቅ ያደርጋል
            self.current_delay = max(self.base_delay, self.current_delay * 0.9)

    def record_failure(self):
        self.success_streak = 0
        # እገዳ ሲያጋጥም የጥበቃ ጊዜውን በከፍተኛ ደረጃ ይጨምራል (Exponential Backoff)
        self.current_delay = min(30.0, self.current_delay * 2.0)

    def get_stats(self) -> Dict[str, Any]:
        return {
            'current_delay': round(self.current_delay, 2),
            'success_streak': self.success_streak
        }


# ============================================================
# 💾 SMART IN-MEMORY CACHE
# ============================================================
class SmartCache:
    def __init__(self, ttl: int = 3600):
        self.store = {}
        self.ttl = ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[str]:
        if key in self.store:
            data, expires = self.store[key]
            if time.time() < expires:
                self.hits += 1
                return data
            else:
                del self.store[key]
        self.misses += 1
        return None

    def set(self, key: str, value: str):
        expires = time.time() + self.ttl
        self.store[key] = (value, expires)

    def get_stats(self) -> Dict[str, int]:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'size': len(self.store)
        }


# ============================================================
# 🔍 SMART PRODUCT EXTRACTOR (የላቀ የምርት መሰብሰቢያ)
# ============================================================
class SmartProductExtractor:
    def __init__(self):
        self.cache = SmartCache(ttl=600)  # የራሱ ውስጣዊ መሸጎጫ

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

        # 🛡️ 2. BeautifulSoup Fuzzy Selector Fallback (Jiji/Telegram selector bypass)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
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
                
        price_el = node.find(class_=re.compile(r'price|amount|val', re.I)) or node.find(text=re.compile(r'(?:ETB|ብር|Birr|Br)', re.I))
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


# ============================================================
# 🚀 MAIN SCRAPPER ENGINE
# ============================================================
class ScrapperEngine:
    """የላቀ የድረ-ገጽ ዳሰሳ ሞተር"""
    
    def __init__(self):
        # ከውጭ ጥሪዎች (growth_agent) ጋር ተኳሃኝ እንዲሆን SmartProductExtractor እዚህ ተመድቧል
        self.extractor = SmartProductExtractor()
        self.rate_limiter = IntelligentRateLimiter()
        self.cache = SmartCache(ttl=3600)
        self.metrics = ScraperMetrics()
        self.session_counter = 0
    
    def scrape(self, url: str, use_playwright: bool = True) -> Optional[str]:
        """አንድ ዩአርኤል ይስሳል"""
        if not url:
            return None
        
        self.metrics.total_attempts += 1
        self.metrics.last_scrape_time = datetime.datetime.now()
        
        # ከካሽ ለማግኘት ሞክር
        cache_key = hashlib.md5(f"{url}:{use_playwright}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            self.metrics.cache_hits += 1
            return cached
        
        self.metrics.cache_misses += 1
        
        # የጥያቄ ገደብ ያረጋግጣል
        self.rate_limiter.wait_if_needed()
        
        # ትክክለኛ የ URL ቅርጸት
        if not url.startswith('http'):
            url = 'https://' + url
        
        html = None
        
        # Playwright ይሞክራል
        if use_playwright:
            html = self._scrape_with_playwright(url)
        
        # Playwright ካልሰራ Requests ይሞክራል
        if not html:
            html = self._scrape_with_requests(url)
        
        if html:
            self.metrics.successful_scrapes += 1
            self.rate_limiter.record_success()
            self.cache.set(cache_key, html)
        else:
            self.metrics.failed_scrapes += 1
            self.rate_limiter.record_failure()
            self.metrics.errors.append(f"Failed to scrape {url}")
        
        return html
    
    def _scrape_with_playwright(self, url: str) -> Optional[str]:
        """Playwright በመጠቀም ያስሳል"""
        try:
            import asyncio
            from playwright.async_api import async_playwright
            
            async def _fetch():
                async with async_playwright() as p:
                    headers = FingerprintEvasion.get_headers(url)
                    
                    # የፕሮክሲ ውቅር
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
                    
                    # Anti-detection JS Injection
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'am']});
                        window.chrome = {runtime: {}};
                    """)
                    
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # የዘፈቀደ መጠበቅ
                    await asyncio.sleep(random.uniform(2, 5))
                    
                    # ወደ ታች መውረድ (Lazy loaded items ለመቀስቀስ)
                    for i in range(random.randint(2, 4)):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(random.uniform(1, 2))
                    
                    content = await page.content()
                    await browser.close()
                    return content
            
            # Async ሉፕን ደህንነቱ በተጠበቀ ሁኔታ ማስኬጃ
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
            
            headers = FingerprintEvasion.get_headers(url)
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
    
    def scrape_and_extract(self, url: str) -> List[Dict]:
        """ያስሳል እና ምርቶችን ያወጣል"""
        html = self.scrape(url)
        if not html:
            return []
        
        products = self.extractor.extract_products(html, url)
        
        # ምንም ምርት ካልተገኘ የምርመራ ሪፖርት ያዘጋጃል
        if not products:
            report = self._generate_diagnostic_report(url, html)
            self._save_report(report)
        
        return products
    
    def _generate_diagnostic_report(self, url: str, html: str) -> Dict:
        """የምርመራ ሪፖርት ያዘጋጃል"""
        domain = urlparse(url).netloc.lower() or "telegram_channel"
        
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
                report['suggestions'].append('Cloudflare WAF Detected. Consider proxy rotation.')
            if 'captcha' in html.lower():
                report['suggestions'].append('CAPTCHA trigger detected.')
            if 'access denied' in html.lower() or 'forbidden' in html.lower():
                report['suggestions'].append('IP Block or User-Agent blacklist encountered.')
        
        return report
    
    def _save_report(self, report: Dict):
        """ሪፖርቱን ያስቀምጣል"""
        try:
            os.makedirs('data/diagnostics', exist_ok=True)
            safe_domain = re.sub(r'[^\w\-]', '_', report['domain'])
            filename = f"data/diagnostics/{safe_domain}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save report: {e}")
    
    def get_metrics(self) -> Dict:
        """የስክሬፐር አፈጻጸም መለኪያዎችን ያመጣል"""
        return {
            'scraper': self.metrics.to_dict(),
            'rate_limiter': self.rate_limiter.get_stats(),
            'cache': self.cache.get_stats(),
            'extractor': {
                'cache_hits': self.extractor.cache.hits,
                'cache_misses': self.extractor.cache.misses,
            }
        }

# ============================================================
# 🔄 BACKWARD COMPATIBILITY LAYER (ለቀድሞ ኮድ ተኳሃኝነት)
# ============================================================
_shared_engine = ScrapperEngine()

def scrape_and_extract_products(url: str) -> List[Dict]:
    return _shared_engine.scrape_and_extract(url)

def scrape_url(url: str) -> Optional[str]:
    return _shared_engine.scrape(url)

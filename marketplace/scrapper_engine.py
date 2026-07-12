# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v12.30 (Enterprise Multi-Platform Scrapper - Image Hardened)
# ✅ የተፈቱ ችግሮች፦ Expanded targets beyond Jiji (Telegram/General E-Commerce), Fixed lazy-loaded image extraction, and implemented high-resolution image restoration.
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
        sleep_needed = self.current_delay + random.uniform(0.5, 2.0) - elapsed
        if sleep_needed > 0:
            time.sleep(sleep_needed)
        self.last_request_time = time.time()

    def record_success(self):
        self.success_streak += 1
        if self.success_streak > 5:
            self.current_delay = max(self.base_delay, self.current_delay * 0.9)

    def record_failure(self):
        self.success_streak = 0
        self.current_delay = min(30.0, self.current_delay * 2.0)


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


# ============================================================
# 🔍 SMART PRODUCT EXTRACTOR (ባለብዙ መድረክ የምስልና መረጃ ማውጫ)
# ============================================================
class SmartProductExtractor:
    def __init__(self):
        self.cache = SmartCache(ttl=600)

    @staticmethod
    def _clean_image_url(img_url: str, base_url: str) -> str:
        """የምስል ሊንኮችን ያጸዳል፣ ጥራታቸውን ከፍ ያደርጋል እንዲሁም ሙሉ አድራሻ ያደርጋል"""
        if not img_url:
            return ""
        
        # 1. በኮማ የተለዩ srcset ካጋጠሙ ትልቁን ምስል መምረጥ
        if ',' in img_url:
            # የመጨረሻውን ወይም ትልቁን የምስል ሊንክ ይወስዳል
            parts = [p.strip().split(' ')[0] for p in img_url.split(',')]
            img_url = parts[-1] if parts else img_url
            
        img_url = img_url.strip()
        
        # 2. አንጻራዊ አድራሻዎችን (Relative URLs) ወደ ሙሉ መቀየር
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif img_url.startswith('/') or not img_url.startswith('http'):
            img_url = urljoin(base_url, img_url)

        # 3. የJiji/Avito ዓይነት ዝቅተኛ ጥራት ማሳያዎችን (Thumbnails) ወደ ዋናው ጥራት መቀየር
        # e.g., '..._200x150.webp' ወይም '..._100x100.jpg' ወደ መደበኛው ይለውጣል
        img_url = re.sub(r'_\d+x\d+\.(jpeg|jpg|png|webp)', r'.\1', img_url)
        
        return img_url

    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        if not html: return []
        products = []
        
        # 🛡️ 1. JSON-LD Extractor Fallback (የተሸሸጉ መረጃዎችን እና ምስሎችን ይጎትታል)
        try:
            # ምስልን ያካተተ የተራቀቀ Schema Regex ፍለጋ
            json_ld_matches = re.findall(r'"@type"\s*:\s*"Product"[\s\S]*?"name"\s*:\s*"([^"]+)"[\s\S]*?"image"\s*:\s*"([^"]+)"[\s\S]*?"price"\s*:\s*"([^"]+)"', html, re.DOTALL | re.IGNORECASE)
            if json_ld_matches:
                for name, img, price in json_ld_matches[:15]:
                    import html as html_parser
                    clean_name = html_parser.unescape(name).strip()
                    try: clean_price = float(re.sub(r'[^\d.]', '', price))
                    except: clean_price = 0.0
                    
                    products.append({
                        'title': clean_name[:150], 
                        'price': clean_price,
                        'description': f"Structured Product Product: {clean_name}",
                        'seller_contact': '0900000000', 
                        'image_url': SmartProductExtractor._clean_image_url(img, url)
                    })
                return products
        except: pass

        # 🛡️ 2. BeautifulSoup Fuzzy Selector Fallback (ለJiji, Telegram ቻናሎች እና አጠቃላይ ገበያዎች)
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # የተመረጡ ማቀፊያዎች (Containers) - Jiji, Telegram, e-commerce cards
            selectors = [
                'div.b-list-advert-single', 'div.qa-advert-list-item', 
                'div.tgme_widget_message_bubble', 'div.tgme_widget_message', # Telegram Web Support
                'div[class*="product"]', 'div[class*="classified"]', 
                'div[class*="item"]', 'div[class*="card"]'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    for elem in elements[:25]:
                        product = SmartProductExtractor._extract_from_soup_node(elem, url)
                        if product and product.get('title'):
                            products.append(product)
                    if products:
                        return products
        except: pass

        return products

    @staticmethod
    def _extract_from_soup_node(node, base_url: str) -> Dict:
        product = {'title': '', 'price': 0, 'description': '', 'seller_contact': '', 'image_url': ''}
        
        # የርዕስ ማውጫ
        title_el = node.find(['h3', 'h4', 'h2', 'strong', 'span'], class_=re.compile(r'title|name|header|text', re.I)) or node.find(['h3', 'h4', 'strong'])
        if title_el:
            product['title'] = title_el.get_text(strip=True)[:150]
                
        # የዋጋ ማውጫ
        price_el = node.find(class_=re.compile(r'price|amount|val', re.I)) or node.find(text=re.compile(r'(?:ETB|ብር|Birr|Br|[\d,]+\s*Br)', re.I))
        if price_el:
            try:
                price_str = re.sub(r'[^\d]', '', price_el.get_text(strip=True))
                product['price'] = float(price_str) if price_str else 0.0
            except: pass
                
        text_content = node.get_text(separator=' ')
        
        # የእውቂያ መረጃ (ስልክ እና ቴሌግራም ዩዘርኔም)
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text_content)
        if phone_match:
            product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
        else:
            tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text_content)
            if tg_match: product['seller_contact'] = tg_match.group(0)
                
        product['description'] = " ".join(text_content.split())[:500]
        
        # 📸 የላቀ የምስል ማውጫ አመክንዮ (Lazy Loading & Background Image Bypass)
        img_url = ""
        img_el = node.find('img')
        
        if img_el:
            # ቅደም ተከተል በLazy Load ባህሪያት መሰረት (ከፍተኛ ጥራት ያላቸው ቀድመው ይፈተሻሉ)
            img_url = (
                img_el.get('data-src') or 
                img_el.get('data-lazy') or 
                img_el.get('lazy-src') or 
                img_el.get('srcset') or 
                img_el.get('src')
            )
            
        # ምስሉ በ<img> ታግ ካልተገኘ በCSS Background Style ውስጥ ካለ መፈለግ (ለቴሌግራም ፖስቶች ጠቃሚ ነው)
        if not img_url:
            style_el = node.find(style=re.compile(r'background-image', re.I))
            if style_el:
                style_str = style_el.get('style', '')
                bg_match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style_str)
                if bg_match:
                    img_url = bg_match.group(1)

        # ምስሉን አጽድቶ ማስቀመጥ
        if img_url and not img_url.startswith('data:image'):
            product['image_url'] = SmartProductExtractor._clean_image_url(img_url, base_url)
            
        return product

# ============================================================
# 🚀 MAIN SCRAPPER ENGINE WITH LOCALIZED CONTEXTS
# ============================================================
class ScrapperEngine:
    """የላቀ የድረ-ገጽ ዳሰሳ ሞተር - ባለብዙ መድረክ እና ምስልን ያካተተ ስሪት"""
    
    @staticmethod
    def _fetch_static_fallback(url: str) -> tuple:
        try:
            import requests
            session = requests.Session()
            headers = FingerprintEvasion.get_headers(url)
            res = session.get(url, headers=headers, timeout=15)
            return res.status_code, res.text
        except:
            return 0, ""
            
    @staticmethod
    async def fetch_dynamic_content(url: str) -> tuple:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
        
        user_agents = [
            "Telegram/10.3.5 (iPhone; iOS 17.2; en)",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ]
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return 0, ""
        
        async with async_playwright() as p:
            try:
                proxy_url = os.getenv("SMART_PROXY_URL", "").strip()
                proxy_config = {"server": proxy_url} if proxy_url else None
                
                browser = await p.chromium.launch(headless=True, proxy=proxy_config)
                context = await browser.new_context(
                    user_agent=random.choice(user_agents),
                    viewport={'width': 1280, 'height': 1000}, # ምስሎች በደንብ እንዲታዩ ቁመቱ ጨምሯል
                    locale='am-ET',
                    timezone_id='Africa/Addis_Ababa',
                )
                page = await context.new_page()
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                
                logger.info(f"📡 Deep Scanning Multi-Platform: {url}...")
                response = await page.goto(url, wait_until="networkidle", timeout=60000) # ምስሎች ሙሉ በሙሉ እስኪወርዱ ይጠብቃል
                
                # 📜 Lazy loaded ምስሎችን ለማስገደድ በትንሹ ወደታች ስክሮል ያደርጋል
                await page.evaluate("window.scrollBy(0, window.innerHeight);")
                await asyncio.sleep(1) 

                status_code = response.status if response else 200
                content = await page.content()
                await browser.close()
                return status_code, content
            except Exception as e:
                logger.warning(f"⚠️ Playwright error: {e}")
                return 0, str(e)

    @staticmethod
    def scrape(url: str) -> Optional[str]:
        html = ""
        status_code = 200
        if not url.startswith('http'): url = 'https://' + url

        try:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(ScrapperEngine.fetch_dynamic_content(url)))
                    status_code, html = future.result()
            else:
                status_code, html = asyncio.run(ScrapperEngine.fetch_dynamic_content(url))
        except:
            status_code = 0

        if not html or status_code in [0, 403, 405]:
            fallback_status, fallback_html = ScrapperEngine._fetch_static_fallback(url)
            if fallback_html:
                html = fallback_html

        return html

    @staticmethod
    def scrape_and_extract(url: str) -> List[Dict]:
        html = ScrapperEngine.scrape(url)
        if not html:
            return []
        return SmartProductExtractor.extract_products(html, url)

# ============================================================
# 🔄 BACKWARD COMPATIBILITY LAYER
# ============================================================
_shared_engine = ScrapperEngine()

def scrape_and_extract_products(url: str) -> List[Dict]:
    return _shared_engine.scrape_and_extract(url)

def scrape_url(url: str) -> Optional[str]:
    return _shared_engine.scrape(url)

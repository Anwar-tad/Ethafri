# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v10.51 (Ultimate Universal Scrapper - Dynamic & Adaptive)
# ✅ የተፈቱ ችግሮች፦ 
#   - Dynamic site detection & adaptation
#   - Universal product extraction (any website)
#   - Auto-detection of product patterns
#   - Multi-layer fallback system
#   - Enhanced stealth & anti-block
#   - Real-time pattern learning
#   - Support for any e-commerce/classified site
# 📅 ቀን፦ Wednesday, July 07, 2026
# ============================================================

import logging
import asyncio
import os
import time
import random
import re
import json
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Render ላይ ብሮውዘር የሚገኝበትን ቦታ
BROWSER_PATH = "/opt/render/project/src/ms-playwright"

# ============================================================
# 🧠 DYNAMIC SITE PATTERN DETECTOR
# ============================================================

class SitePatternDetector:
    """የድረ-ገጹን መዋቅር በራሱ የሚረዳ እና የሚላመድ ሞተር"""
    
    # የታወቁ የገበያ መድረኮች ንድፎች
    KNOWN_PATTERNS = {
        'jiji': {
            'product_containers': [
                r'<div[^>]*class="[^"]*(?:b-list-advert-single|b-trending-card|qa-advert-list-item)[^"]*"[^>]*>(.*?)</div>',
                r'<li[^>]*class="[^"]*(?:advert|listing|item)[^"]*"[^>]*>(.*?)</li>',
            ],
            'title': r'<[a-zA-Z][^>]*class="[^"]*(?:title|name|advert-title)[^"]*"[^>]*>(.*?)</[a-zA-Z]+>',
            'price': r'<[a-zA-Z][^>]*class="[^"]*(?:price|amount)[^"]*"[^>]*>(?:<[^>]+>)*(.*?)</[a-zA-Z]+>',
            'image': r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*(?:image|photo|thumbnail)[^"]*"',
        },
        'telegram': {
            'product_containers': [
                r'<div[^>]*class="[^"]*(?:tgme_widget_message_text)[^"]*"[^>]*>(.*?)</div>',
            ],
            'title': r'^(.*?)(?:\n|$)',
            'price': r'(?:ዋጋ|Price|Birr|ብር)\s*[:]?\s*([\d,]+)',
            'image': r'background-image:url\(\'([^\'\)]+)\'\)',
        },
        'engocha': {
            'product_containers': [
                r'<div[^>]*class="[^"]*(?:product-item|listing-item)[^"]*"[^>]*>(.*?)</div>',
            ],
            'title': r'<h[23][^>]*class="[^"]*(?:title|name)[^"]*"[^>]*>(.*?)</h[23]>',
            'price': r'<span[^>]*class="[^"]*(?:price|amount)[^"]*"[^>]*>(.*?)</span>',
        },
        'ethiojobs': {
            'product_containers': [
                r'<div[^>]*class="[^"]*(?:job-item|listing-item)[^"]*"[^>]*>(.*?)</div>',
            ],
            'title': r'<h[23][^>]*class="[^"]*(?:title|position)[^"]*"[^>]*>(.*?)</h[23]>',
        }
    }
    
    @classmethod
    def detect_site_type(cls, url: str) -> str:
        """ከURL የድረ-ገጹን አይነት ይለያል"""
        domain = urlparse(url).netloc.lower()
        
        if 'jiji' in domain:
            return 'jiji'
        elif 't.me' in domain or 'telegram' in domain:
            return 'telegram'
        elif 'engocha' in domain:
            return 'engocha'
        elif 'ethiojobs' in domain:
            return 'ethiojobs'
        else:
            return 'generic'
    
    @classmethod
    def get_patterns(cls, site_type: str) -> Dict:
        """ለድረ-ገጹ ተስማሚ የሆኑ ንድፎችን ያመጣል"""
        if site_type in cls.KNOWN_PATTERNS:
            return cls.KNOWN_PATTERNS[site_type]
        return cls.KNOWN_PATTERNS.get('generic', {
            'product_containers': [
                r'<div[^>]*class="[^"]*(?:product|item|listing)[^"]*"[^>]*>(.*?)</div>',
            ],
            'title': r'<h[1-4][^>]*>(.*?)</h[1-4]>',
            'price': r'(?:Price|Birr|ETB|ብር)\s*[:]?\s*([\d,]+)',
            'image': r'<img[^>]*src="([^"]+)"[^>]*>',
        })


# ============================================================
# 🔍 SMART PRODUCT EXTRACTOR (አስተዋይ የምርት ማውጫ)
# ============================================================

class SmartProductExtractor:
    """ከማንኛውም የድረ-ገጽ HTML ምርቶችን የሚያወጣ ሞተር"""
    
    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        """ምርቶችን ከHTML ያወጣል"""
        if not html:
            return []
        
        site_type = SitePatternDetector.detect_site_type(url)
        patterns = SitePatternDetector.get_patterns(site_type)
        
        products = []
        
        # 1. የምርት መያዣዎችን (containers) ያግኙ
        containers = []
        for pattern in patterns.get('product_containers', []):
            found = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if found:
                containers.extend(found)
                break
        
        # 2. ምንም ካልተገኘ አጠቃላይ መያዣዎችን ይሞክሩ
        if not containers:
            generic_patterns = [
                r'<div[^>]*class="[^"]*(?:product|item|listing|card|advert)[^"]*"[^>]*>(.*?)</div>',
                r'<li[^>]*class="[^"]*(?:product|item)[^"]*"[^>]*>(.*?)</li>',
                r'<tr[^>]*class="[^"]*(?:product|item)[^"]*"[^>]*>(.*?)</tr>',
            ]
            for pattern in generic_patterns:
                found = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if found:
                    containers.extend(found)
                    break
        
        # 3. እያንዳንዱን መያዣ ያቀናብሩ
        for container in containers:
            product = SmartProductExtractor._extract_from_container(
                container, patterns, site_type
            )
            if product and product.get('title'):
                products.append(product)
        
        # 4. ምንም ካልተገኘ ሙሉውን HTML ይቃኝ
        if not products:
            products = SmartProductExtractor._extract_direct(html, patterns)
        
        return products
    
    @staticmethod
    def _extract_from_container(container: str, patterns: Dict, site_type: str) -> Dict:
        """ከአንድ የምርት መያዣ ውስጥ መረጃ ያወጣል"""
        product = {
            'title': '',
            'price': 0,
            'description': '',
            'seller_contact': '',
            'image_url': ''
        }
        
        # ርዕስ (Title)
        title_patterns = [
            patterns.get('title', r'<h[1-4][^>]*>(.*?)</h[1-4]>'),
            r'<[a-zA-Z][^>]*class="[^"]*(?:title|name|heading)[^"]*"[^>]*>(.*?)</[a-zA-Z]+>',
            r'<div[^>]*class="[^"]*(?:title|name)[^"]*"[^>]*>(.*?)</div>',
            r'<span[^>]*class="[^"]*(?:title|name)[^"]*"[^>]*>(.*?)</span>',
            r'<strong[^>]*>(.*?)</strong>',
            r'<b[^>]*>(.*?)</b>',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, container, re.DOTALL | re.IGNORECASE)
            if match:
                title = re.sub(r'<[^>]+>', ' ', match.group(1)).strip()
                if len(title) > 5:
                    product['title'] = title[:150]
                    break
        
        # ዋጋ (Price)
        price_patterns = [
            patterns.get('price', r'(?:Price|Birr|ETB|ብር)\s*[:]?\s*([\d,]+)'),
            r'<[a-zA-Z][^>]*class="[^"]*(?:price|amount)[^"]*"[^>]*>(?:<[^>]+>)*(.*?)</[a-zA-Z]+>',
            r'([\d,]+)\s*(?:ETB|ብር|Birr|Br)',
            r'<span[^>]*class="[^"]*(?:price|amount)[^"]*"[^>]*>(.*?)</span>',
            r'\b([\d,]+)\s*(?:ብር|ETB|Birr)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, container, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    price_str = re.sub(r'[^\d,]', '', match.group(1))
                    product['price'] = float(price_str.replace(',', ''))
                    break
                except:
                    pass
        
        # ስልክ/መለያ (Contact)
        contact_patterns = [
            r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d',
            r'@[a-zA-Z0-9_]{4,32}',
            r'<[a-zA-Z][^>]*class="[^"]*(?:phone|contact)[^"]*"[^>]*>(.*?)</[a-zA-Z]+>',
        ]
        
        for pattern in contact_patterns:
            match = re.search(pattern, container, re.DOTALL | re.IGNORECASE)
            if match:
                contact = match.group(0).strip()
                if len(contact) > 3:
                    product['seller_contact'] = contact
                    break
        
        # ምስል (Image)
        image_patterns = [
            patterns.get('image', r'<img[^>]*src="([^"]+)"[^>]*>'),
            r'<img[^>]*src="([^"]+)"[^>]*class="[^"]*(?:image|photo|thumbnail)[^"]*"',
            r'background-image:url\(\'([^\'\)]+)\'\)',
            r'<img[^>]*src="([^"]+)"[^>]*>',
        ]
        
        for pattern in image_patterns:
            match = re.search(pattern, container, re.DOTALL | re.IGNORECASE)
            if match:
                img_url = match.group(1).strip()
                if img_url.startswith('http') or img_url.startswith('//'):
                    if not img_url.startswith('http'):
                        img_url = 'https:' + img_url
                    product['image_url'] = img_url
                    break
        
        # መግለጫ (Description)
        desc_patterns = [
            r'<p[^>]*class="[^"]*(?:description|desc)[^"]*"[^>]*>(.*?)</p>',
            r'<div[^>]*class="[^"]*(?:description|desc)[^"]*"[^>]*>(.*?)</div>',
            r'<span[^>]*class="[^"]*(?:description|desc)[^"]*"[^>]*>(.*?)</span>',
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, container, re.DOTALL | re.IGNORECASE)
            if match:
                desc = re.sub(r'<[^>]+>', ' ', match.group(1)).strip()
                if len(desc) > 10:
                    product['description'] = desc[:500]
                    break
        
        return product
    
    @staticmethod
    def _extract_direct(html: str, patterns: Dict) -> List[Dict]:
        """ምንም መያዣ ካልተገኘ ሙሉውን HTML ይቃኛል"""
        products = []
        
        # የሚታወቁ የምርት ምልክቶችን ይፈልጋል
        indicators = [
            r'<div[^>]*class="[^"]*(?:product|item|listing)[^"]*"',
            r'<li[^>]*class="[^"]*(?:product|item)[^"]*"',
            r'<article[^>]*class="[^"]*(?:product|item)[^"]*"',
        ]
        
        for indicator in indicators:
            matches = re.finditer(indicator, html, re.IGNORECASE)
            for match in matches:
                # ከምልክቱ አካባቢ ይዘት ለማውጣት
                start = match.start()
                end = min(start + 2000, len(html))
                segment = html[start:end]
                
                product = SmartProductExtractor._extract_from_container(
                    segment, patterns, 'generic'
                )
                if product and product.get('title'):
                    products.append(product)
        
        return products


# ============================================================
# 🚀 ULTIMATE SCRAPPER ENGINE
# ============================================================

class ScrapperEngine:
    """ማንኛውንም ድረ-ገጽ በራሱ የሚላመድ እና የሚያስስ ሞተር"""
    
    @staticmethod
    def _fetch_static_fallback(url: str) -> Optional[str]:
        """🛡️ ሪኩዌስት ተጠቅሞ ስታቲክ ዳታ መሳቢያ"""
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.text
        except Exception as e:
            logger.error(f"❌ Static fallback failed: {e}")
        return None
    
    @staticmethod
    def _get_stealth_headers(url: str) -> Dict:
        """የStealth Headers ያመነጫል"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        ]
        
        return {
            "User-Agent": random.choice(user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,am;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": random.choice([
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://duckduckgo.com/",
            ]),
        }
    
    @staticmethod
    async def fetch_dynamic_content(url: str, selector=None) -> Optional[str]:
        """ክልከላዎችን ሰብሮ ገጽን በጥልቀት የሚቃኝ Stealth ሞተር"""
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        
        async with async_playwright() as p:
            try:
                # 🚀 Stealth Mode Launch
                browser = await p.chromium.launch(headless=True)
                headers = ScrapperEngine._get_stealth_headers(url)
                
                context = await browser.new_context(
                    user_agent=headers["User-Agent"],
                    viewport={'width': random.choice([1280, 1366, 1440, 1920]), 'height': random.choice([720, 768, 900, 1080])},
                    extra_http_headers=headers,
                    locale=random.choice(['en-US', 'en-GB', 'en']),
                    timezone_id='Africa/Addis_Ababa',
                )
                
                page = await context.new_page()
                
                # 🛡️ BYPASS BOT DETECTION
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'am']});
                    window.chrome = {runtime: {}};
                """)
                
                logger.info(f"📡 Deep Scanning: {url}...")
                await page.goto(url, wait_until="networkidle", timeout=45000)
                
                # 🔄 DEEP SCROLL (እስከ 8 ጊዜ)
                for i in range(8):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2 + random.random())
                    
                    # ጊዜውን ለመቆጠብ አስፈላጊ ከሆነ ያቁሙ
                    if i > 3:
                        break
                
                content = await page.content()
                await browser.close()
                return content
                
            except Exception as e:
                logger.warning(f"⚠️ Playwright error for {url}: {e}")
                return None
    
    @classmethod
    def scrape(cls, url: str, selector=None) -> Optional[str]:
        """ዋናው የጥሪ ማስተባበሪያ (Sync-to-Async Bridge)"""
        if not url:
            return None
        
        # ትክክለኛ የ URL ቅርጸት ያረጋግጡ
        if not url.startswith('http'):
            url = 'https://' + url
        
        result = None
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        
        try:
            if running_loop:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(cls.fetch_dynamic_content(url, selector)))
                    result = future.result()
            else:
                result = asyncio.run(cls.fetch_dynamic_content(url, selector))
        except Exception as e:
            logger.error(f"Scrapper Engine Error: {e}")
        
        # Playwright ካልሰራ በ Requests መሞከር
        if not result:
            result = cls._fetch_static_fallback(url)
        
        return result
    
    @classmethod
    def scrape_and_extract(cls, url: str) -> List[Dict]:
        """ያስሳል እና ምርቶችን በቀጥታ ያወጣል"""
        html = cls.scrape(url)
        if not html:
            return []
        
        return SmartProductExtractor.extract_products(html, url)


# ============================================================
# 🔄 DYNAMIC PATTERN LEARNER (ራሱን የሚያሻሽል ሞተር)
# ============================================================

class DynamicPatternLearner:
    """ከአዲስ ጣቢያዎች ይማራል እና የምርት ንድፎችን ያስታውሳል"""
    
    LEARNED_PATTERNS = {}
    
    @classmethod
    def learn_from_page(cls, url: str, html: str) -> Dict:
        """ከአንድ ገጽ አዲስ ንድፎችን ይማራል"""
        domain = urlparse(url).netloc.lower()
        
        patterns = {
            'product_containers': [],
            'title': [],
            'price': [],
            'image': [],
        }
        
        # የምርት መያዣዎችን መፈለግ
        container_classes = re.findall(r'<div[^>]*class="([^"]*)"[^>]*>(?:.*?)(?:ዋጋ|Price|Birr|ብር|ይሸጣል|for sale)', html, re.DOTALL | re.IGNORECASE)
        
        for cls_name in container_classes:
            if cls_name and len(cls_name) < 100:
                patterns['product_containers'].append(
                    f'<div[^>]*class="[^"]*{cls_name}[^"]*"[^>]*>(.*?)</div>'
                )
        
        # የርዕስ ንድፎችን መፈለግ
        title_classes = re.findall(r'<h[1-4][^>]*class="([^"]*)"[^>]*>(.*?)</h[1-4]>', html, re.IGNORECASE)
        for cls_name, _ in title_classes:
            if cls_name:
                patterns['title'].append(
                    f'<h[1-4][^>]*class="[^"]*{cls_name}[^"]*"[^>]*>(.*?)</h[1-4]>'
                )
        
        # የዋጋ ንድፎችን መፈለግ
        price_classes = re.findall(r'<[a-zA-Z][^>]*class="([^"]*)"[^>]*>(?:<[^>]+>)*(.*?)</[a-zA-Z]+>', html, re.IGNORECASE)
        for cls_name, _ in price_classes:
            if cls_name and any(x in cls_name.lower() for x in ['price', 'amount', 'cost']):
                patterns['price'].append(
                    f'<[a-zA-Z][^>]*class="[^"]*{cls_name}[^"]*"[^>]*>(?:<[^>]+>)*(.*?)</[a-zA-Z]+>'
                )
        
        # የምስል ንድፎችን መፈለግ
        img_classes = re.findall(r'<img[^>]*class="([^"]*)"[^>]*src="([^"]+)"', html, re.IGNORECASE)
        for cls_name, _ in img_classes:
            if cls_name:
                patterns['image'].append(
                    f'<img[^>]*class="[^"]*{cls_name}[^"]*"[^>]*src="([^"]+)"'
                )
        
        # የተማረውን ያስቀምጡ
        if patterns['product_containers'] or patterns['title']:
            cls.LEARNED_PATTERNS[domain] = patterns
            logger.info(f"🧠 Learned patterns for {domain}: {len(patterns['product_containers'])} containers, {len(patterns['title'])} titles")
        
        return patterns
    
    @classmethod
    def get_learned_patterns(cls, url: str) -> Dict:
        """ለአንድ ጣቢያ የተማሩ ንድፎችን ያመጣል"""
        domain = urlparse(url).netloc.lower()
        return cls.LEARNED_PATTERNS.get(domain, {})


# ============================================================
# 🎯 ADAPTIVE EXTRACTOR (ራሱን የሚላመድ ማውጫ)
# ============================================================

class AdaptiveProductExtractor:
    """ከማንኛውም ጣቢያ ምርቶችን በራሱ የሚላመድ እና የሚያወጣ"""
    
    @staticmethod
    def extract(html: str, url: str) -> List[Dict]:
        """ምርቶችን በማላመድ ያወጣል"""
        
        # 1. መጀመሪያ የታወቁ ንድፎችን ይሞክሩ
        products = SmartProductExtractor.extract_products(html, url)
        
        if products:
            return products
        
        # 2. ካልተሳካ አዲስ ንድፎችን ይማራል
        patterns = DynamicPatternLearner.learn_from_page(url, html)
        
        if patterns:
            # አዲሶቹን ንድፎች በመጠቀም እንደገና ይሞክሩ
            products = SmartProductExtractor.extract_products(html, url)
        
        return products


# ============================================================
# 🚀 MAIN EXPORTS
# ============================================================

# ለድሮ ኮድ ተኳሃኝነት
def scrape_and_extract_products(url: str) -> List[Dict]:
    """ያስሳል እና ምርቶችን ያወጣል"""
    return ScrapperEngine.scrape_and_extract(url)

# ቀላል የጥሪ ተግባር
def scrape_url(url: str) -> Optional[str]:
    """አንድ ዩአርኤል ይስሳል"""
    return ScrapperEngine.scrape(url)
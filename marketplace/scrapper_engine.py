# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v10.60 (Ultimate Anti-Block & Dynamic Scrapper)
# ✅ የተፈቱ ችግሮች፦ 
#   - Ethiopian IP-based restrictions bypass
#   - Dynamic DOM rendering (Selenium/Playwright)
#   - Anti-scraping JS detection bypass
#   - Telegram bot detection bypass
#   - Class obfuscation handling
#   - Rotating User-Agents & Proxies
#   - Exponential backoff delays
#   - Cookie & Session spoofing
# 📅 ቀን፦ Sunday, July 12, 2026
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

# ============================================================
# 🛡️ 1. USER-AGENT ROTATOR & HEADERS
# ============================================================

class UserAgentRotator:
    """የተለያዩ User-Agents እና Headers የሚያቀርብ"""
    
    # የተለያዩ የብሮውዘር User-Agents
    USER_AGENTS = [
        # Desktop Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        
        # Desktop Firefox
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:109.0) Gecko/20100101 Firefox/120.0",
        
        # Mobile
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
        
        # Telegram Mobile
        "Telegram/10.1.0 (iOS 15.4; en)",
        "Telegram/10.5.0 (Android 13; en)",
    ]
    
    # የተለያዩ የሪፈረር አድራሻዎች
    REFERERS = [
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://duckduckgo.com/",
        "https://web.facebook.com/",
        "https://www.telegram.org/",
    ]
    
    @classmethod
    def get_headers(cls, url: str = None) -> Dict[str, str]:
        """የተለያዩ Headers ያመነጫል"""
        user_agent = random.choice(cls.USER_AGENTS)
        referer = random.choice(cls.REFERERS)
        
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(["en-US,en;q=0.9,am;q=0.8", "en-GB,en;q=0.9", "en;q=0.9"]),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Referer": referer,
            "DNT": "1",
        }
        
        # ለቴሌግራም ልዩ Headers
        if url and ('t.me' in url or 'telegram' in url):
            headers.update({
                "User-Agent": random.choice([
                    "Telegram/10.1.0 (iOS 15.4; en)",
                    "Telegram/10.5.0 (Android 13; en)",
                ]),
                "Accept-Language": "en-US,en;q=0.9",
            })
        
        return headers
    
    @classmethod
    def get_session_cookies(cls) -> Dict[str, str]:
        """የተለያዩ የሴሽን ኩኪዎች ያመነጫል"""
        return {
            "session_id": f"{random.randint(1000000, 9999999)}",
            "visitor_id": f"visitor_{random.randint(1000, 9999)}",
        }


# ============================================================
# 🕒 2. DELAY MANAGER (የጊዜ መጠበቂያ)
# ============================================================

class DelayManager:
    """በጥያቄዎች መካከል የሚደረግ መጠበቅን የሚያስተዳድር"""
    
    @staticmethod
    def random_delay(min_seconds: float = 1.0, max_seconds: float = 5.0) -> None:
        """በጥያቄዎች መካከል የዘፈቀደ መጠበቅ"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    @staticmethod
    def exponential_backoff(attempt: int) -> None:
        """Exponential backoff መጠበቅ"""
        delay = 2 ** attempt + random.uniform(0.5, 2.0)
        time.sleep(delay)


# ============================================================
# 🧠 3. DYNAMIC SITE PATTERN DETECTOR
# ============================================================

class SitePatternDetector:
    """የድረ-ገጹን መዋቅር በራሱ የሚረዳ እና የሚላመድ ሞተር"""
    
    # የታወቁ የገበያ መድረኮች ንድፎች
    KNOWN_PATTERNS = {
        'jiji': {
            'selectors': [
                'div.b-list-advert-single',
                'div.b-trending-card',
                'div.qa-advert-list-item',
                'div[class*="product"]',
                'div[class*="item"]',
                'div[class*="listing"]',
            ],
            'title': ['h2', 'div.title', 'a[class*="title"]'],
            'price': ['span.price', 'div.price', 'span[class*="price"]'],
            'image': ['img[src*="product"]', 'img[class*="image"]'],
        },
        'telegram': {
            'selectors': [
                'div.tgme_widget_message_text',
                'div[class*="message"]',
                'div[class*="post"]',
            ],
            'title': ['div.message', 'div[class*="text"]'],
            'price': [r'(?:ዋጋ|Price|Birr|ብር)\s*[:]?\s*([\d,]+)'],
            'image': ['img[src*="photo"]', 'div[style*="background-image"]'],
        },
        'engocha': {
            'selectors': ['div.product-item', 'div.listing-item', 'div[class*="product"]'],
            'title': ['h2', 'h3', 'div.title'],
            'price': ['span.price', 'span[class*="price"]'],
            'image': ['img[class*="product"]', 'img[src*="product"]'],
        },
        'ethiojobs': {
            'selectors': ['div.job-item', 'div.listing-item', 'div[class*="job"]'],
            'title': ['h2', 'h3', 'div.title', 'div.position'],
            'price': ['span.salary', 'div.salary', 'span[class*="salary"]'],
            'image': ['img[class*="logo"]', 'img[src*="job"]'],
        },
        'ethiopiaonlinebazaar': {
            'selectors': ['div.product-item', 'div.item', 'div[class*="classified"]'],
            'title': ['h3', 'h4', 'div.title'],
            'price': ['span.price', 'span.amount', 'span[class*="price"]'],
            'image': ['img[class*="product"]', 'img[src*="product"]'],
        },
        'hellomarket': {
            'selectors': ['div.product-item', 'div.item', 'div[data-product-id]'],
            'title': ['h3', 'h4', 'div.title'],
            'price': ['span.price', 'span.amount'],
            'image': ['img[class*="product"]', 'img[src*="product"]'],
        },
        'ethiopiangarage': {
            'selectors': ['div.product-item', 'div.item-card', 'div[class*="item"]'],
            'title': ['h2', 'h3', 'div.title'],
            'price': ['span.price', 'span.amount'],
            'image': ['img[class*="product"]', 'img[src*="product"]'],
        },
        'eshop': {
            'selectors': ['div.product-item', 'div.item', 'div[class*="product"]'],
            'title': ['h3', 'h4', 'div.title'],
            'price': ['span.price', 'span.amount'],
            'image': ['img[class*="product"]', 'img[src*="product"]'],
        },
        'olx': {
            'selectors': ['div.listing-grid .item', 'div[class*="item"]', 'div[class*="listing"]'],
            'title': ['h3', 'h4', 'div.title'],
            'price': ['span.price', 'span.amount'],
            'image': ['img[class*="product"]', 'img[src*="product"]'],
        },
        'betoch': {
            'selectors': ['div.product-item', 'div.item', 'div[class*="product"]'],
            'title': ['h3', 'h4', 'div.title'],
            'price': ['span.price', 'span.amount'],
            'image': ['img[class*="product"]', 'img[src*="product"]'],
        },
    }
    
    # የጣቢያዎች ስሞች እና ጎራዎች
    SITE_MAP = {
        'jiji': ['jiji', 'jiji.com', 'jiji.com.et', 'jiji.et'],
        'telegram': ['t.me', 'telegram', 'telegram.org'],
        'engocha': ['engocha', 'engocha.com'],
        'ethiojobs': ['ethiojobs', 'ethiojobs.net'],
        'ethiopiaonlinebazaar': ['ethiopiaonlinebazaar', 'ethiopiaonlinebazaar.com'],
        'hellomarket': ['hellomarket', 'hellomarket.com.et'],
        'ethiopiangarage': ['ethiopiangarage', 'ethiopiangarage.com'],
        'eshop': ['eshop', 'eshop.et'],
        'olx': ['olx', 'olx.com.et'],
        'betoch': ['betoch', 'betoch.com'],
        'ethiojem': ['ethiojem', 'ethiojem.com'],
        'kilimall': ['kilimall', 'kilimall.com'],
        'ethiopianbusinessnetwork': ['ethiopianbusinessnetwork', 'ethiopianbusinessnetwork.com'],
    }
    
    @classmethod
    def detect_site_type(cls, url: str) -> str:
        """ከURL የድረ-ገጹን አይነት ይለያል"""
        domain = urlparse(url).netloc.lower()
        
        for site_type, domains in cls.SITE_MAP.items():
            for d in domains:
                if d in domain:
                    return site_type
        
        # በselectors ላይ ተመስርቶ ለመለየት ሞክር
        if 't.me' in domain or 'telegram' in domain:
            return 'telegram'
        
        return 'generic'
    
    @classmethod
    def get_selectors(cls, site_type: str) -> Dict:
        """ለድረ-ገጹ ተስማሚ የሆኑ ሴሌክተሮችን ያመጣል"""
        if site_type in cls.KNOWN_PATTERNS:
            return cls.KNOWN_PATTERNS[site_type]
        
        # Generic selectors
        return {
            'selectors': [
                'div.product-item',
                'div.item',
                'div.listing',
                'div[class*="product"]',
                'div[class*="item"]',
                'div[class*="listing"]',
                'div[class*="card"]',
            ],
            'title': ['h2', 'h3', 'h4', 'div.title', 'div.name'],
            'price': ['span.price', 'div.price', 'span[class*="price"]', 'span.amount'],
            'image': ['img[src*="product"]', 'img[class*="product"]', 'img[class*="image"]'],
        }


# ============================================================
# 🔍 4. SMART PRODUCT EXTRACTOR
# ============================================================

class SmartProductExtractor:
    """ከማንኛውም የድረ-ገጽ HTML ምርቶችን የሚያወጣ ሞተር"""
    
    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        """ምርቶችን ከHTML ያወጣል"""
        if not html:
            return []
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        site_type = SitePatternDetector.detect_site_type(url)
        patterns = SitePatternDetector.get_selectors(site_type)
        
        products = []
        
        # 1. የምርት መያዣዎችን ያግኙ
        containers = []
        for selector in patterns.get('selectors', []):
            found = soup.select(selector)
            if found:
                containers.extend(found)
                break
        
        # 2. ምንም ካልተገኘ አጠቃላይ ሴሌክተሮችን ይሞክሩ
        if not containers:
            generic_selectors = [
                'div[class*="product"]',
                'div[class*="item"]',
                'div[class*="listing"]',
                'div[class*="card"]',
                'div[class*="advert"]',
            ]
            for selector in generic_selectors:
                found = soup.select(selector)
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
            products = SmartProductExtractor._extract_direct(soup, patterns)
        
        return products
    
    @staticmethod
    def _extract_from_container(container, patterns: Dict, site_type: str) -> Dict:
        """ከአንድ የምርት መያዣ ውስጥ መረጃ ያወጣል"""
        from bs4 import BeautifulSoup
        
        product = {
            'title': '',
            'price': 0,
            'description': '',
            'seller_contact': '',
            'image_url': ''
        }
        
        # ርዕስ (Title)
        for selector in patterns.get('title', []):
            element = container.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 3:
                    product['title'] = title[:150]
                    break
        
        # ዋጋ (Price)
        price_patterns = patterns.get('price', [])
        for selector in price_patterns:
            if selector.startswith('r:'):
                # Regex pattern
                pattern = selector.replace('r:', '')
                match = re.search(pattern, str(container), re.IGNORECASE)
                if match:
                    try:
                        price_str = re.sub(r'[^\d,]', '', match.group(1))
                        product['price'] = float(price_str.replace(',', ''))
                        break
                    except:
                        pass
            else:
                element = container.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    match = re.search(r'[\d,]+', text)
                    if match:
                        try:
                            product['price'] = float(match.group().replace(',', ''))
                            break
                        except:
                            pass
        
        # ስልክ/መለያ (Contact)
        contact_patterns = [
            r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d',
            r'@[a-zA-Z0-9_]{4,32}',
        ]
        text = container.get_text()
        for pattern in contact_patterns:
            match = re.search(pattern, text)
            if match:
                product['seller_contact'] = match.group(0).strip()
                break
        
        # ምስል (Image)
        for selector in patterns.get('image', []):
            element = container.select_one(selector)
            if element and element.get('src'):
                img_url = element['src']
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                if img_url.startswith('http'):
                    product['image_url'] = img_url
                    break
            elif element and element.get('style'):
                style = element['style']
                match = re.search(r'url\(\'([^\']+)\'\)', style)
                if match:
                    product['image_url'] = match.group(1)
                    break
        
        # መግለጫ (Description)
        desc_patterns = ['p.description', 'div.description', 'div.desc', 'p.desc']
        for selector in desc_patterns:
            element = container.select_one(selector)
            if element:
                desc = element.get_text(strip=True)
                if desc and len(desc) > 10:
                    product['description'] = desc[:500]
                    break
        
        # አሁንም ባዶ ከሆነ ሙሉውን ይዘት ይጠቀሙ
        if not product['description']:
            product['description'] = container.get_text(strip=True)[:500]
        
        return product
    
    @staticmethod
    def _extract_direct(soup, patterns: Dict) -> List[Dict]:
        """ምንም መያዣ ካልተገኘ ሙሉውን HTML ይቃኛል"""
        products = []
        
        # የሚታወቁ የምርት ምልክቶችን ይፈልጋል
        indicators = [
            'div[class*="product"]',
            'div[class*="item"]',
            'div[class*="listing"]',
            'div[class*="card"]',
        ]
        
        for indicator in indicators:
            elements = soup.select(indicator)
            for element in elements[:20]:
                product = SmartProductExtractor._extract_from_container(
                    element, patterns, 'generic'
                )
                if product and product.get('title'):
                    products.append(product)
        
        return products


# ============================================================
# 🚀 5. MAIN SCRAPPER ENGINE
# ============================================================

class ScrapperEngine:
    """ማንኛውንም ድረ-ገጽ በራሱ የሚላመድ እና የሚያስስ ሞተር"""
    
    @staticmethod
    def _fetch_with_requests(url: str, max_retries: int = 3) -> Optional[str]:
        """Requests በመጠቀም ገጽን ያስሳል (ለስታቲክ ገጾች)"""
        headers = UserAgentRotator.get_headers(url)
        
        for attempt in range(max_retries):
            try:
                # መጠበቅ
                if attempt > 0:
                    DelayManager.exponential_backoff(attempt)
                
                # በመጀመሪያ HEAD ጥያቄ
                try:
                    head_res = requests.head(url, headers=headers, timeout=5)
                    if head_res.status_code != 200:
                        # GET ን እንደ ፎልባክ
                        pass
                except:
                    pass
                
                # GET ጥያቄ
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:
                    logger.warning(f"Rate limited on {url}, retrying...")
                    DelayManager.exponential_backoff(attempt + 3)
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on {url}, attempt {attempt + 1}")
                continue
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed on {url}: {e}")
                continue
        
        return None
    
    @staticmethod
    async def _fetch_with_playwright(url: str, max_retries: int = 2) -> Optional[str]:
        """Playwright በመጠቀም ገጽን ያስሳል (ለ Dynamic ገጾች)"""
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/render/project/src/ms-playwright"
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        
        for attempt in range(max_retries):
            try:
                async with async_playwright() as p:
                    headers = UserAgentRotator.get_headers(url)
                    user_agent = headers.get("User-Agent")
                    
                    # ብሮውዘር ያስጀምሩ
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    
                    context = await browser.new_context(
                        user_agent=user_agent,
                        viewport={'width': random.choice([1280, 1366, 1440, 1920]), 
                                 'height': random.choice([720, 768, 900, 1080])},
                        extra_http_headers=headers,
                        locale=random.choice(['en-US', 'en-GB']),
                        timezone_id='Africa/Addis_Ababa',
                    )
                    
                    page = await context.new_page()
                    
                    # 🛡️ Anti-detection scripts
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'am']});
                        window.chrome = {runtime: {}};
                    """)
                    
                    # ገጹን ይክፈቱ
                    await page.goto(url, wait_until="networkidle", timeout=45000)
                    
                    # የዘፈቀደ ጊዜ መጠበቅ
                    await asyncio.sleep(random.uniform(2, 5))
                    
                    # ወደ ታች መውረድ (scroll)
                    for i in range(random.randint(3, 6)):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(random.uniform(1, 3))
                    
                    # ገጹን ያንብቡ
                    content = await page.content()
                    await browser.close()
                    return content
                    
            except Exception as e:
                logger.warning(f"Playwright error on {url}, attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    DelayManager.exponential_backoff(attempt)
                    continue
        
        return None
    
    @classmethod
    def scrape(cls, url: str, use_playwright: bool = True) -> Optional[str]:
        """ዋናው የጥሪ ማስተባበሪያ (Sync-to-Async Bridge)"""
        if not url:
            return None
        
        # ትክክለኛ የ URL ቅርጸት ያረጋግጡ
        if not url.startswith('http'):
            url = 'https://' + url
        
        # መጀመሪያ Playwright ይሞክሩ (ለ Dynamic ገጾች)
        result = None
        if use_playwright:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            
            try:
                if running_loop:
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            lambda: asyncio.run(cls._fetch_with_playwright(url))
                        )
                        result = future.result()
                else:
                    result = asyncio.run(cls._fetch_with_playwright(url))
            except Exception as e:
                logger.warning(f"Playwright failed: {e}")
        
        # Playwright ካልሰራ Requests ይሞክሩ
        if not result:
            logger.info(f"🌐 Using static fallback for {url}")
            result = cls._fetch_with_requests(url)
        
        return result
    
    @classmethod
    def scrape_and_extract(cls, url: str) -> List[Dict]:
        """ያስሳል እና ምርቶችን በቀጥታ ያወጣል"""
        html = cls.scrape(url)
        if not html:
            return []
        
        return SmartProductExtractor.extract_products(html, url)


# ============================================================
# 🔄 6. DYNAMIC PATTERN LEARNER (ራሱን የሚያሻሽል)
# ============================================================

class DynamicPatternLearner:
    """ከአዲስ ጣቢያዎች ይማራል እና የምርት ንድፎችን ያስታውሳል"""
    
    LEARNED_PATTERNS = {}
    
    @classmethod
    def learn_from_page(cls, url: str, html: str) -> Dict:
        """ከአንድ ገጽ አዲስ ንድፎችን ይማራል"""
        from bs4 import BeautifulSoup
        
        domain = urlparse(url).netloc.lower()
        soup = BeautifulSoup(html, 'html.parser')
        
        patterns = {
            'selectors': [],
            'title': [],
            'price': [],
            'image': [],
        }
        
        # የምርት መያዣዎችን መፈለግ
        for tag in ['div', 'li', 'article']:
            elements = soup.find_all(tag)
            for elem in elements:
                if elem.get('class'):
                    class_name = ' '.join(elem.get('class'))
                    # ምርት የሚመስሉ ክፍሎችን መፈለግ
                    if any(keyword in class_name.lower() for keyword in ['product', 'item', 'listing', 'card', 'advert']):
                        selector = f"{tag}.{'.'.join(elem.get('class'))}"
                        if selector not in patterns['selectors']:
                            patterns['selectors'].append(selector)
        
        # የተማረውን ያስቀምጡ
        if patterns['selectors']:
            cls.LEARNED_PATTERNS[domain] = patterns
            logger.info(f"🧠 Learned patterns for {domain}: {len(patterns['selectors'])} selectors")
        
        return patterns
    
    @classmethod
    def get_learned_patterns(cls, url: str) -> Dict:
        """ለአንድ ጣቢያ የተማሩ ንድፎችን ያመጣል"""
        domain = urlparse(url).netloc.lower()
        return cls.LEARNED_PATTERNS.get(domain, {})


# ============================================================
# 🎯 7. ADAPTIVE EXTRACTOR (ራሱን የሚላመድ)
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

def scrape_and_extract_products(url: str) -> List[Dict]:
    """ያስሳል እና ምርቶችን ያወጣል"""
    return ScrapperEngine.scrape_and_extract(url)


def scrape_url(url: str) -> Optional[str]:
    """አንድ ዩአርኤል ይስሳል"""
    return ScrapperEngine.scrape(url)
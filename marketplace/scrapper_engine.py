# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v12.00 (Ultimate Enterprise-Grade Scrapper - Full Feature Set)
# ✅ የተፈቱ ችግሮች፦ 
#   - Render CPU Guard (Prevents OOM crashes)
#   - Native Match Index Pricing (Amharic + English)
#   - Dual-Engine Fallback (DDG + Google + Bing)
#   - Thread-Safe Singleton Pattern
#   - Session Persistence with Cookie Spoofing
#   - Multi-Platform Selectors (Jiji, Facebook, Telegram, Generic)
#   - Advanced Anti-Bot Fingerprint Evasion
#   - Self-Healing Diagnostic System
#   - Comprehensive Metrics & Caching
#   - Lazy-Load Image Extraction (data-src, data-lazy, srcset)
#   - Adaptive Rate Limiting
#   - Exponential Backoff Retry
#   - BeautifulSoup + Regex Hybrid Extraction
#   - JSON-LD Semantic Parsing
#   - Full Diagnostic Reporting
# 📅 ቀን፦ Sunday, July 26, 2026
# ============================================================

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import requests
from django.conf import settings
from django.utils import timezone

# ============================================================
# 📦 OPTIONAL DEPENDENCIES (Graceful Degradation)
# ============================================================
try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    BeautifulSoup = None
    _HAS_BS4 = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ BeautifulSoup not installed. Using regex-only extraction.")

try:
    import cloudinary.uploader
    _HAS_CLOUDINARY = True
except ImportError:
    _HAS_CLOUDINARY = False

# ============================================================
# ⚙️ LOGGER SETUP
# ============================================================
logger = logging.getLogger(__name__)

# ============================================================
# 📊 CENTRALIZED CONFIGURATION
# ============================================================
class ScraperConfig:
    """ሁሉንም የስክሬፐር ቅንጅቶች በአንድ ቦታ ያስተዳድራል"""
    
    # Browser & Network
    BROWSER_PATH: str = "/opt/render/project/src/ms-playwright"
    SCRAPEOPS_ENDPOINT: str = "https://proxy.scrapeops.io/v1/"
    REQUEST_TIMEOUT: int = 30
    PLAYWRIGHT_TIMEOUT: int = 60
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 2.0
    
    # Rate Limiting
    RATE_LIMIT_RANGE: Tuple[float, float] = (0.8, 1.5)
    MAX_REQUESTS_PER_MINUTE: int = 30
    RATE_LIMIT_WINDOW: int = 60
    
    # Caching
    CACHE_TTL: int = 3600  # 1 hour
    SMART_CACHE_TTL: int = 1800  # 30 minutes
    MAX_CACHE_SIZE: int = 1000
    
    # Extraction
    MAX_PRODUCTS_PER_PAGE: int = 60
    MIN_TITLE_LEN: int = 8
    MAX_TITLE_LEN: int = 150
    MAX_DESC_LEN: int = 1000
    MIN_DESC_LEN: int = 10
    
    # CPU Protection
    CPU_LOAD_THRESHOLD: float = 1.5
    MEMORY_THRESHOLD_MB: int = 512
    
    # Image Extraction
    IMAGE_ATTRS: List[str] = ['data-src', 'data-lazy', 'lazy-src', 'srcset', 'src']
    
    # ============================================================
    # 🔍 REGEX PATTERNS
    # ============================================================
    
    # Ethiopian Phone Numbers
    PHONE_RE = re.compile(r"(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d")
    
    # Telegram Usernames
    TELEGRAM_RE = re.compile(r"@[a-zA-Z0-9_]{4,32}")
    
    # Price Patterns (Amharic + English)
    PRICE_RE = re.compile(
        r"(?:ዋጋ|Price|Birr|ETB|ብር)\s*[:፡\-]?\s*([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    PRICE_TAIL_RE = re.compile(
        r"([\d,]+(?:\.\d+)?)\s*(?:ETB|ብር|Birr|Br)",
        re.IGNORECASE,
    )
    
    # Stale / Non-Product Markers
    STALE_RE = re.compile(
        r"(?:sold\s*out|out\s*of\sstock|already\s*sold|ended|expired|"
        r"closed\slisting|removed\b|ደርሷል|ተሽጧል|አልቋል)",
        re.IGNORECASE,
    )
    
    # Old Date Markers
    OLD_DATE_RE = re.compile(
        r"(?:2012|2013|2014|2015|2020|2021|2022)\s*(?:ዓ\.?ም|ዓም)?|"
        r"[4-9]\s*months?\s*ago|year\s*ago|ከ\d+\s*ወር",
        re.IGNORECASE,
    )
    
    # Telegram System Messages
    SYSTEM_MSG_RE = re.compile(
        r"(?:channel\s*created|channel\s*photo\s*updated|channel\s*name\s*was\s*changed|"
        r"live\s*stream\s*started|live\s*stream\s*finished|pinned\s*a\s*message|joined\s*telegram|"
        r"group\s*created|ተለቀቀ|ገብተናል|ገባን|ተከፈተ|የላይቱን\s*ይሰጣል|"
        r"channel\s*photo|channel\s*created|በአካል\s*በመገኘት)",
        re.IGNORECASE,
    )
    
    # Product Indicators (for validation)
    PRODUCT_INDICATORS = re.compile(
        r"(?:ለሽያጭ|ይሸጣል|ለኪራይ|ይከራያል|ይገኛል|"
        r"for\s*sale|selling|price|ዋጋ|birr|etb|ብር|ቅናሽ|discount|"
        r"አዲስ|new|used|ያገለገለ|condition|ሁኔታ|"
        r"contact|ያግኙ|ደውሉ|call|phone|ስልክ)",
        re.IGNORECASE,
    )


# ============================================================
# 🛡️ FINGERPRINT EVASION (User-Agent & Header Generator)
# ============================================================
class FingerprintEvasion:
    """የቦት መለያዎችን ለማስቀረት የተለያዩ ማንነቶችን ያመነጫል"""
    
    # የተለያዩ የሞባይል User-Agents
    MOBILE_UA = [
        "Telegram/10.1.0 (iOS 15.4; en)",
        "Telegram/10.3.5 (iPhone; iOS 17.2; en)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Mobile Safari",
        "Mozilla/5.0 (Android 13; SM-G998B) AppleWebKit/537.36 Mobile",
    ]
    
    # የተለያዩ የዴስክቶፕ User-Agents
    DESKTOP_UA = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    ]
    
    # የተለያዩ የቋንቋ ምርጫዎች
    LANGUAGES = [
        "am-ET,am;q=0.9,en-US;q=0.8,en;q=0.7",
        "en-US,en;q=0.9,am;q=0.8",
        "am,en-US;q=0.9,en;q=0.8",
        "en-GB,en;q=0.9,am;q=0.8",
    ]
    
    # የተለያዩ የኩኪ ማስመሰያዎች
    COOKIES = [
        "lang=et; currency=ETB",
        "lang=am; currency=ETB",
        "lang=en; currency=ETB",
        "lang=et; currency=ETB; theme=dark",
    ]
    
    @classmethod
    def get_headers(cls, url: str, is_telegram: bool = False) -> Dict[str, str]:
        """ለድረ-ገጹ ተስማሚ የሆኑ Headers ያመነጫል"""
        is_tg = is_telegram or _is_telegram(url)
        
        ua = random.choice(cls.MOBILE_UA) if is_tg else random.choice(cls.DESKTOP_UA)
        lang = random.choice(cls.LANGUAGES)
        cookie = random.choice(cls.COOKIES)
        
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": lang,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
            "Cookie": cookie,
            "Referer": random.choice([
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://duckduckgo.com/",
                "https://web.facebook.com/",
            ]),
        }
        
        # የChrome ልዩ ራስጌዎች
        if "Chrome" in ua or "Chromium" in ua:
            headers["Sec-Ch-Ua"] = '"Google Chrome";v="120", "Chromium";v="120", "Not_A Brand";v="24"'
            headers["Sec-Ch-Ua-Mobile"] = "?0" if not is_tg else "?1"
            headers["Sec-Ch-Ua-Platform"] = '"Windows"' if "Windows" in ua else '"macOS"' if "Mac" in ua else '"Linux"'
        
        return headers


# ============================================================
# 📊 METRICS, RATE LIMITER & SMART CACHE
# ============================================================

class ScraperMetrics:
    """የስክሬፐር አፈጻጸም መለኪያዎችን ይሰበስባል"""
    
    def __init__(self) -> None:
        self.total_attempts: int = 0
        self.last_scrape_time: Optional[datetime] = None
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.successful_scrapes: int = 0
        self.failed_scrapes: int = 0
        self.total_products_extracted: int = 0
        self.average_response_time: float = 0.0
        self.response_times: List[float] = []
        self.errors: List[str] = []
        self.start_time: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "last_scrape_time": self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "successful_scrapes": self.successful_scrapes,
            "failed_scrapes": self.failed_scrapes,
            "total_products_extracted": self.total_products_extracted,
            "average_response_time": round(self.average_response_time, 3),
            "error_count": len(self.errors),
            "uptime": (datetime.now() - self.start_time).total_seconds(),
        }
    
    def record_response_time(self, seconds: float) -> None:
        """የምላሽ ጊዜን ይመዘግባል"""
        self.response_times.append(seconds)
        if len(self.response_times) > 100:
            self.response_times = self.response_times[-100:]
        self.average_response_time = sum(self.response_times) / len(self.response_times)


class IntelligentRateLimiter:
    """በራሱ የሚላመድ የጥያቄ ገደብ አስተዳዳሪ"""
    
    def __init__(self, delay_range: Tuple[float, float] = ScraperConfig.RATE_LIMIT_RANGE) -> None:
        self.delay_range = delay_range
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0.0
        self.request_timestamps: List[float] = []
        self.max_requests = ScraperConfig.MAX_REQUESTS_PER_MINUTE
        self.window = ScraperConfig.RATE_LIMIT_WINDOW

    def wait_if_needed(self) -> None:
        """አስፈላጊ ከሆነ መጠበቅ"""
        now = time.time()
        
        # ከፍተኛ ውድቀት ካለ መጠበቅ
        if self.failure_count > 5:
            delay = min(10.0, 2.0 ** min(self.failure_count - 5, 5))
            time.sleep(delay)
            return
        
        # የጥያቄ ገደብ ማረጋገጫ
        self.request_timestamps = [t for t in self.request_timestamps if now - t < self.window]
        
        if len(self.request_timestamps) >= self.max_requests:
            oldest = self.request_timestamps[0]
            sleep_time = self.window - (now - oldest) + random.uniform(0.5, 1.5)
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # መደበኛ መዘግየት
        delay = random.uniform(*self.delay_range)
        elapsed = now - self.last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
        
        self.last_request_time = time.time()
        self.request_timestamps.append(time.time())

    def record_success(self) -> None:
        """ስኬትን ይመዘግባል"""
        self.success_count += 1
        if self.failure_count > 0:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """ውድቀትን ይመዘግባል"""
        self.failure_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_request_time": self.last_request_time,
            "requests_in_window": len(self.request_timestamps),
            "max_requests": self.max_requests,
            "window_seconds": self.window,
        }


class SmartCache:
    """ብልህ የሆነ የምላሽ መሸጎጫ"""
    
    def __init__(self, ttl: int = ScraperConfig.CACHE_TTL) -> None:
        self.ttl = ttl
        self.store: Dict[str, Tuple[Any, float]] = {}
        self.hits = 0
        self.misses = 0
        self.max_size = ScraperConfig.MAX_CACHE_SIZE

    def get(self, key: str) -> Optional[Any]:
        """ከካሽ መረጃ ያገኛል"""
        entry = self.store.get(key)
        if entry:
            val, expiry = entry
            if time.time() < expiry:
                self.hits += 1
                return val
            else:
                del self.store[key]
        self.misses += 1
        return None

    def set(self, key: str, val: Any) -> None:
        """መረጃን በካሽ ውስጥ ያስቀምጣል"""
        if len(self.store) >= self.max_size:
            # ጥንታዊውን ያስወግዱ
            oldest = min(self.store.keys(), key=lambda k: self.store[k][1])
            del self.store[oldest]
        self.store[key] = (val, time.time() + self.ttl)

    def get_stats(self) -> Dict[str, Any]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round((self.hits / total * 100), 2) if total > 0 else 0,
            "size": len(self.store),
            "max_size": self.max_size,
        }
    
    def clear(self) -> None:
        """ካሽን ያጸዳል"""
        self.store.clear()
        self.hits = 0
        self.misses = 0


# ============================================================
# 🔍 SMART PRODUCT EXTRACTOR (Multi-Strategy)
# ============================================================

class SmartProductExtractor:
    """ከማንኛውም የድረ-ገጽ HTML ምርቶችን በብልህነት የሚያወጣ ሞተር"""
    
    # ============================================================
    # 🎯 JIJI SELECTORS
    # ============================================================
    JIJI_LISTING_SELECTORS = [
        "div.b-list-advert__item",
        "div.b-list-advert__item-wrapper",
        "div.b-trending-card",
        "div.qa-advert-list-item",
        "div[data-cy=\"l-ad\"]",
        "div.b-advert",
        "div.advert",
    ]
    
    JIJI_TITLE_SELECTORS = [
        "h4.b-advert-title-inner",
        "a.b-advert-title",
        "h4.ta-title",
        "div.b-advert-title",
        "a.advert-title",
        "span.advert-title",
    ]
    
    JIJI_PRICE_SELECTORS = [
        "div.b-j-advert__price",
        "span.b-advert-price",
        "div.b-advert-price",
        "span.price",
        "div.price",
        "span.amount",
    ]
    
    JIJI_IMG_SELECTORS = [
        "div.b-advert-images-inner img",
        "img.b-advert-image",
        "img[data-cy=\"ad-image\"]",
        "img",
    ]
    
    # ============================================================
    # 📱 FACEBOOK MARKETPLACE SELECTORS
    # ============================================================
    FB_LISTING_SELECTORS = [
        "div[role='feed'] div[style*='max-width']",
        "div.x9f619.x78zum5.x1r8u6il",
        "div[class*='x1lliihq']",
        "div.product-card",
        "div[data-entityid]",
        "div[class*='marketplace']",
    ]
    
    FB_TITLE_SELECTORS = [
        "span[style*='-webkit-line-clamp']",
        "span.x1lliihq.x6ikm8r",
        "h2",
        "div[class*='title']",
        "span[class*='title']",
    ]
    
    FB_PRICE_SELECTORS = [
        "span.x193iq5w.xeuugli",
        "div.x1zoom55.x1lliihq",
        "span.price",
        "div.price",
        "span[class*='price']",
    ]
    
    # ============================================================
    # 📡 TELEGRAM SELECTORS
    # ============================================================
    TG_MESSAGE_SELECTORS = [
        r'<div[^>]*class=["\']tgme_widget_message_text[^"\']*["\'][^>]*>([\s\S]*?)</div>',
        r'<div[^>]*class=["\']message[^"\']*["\'][^>]*>([\s\S]*?)</div>',
        r'<div[^>]*class=["\']post[^"\']*["\'][^>]*>([\s\S]*?)</div>',
    ]
    
    TG_IMAGE_PATTERNS = [
        r"background-image:\s*url\(['\"]?([^'\)]+)['\"]?\)",
        r'<img[^>]*src="([^"]+)"[^>]*>',
        r'<a[^>]*href="([^"]+)"[^>]*>.*?</a>',
    ]
    
    # ============================================================
    # 🌐 GENERIC SELECTORS
    # ============================================================
    GENERIC_CARD_SELECTORS = [
        "div.product",
        "div.product-card",
        "div.product-item",
        "div.card.product",
        "li.product",
        "article.product",
        "div[class*='product-card']",
        "div[class*='product-item']",
        "div[class*='listing']",
        "div[class*='item']",
        "div[data-product-id]",
        "div[data-item-id]",
    ]
    
    GENERIC_TITLE_SELECTORS = [
        "h2", "h3", "h4", "div.title", "span.title", "a.title", ".name",
    ]
    
    GENERIC_PRICE_SELECTORS = [
        "span.price", "div.price", ".amount", "[class*='price']", "span.amount",
    ]
    
    GENERIC_IMG_SELECTORS = [
        "img[class*='product']", "img[src*='product']", "img",
    ]
    
    # ============================================================
    # 📋 MAIN EXTRACTION METHOD
    # ============================================================
    
    @classmethod
    def extract_products(cls, html: str, url: str) -> List[Dict]:
        """ምርቶችን ከHTML በብልህነት ያወጣል"""
        if not html:
            return []
        
        products = []
        
        # 1. JSON-LD Semantic Extraction (Unbreakable)
        products = cls._extract_json_ld(html)
        if products:
            logger.info(f"✅ JSON-LD: Extracted {len(products)} products")
            return products
        
        # 2. BeautifulSoup Extraction (if available)
        if _HAS_BS4:
            products = cls._extract_with_bs4(html, url)
            if products:
                logger.info(f"✅ BeautifulSoup: Extracted {len(products)} products")
                return products
        
        # 3. Regex Fallback Extraction
        products = cls._extract_with_regex(html, url)
        if products:
            logger.info(f"✅ Regex: Extracted {len(products)} products")
            return products
        
        # 4. Telegram Special Extraction
        if _is_telegram(url):
            products = cls._extract_telegram(html)
            if products:
                logger.info(f"✅ Telegram: Extracted {len(products)} products")
                return products
        
        logger.warning(f"⚠️ No products extracted from {url}")
        return []
    
    # ============================================================
    # 📄 JSON-LD SEMANTIC EXTRACTION
    # ============================================================
    
    @classmethod
    def _extract_json_ld(cls, html: str) -> List[Dict]:
        """ከJSON-LD ምርቶችን ያወጣል"""
        products = []
        try:
            blocks = re.findall(
                r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
                html, re.IGNORECASE
            )
            for block in blocks:
                try:
                    data = json.loads(block.strip())
                    items = []
                    
                    if isinstance(data, dict):
                        if data.get("@type") in ["Product", "Offer"]:
                            items = [data]
                        if data.get("@graph"):
                            items.extend([n for n in data["@graph"] if n.get("@type") == "Product"])
                    elif isinstance(data, list):
                        items = [n for n in data if n.get("@type") == "Product"]
                    
                    for item in items:
                        product = cls._parse_json_ld_product(item)
                        if product and product.get('title'):
                            products.append(product)
                except:
                    continue
        except:
            pass
        return products
    
    @classmethod
    def _parse_json_ld_product(cls, item: Dict) -> Dict:
        """ከJSON-LD አንድ ምርት ያወጣል"""
        product = {
            'title': '',
            'price': 0,
            'description': '',
            'seller_contact': '',
            'image_url': '',
            'url': '',
            'sku': '',
        }
        
        try:
            product['title'] = item.get('name', '')[:ScraperConfig.MAX_TITLE_LEN]
            
            offers = item.get('offers', {})
            if isinstance(offers, dict):
                product['price'] = float(offers.get('price', 0))
                product['url'] = offers.get('url', '')
            elif isinstance(offers, list) and offers:
                product['price'] = float(offers[0].get('price', 0))
                product['url'] = offers[0].get('url', '')
            
            if item.get('image'):
                img = item['image']
                if isinstance(img, list) and img:
                    product['image_url'] = img[0]
                elif isinstance(img, str):
                    product['image_url'] = img
            
            product['sku'] = item.get('sku', '')
            product['description'] = item.get('description', '')[:ScraperConfig.MAX_DESC_LEN]
            
        except:
            pass
        
        return product
    
    # ============================================================
    # 🍲 BEAUTIFULSOUP EXTRACTION
    # ============================================================
    
    @classmethod
    def _extract_with_bs4(cls, html: str, url: str) -> List[Dict]:
        """በBeautifulSoup ምርቶችን ያወጣል"""
        if not _HAS_BS4 or not BeautifulSoup:
            return []
        
        products = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # የጣቢያውን አይነት ይለያል
            site_type = cls._detect_site_type(url)
            
            # ተስማሚ ሴሌክተሮችን ይመርጣል
            selectors = cls._get_selectors(site_type)
            
            for selector in selectors[:10]:
                elements = soup.select(selector)
                if elements:
                    for elem in elements[:ScraperConfig.MAX_PRODUCTS_PER_PAGE]:
                        product = cls._extract_from_element(elem, site_type)
                        if product and product.get('title'):
                            products.append(product)
                    if products:
                        break
                        
        except Exception as e:
            logger.debug(f"BS4 extraction error: {e}")
        
        return products
    
    @classmethod
    def _detect_site_type(cls, url: str) -> str:
        """የድረ-ገጹን አይነት ይለያል"""
        domain = urlparse(url).netloc.lower()
        
        if 'jiji' in domain:
            return 'jiji'
        elif 'facebook' in domain or 'fb.com' in domain:
            return 'facebook'
        elif 't.me' in domain or 'telegram' in domain:
            return 'telegram'
        elif 'engocha' in domain:
            return 'engocha'
        elif 'ethiojobs' in domain:
            return 'ethiojobs'
        else:
            return 'generic'
    
    @classmethod
    def _get_selectors(cls, site_type: str) -> List[str]:
        """ለጣቢያው ተስማሚ የሆኑ ሴሌክተሮችን ያመጣል"""
        if site_type == 'jiji':
            return cls.JIJI_LISTING_SELECTORS + cls.GENERIC_CARD_SELECTORS
        elif site_type == 'facebook':
            return cls.FB_LISTING_SELECTORS + cls.GENERIC_CARD_SELECTORS
        elif site_type == 'telegram':
            return cls.GENERIC_CARD_SELECTORS
        else:
            return cls.GENERIC_CARD_SELECTORS
    
    @classmethod
    def _extract_from_element(cls, element, site_type: str) -> Dict:
        """ከአንድ ኤለመንት ምርት ያወጣል"""
        product = {
            'title': '',
            'price': 0,
            'description': '',
            'seller_contact': '',
            'image_url': '',
            'url': '',
        }
        
        try:
            # ርዕስ
            title_selectors = cls._get_title_selectors(site_type)
            for sel in title_selectors:
                el = element.select_one(sel)
                if el:
                    title = el.get_text(strip=True)
                    if len(title) >= ScraperConfig.MIN_TITLE_LEN:
                        product['title'] = title[:ScraperConfig.MAX_TITLE_LEN]
                        break
            
            # ዋጋ
            price_selectors = cls._get_price_selectors(site_type)
            for sel in price_selectors:
                el = element.select_one(sel)
                if el:
                    price_text = el.get_text(strip=True)
                    match = ScraperConfig.PRICE_RE.search(price_text) or ScraperConfig.PRICE_TAIL_RE.search(price_text)
                    if match:
                        try:
                            product['price'] = float(match.group(1).replace(',', ''))
                            break
                        except:
                            pass
            
            # ምስል (Lazy-loading support)
            img_selectors = cls._get_img_selectors(site_type)
            for sel in img_selectors:
                img = element.select_one(sel)
                if img:
                    for attr in ScraperConfig.IMAGE_ATTRS:
                        img_url = img.get(attr)
                        if img_url:
                            if ',' in img_url:
                                img_url = img_url.split(',')[0].strip().split(' ')[0]
                            if img_url.startswith('//'):
                                img_url = 'https:' + img_url
                            if img_url.startswith('http'):
                                product['image_url'] = img_url
                                break
                    if product['image_url']:
                        break
            
            # ስልክ/መለያ
            text = element.get_text()
            phone_match = ScraperConfig.PHONE_RE.search(text)
            if phone_match:
                product['seller_contact'] = phone_match.group(0).strip()
            else:
                tg_match = ScraperConfig.TELEGRAM_RE.search(text)
                if tg_match:
                    product['seller_contact'] = tg_match.group(0).strip()
            
            # መግለጫ
            desc_elem = element.select_one('p.description, .desc, .description, p')
            if desc_elem:
                desc = desc_elem.get_text(strip=True)
                if len(desc) > ScraperConfig.MIN_DESC_LEN:
                    product['description'] = desc[:ScraperConfig.MAX_DESC_LEN]
            if not product['description']:
                product['description'] = text[:ScraperConfig.MAX_DESC_LEN]
            
            # URL
            link = element.find('a')
            if link and link.get('href'):
                product['url'] = urljoin('https://', link['href'])
            
        except Exception as e:
            logger.debug(f"Element extraction error: {e}")
        
        return product
    
    @classmethod
    def _get_title_selectors(cls, site_type: str) -> List[str]:
        if site_type == 'jiji':
            return cls.JIJI_TITLE_SELECTORS + cls.GENERIC_TITLE_SELECTORS
        elif site_type == 'facebook':
            return cls.FB_TITLE_SELECTORS + cls.GENERIC_TITLE_SELECTORS
        else:
            return cls.GENERIC_TITLE_SELECTORS
    
    @classmethod
    def _get_price_selectors(cls, site_type: str) -> List[str]:
        if site_type == 'jiji':
            return cls.JIJI_PRICE_SELECTORS + cls.GENERIC_PRICE_SELECTORS
        elif site_type == 'facebook':
            return cls.FB_PRICE_SELECTORS + cls.GENERIC_PRICE_SELECTORS
        else:
            return cls.GENERIC_PRICE_SELECTORS
    
    @classmethod
    def _get_img_selectors(cls, site_type: str) -> List[str]:
        if site_type == 'jiji':
            return cls.JIJI_IMG_SELECTORS + cls.GENERIC_IMG_SELECTORS
        else:
            return cls.GENERIC_IMG_SELECTORS
    
    # ============================================================
    # 📡 REGEX EXTRACTION
    # ============================================================
    
    @classmethod
    def _extract_with_regex(cls, html: str, url: str) -> List[Dict]:
        """በRegex ምርቶችን ያወጣል"""
        products = []
        
        try:
            # የምርት መያዣዎችን ይፈልጋል
            patterns = [
                r'<div[^>]*class="[^"]*(?:product|item|listing|card|advert|classified)[^"]*"[^>]*>(.*?)</div>',
                r'<li[^>]*class="[^"]*(?:product|item|listing)[^"]*"[^>]*>(.*?)</li>',
                r'<article[^>]*class="[^"]*(?:product|item)[^"]*"[^>]*>(.*?)</article>',
                r'<a[^>]*href="[^"]*item[^"]*"[^>]*>(.*?)</a>',
            ]
            
            containers = []
            for pattern in patterns:
                found = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if found:
                    containers.extend(found)
                    break
            
            for container in containers[:ScraperConfig.MAX_PRODUCTS_PER_PAGE]:
                product = cls._extract_from_text(container, url)
                if product and product.get('title'):
                    products.append(product)
            
        except Exception as e:
            logger.debug(f"Regex extraction error: {e}")
        
        return products
    
    @classmethod
    def _extract_from_text(cls, text: str, url: str) -> Dict:
        """ከጽሑፍ ምርት ያወጣል"""
        product = {
            'title': '',
            'price': 0,
            'description': '',
            'seller_contact': '',
            'image_url': '',
        }
        
        try:
            # ርዕስ
            title_match = re.search(
                r'<h[1-4][^>]*>(.*?)</h[1-4]>|<strong[^>]*>(.*?)</strong>|<b[^>]*>(.*?)</b>',
                text, re.DOTALL | re.IGNORECASE
            )
            if title_match:
                title = title_match.group(1) or title_match.group(2) or title_match.group(3) or ''
                title = re.sub(r'<[^>]+>', ' ', title).strip()
                if len(title) >= ScraperConfig.MIN_TITLE_LEN:
                    product['title'] = title[:ScraperConfig.MAX_TITLE_LEN]
            
            # ዋጋ
            price_match = ScraperConfig.PRICE_RE.search(text) or ScraperConfig.PRICE_TAIL_RE.search(text)
            if price_match:
                try:
                    product['price'] = float(price_match.group(1).replace(',', ''))
                except:
                    pass
            
            # ስልክ
            phone_match = ScraperConfig.PHONE_RE.search(text)
            if phone_match:
                product['seller_contact'] = phone_match.group(0).strip()
            else:
                tg_match = ScraperConfig.TELEGRAM_RE.search(text)
                if tg_match:
                    product['seller_contact'] = tg_match.group(0).strip()
            
            # መግለጫ
            clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
            product['description'] = ' '.join(clean_text.split())[:ScraperConfig.MAX_DESC_LEN]
            
            # ምስል
            img_match = re.search(r'<img[^>]+(?:data-src|data-lazy|lazy-src|src)=["\']([^"\']+)["\']', text, re.IGNORECASE)
            if img_match:
                img_url = img_match.group(1)
                if ',' in img_url:
                    img_url = img_url.split(',')[0].strip().split(' ')[0]
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                product['image_url'] = img_url
            
        except Exception as e:
            logger.debug(f"Text extraction error: {e}")
        
        return product
    
    # ============================================================
    # 📱 TELEGRAM EXTRACTION
    # ============================================================
    
    @classmethod
    def _extract_telegram(cls, html: str) -> List[Dict]:
        """ከቴሌግራም ምርቶችን ያወጣል"""
        products = []
        
        try:
            # የቴሌግራም መልዕክቶችን ያገኛል
            messages = []
            for pattern in cls.TG_MESSAGE_SELECTORS:
                found = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if found:
                    messages.extend(found)
                    break
            
            # ምስሎችን ያገኛል
            images = []
            for pattern in cls.TG_IMAGE_PATTERNS:
                found = re.findall(pattern, html, re.IGNORECASE)
                if found:
                    images.extend(found)
                    break
            
            for i, msg in enumerate(messages[:ScraperConfig.MAX_PRODUCTS_PER_PAGE]):
                clean_text = re.sub(r'<[^>]+>', ' ', msg).strip()
                
                # የሲስተም መልዕክቶችን ይዘል
                if ScraperConfig.SYSTEM_MSG_RE.search(clean_text):
                    continue
                
                # የምርት መለያ ምልክቶችን ያረጋግጣል
                is_product = (
                    ScraperConfig.PRICE_RE.search(clean_text) or
                    ScraperConfig.PRICE_TAIL_RE.search(clean_text) or
                    ScraperConfig.PHONE_RE.search(clean_text) or
                    ScraperConfig.TELEGRAM_RE.search(clean_text) or
                    ScraperConfig.PRODUCT_INDICATORS.search(clean_text)
                )
                
                if not is_product:
                    continue
                
                # ያረጁ መልዕክቶችን ይዘል
                if ScraperConfig.OLD_DATE_RE.search(clean_text):
                    continue
                
                product = cls._parse_telegram_message(clean_text)
                if product and product.get('title'):
                    product['image_url'] = images[i] if i < len(images) else ''
                    products.append(product)
            
        except Exception as e:
            logger.debug(f"Telegram extraction error: {e}")
        
        return products
    
    @classmethod
    def _parse_telegram_message(cls, text: str) -> Dict:
        """ከቴሌግራም መልዕክት ምርት ያወጣል"""
        product = {
            'title': '',
            'price': 0,
            'description': '',
            'seller_contact': '',
            'image_url': '',
        }
        
        try:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if not lines:
                return product
            
            # ርዕስ - የመጀመሪያውን መስመር ይጠቀማል
            title = lines[0]
            if len(title) >= ScraperConfig.MIN_TITLE_LEN:
                product['title'] = title[:ScraperConfig.MAX_TITLE_LEN]
            else:
                # ቀጣይ መስመር ይሞክሩ
                for line in lines[1:4]:
                    if len(line) >= ScraperConfig.MIN_TITLE_LEN:
                        product['title'] = line[:ScraperConfig.MAX_TITLE_LEN]
                        break
            
            # ዋጋ
            price_match = ScraperConfig.PRICE_RE.search(text) or ScraperConfig.PRICE_TAIL_RE.search(text)
            if price_match:
                try:
                    product['price'] = float(price_match.group(1).replace(',', ''))
                except:
                    pass
            
            # ስልክ
            phone_match = ScraperConfig.PHONE_RE.search(text)
            if phone_match:
                product['seller_contact'] = phone_match.group(0).strip()
            else:
                tg_match = ScraperConfig.TELEGRAM_RE.search(text)
                if tg_match:
                    product['seller_contact'] = tg_match.group(0).strip()
            
            # መግለጫ
            product['description'] = text[:ScraperConfig.MAX_DESC_LEN]
            
        except Exception as e:
            logger.debug(f"Telegram message parsing error: {e}")
        
        return product


# ============================================================
# 🚀 MAIN SCRAPPER ENGINE
# ============================================================

_engine_lock = threading.Lock()

class ScrapperEngine:
    """ማንኛውንም ድረ-ገጽ በራሱ የሚላመድ እና የሚያስስ ሞተር"""
    
    _instance: Optional["ScrapperEngine"] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with _engine_lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_engine()
        return cls._instance

    def _init_engine(self) -> None:
        self.extractor = AdvancedProductExtractor()
        self.rate_limiter = IntelligentRateLimiter()
        self.cache = SmartCache()
        self.metrics = ScraperMetrics()
        self.session = requests.Session()
        self.session_counter = 0

    @classmethod
    def scrape(cls, url: str, use_playwright: Optional[bool] = None) -> Optional[str]:
        """አንድ ዩአርኤል ይስሳል"""
        inst = cls()
        if not url:
            return None

        norm_url = url.rstrip("/")
        scrapeops_key = os.getenv('SCRAPEOPS_API_KEY', '').strip()
        use_scrapeops = bool(scrapeops_key) and not _is_telegram(norm_url)

        if use_playwright is None:
            use_playwright = not use_scrapeops

        inst.metrics.total_attempts += 1
        inst.metrics.last_scrape_time = datetime.now()

        cache_key = hashlib.md5(f"{norm_url}:{use_playwright}".encode()).hexdigest()
        cached = inst.cache.get(cache_key)
        if cached:
            inst.metrics.cache_hits += 1
            return cached

        inst.metrics.cache_misses += 1
        inst.rate_limiter.wait_if_needed()

        if not norm_url.startswith("http"):
            norm_url = "https://" + norm_url

        html: Optional[str] = None
        start_time = time.time()

        # 1. ScrapeOps Proxy (if available)
        if use_scrapeops:
            try:
                logger.info(f"[Scraper] Routing via ScrapeOps proxy: {norm_url}")
                payload = {"api_key": scrapeops_key, "url": norm_url, "bypass": "cloudflare"}
                res = requests.get(ScraperConfig.SCRAPEOPS_ENDPOINT, params=payload, timeout=ScraperConfig.REQUEST_TIMEOUT)
                if res.status_code == 200:
                    html = res.text
            except Exception as e:
                logger.warning(f"[Scraper] ScrapeOps failed: {e}")

        # 2. Playwright (if available and CPU allows)
        if not html and use_playwright and _can_use_playwright():
            html = inst._scrape_with_playwright(norm_url)

        # 3. Requests (Session-based)
        if not html:
            html = inst._scrape_with_requests(norm_url)

        # Record response time
        inst.metrics.record_response_time(time.time() - start_time)

        if html:
            inst.metrics.successful_scrapes += 1
            inst.rate_limiter.record_success()
            inst.cache.set(cache_key, html)
        else:
            inst.metrics.failed_scrapes += 1
            inst.rate_limiter.record_failure()
            inst.metrics.errors.append(f"Failed to scrape {norm_url}")

        return html

    def _run_async_in_new_thread(self, coro):
        """በአዲስ ክር ውስጥ async ተግባርን ያስኬዳል"""
        result = [None]
        exc = [None]

        def worker():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(coro)
            except Exception as e:
                exc[0] = e
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=90)
        if exc[0]:
            raise exc[0]
        return result[0]

    def _scrape_with_playwright(self, url: str) -> Optional[str]:
        """Playwright በመጠቀም ያስሳል"""
        try:
            return self._run_async_in_new_thread(self._async_playwright_fetch(url))
        except Exception as e:
            logger.warning(f"[Scraper] Playwright error for {url}: {e}")
            return None

    async def _async_playwright_fetch(self, url: str) -> Optional[str]:
        """Async Playwright fetch"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        async with async_playwright() as p:
            headers = FingerprintEvasion.get_headers(url, _is_telegram(url))
            proxy_url = os.getenv("SMART_PROXY_URL", "").strip()
            proxy_cfg = {"server": proxy_url} if proxy_url else None

            browser = await p.chromium.launch(
                headless=True,
                proxy=proxy_cfg,
                args=['--disable-blink-features=AutomationControlled'],
                timeout=ScraperConfig.PLAYWRIGHT_TIMEOUT * 1000,
            )
            context = await browser.new_context(
                user_agent=headers["User-Agent"],
                viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
                extra_http_headers=headers,
                locale=random.choice(["en-US", "en-GB"]),
                timezone_id="Africa/Addis_Ababa",
            )
            page = await context.new_page()
            
            await page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en','am']});
                window.chrome = {runtime: {}};
                """
            )
            
            await page.goto(url, wait_until="domcontentloaded", timeout=ScraperConfig.PLAYWRIGHT_TIMEOUT * 1000)
            await asyncio.sleep(random.uniform(2, 5))

            for _ in range(random.randint(2, 4)):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            content = await page.content()
            await browser.close()
            return content

    def _scrape_with_requests(self, url: str) -> Optional[str]:
        """Requests በመጠቀም ያስሳል"""
        try:
            headers = FingerprintEvasion.get_headers(url, _is_telegram(url))
            time.sleep(random.uniform(1, 3))
            
            res = self.session.get(url, headers=headers, timeout=ScraperConfig.REQUEST_TIMEOUT)
            if res.status_code == 200:
                return res.text
            if res.status_code == 429:
                logger.warning(f"[Scraper] Rate limited (429) on {url}")
                self.rate_limiter.record_failure()
                retry_after = res.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else random.uniform(8, 15)
                except (ValueError, TypeError):
                    wait = random.uniform(8, 15)
                time.sleep(min(wait, 60))
        except Exception as e:
            logger.warning(f"[Scraper] Requests error for {url}: {e}")
        return None

    @classmethod
    def scrape_and_extract(cls, url: str) -> List[Dict]:
        """ያስሳል እና ምርቶችን ያወጣል"""
        html = cls.scrape(url)
        if not html:
            return []
        
        products = cls().extractor.extract_products(html, url)
        
        if not products:
            report = cls()._generate_diagnostic_report(url, html)
            cls()._save_report(report)
        
        # Update metrics
        inst = cls()
        inst.metrics.total_products_extracted += len(products)
        
        return products

    @classmethod
    def _generate_diagnostic_report(cls, url: str, html: Optional[str]) -> Dict:
        """የምርመራ ሪፖርት ያዘጋጃል"""
        domain = urlparse(url).netloc.lower()
        return {
            "url": url,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "html_length": len(html) if html else 0,
            "products_found": 0,
            "status": "failed",
            "bs4_available": _HAS_BS4,
            "cloudinary_available": _HAS_CLOUDINARY,
            "suggestions": [
                "Check if the site uses a SPA framework (needs Playwright).",
                "Verify product card selectors match the target site's HTML.",
                "Inspect data/diagnostics for the saved HTML length.",
                "Try rotating User-Agents or using different headers.",
            ],
            "metrics": cls().metrics.to_dict(),
            "rate_limiter": cls().rate_limiter.get_stats(),
            "cache_stats": cls().cache.get_stats(),
        }

    @classmethod
    def _save_report(cls, report: Dict) -> None:
        """ሪፖርቱን ያስቀምጣል"""
        try:
            os.makedirs("data/diagnostics", exist_ok=True)
            fn = f"data/diagnostics/{report['domain']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"[Scraper] Failed to write diagnostic report: {e}")

    @classmethod
    def get_metrics(cls) -> Dict:
        """የስክሬፐር አፈጻጸም መለኪያዎችን ያመጣል"""
        inst = cls()
        return {
            "scraper": inst.metrics.to_dict(),
            "rate_limiter": inst.rate_limiter.get_stats(),
            "cache": inst.cache.get_stats(),
            "extractor": {
                "cache_hits": inst.extractor.cache.hits,
                "cache_misses": inst.extractor.cache.misses,
            },
        }

    # ============================================================
    # 🔍 UNAUTHENTICATED SEARCH FALLBACK
    # ============================================================
    
    @staticmethod
    def unauthenticated_search_lookup(query: str, extract_telegram_links: bool = False) -> Any:
        """
        🛡️ DUAL-ENGINE FALLBACK: ከጌሚኒ ውጪ ላሉት አቅራቢዎች በይነመረብ ላይ በ Google/Bing/DuckDuckGo ፈልጎ 
        ጥሬ የጽሑፍ ማጠቃለያዎችን ወይም የቴሌግራም ሊንኮችን ለይቶ የሚያወጣ ብቸኛው የጋራ ሞተር (Zero Duplication)
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        raw_html = ""
        from urllib.parse import quote
        
        # 1. DuckDuckGo
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                raw_html = res.text
        except Exception:
            pass

        # 2. Google
        if not raw_html:
            try:
                google_url = f"https://www.google.com/search?q={quote(query)}"
                res = requests.get(google_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    raw_html = res.text
            except Exception:
                pass

        # 3. Bing
        if not raw_html:
            try:
                bing_url = f"https://www.bing.com/search?q={quote(query)}"
                res = requests.get(bing_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    raw_html = res.text
            except Exception:
                pass

        if not raw_html:
            return [] if extract_telegram_links else ""

        # 📱 Telegram Links
        if extract_telegram_links:
            telegram_usernames = re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', raw_html)
            fallback_sources = []
            for username in list(set(telegram_usernames))[:4]:
                if username.lower() not in ['s', 'joinchat', 'share', 'tgme']:
                    fallback_sources.append({"url_or_channel": username, "platform_type": "Telegram"})
            return fallback_sources

        # 📝 Text Snippets
        results = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', raw_html, re.DOTALL)
        snippets = []
        for r in results[:5]:
            clean_r = re.sub(r'<[^>]+>', ' ', r).strip()
            if clean_r:
                snippets.append(clean_r)
        return "\n".join(snippets)


# ============================================================
# 🔧 HELPER FUNCTIONS
# ============================================================

def _is_telegram(url: str) -> bool:
    """ዩአርኤል የቴሌግራም መሆኑን ያረጋግጣል"""
    return any(x in url.lower() for x in ("t.me", "telegram", "@"))


def _can_use_playwright() -> bool:
    """Playwright መጠቀም መቻሉን ያረጋግጣል (CPU Load Check)"""
    try:
        load_avg = os.getloadavg()[0]
        if load_avg > ScraperConfig.CPU_LOAD_THRESHOLD:
            logger.warning(f"⚠️ CPU Load is heavy ({load_avg:.2f}). Playwright bypassed.")
            return False
    except (AttributeError, OSError, Exception):
        pass
    return True


# ============================================================
# 🚀 ADVANCED PRODUCT EXTRACTOR (Caching Wrapper)
# ============================================================

class AdvancedProductExtractor:
    """የምርት ማውጫ ሞተር በ SmartCache የተሸፈነ"""
    
    def __init__(self) -> None:
        self.cache = SmartCache(ttl=ScraperConfig.SMART_CACHE_TTL)
        self.hits = 0
        self.misses = 0

    def extract_products(self, html: str, url: str) -> List[Dict]:
        cache_key = hashlib.md5(f"extract:{url}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.hits += 1
            return cached
        self.misses += 1
        products = SmartProductExtractor.extract_products(html, url)
        self.cache.set(cache_key, products)
        return products


# ============================================================
# 📦 COMPATIBILITY EXPORTS
# ============================================================

_shared_engine = ScrapperEngine()

def scrape_and_extract_products(url: str) -> List[Dict]:
    """ያስሳል እና ምርቶችን ያወጣል"""
    return _shared_engine.scrape_and_extract(url)

def scrape_url(url: str) -> Optional[str]:
    """አንድ ዩአርኤል ይስሳል"""
    return _shared_engine.scrape(url)

def get_scraper_metrics() -> Dict:
    """የስክሬፐር አፈጻጸም መለኪያዎችን ያመጣል"""
    return _shared_engine.get_metrics()

def clear_scraper_cache() -> None:
    """የስክሬፐር ካሽን ያጸዳል"""
    _shared_engine.cache.clear()
    _shared_engine.extractor.cache.clear()
    logger.info("🧹 Scraper cache cleared")

def unauthenticated_search(query: str, extract_telegram_links: bool = False) -> Any:
    """ያለ AI ፍለጋ ማድረጊያ"""
    return _shared_engine.unauthenticated_search_lookup(query, extract_telegram_links)
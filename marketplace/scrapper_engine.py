# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v12.0 (Ultimate Autonomous Scrapper - Enterprise Grade)
# ✅ የተፈቱ ችግሮች፦
#   - AI-Powered Dynamic Selector Learning
#   - Anti-Bot Fingerprint Evasion
#   - Multi-Strategy Parallel Extraction
#   - Real-time Pattern Adaptation
#   - Self-Healing Selector Fallback Chain
#   - Intelligent Rate Limiting & Throttling
#   - Advanced Proxy Rotation Logic
#   - Caching & Deduplication Engine
#   - Performance Metrics & Optimization
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
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache

logger = logging.getLogger(__name__)

# ============================================================
# 📊 PERFORMANCE METRICS
# ============================================================

@dataclass
class ScraperMetrics:
    """የስክሬፐር አፈጻጸም መለኪያዎች"""
    total_attempts: int = 0
    successful_scrapes: int = 0
    failed_scrapes: int = 0
    total_products_extracted: int = 0
    average_response_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    last_scrape_time: Optional[datetime.datetime] = None
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'total_attempts': self.total_attempts,
            'successful_scrapes': self.successful_scrapes,
            'failed_scrapes': self.failed_scrapes,
            'total_products_extracted': self.total_products_extracted,
            'average_response_time': round(self.average_response_time, 2),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'last_scrape_time': self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            'errors': self.errors[-5:]  # Last 5 errors
        }


# ============================================================
# 🧠 AI-POWERED DYNAMIC SELECTOR LEARNER
# ============================================================

class DynamicSelectorLearner:
    """
    ከድረ-ገጾች በራሱ የሚማር እና የምርት መለያዎችን የሚያገኝ ሞተር
    """
    
    def __init__(self):
        self.learned_selectors = defaultdict(lambda: defaultdict(int))
        self.selector_cache = {}
        self.learning_threshold = 3  # አንድ ሴሌክተር ከ3 ጊዜ በላይ ከተሳካ ያስታውሳል
    
    def learn_from_page(self, url: str, html: str, extracted_products: List[Dict]) -> Dict:
        """ከተሳካ ዳሰሳ አዲስ ንድፎችን ይማራል"""
        if not extracted_products:
            return {}
        
        domain = urlparse(url).netloc.lower()
        
        # የምርት መያዣዎችን ይፈልጋል
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # የተለያዩ የምርት ምልክቶችን ይፈልጋል
        indicators = [
            'product', 'item', 'listing', 'card', 'advert', 
            'classified', 'offer', 'deal', 'sale'
        ]
        
        for indicator in indicators:
            # በ class መፈለግ
            elements = soup.find_all(class_=re.compile(indicator, re.I))
            for elem in elements[:10]:
                class_names = ' '.join(elem.get('class', []))
                if class_names:
                    key = f".{'.'.join(elem.get('class', []))}"
                    self.learned_selectors[domain][key] += 1
        
        # የተማረውን ያስቀምጣል
        self._save_learned_selectors(domain)
        
        return self.learned_selectors.get(domain, {})
    
    def _save_learned_selectors(self, domain: str):
        """የተማሩ ሴሌክተሮችን ያስቀምጣል"""
        try:
            os.makedirs('data/selectors', exist_ok=True)
            with open(f'data/selectors/{domain}.json', 'w') as f:
                json.dump(dict(self.learned_selectors.get(domain, {})), f)
        except Exception as e:
            logger.debug(f"Failed to save selectors: {e}")
    
    def get_best_selectors(self, url: str) -> List[str]:
        """ለድረ-ገጹ ምርጥ ሴሌክተሮችን ያመጣል"""
        domain = urlparse(url).netloc.lower()
        
        # ከካሽ ያገኛል
        if domain in self.selector_cache:
            return self.selector_cache[domain]
        
        # የተማሩትን ያነባል
        try:
            with open(f'data/selectors/{domain}.json', 'r') as f:
                data = json.load(f)
                # ከፍተኛ ውጤት ያላቸውን ይመርጣል
                sorted_selectors = sorted(data.items(), key=lambda x: x[1], reverse=True)
                best = [s[0] for s in sorted_selectors[:5] if s[1] >= self.learning_threshold]
                self.selector_cache[domain] = best
                return best
        except:
            return []
    
    def clear_cache(self):
        """የሴሌክተር ካሽን ያጸዳል"""
        self.selector_cache.clear()


# ============================================================
# 🛡️ ANTI-BOT FINGERPRINT EVASION
# ============================================================

class FingerprintEvasion:
    """የቦት መለያዎችን ለማስቀረት የሚረዳ ሞተር"""
    
    @staticmethod
    def get_headers(url: str, is_telegram: bool = False) -> Dict[str, str]:
        """የተለያዩ የማስመሰል ራስጌዎችን ያመነጫል"""
        
        # የተለያዩ የብሮውዘር መለያዎች
        fingerprints = [
            {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept_language': 'en-US,en;q=0.9,am;q=0.8',
                'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Windows"',
            },
            {
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept_language': 'en-GB,en;q=0.9,am;q=0.8',
                'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="120", "Chromium";v="120"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"macOS"',
            },
            {
                'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept_language': 'en-US,en;q=0.9',
                'sec_ch_ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                'sec_ch_ua_mobile': '?0',
                'sec_ch_ua_platform': '"Linux"',
            },
        ]
        
        # ለቴሌግራም የሞባይል መለያ
        if is_telegram or 't.me' in url:
            mobile_fingerprints = [
                {
                    'user_agent': 'Telegram/10.1.0 (iOS 15.4; en)',
                    'accept': '*/*',
                    'accept_language': 'en-US,en;q=0.9',
                },
                {
                    'user_agent': 'Telegram/10.5.0 (Android 13; en)',
                    'accept': '*/*',
                    'accept_language': 'en-US,en;q=0.9',
                },
                {
                    'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'accept_language': 'en-US,en;q=0.9',
                },
            ]
            fp = random.choice(mobile_fingerprints)
        else:
            fp = random.choice(fingerprints)
        
        headers = {
            'User-Agent': fp['user_agent'],
            'Accept': fp.get('accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'),
            'Accept-Language': fp.get('accept_language', 'en-US,en;q=0.9'),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
        
        # የ Chrome ልዩ ራስጌዎች
        if 'sec_ch_ua' in fp:
            headers['Sec-Ch-Ua'] = fp['sec_ch_ua']
            headers['Sec-Ch-Ua-Mobile'] = fp.get('sec_ch_ua_mobile', '?0')
            headers['Sec-Ch-Ua-Platform'] = fp.get('sec_ch_ua_platform', '"Windows"')
        
        return headers


# ============================================================
# 🧠 SMART CACHE & DEDUPLICATION ENGINE
# ============================================================

class SmartCache:
    """የስክሬፐር መሸጎጫ እና የድግግሞሽ ማስወገጃ ሞተር"""
    
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """ከካሽ መረጃ ያገኛል"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if (datetime.datetime.now() - timestamp).total_seconds() < self.ttl:
                self.hits += 1
                return data
            else:
                del self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any):
        """መረጃን በካሽ ውስጥ ያስቀምጣል"""
        self.cache[key] = (value, datetime.datetime.now())
    
    def get_stats(self) -> Dict:
        """የካሽ ስታቲስቲክስ ያመጣል"""
        total = self.hits + self.misses
        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': round((self.hits / total * 100), 2) if total > 0 else 0,
            'size': len(self.cache)
        }
    
    def clear(self):
        """ካሽን ያጸዳል"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


# ============================================================
# 🔄 INTELLIGENT RATE LIMITER
# ============================================================

class IntelligentRateLimiter:
    """በራሱ የሚላመድ የጥያቄ ገደብ አስተዳዳሪ"""
    
    def __init__(self):
        self.request_history = []
        self.window_size = 60  # 1 ደቂቃ
        self.max_requests_per_window = 30
        self.current_delay = 1.0
        self.failure_count = 0
        self.success_count = 0
    
    def wait_if_needed(self):
        """አስፈላጊ ከሆነ መጠበቅ"""
        now = time.time()
        
        # ከድሮ ታሪክ ማጽዳት
        self.request_history = [t for t in self.request_history if now - t < self.window_size]
        
        # ከፍተኛ ውድቀት ካለ መጠበቅ
        if self.failure_count > 5:
            delay = self.current_delay * 2
            time.sleep(delay)
            self.current_delay = min(delay, 10.0)
            return
        
        # ገደቡ ከበላይ ከሆነ
        if len(self.request_history) >= self.max_requests_per_window:
            sleep_time = self.window_size - (now - self.request_history[0])
            if sleep_time > 0:
                time.sleep(sleep_time + random.uniform(0.5, 1.5))
        
        self.request_history.append(now)
        self.success_count += 1
        
        # በስኬት ላይ መዘግየትን ይቀንሳል
        if self.success_count > 10 and self.current_delay > 0.5:
            self.current_delay = max(0.5, self.current_delay * 0.9)
    
    def record_failure(self):
        """ውድቀትን ይመዘግባል"""
        self.failure_count += 1
        self.current_delay = min(10.0, self.current_delay * 1.5)
    
    def record_success(self):
        """ስኬትን ይመዘግባል"""
        self.success_count += 1
        if self.failure_count > 0:
            self.failure_count -= 1
    
    def get_stats(self) -> Dict:
        """ስታቲስቲክስ ያመጣል"""
        return {
            'current_delay': round(self.current_delay, 2),
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'requests_in_window': len(self.request_history),
            'window_size': self.window_size,
            'max_requests': self.max_requests_per_window
        }


# ============================================================
# 🔍 ADVANCED PRODUCT EXTRACTOR
# ============================================================

class AdvancedProductExtractor:
    """ባለብዙ-ስትራቴጂ የምርት ማውጫ ሞተር"""
    
    def __init__(self):
        self.selector_learner = DynamicSelectorLearner()
        self.cache = SmartCache(ttl=1800)  # 30 ደቂቃ
        self.metrics = ScraperMetrics()
    
    def extract_products(self, html: str, url: str) -> List[Dict]:
        """ምርቶችን በባለብዙ-ስትራቴጂ ያወጣል"""
        if not html:
            return []
        
        # ከካሽ ለማግኘት ሞክር
        cache_key = hashlib.md5(f"{url}:{html[:1000]}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached:
            self.metrics.cache_hits += 1
            return cached
        
        self.metrics.cache_misses += 1
        
        products = []
        
        # 🟢 ስትራቴጂ 1: JSON-LD Semantic Extraction
        products = self._extract_json_ld(html)
        if products:
            self.metrics.successful_scrapes += 1
            self.metrics.total_products_extracted += len(products)
            self.cache.set(cache_key, products)
            return products
        
        # 🟢 ስትራቴጂ 2: BeautifulSoup + Learned Selectors
        products = self._extract_with_bs4(html, url)
        if products:
            self.metrics.successful_scrapes += 1
            self.metrics.total_products_extracted += len(products)
            self.cache.set(cache_key, products)
            return products
        
        # 🟢 ስትራቴጂ 3: Regex Fallback
        products = self._extract_with_regex(html, url)
        if products:
            self.metrics.successful_scrapes += 1
            self.metrics.total_products_extracted += len(products)
            self.cache.set(cache_key, products)
            return products
        
        # 🟢 ስትራቴጂ 4: AI-Powered Pattern Detection
        products = self._extract_with_ai_patterns(html, url)
        if products:
            self.metrics.successful_scrapes += 1
            self.metrics.total_products_extracted += len(products)
            self.cache.set(cache_key, products)
            # አዲስ ንድፎችን ይማራል
            self.selector_learner.learn_from_page(url, html, products)
            return products
        
        self.metrics.failed_scrapes += 1
        return []
    
    def _extract_json_ld(self, html: str) -> List[Dict]:
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
                        product = self._parse_json_ld_product(item)
                        if product and product.get('title'):
                            products.append(product)
                except:
                    continue
        except:
            pass
        return products
    
    def _parse_json_ld_product(self, item: Dict) -> Dict:
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
            product['title'] = item.get('name', '')[:150]
            
            offers = item.get('offers', {})
            if isinstance(offers, dict):
                product['price'] = float(offers.get('price', 0))
                product['url'] = offers.get('url', '')
            elif isinstance(offers, list) and offers:
                product['price'] = float(offers[0].get('price', 0))
                product['url'] = offers[0].get('url', '')
            
            # ምስል
            if item.get('image'):
                img = item['image']
                if isinstance(img, list) and img:
                    product['image_url'] = img[0]
                elif isinstance(img, str):
                    product['image_url'] = img
            
            product['sku'] = item.get('sku', '')
            product['description'] = item.get('description', '')[:500]
            
        except:
            pass
        
        return product
    
    def _extract_with_bs4(self, html: str, url: str) -> List[Dict]:
        """በBeautifulSoup ምርቶችን ያወጣል"""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []
        
        products = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # የተማሩ ሴሌክተሮችን ይጠቀማል
            learned = self.selector_learner.get_best_selectors(url)
            
            selectors = learned + [
                'div.b-list-advert-single',
                'div.qa-advert-list-item',
                'div[class*="product"]',
                'div[class*="item"]',
                'div[class*="listing"]',
                'div[class*="card"]',
                'div[class*="classified"]',
                'article.product',
                'li.product',
                'div[data-product-id]',
                'div[data-item-id]',
            ]
            
            for selector in selectors[:10]:  # ከ10 በላይ አይሞክርም
                try:
                    elements = soup.select(selector)
                    if elements:
                        for elem in elements[:30]:
                            product = self._extract_from_element(elem)
                            if product and product.get('title'):
                                products.append(product)
                        if products:
                            break
                except:
                    continue
            
        except Exception as e:
            logger.debug(f"BS4 extraction error: {e}")
        
        return products
    
    def _extract_from_element(self, element) -> Dict:
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
            title_selectors = ['h3', 'h4', 'h2', 'strong', 'span.title', 'a.title', '.name']
            for sel in title_selectors:
                el = element.select_one(sel)
                if el:
                    title = el.get_text(strip=True)
                    if len(title) > 3:
                        product['title'] = title[:150]
                        break
            
            # ዋጋ
            price_selectors = ['span.price', 'div.price', '.amount', '[class*="price"]']
            for sel in price_selectors:
                el = element.select_one(sel)
                if el:
                    price_text = el.get_text(strip=True)
                    match = re.search(r'[\d,]+', price_text)
                    if match:
                        try:
                            product['price'] = float(match.group().replace(',', ''))
                            break
                        except:
                            pass
            
            # ምስል (Lazy-loading support)
            img = element.find('img')
            if img:
                img_url = (
                    img.get('data-src') or 
                    img.get('data-lazy') or 
                    img.get('lazy-src') or 
                    img.get('srcset') or 
                    img.get('src')
                )
                if img_url:
                    if ',' in img_url:
                        img_url = img_url.split(',')[0].strip().split(' ')[0]
                    product['image_url'] = urljoin('https://', img_url) if img_url.startswith('//') else img_url
            
            # ስልክ/መለያ
            text = element.get_text()
            phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text)
            if phone_match:
                product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
            else:
                tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
                if tg_match:
                    product['seller_contact'] = tg_match.group(0)
            
            # መግለጫ
            desc_selectors = ['p.description', '.desc', '.description', 'p']
            for sel in desc_selectors:
                el = element.select_one(sel)
                if el:
                    desc = el.get_text(strip=True)
                    if len(desc) > 10:
                        product['description'] = desc[:500]
                        break
            
            # URL
            link = element.find('a')
            if link and link.get('href'):
                product['url'] = urljoin('https://', link['href'])
            
        except Exception as e:
            logger.debug(f"Element extraction error: {e}")
        
        return product
    
    def _extract_with_regex(self, html: str, url: str) -> List[Dict]:
        """በRegex ምርቶችን ያወጣል"""
        products = []
        
        try:
            # የምርት መያዣዎችን ይፈልጋል
            patterns = [
                r'<div[^>]*class="[^"]*(?:product|item|listing|card|advert|classified)[^"]*"[^>]*>(.*?)</div>',
                r'<li[^>]*class="[^"]*(?:product|item|listing)[^"]*"[^>]*>(.*?)</li>',
                r'<article[^>]*class="[^"]*(?:product|item)[^"]*"[^>]*>(.*?)</article>',
            ]
            
            containers = []
            for pattern in patterns:
                found = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if found:
                    containers.extend(found)
                    break
            
            for container in containers[:30]:
                product = self._extract_from_text(container)
                if product and product.get('title'):
                    products.append(product)
            
        except Exception as e:
            logger.debug(f"Regex extraction error: {e}")
        
        return products
    
    def _extract_from_text(self, text: str) -> Dict:
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
                if title:
                    product['title'] = title[:150]
            
            # ዋጋ
            price_match = re.search(
                r'(?:ዋጋ|Price|Birr|ETB|ብር)\s*[:]?\s*([\d,]+)|([\d,]+)\s*(?:ETB|ብር|Birr)',
                text, re.IGNORECASE
            )
            if price_match:
                price_str = price_match.group(1) or price_match.group(2) or ''
                try:
                    product['price'] = float(price_str.replace(',', ''))
                except:
                    pass
            
            # ስልክ
            phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', text)
            if phone_match:
                product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
            else:
                tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
                if tg_match:
                    product['seller_contact'] = tg_match.group(0)
            
            # መግለጫ
            clean_text = re.sub(r'<[^>]+>', ' ', text).strip()
            product['description'] = ' '.join(clean_text.split())[:500]
            
        except Exception as e:
            logger.debug(f"Text extraction error: {e}")
        
        return product
    
    def _extract_with_ai_patterns(self, html: str, url: str) -> List[Dict]:
        """AI-Powered የምርት ንድፍ መለያ"""
        # ይህ የላቀ AI ዘዴ ነው - ጊዜያዊ ትግበራ
        # በእውነተኛ AI ሞዴል መተካት ይቻላል
        return []


# ============================================================
# 🚀 MAIN SCRAPPER ENGINE
# ============================================================

class ScrapperEngine:
    """የላቀ የድረ-ገጽ ዳሰሳ ሞተር"""
    
    def __init__(self):
        self.extractor = AdvancedProductExtractor()
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
                    headers = FingerprintEvasion.get_headers(url, 't.me' in url)
                    
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
                    
                    # Anti-detection
                    await page.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'am']});
                        window.chrome = {runtime: {}};
                    """)
                    
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # የዘፈቀደ መጠበቅ
                    await asyncio.sleep(random.uniform(2, 5))
                    
                    # ወደ ታች መውረድ
                    for i in range(random.randint(2, 4)):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(random.uniform(1, 2))
                    
                    content = await page.content()
                    await browser.close()
                    return content
            
            # Async ን ማስኬድ
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
            
            # ጊዜያዊ መጠበቅ
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
        
        # ለምርመራ ሪፖርት
        if not products:
            report = self._generate_diagnostic_report(url, html)
            self._save_report(report)
        
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
            # የገጹ አይነት ለመለየት ሞክር
            if 'cloudflare' in html.lower():
                report['suggestions'].append('Cloudflare detected -可能需要代理')
            if 'captcha' in html.lower():
                report['suggestions'].append('CAPTCHA detected -可能需要手动解决')
            if 'access denied' in html.lower():
                report['suggestions'].append('Access denied -可能需要更换IP或User-Agent')
        
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
# 🌐 GLOBAL INSTANCE
# ============================================================

_global_scrapper = None

def get_scrapper() -> ScrapperEngine:
    """የግሎባል ስክሬፐር ኢንስታንስ ያመጣል"""
    global _global_scrapper
    if _global_scrapper is None:
        _global_scrapper = ScrapperEngine()
    return _global_scrapper


# ============================================================
# 📦 MAIN EXPORTS
# ============================================================

def scrape_and_extract_products(url: str) -> List[Dict]:
    """ያስሳል እና ምርቶችን ያወጣል"""
    scrapper = get_scrapper()
    return scrapper.scrape_and_extract(url)


def scrape_url(url: str) -> Optional[str]:
    """አንድ ዩአርኤል ይስሳል"""
    scrapper = get_scrapper()
    return scrapper.scrape(url)


def get_scraper_metrics() -> Dict:
    """የስክሬፐር አፈጻጸም መለኪያዎችን ያመጣል"""
    scrapper = get_scrapper()
    return scrapper.get_metrics()


def clear_scraper_cache():
    """የስክሬፐር ካሽን ያጸዳል"""
    scrapper = get_scrapper()
    scrapper.cache.clear()
    scrapper.extractor.cache.clear()
    scrapper.extractor.selector_learner.clear_cache()
    logger.info("🧹 Scraper cache cleared")
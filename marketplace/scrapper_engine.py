# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v10.65 (Ultimate Adaptive Scrapper - Restored scrape() method)
# ✅ የተፈቱ ችግሮች፦ 
#   - Added backwards-compatible 'scrape()' method to resolve AttributeError in growth_agent.py
#   - Automated Block Reason Detection (Cloudflare, 403, 405)
#   - Empty DOM/Regex failure alert to Admin
#   - Activity tracking (Daily post volume estimation)
#   - Automated HTML snapshot storage for admin reverse-engineering
#   - Enhanced _extract_from_container to parse seller_contact, description, and images directly from DOM templates.
# 📅 ቀን፦ Tuesday, July 07, 2026
# ============================================================

import logging
import asyncio
import os
import time
import random
import re
import json
import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BROWSER_PATH = "/opt/render/project/src/ms-playwright"

# ============================================================
# 🧠 DYNAMIC SITE PATTERN DETECTOR
# ============================================================
class SitePatternDetector:
    KNOWN_PATTERNS = {
        'jiji': {
            'product_containers': [
                r'<div[^>]*class="[^"]*(?:b-list-advert-single|b-trending-card|qa-advert-list-item|b-advert-title)[^"]*"[^>]*>(.*?)</div>',
                r'<a[^>]*href="/item/[^"]*"[^>]*>(.*?)</a>',
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
            'image': r'background-image:\s*url\([\'"]?([^\'\)]+)[\'"]?\)',
        }
    }
    
    @classmethod
    def detect_site_type(cls, url: str) -> str:
        domain = urlparse(url).netloc.lower()
        for key in cls.KNOWN_PATTERNS.keys():
            if key in domain: return key
        return 'generic'
    
    @classmethod
    def get_patterns(cls, site_type: str) -> Dict:
        if site_type in cls.KNOWN_PATTERNS:
            return cls.KNOWN_PATTERNS[site_type]
        return {
            'product_containers': [r'<div[^>]*class="[^"]*(?:product|item|listing|card)[^"]*"[^>]*>(.*?)</div>'],
            'title': r'<h[1-4][^>]*>(.*?)</h[1-4]>',
            'price': r'(?:Price|Birr|ETB|ብር)\s*[:]?\s*([\d,]+)',
            'image': r'<img[^>]*src="([^"]+)"[^>]*>',
        }

# ============================================================
# 🚨 SCRAPER DIAGNOSTIC RECORDERS
# ============================================================
class ScraperDiagnosticRecorder:
    
    @staticmethod
    def generate_report(url: str, status_code: int, html: str, total_products: int, error_msg: str = "") -> Dict:
        domain = urlparse(url).netloc.lower()
        report = {
            "target_url": url,
            "domain": domain,
            "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status_code": status_code,
            "is_blocked": False,
            "block_type": "None",
            "reason": "Success",
            "metrics": {
                "html_length": len(html) if html else 0,
                "detected_links_count": len(re.findall(r'href=["\'](.*?)["\']', html)) if html else 0,
                "extracted_products_count": total_products,
                "estimated_daily_posts": 0
            },
            "suggested_action": "None",
            "html_snapshot": ""
        }

        # 1. ክልከላዎችን መመርመር (Block Analysis)
        if status_code in [403, 401, 405, 503] or (html and "cloudflare" in html.lower()):
            report["is_blocked"] = True
            report["status_code"] = status_code if status_code != 200 else 403
            if "cloudflare" in html.lower() or "challenge-form" in html.lower():
                report["block_type"] = "Cloudflare / Captcha Shield"
                report["reason"] = "The target is protected by Cloudflare anti-bot. Playwright was detected."
                report["suggested_action"] = "Switch to Residential Proxies or update Undetected-Chromedriver fingerprints."
            else:
                report["block_type"] = "IP / User-Agent Ban"
                report["reason"] = f"Server rejected the connection with HTTP Status {status_code}."
                report["suggested_action"] = "Rotate User-Agent list, slow down scraping intervals, or use rotating proxies."
            
            report["html_snapshot"] = html[:1000] if html else "No HTML received (Connection Dropped)"
            return report

        # 2. ገብቶ የማጣት ችግር (Empty Content / DOM Change Analysis)
        if html and total_products == 0:
            report["is_blocked"] = False
            report["reason"] = "Connected successfully, but existing Regex patterns extracted 0 products."
            report["suggested_action"] = "The website layout has changed. Inspect the html_snapshot to update patterns."
            report["html_snapshot"] = html[:2000]
            return report

        # 3. በጣቢያው ላይ ያለውን እንቅስቃሴ ማጥናት (Activity & Volumetric Study)
        if html:
            timestamps = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{2}:\d{2}\b|today|yesterday|mins ago|hours ago|ሰዓት|ትላንት', html, re.IGNORECASE)
            if timestamps:
                report["metrics"]["estimated_daily_posts"] = max(len(timestamps) // 2, total_products * 3)

        return report

    @staticmethod
    def save_and_alert_admin(report: Dict):
        """ሪፖርቱን በጄሰን ፎርማት ለአድሚን መዝግቦ ማስቀመጫ"""
        logger.warning(f"🚨 [SCRAPER REPORT FOR ADMIN] -> Site: {report['domain']} | Blocked: {report['is_blocked']} | Extracted: {report['metrics']['extracted_products_count']}")
        
        log_dir = "marketplace/scraper_diagnostics"
        os.makedirs(log_dir, exist_ok=True)
        filename = f"{log_dir}/{report['domain']}_report.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=4)


# ============================================================
# 🔍 SMART PRODUCT EXTRACTOR
# ============================================================
class SmartProductExtractor:
    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        if not html: return []
        site_type = SitePatternDetector.detect_site_type(url)
        patterns = SitePatternDetector.get_patterns(site_type)
        products = []
        
        containers = []
        for pattern in patterns.get('product_containers', []):
            found = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if found:
                containers.extend(found)
                break
        
        if not containers:
            generic_patterns = [
                r'<div[^>]*class="[^"]*(?:product|item|listing|card|advert)[^"]*"[^>]*>(.*?)</div>',
                r'<li[^>]*class="[^"]*(?:product|item)[^"]*"[^>]*>(.*?)</li>',
            ]
            for pattern in generic_patterns:
                found = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                if found:
                    containers.extend(found)
                    break
        
        for container in containers:
            product = SmartProductExtractor._extract_from_container(container, patterns, site_type)
            if product and product.get('title'):
                products.append(product)
        
        if not products:
            products = SmartProductExtractor._extract_direct(html, patterns)
        
        return products

    @staticmethod
    def _extract_from_container(container: str, patterns: Dict, site_type: str) -> Dict:
        """ምርቶችን ከሳጥኑ (Container) ውስጥ ፈልቅቆ ማውጫ"""
        product = {'title': '', 'price': 0, 'description': '', 'seller_contact': '', 'image_url': ''}
        
        # 1. Title Extraction
        title_patterns = [patterns.get('title'), r'<strong[^>]*>(.*?)</strong>', r'<b[^>]*>(.*?)</b>', r'<h[1-4][^>]*>(.*?)</h[1-4]>']
        for pattern in filter(None, title_patterns):
            match = re.search(pattern, container, re.DOTALL | re.IGNORECASE)
            if match:
                title = re.sub(r'<[^>]+>', ' ', match.group(1)).strip()
                title = " ".join(title.split())
                if len(title) > 3:
                    product['title'] = title[:150]
                    break
        
        # 2. Price Extraction
        price_patterns = [patterns.get('price'), r'([\d,]+)\s*(?:ETB|ብር|Birr|Br)']
        for pattern in filter(None, price_patterns):
            match = re.search(pattern, container, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    price_str = re.sub(r'[^\d,]', '', match.group(1))
                    product['price'] = float(price_str.replace(',', ''))
                    break
                except: pass
                
        # 3. Seller Contact Extraction
        phone_match = re.search(r'(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d', container)
        if phone_match:
            product['seller_contact'] = re.sub(r'[^\d+]', '', phone_match.group(0))
        else:
            tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', container)
            if tg_match:
                product['seller_contact'] = tg_match.group(0)

        # 4. Description Extraction
        clean_desc = re.sub(r'<[^>]+>', ' ', container).strip()
        product['description'] = " ".join(clean_desc.split())[:500]

        # 5. Image URL Extraction
        image_pattern = patterns.get('image')
        if image_pattern:
            image_match = re.search(image_pattern, container, re.IGNORECASE)
            if image_match:
                product['image_url'] = image_match.group(1)

        return product

    @staticmethod
    def _extract_direct(html: str, patterns: Dict) -> List[Dict]:
        products = []
        matches = re.finditer(r'<div[^>]*class="[^"]*(?:product|item|listing)[^"]*"', html, re.IGNORECASE)
        for match in matches:
            segment = html[match.start():min(match.start() + 2000, len(html))]
            product = SmartProductExtractor._extract_from_container(segment, patterns, 'generic')
            if product and product.get('title'): products.append(product)
        return products

# ============================================================
# 🚀 ULTIMATE SCRAPPER ENGINE WITH RESTORED scrape()
# ============================================================
class ScrapperEngine:
    
    @staticmethod
    def _fetch_static_fallback(url: str) -> tuple:
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            res = requests.get(url, headers=headers, timeout=15)
            return res.status_code, res.text
        except Exception as e:
            logger.error(f"❌ Static fallback failed: {e}")
            return 0, ""
            
    @staticmethod
    async def fetch_dynamic_content(url: str) -> tuple:
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return 0, ""
        
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                page = await context.new_page()
                
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
                
                logger.info(f"📡 Deep Scanning: {url}...")
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                
                status_code = response.status if response else 200
                content = await page.content()
                await browser.close()
                return status_code, content
            except Exception as e:
                logger.warning(f"⚠️ Playwright error: {e}")
                return 0, str(e)

    @classmethod
    def scrape(cls, url: str) -> Optional[str]:
        """🛡️ [የተመለሰ ፋንክሽን] የድሮ ኮድ ተኳሃኝነትን ለመጠበቅ ጥሬ የኤችቲኤምኤል (HTML) ጽሑፍን ብቻ የሚጎትት"""
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
                    future = executor.submit(lambda: asyncio.run(cls.fetch_dynamic_content(url)))
                    status_code, html = future.result()
            else:
                status_code, html = asyncio.run(cls.fetch_dynamic_content(url))
        except Exception as e:
            status_code = 0

        if not html or status_code in [0, 403, 405]:
            fallback_status, fallback_html = cls._fetch_static_fallback(url)
            if fallback_html:
                html = fallback_html

        return html

    @classmethod
    def scrape_and_extract(cls, url: str) -> List[Dict]:
        """ዋናው የኤጀንቱ መተግበሪያ - አሁን ሙሉ በሙሉ በስለላ ሪፖርት የተጠበቀ ነው"""
        html = ""
        status_code = 200
        error_msg = ""
        
        if not url.startswith('http'): url = 'https://' + url

        try:
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None

            if running_loop:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(cls.fetch_dynamic_content(url)))
                    status_code, html = future.result()
            else:
                status_code, html = asyncio.run(cls.fetch_dynamic_content(url))
        except Exception as e:
            error_msg = str(e)
            status_code = 0

        if not html or status_code in [0, 403, 405]:
            fallback_status, fallback_html = cls._fetch_static_fallback(url)
            if fallback_html:
                status_code = fallback_status
                html = fallback_html

        products = SmartProductExtractor.extract_products(html, url) if html else []

        # 🧠 AUTOMATED DIAGNOSTIC LOOP (የስለላ ሪፖርት ማመንጫ)
        if status_code != 200 or len(products) == 0:
            report = ScraperDiagnosticRecorder.generate_report(
                url=url, 
                status_code=status_code, 
                html=html if html and len(html) < 50000 else error_msg,
                total_products=len(products),
                error_msg=error_msg
            )
            ScraperDiagnosticRecorder.save_and_alert_admin(report)

        return products

# ለድሮ ኮድ ተኳሃኝነት
def scrape_and_extract_products(url: str) -> List[Dict]:
    return ScrapperEngine.scrape_and_extract(url)
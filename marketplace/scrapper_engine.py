# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v12.30 (Enterprise Multi-Platform Scrapper)
# ============================================================

import logging
import asyncio
import os
import time
import random
import re
import html as html_parser
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
BROWSER_PATH = "/opt/render/project/src/ms-playwright"

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

class SmartProductExtractor:
    @staticmethod
    def _clean_image_url(img_url: str, base_url: str) -> str:
        if not img_url: return ""
        if ',' in img_url:
            parts = [p.strip().split(' ')[0] for p in img_url.split(',')]
            img_url = parts[-1]
        img_url = img_url.strip()
        if img_url.startswith('//'): img_url = 'https:' + img_url
        elif img_url.startswith('/') or not img_url.startswith('http'):
            img_url = urljoin(base_url, img_url)
        img_url = re.sub(r'_\d+x\d+\.(jpeg|jpg|png|webp)', r'.\1', img_url)
        return img_url

    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        if not html: return []
        products = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            selectors = ['div.b-list-advert-single', 'div.qa-advert-list-item', 'div[class*="product"]', 'div[class*="card"]']
            for selector in selectors:
                elements = soup.select(selector)
                for elem in elements[:20]:
                    prod = SmartProductExtractor._extract_from_soup_node(elem, url)
                    if prod.get('title'): products.append(prod)
                if products: break
        except Exception as e:
            logger.error(f"Extraction error: {e}")
        return products

    @staticmethod
    def _extract_from_soup_node(node, base_url: str) -> Dict:
        product = {'title': '', 'price': 0.0, 'description': '', 'seller_contact': '', 'image_url': ''}
        title_el = node.find(['h3', 'h4', 'span'], class_=re.compile(r'title|name', re.I))
        if title_el: product['title'] = title_el.get_text(strip=True)[:150]
        
        price_el = node.find(class_=re.compile(r'price', re.I))
        if price_el:
            price_str = re.sub(r'[^\d]', '', price_el.get_text(strip=True))
            product['price'] = float(price_str) if price_str else 0.0
            
        img_el = node.find('img')
        if img_el:
            url = img_el.get('data-src') or img_el.get('src')
            if url: product['image_url'] = SmartProductExtractor._clean_image_url(url, base_url)
            
        return product

class ScrapperEngine:
    @staticmethod
    async def fetch_dynamic_content(url: str) -> tuple:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                content = await page.content()
                await browser.close()
                return 200, content
            except Exception as e:
                return 0, str(e)

    @staticmethod
    def scrape_and_extract(url: str) -> List[Dict]:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        status, html = loop.run_until_complete(ScrapperEngine.fetch_dynamic_content(url))
        return SmartProductExtractor.extract_products(html, url)

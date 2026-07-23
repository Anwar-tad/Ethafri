# =================================================================
#  scrapper_engine.py – high‑performance, thread‑safe, self‑healing
#  v11.00 • SmartProductExtractor fully upgraded with native match index pricing
#         • Render CPU Guard integrated to prevent heavy browser OOM crashes
#         • requests.Session() with local cookie & language header spoofing
#         • Dual-engine fallback for DuckDuckGo and Google Search lookup
# =================================================================

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
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.utils import timezone

# --------------------------------------------------------------
#  Optional BeautifulSoup (Gracefully degrades to regex if missing)
# --------------------------------------------------------------
try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    BeautifulSoup = None
    _HAS_BS4 = False

# --------------------------------------------------------------
#  Global logger
# --------------------------------------------------------------
logger = logging.getLogger(__name__)

# ==============================================================
#  Centralised configuration (tunable constants)
# ==============================================================
class ScraperConfig:
    BROWSER_PATH: str = "/opt/render/project/src/ms-playwright"
    SCRAPEOPS_ENDPOINT: str = "https://proxy.scrapeops.io/v1/"
    REQUEST_TIMEOUT: int = 30
    PLAYWRIGHT_TIMEOUT: int = 60
    RATE_LIMIT_RANGE: Tuple[float, float] = (0.8, 1.5)
    CACHE_TTL: int = 3600
    SMART_CACHE_TTL: int = 1800
    
    # Extraction tuning 
    MAX_PRODUCTS_PER_PAGE: int = 60
    MIN_TITLE_LEN: int = 8
    MAX_TITLE_LEN: int = 150
    MAX_DESC_LEN: int = 1000
    
    # Ethiopian phone / contact patterns
    PHONE_RE = re.compile(r"(?:\+251|09|07)\s*[\d\s\-\(\)\.]{7,15}\d")
    TELEGRAM_RE = re.compile(r"@[a-zA-Z0-9_]{4,32}")
    
    # Price patterns (Amharic ዋጋ/ብር + English)
    PRICE_RE = re.compile(
        r"(?:ዋጋ|Price|Birr|ETB|ብር)\s*[:፡\-]?\s*([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    PRICE_TAIL_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:ETB|ብር|Birr|Br)", re.IGNORECASE)
    
    # Stale / non‑product markers
    STALE_RE = re.compile(
        r"(?:sold\s*out|out\s*of\sstock|already\s*sold|ended|expired|"
        r"closed\slisting|removed\b)",
        re.IGNORECASE,
    )
    OLD_DATE_RE = re.compile(
        r"(?:2012|2013|2014|2015)\s*(?:ዓ\.?ም|ዓም)?|"
        r"[4-9]\s*months?\s*ago|year\s*ago",
        re.IGNORECASE,
    )
    
    # 🛡️ ቴሌግራም ላይ የሚለጠፉ የምርት ያልሆኑ የሲስተም መልዕክቶች ማጣሪያ
    SYSTEM_MSG_RE = re.compile(
        r"(?:channel\s*created|channel\s*photo\s*updated|channel\s*name\s*was\s*changed|"
        r"live\s*stream\s*started|live\s*stream\s*finished|pinned\s*a\s*message|joined\s*telegram|"
        r"group\s*created|ተለቀቀ|ገብተናል|ገባን|ተከፈተ)",
        re.IGNORECASE
    )


# ==============================================================
#  Helper utilities
# ==============================================================
def _is_telegram(url: str) -> bool:
    return any(x in url.lower() for x in ("t.me", "telegram", "@"))


def _safe_json_load(text: str) -> Optional[Dict]:
    """Parse JSON safely – returns None on any error."""
    try:
        return json.loads(text)
    except Exception as e:
        logger.debug(f"[Scraper] JSON decode error: {e}")
        return None


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


# ==============================================================
#  FingerprintEvasion (user‑agent & header generator)
# ==============================================================
class FingerprintEvasion:
    MOBILE_UA = [
        "Telegram/10.1.0 (iOS 15.4; en)",
        "Telegram/10.3.5 (iPhone; iOS 17.2; en)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Mobile Safari",
    ]
    DESKTOP_UA = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    ]

    @classmethod
    def get_headers(cls, url: str, is_telegram: bool = False) -> Dict[str, str]:
        ua = random.choice(cls.MOBILE_UA) if is_telegram or _is_telegram(url) else random.choice(cls.DESKTOP_UA)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "am-ET,am;q=0.9,en-US;q=0.8,en;q=0.7",  # የአማርኛ ቋንቋ ማስመሰል
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
            "Cookie": "lang=et; currency=ETB",  # የሀገር ውስጥ ሻጭ ኩኪዎችን ማስመሰል (Cookie Spoofing)
        }


# ==============================================================
#  Metrics, RateLimiter & SmartCache
# ==============================================================
class ScraperMetrics:
    def __init__(self) -> None:
        self.total_attempts: int = 0
        self.last_scrape_time: Optional[datetime] = None
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.successful_scrapes: int = 0
        self.failed_scrapes: int = 0
        self.errors: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "last_scrape_time": self.last_scrape_time.isoformat() if self.last_scrape_time else None,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "successful_scrapes": self.successful_scrapes,
            "failed_scrapes": self.failed_scrapes,
            "error_count": len(self.errors),
        }


class IntelligentRateLimiter:
    def __init__(self, delay_range: Tuple[float, float] = ScraperConfig.RATE_LIMIT_RANGE) -> None:
        self.delay_range = delay_range
        self.success_count = 0
        self.failure_count = 0
        self.last_request_time = 0.0

    def wait_if_needed(self) -> None:
        now = time.time()
        elapsed = now - self.last_request_time
        delay = random.uniform(*self.delay_range)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()

    def record_success(self) -> None:
        self.success_count += 1

    def record_failure(self) -> None:
        self.failure_count += 1

    def get_stats(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_request_time": self.last_request_time,
        }


class SmartCache:
    def __init__(self, ttl: int = ScraperConfig.CACHE_TTL) -> None:
        self.ttl = ttl
        self.store: Dict[str, Tuple[Any, float]] = {}
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
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
        self.store[key] = (val, time.time() + self.ttl)

    def get_stats(self) -> Dict[str, Any]:
        return {"hits": self.hits, "misses": self.misses, "size": len(self.store)}


# ==============================================================
#  Product extraction  (BeautifulSoup + regex, multi‑strategy)
# ==============================================================
class SmartProductExtractor:
    """Extracts product dicts from marketplace HTML."""

    # 🛡️ የፌስቡክ ማርኬትፕሌስ እና የሀገር ውስጥ ድረ-ገጾች ልዩ አሰሳ መዋቅሮች
    FB_LISTING_SELECTORS = [
        "div[role='feed'] div[style*='max-width']",
        "div.x9f619.x78zum5.x1r8u6il",
        "div[class*='x1lliihq']",
        "div.product-card",
    ]
    FB_TITLE_SELECTORS = [
        "span[style*='-webkit-line-clamp']",
        "span.x1lliihq.x6ikm8r",
        "h2",
    ]
    FB_PRICE_SELECTORS = [
        "span.x193iq5w.xeuugli",
        "div.x1zoom55.x1lliihq",
        "span.price",
    ]

    JIJI_LISTING_SELECTORS = [
        "div.b-list-advert__item",
        "div.b-list-advert",
        "article.b-list-advert",
        "div[data-cy=\"l-ad\"]",
        "div.listing",
    ] + FB_LISTING_SELECTORS
    
    JIJI_TITLE_SELECTORS = [
        "h4.b-advert-title-inner",
        "a.b-advert-title",
        "h4.ta-title",
        "div.b-advert-title",
    ] + FB_TITLE_SELECTORS
    
    JIJI_PRICE_SELECTORS = [
        "div.b-j-advert__price",
        "span.b-advert-price",
        "div.b-advert-price",
    ] + FB_PRICE_SELECTORS
    
    JIJI_IMG_SELECTORS = [
        "div.b-advert-images-inner img",
        "img.b-advert-image",
        "img[data-cy=\"ad-image\"]",
        "img",
    ]

    GENERIC_CARD_SELECTORS = [
        "div.product",
        "div.product-card",
        "div.product-item",
        "div.card.product",
        "li.product",
        "article.product",
        "div[class*=\"product\"]",
        "div[class*=\"listing\"]",
        "div[class*=\"item\"]",
    ]
    GENERIC_TITLE_SELECTORS = [
        "h2 a", "h3 a", "h4 a",
        ".product-title", ".product-name", ".title",
        "[itemprop=\"name\"]",
        "a[class*=\"title\"]",
    ]
    GENERIC_PRICE_SELECTORS = [
        ".price", ".product-price", ".amount",
        "[itemprop=\"price\"]", "[itemprop=\"price\"] [content]",
        ".price-box .price",
    ]
    GENERIC_IMG_SELECTORS = [
        "img[itemprop=\"image\"]",
        ".product-image img",
        ".card-img-top img",
        "img[class*=\"product\"]",
        "img",
    ]

    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        if not html or not html.strip():
            return []

        domain = _extract_domain(url)
        products: List[Dict] = []
        seen_titles: set = set()

        for p in SmartProductExtractor._extract_from_jsonld(html, url):
            t = (p.get("title") or "").strip().lower()
            if t and t not in seen_titles:
                seen_titles.add(t)
                products.append(p)
            if len(products) >= ScraperConfig.MAX_PRODUCTS_PER_PAGE:
                return products

        if len(products) >= ScraperConfig.MAX_PRODUCTS_PER_PAGE:
            return products

        if _HAS_BS4:
            try:
                soup = BeautifulSoup(html, "html.parser")
            except Exception as e:
                logger.debug(f"[Extractor] BeautifulSoup parse failed: {e}")
                soup = None

            if soup is not None:
                for p in SmartProductExtractor._extract_with_selectors(
                    soup, url,
                    SmartProductExtractor.JIJI_LISTING_SELECTORS,
                    SmartProductExtractor.JIJI_TITLE_SELECTORS,
                    SmartProductExtractor.JIJI_PRICE_SELECTORS,
                    SmartProductExtractor.JIJI_IMG_SELECTORS,
                ):
                    t = (p.get("title") or "").strip().lower()
                    if t and t not in seen_titles:
                        seen_titles.add(t)
                        products.append(p)
                    if len(products) >= ScraperConfig.MAX_PRODUCTS_PER_PAGE:
                        return products

                if len(products) < ScraperConfig.MAX_PRODUCTS_PER_PAGE:
                    for p in SmartProductExtractor._extract_with_selectors(
                        soup, url,
                        SmartProductExtractor.GENERIC_CARD_SELECTORS,
                        SmartProductExtractor.GENERIC_TITLE_SELECTORS,
                        SmartProductExtractor.GENERIC_PRICE_SELECTORS,
                        SmartProductExtractor.GENERIC_IMG_SELECTORS,
                    ):
                        t = (p.get("title") or "").strip().lower()
                        if t and t not in seen_titles:
                            seen_titles.add(t)
                            products.append(p)
                        if len(products) >= ScraperConfig.MAX_PRODUCTS_PER_PAGE:
                            return products

                if not products:
                    og = SmartProductExtractor._extract_og_meta(soup, url)
                    if og and (og.get("title")):
                        products.append(og)

        if not products:
            for p in SmartProductExtractor._extract_with_regex(html, url):
                t = (p.get("title") or "").strip().lower()
                if t and t not in seen_titles:
                    seen_titles.add(t)
                    products.append(p)
                if len(products) >= ScraperConfig.MAX_PRODUCTS_PER_PAGE:
                    break

        return products

    @staticmethod
    def _extract_from_jsonld(html: str, url: str) -> List[Dict]:
        out: List[Dict] = []
        if not _HAS_BS4:
            for m in re.finditer(
                r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>',
                html, re.IGNORECASE,
            ):
                SmartProductExtractor._ingest_jsonld_blob(m.group(1), url, out)
            return out

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return out
        for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
            SmartProductExtractor._ingest_jsonld_blob(tag.string or tag.get_text() or "", url, out)
        return out

    @staticmethod
    def _ingest_jsonld_blob(raw: str, url: str, out: List[Dict]) -> None:
        data = _safe_json_load(raw.strip())
        if data is None:
            return
        if isinstance(data, dict) and "@graph" in data:
            data = data["@graph"]
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data]
        else:
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            itype = (item.get("@type") or "").lower()
            if itype and "product" not in itype and "offer" not in itype:
                continue
            title = (item.get("name") or "").strip()
            import html as _html
            title = _html.unescape(title)
            if not title or len(title) < ScraperConfig.MIN_TITLE_LEN:
                continue
            price = 0.0
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                p_raw = offers.get("price") or offers.get("lowPrice")
                if p_raw is None and offers.get("priceSpecification"):
                    ps = offers["priceSpecification"]
                    if isinstance(ps, dict):
                        p_raw = ps.get("price")
                if p_raw is not None:
                    try:
                        price = float(str(p_raw).replace(",", ""))
                    except (ValueError, TypeError):
                        price = 0.0
            image = item.get("image") or ""
            if isinstance(image, list):
                image = image[0] if image else ""
            if image:
                image = urljoin(url, str(image))
            desc = (item.get("description") or "").strip()
            desc = _html.unescape(desc)
            out.append({
                "title": title[:ScraperConfig.MAX_TITLE_LEN],
                "price": price,
                "description": desc[:ScraperConfig.MAX_DESC_LEN],
                "desc": desc[:ScraperConfig.MAX_DESC_LEN],
                "seller_contact": "0900000000",
                "image_url": image,
                "source_url": url,
                "listing_type": "sale",
            })

    @staticmethod
    def _extract_with_selectors(
        soup, url: str,
        card_sels: List[str],
        title_sels: List[str],
        price_sels: List[str],
        img_sels: List[str],
    ) -> List[Dict]:
        out: List[Dict] = []
        nodes: List = []
        for sel in card_sels:
            try:
                found = soup.select(sel)
            except Exception:
                found = []
            if found:
                nodes = found
                break
        if not nodes:
            return out
        for node in nodes:
            try:
                prod = SmartProductExtractor._extract_from_soup_node(
                    node, url, title_sels, price_sels, img_sels,
                )
            except Exception as e:
                logger.debug(f"[Extractor] node parse error: {e}")
                continue
            if prod and prod.get("title"):
                out.append(prod)
        return out

    @staticmethod
    def _extract_from_soup_node(
        node, url: str = "",
        title_sels: Optional[List[str]] = None,
        price_sels: Optional[List[str]] = None,
        img_sels: Optional[List[str]] = None,
    ) -> Dict:
        if node is None:
            return {}

        title_sels = title_sels or SmartProductExtractor.GENERIC_TITLE_SELECTORS
        price_sels = price_sels or SmartProductExtractor.GENERIC_PRICE_SELECTORS
        img_sels = img_sels or SmartProductExtractor.GENERIC_IMG_SELECTORS

        def _first_text(selectors: List[str]) -> str:
            for sel in selectors:
                try:
                    el = node.select_one(sel)
                except Exception:
                    el = None
                if el:
                    txt = el.get_text(strip=True)
                    if txt:
                        return txt
            return ""

        def _first_img(selectors: List[str]) -> str:
            for sel in selectors:
                try:
                    el = node.select_one(sel)
                except Exception:
                    el = None
                if el and el.name == "img":
                    src = el.get("data-src") or el.get("src") or ""
                    if src:
                        return urljoin(url, src)
                if el:
                    style = el.get("style") or ""
                    m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", style)
                    if m:
                        return urljoin(url, m.group(1))
            return ""

        title = _first_text(title_sels)
        if not title:
            for cand in node.find_all(["h1", "h2", "h3", "h4", "h5", "a"], limit=3):
                txt = cand.get_text(strip=True)
                if txt and len(txt) >= ScraperConfig.MIN_TITLE_LEN:
                    title = txt
                    break
        if not title:
            title = node.get_text(" ", strip=True)
            
        import html as _html
        title = _html.unescape(title)
        
        # 🛡️ Boilerplate Stripper (የቆሻሻ የJiji እና የዋጋ መግለጫዎችን ከርዕስ ላይ መቁረጥ)
        title = re.sub(r'\d+\+?\s*(?:years?|ዓመታት|months?|ወራት)\s*(?:on Jiji|በ Jiji ላይ)', '', title, flags=re.I)
        title = re.sub(r'(?:ETB|Birr|ብር)\s*[:፡-]?\s*[\d,]+', '', title, flags=re.I)
        title = re.sub(r'[\d,]+\s*(?:ETB|Birr|ብር)', '', title, flags=re.I)
        
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) < ScraperConfig.MIN_TITLE_LEN:
            return {}
        title = title[:ScraperConfig.MAX_TITLE_LEN]

        price_text = _first_text(price_sels)
        price = SmartProductExtractor._parse_price(price_text)
        if price == 0.0:
            price = SmartProductExtractor._parse_price(node.get_text(" ", strip=True))

        node_text = node.get_text(" ", strip=True)
        node_text = _html.unescape(node_text)
        contact = SmartProductExtractor._parse_contact(node_text)
        image_url = _first_img(img_sels)

        desc = node_text
        desc = re.sub(r"\s+", " ", desc)[:ScraperConfig.MAX_DESC_LEN].strip()

        if SmartProductExtractor._is_stale(node_text):
            return {}

        return {
            "title": title,
            "price": price,
            "description": desc,
            "desc": desc,
            "seller_contact": contact,
            "image_url": image_url,
            "source_url": url,
            "listing_type": SmartProductExtractor._guess_listing_type(node_text),
        }

    @staticmethod
    def _extract_og_meta(soup, url: str) -> Optional[Dict]:
        def _meta(prop: str) -> str:
            tag = soup.find("meta", attrs={"property": prop}) or \
                  soup.find("meta", attrs={"name": prop})
            return (tag.get("content") or "").strip() if tag else ""

        title = _meta("og:title") or ""
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
            
        import html as _html
        title = _html.unescape(title)
        if len(title) < ScraperConfig.MIN_TITLE_LEN:
            return None

        price = SmartProductExtractor._parse_price(_meta("og:description"))
        image = _meta("og:image")
        if image:
            image = urljoin(url, image)
        desc = _meta("og:description") or soup.get_text(" ", strip=True)
        desc = _html.unescape(desc)
        desc = re.sub(r"\s+", " ", desc)[:ScraperConfig.MAX_DESC_LEN].strip()
        contact = SmartProductExtractor._parse_contact(desc)

        return {
            "title": title[:ScraperConfig.MAX_TITLE_LEN],
            "price": price,
            "description": desc,
            "desc": desc,
            "seller_contact": contact,
            "image_url": image,
            "source_url": url,
            "listing_type": SmartProductExtractor._guess_listing_type(desc),
        }

    @staticmethod
    def _extract_with_regex(html: str, url: str) -> List[Dict]:
        out: List[Dict] = []
        text = re.sub(r"<[^>]+>", "\n", html)
        import html as _html
        text = _html.unescape(text)
        text = re.sub(r"\n{2,}", "\n", text)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        block: List[str] = []
        for line in lines:
            if len(line) >= ScraperConfig.MIN_TITLE_LEN and not block:
                block = [line]
            elif block:
                block.append(line)
                if len(block) >= 6:
                    blk_text = "\n".join(block)
                    prod = SmartProductExtractor._block_to_product(blk_text, url)
                    if prod:
                        out.append(prod)
                    block = []
        if block:
            prod = SmartProductExtractor._block_to_product("\n".join(block), url)
            if prod:
                out.append(prod)
        return out

    @staticmethod
    def _block_to_product(text: str, url: str) -> Optional[Dict]:
        title = ""
        for line in text.split("\n"):
            if len(line) >= ScraperConfig.MIN_TITLE_LEN:
                title = line[:ScraperConfig.MAX_TITLE_LEN]
                break
        if not title:
            return None
        
        import html as _html
        title = _html.unescape(title)
        price = SmartProductExtractor._parse_price(text)
        contact = SmartProductExtractor._parse_contact(text)
        if SmartProductExtractor._is_stale(text):
            return None
        desc = re.sub(r"\s+", " ", text)[:ScraperConfig.MAX_DESC_LEN].strip()
        return {
            "title": title,
            "price": price,
            "description": desc,
            "desc": desc,
            "seller_contact": contact,
            "image_url": "",
            "source_url": url,
            "listing_type": SmartProductExtractor._guess_listing_type(text),
        }

    # ----------------------------------------------------------
    #  Shared parsing helpers (Deduplicated & Amharic-aware)
    # ----------------------------------------------------------
    @staticmethod
    def _parse_price(text: str) -> float:
        if not text:
            return 0.0
        m = ScraperConfig.PRICE_RE.search(text) or ScraperConfig.PRICE_TAIL_RE.search(text)
        if not m:
            m = re.search(r"(?<!\d)([\d,]{4,9})(?!\d)", text)
        if not m:
            return 0.0
        try:
            val_str = m.group(1).replace(",", "")
            val = float(val_str)
            
            # 🛡️ FIXED: Native match index-based slicing completely avoids comma mismatch bugs [1]
            text_lower = text.lower()
            start_idx = m.start()
            end_idx = m.end()
            matched_price_segment = text_lower[max(0, start_idx - 10) : end_idx + 10]
            
            amharic_numeral_map = {
                "፩": 1, "፪": 2, "፫": 3, "፬": 4, "፭": 5, "፮": 6, "፯": 7, "፰": 8, "፺": 9,
                "፲": 10, "፳": 20, "፴": 30, "፵": 40, "፶": 50, "፷": 60, "፸": 70, "፹": 80, "፺": 90,
                "፻": 100, "ሺ": 1000, "ሺህ": 1000, "ሚሊዮን": 1000000, "k": 1000, "m": 1000000
            }
            
            for key, multiplier in amharic_numeral_map.items():
                if key in ["k", "m"]:
                    if re.search(rf"\b{val_str}\s*{key}\b", text_lower):
                        val *= multiplier
                        break
                elif key in matched_price_segment:
                    val *= multiplier
                    break
            return val
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _parse_contact(text: str) -> str:
        if not text:
            return "0900000000"
        m = ScraperConfig.PHONE_RE.search(text)
        if m:
            clean_phone = re.sub(r"[^\d+]", "", m.group(0))
            if clean_phone.startswith('0'):
                clean_phone = '251' + clean_phone[1:]
            elif clean_phone.startswith('+'):
                clean_phone = clean_phone.replace('+', '')
            return clean_phone
            
        m = ScraperConfig.TELEGRAM_RE.search(text)
        if m:
            return m.group(0)
        return "0900000000"

    @staticmethod
    def _is_stale(text: str) -> bool:
        if not text:
            return False
        if ScraperConfig.STALE_RE.search(text):
            return True
        if ScraperConfig.OLD_DATE_RE.search(text):
            return True
        if hasattr(ScraperConfig, 'SYSTEM_MSG_RE') and ScraperConfig.SYSTEM_MSG_RE.search(text):
            return True
        return False

    @staticmethod
    def _guess_listing_type(text: str) -> str:
        if not text:
            return "sale"
        low = text.lower()
        if any(w in low for w in ("rent", "ኪራይ", "lease", "ኩራይ", "monthly rent")):
            return "rent"
        if any(w in low for w in ("service", "አገልግሎት", "repair", "fix", "ጥገና", "cleaning")):
            return "service"
        return "sale"


# ==============================================================
#  AdvancedProductExtractor  (caching wrapper)
# ==============================================================
class AdvancedProductExtractor:
    def __init__(self) -> None:
        self.cache = SmartCache(ttl=ScraperConfig.SMART_CACHE_TTL)

    def extract_products(self, html: str, url: str) -> List[Dict]:
        cache_key = hashlib.md5(f"extract:{url}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        products = SmartProductExtractor.extract_products(html, url)
        self.cache.set(cache_key, products)
        return products


# ==============================================================
#  ScrapperEngine – thread‑safe singleton with async Playwright runner
# ==============================================================
_engine_lock = threading.Lock()

class ScrapperEngine:
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
        self.session = requests.Session()  # 🛡️ ቋሚ የኩኪ እና የብሮውዘር ሴሽን መፍጠሪያ
        self.session_counter = 0

    @classmethod
    def scrape(cls, url: str, use_playwright: Optional[bool] = None) -> Optional[str]:
        inst = cls()
        if not url:
            return None

        norm_url = url.rstrip("/")
        scrapeops_key = os.getenv('SCRAPEOPS_API_KEY', '').strip()
        use_scrapeops = bool(scrapeops_key) and not _is_telegram(norm_url)

        if use_playwright is None:
            use_playwright = not use_scrapeops

        try:
            inst.metrics.total_attempts += 1
            inst.metrics.last_scrape_time = datetime.now()
        except Exception:
            pass

        cache_key = hashlib.md5(f"{norm_url}:{use_playwright}".encode()).hexdigest()
        cached = inst.cache.get(cache_key)
        if cached:
            try:
                inst.metrics.cache_hits += 1
            except Exception:
                pass
            return cached

        try:
            inst.metrics.cache_misses += 1
        except Exception:
            pass

        inst.rate_limiter.wait_if_needed()

        if not norm_url.startswith("http"):
            norm_url = "https://" + norm_url

        html: Optional[str] = None

        if use_scrapeops:
            try:
                logger.info("[Scraper] Routing via ScrapeOps proxy")
                payload = {"api_key": scrapeops_key, "url": norm_url, "bypass": "cloudflare"}
                res = requests.get(ScraperConfig.SCRAPEOPS_ENDPOINT, params=payload, timeout=ScraperConfig.REQUEST_TIMEOUT)
                if res.status_code == 200:
                    html = res.text
            except Exception as e:
                logger.warning(f"[Scraper] ScrapeOps failed: {e}")

        playwright_installed = False
        if use_playwright and not use_scrapeops:
            try:
                if os.path.isdir(ScraperConfig.BROWSER_PATH) and os.listdir(ScraperConfig.BROWSER_PATH):
                    playwright_installed = True
                else:
                    import playwright
                    playwright_installed = True
            except Exception:
                pass

        if not html and playwright_installed:
            html = inst._scrape_with_playwright(norm_url)

        if not html:
            html = inst._scrape_with_requests(norm_url)

        if html:
            try:
                inst.metrics.successful_scrapes += 1
                inst.rate_limiter.record_success()
                inst.cache.set(cache_key, html)
            except Exception:
                pass
        else:
            try:
                inst.metrics.failed_scrapes += 1
                inst.rate_limiter.record_failure()
                inst.metrics.errors.append(f"Failed to scrape {norm_url}")
            except Exception:
                pass

        return html

    def _run_async_in_new_thread(self, coro):
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
        # 🛡️ RENDER Performance Safeguard: Disable heavy browser launch under high CPU load average
        try:
            load_avg = os.getloadavg()[0]
        except (AttributeError, OSError, Exception):
            load_avg = 0.5
            
        if load_avg > 1.5:
            logger.warning(f"⚠️ CPU Load is heavy ({load_avg:.2f}). Playwright launch bypassed to protect RAM.")
            return None

        try:
            return self._run_async_in_new_thread(self._async_playwright_fetch(url))
        except Exception as e:
            logger.warning(f"[Scraper] Playwright error for {url}: {e}")
            return None

    async def _async_playwright_fetch(self, url: str) -> Optional[str]:
        from playwright.async_api import async_playwright
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
        try:
            headers = FingerprintEvasion.get_headers(url, _is_telegram(url))
            time.sleep(random.uniform(1, 3))
            
            # 🛡️ FIXED: ቋሚውን self.session በመጠቀም Cloudflare እገዳዎችን ማለፍ
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
        html = cls.scrape(url)
        if not html:
            return []
        products = cls().extractor.extract_products(html, url)
        if not products:
            report = cls()._generate_diagnostic_report(url, html)
            cls()._save_report(report)
        return products

    def _generate_diagnostic_report(self, url: str, html: Optional[str]) -> Dict:
        domain = urlparse(url).netloc.lower()
        return {
            "url": url,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "html_length": len(html) if html else 0,
            "products_found": 0,
            "status": "failed",
            "bs4_available": _HAS_BS4,
            "suggestions": [
                "Check if the site uses a SPA framework (needs Playwright).",
                "Verify product card selectors match the target site's HTML.",
                "Inspect data/diagnostics for the saved HTML length.",
            ],
            "metrics": self.metrics.to_dict(),
            "rate_limiter": self.rate_limiter.get_stats(),
            "cache_stats": self.cache.get_stats(),
        }

    def _save_report(self, report: Dict) -> None:
        try:
            os.makedirs("data/diagnostics", exist_ok=True)
            fn = f"data/diagnostics/{report['domain']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fn, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"[Scraper] Failed to write diagnostic report: {e}")

    @classmethod
    def get_metrics(cls) -> Dict:
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

    # ==================================================================
    #  Unauthenticated Search Engine Fallback
    # ==================================================================
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
        
        # 1. መጀመሪያ በ DuckDuckGo መሞከር
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                raw_html = res.text
        except Exception:
            pass

        # 2. DuckDuckGo ካልሠራ ወዲያውኑ ወደ Google Search Fallback መሸጋገር
        if not raw_html:
            try:
                google_url = f"https://www.google.com/search?q={quote(query)}"
                res = requests.get(google_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    raw_html = res.text
            except Exception:
                pass

        # 3. Google ካልሠራ ወደ Bing Search Fallback መሸጋገር
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

        # 🟢 ሀ. ለ growth_agent.py የቴሌግራም ሊንኮች ተለይተው ከተጠየቁ
        if extract_telegram_links:
            telegram_usernames = re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', raw_html)
            fallback_sources = []
            for username in list(set(telegram_usernames))[:4]:
                if username.lower() not in ['s', 'joinchat', 'share', 'tgme']:
                    fallback_sources.append({"url_or_channel": username, "platform_type": "Telegram"})
            return fallback_sources

        # 🟢 ለ. ለ ai_utils.py የጽሑፍ ማጠቃለያዎች ከተጠየቁ
        results = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', raw_html, re.DOTALL)
        snippets = []
        for r in results[:5]:
            clean_r = re.sub(r'<[^>]+>', ' ', r).strip()
            if clean_r:
                snippets.append(clean_r)
        return "\n".join(snippets)


# ==============================================================
#  Compatibility layer
# ==============================================================
_shared_engine = ScrapperEngine()

def scrape_and_extract_products(url: str) -> List[Dict]:
    return _shared_engine.scrape_and_extract(url)

def scrape_url(url: str) -> Optional[str]:
    return _shared_engine.scrape(url)
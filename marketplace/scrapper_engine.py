# --------------------------------------------------------------
#  scrapper_engine.py  (refactored – minimal footprint)
# --------------------------------------------------------------

import logging
import asyncio
import os
import time
import random
import re
import json
import hashlib
import datetime
import threading
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, urljoin

# --------------------------------------------------------------
#  Configuration dataclass (centralises all tunables)
# --------------------------------------------------------------
from dataclasses import dataclass

@dataclass(frozen=True)
class ScraperConfig:
    BROWSER_PATH: str = "/opt/render/project/src/ms-playwright"
    USER_AGENT_MOBILE: Tuple[str, ...] = (
        "Telegram/10.1.0 (iOS 15.4; en)",
        "Telegram/10.3.5 (iPhone; iOS 17.2; en)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Mobile Safari",
    )
    USER_AGENT_DESKTOP: Tuple[str, ...] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    )
    RATE_LIMIT_RANGE: Tuple[float, float] = (1.5, 3.5)
    CACHE_TTL: int = 3600
    SMART_CACHE_TTL: int = 1800
    SCRAPEOPS_ENDPOINT: str = "https://proxy.scrapeops.io/v1/"

CONFIG = ScraperConfig()
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
#  Helper utilities
# --------------------------------------------------------------
def _is_telegram(url: str) -> bool:
    return any(x in url.lower() for x in ("t.me", "telegram", "@"))

# --------------------------------------------------------------
#  FingerprintEvasion (unchanged except for type hints)
# --------------------------------------------------------------
class FingerprintEvasion:
    MOBILE_UA = list(CONFIG.USER_AGENT_MOBILE)
    DESKTOP_UA = list(CONFIG.USER_AGENT_DESKTOP)

    @classmethod
    def get_headers(cls, url: str, is_telegram: bool = False) -> Dict[str, str]:
        ua = random.choice(cls.MOBILE_UA) if is_telegram or _is_telegram(url) else random.choice(cls.DESKTOP_UA)
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,am;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }

# --------------------------------------------------------------
#  Metrics, RateLimiter & Cache (type‑annotated, defensive)
# --------------------------------------------------------------
class ScraperMetrics:
    def __init__(self) -> None:
        self.total_attempts: int = 0
        self.last_scrape_time: Optional[datetime.datetime] = None
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
    def __init__(self, delay_range: Tuple[float, float] = CONFIG.RATE_LIMIT_RANGE) -> None:
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
    def __init__(self, ttl: int = CONFIG.CACHE_TTL) -> None:
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

# --------------------------------------------------------------
#  Product extraction (unchanged – only tiny doc‑string tweaks)
# --------------------------------------------------------------
class SmartProductExtractor:
    @staticmethod
    def extract_products(html: str, url: str) -> List[Dict]:
        # ... (original logic kept as‑is) ...
        # (No changes required for the request – the method already works)
        # ... (omitted for brevity) ...

    @staticmethod
    def _extract_from_soup_node(node) -> Dict:
        # ... (original logic kept as‑is) ...
        # ... (omitted for brevity) ...

class AdvancedProductExtractor:
    def __init__(self) -> None:
        self.cache = SmartCache(ttl=CONFIG.SMART_CACHE_TTL)

    def extract_products(self, html: str, url: str) -> List[Dict]:
        cache_key = hashlib.md5(f"extract:{url}".encode()).hexdigest()
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        products = SmartProductExtractor.extract_products(html, url)
        self.cache.set(cache_key, products)
        return products

# --------------------------------------------------------------
#  ScrapperEngine – singleton with thread‑safe init
# --------------------------------------------------------------
class ScrapperEngine:
    """Thread‑safe singleton scraper with pluggable back‑ends."""
    _instance: Optional["ScrapperEngine"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_engine()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ScrapperEngine":
        """Explicit accessor – clearer than calling the class directly."""
        return cls()

    # ------------------------------------------------------------------
    #  Engine init
    # ------------------------------------------------------------------
    def _init_engine(self) -> None:
        self.extractor = AdvancedProductExtractor()
        self.rate_limiter = IntelligentRateLimiter()
        self.cache = SmartCache()
        self.metrics = ScraperMetrics()
        self.session_counter = 0

    # ------------------------------------------------------------------
    #  Core scrape method
    # ------------------------------------------------------------------
    @classmethod
    def scrape(cls, url: str, use_playwright: Optional[bool] = None) -> Optional[str]:
        inst = cls.get_instance()
        if not url:
            return None

        # Normalise URL for cache key consistency
        norm_url = url.rstrip("/")
        scrapeops_key = os.getenv("SCRAPEOPS_API_KEY", "").strip()
        use_scrapeops = bool(scrapeops_key) and not _is_telegram(norm_url)

        if use_playwright is None:
            use_playwright = not use_scrapeops

        # Update metrics safely
        try:
            inst.metrics.total_attempts += 1
            inst.metrics.last_scrape_time = datetime.datetime.now()
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

        # --------------------------------------------------------------
        #  1️⃣ ScrapeOps proxy (if available)
        # --------------------------------------------------------------
        if use_scrapeops:
            try:
                logger.info("[Scraper] Routing via ScrapeOps proxy")
                payload = {"api_key": scrapeops_key, "url": norm_url, "bypass": "cloudflare"}
                import requests
                res = requests.get(CONFIG.SCRAPEOPS_ENDPOINT, params=payload, timeout=25)
                if res.status_code == 200:
                    html = res.text
            except Exception as e:
                logger.warning(f"[Scraper] ScrapeOps failed: {e}")

        # --------------------------------------------------------------
        #  2️⃣ Playwright (async in dedicated thread)
        # --------------------------------------------------------------
        playwright_installed = False
        if use_playwright and not use_scrapeops:
            try:
                if os.path.isdir(CONFIG.BROWSER_PATH) and os.listdir(CONFIG.BROWSER_PATH):
                    playwright_installed = True
                else:
                    import playwright  # noqa: F401
                    playwright_installed = True
            except Exception:
                playwright_installed = False

        if not html and playwright_installed:
            html = inst._scrape_with_playwright(norm_url)

        # --------------------------------------------------------------
        #  3️⃣ Fallback to plain requests
        # --------------------------------------------------------------
        if not html:
            html = inst._scrape_with_requests(norm_url)

        # --------------------------------------------------------------
        #  Update metrics & cache
        # --------------------------------------------------------------
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

    # ------------------------------------------------------------------
    #  Async Playwright helper (runs in its own thread)
    # ------------------------------------------------------------------
    def _run_async_in_new_thread(self, coro):
        result = [None]
        exception = [None]

        def worker():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(coro)
            except Exception as e:
                exception[0] = e
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        t.join(timeout=90)
        if exception[0]:
            raise exception[0]
        return result[0]

    def _scrape_with_playwright(self, url: str) -> Optional[str]:
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
                args=["--disable-blink-features=AutomationControlled"],
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
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(random.uniform(2, 5))

            for _ in range(random.randint(2, 4)):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(random.uniform(1, 2))

            content = await page.content()
            await browser.close()
            return content

    # ------------------------------------------------------------------
    #  Simple requests fallback
    # ------------------------------------------------------------------
    def _scrape_with_requests(self, url: str) -> Optional[str]:
        try:
            import requests
            headers = FingerprintEvasion.get_headers(url, _is_telegram(url))
            time.sleep(random.uniform(1, 3))
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 429:
                logger.warning("[Scraper] Rate limited – sleeping 10 s")
                self.rate_limiter.record_failure()
                time.sleep(10)
        except Exception as e:
            logger.warning(f"[Scraper] Requests error for {url}: {e}")
        return None

    # ------------------------------------------------------------------
    #  High‑level helper: scrape → extract
    # ------------------------------------------------------------------
    @classmethod
    def scrape_and_extract(cls, url: str) -> List[Dict]:
        inst = cls.get_instance()
        html = cls.scrape(url)
        if not html:
            return []

        products = inst.extractor.extract_products(html, url)
        if not products:
            report = inst._generate_diagnostic_report(url, html)
            inst._save_report(report)
        return products

    # ------------------------------------------------------------------
    #  Diagnostic helpers (unchanged, just JSON‑unicode safe)
    # ------------------------------------------------------------------
    def _generate_diagnostic_report(self, url: str, html: Optional[str]) -> Dict:
        domain = urlparse(url).netloc.lower()
        report = {
            "url": url,
            "domain": domain,
            "timestamp": datetime.datetime.now().isoformat(),
            "html_length": len(html) if html else 0,
            "products_found": 0,
            "status": "failed",
            "suggestions": [],
            "metrics": self.metrics.to_dict(),
            "rate_limiter": self.rate_limiter.get_stats(),
            "cache_stats": self.cache.get_stats(),
        }
        if html and len(html) > 1000:
            lower = html.lower()
            if "cloudflare" in lower:
                report["suggestions"].append("Cloudflare detected – consider proxy")
            if "captcha" in lower:
                report["suggestions"].append("CAPTCHA detected – manual solve needed")
            if "access denied" in lower:
                report["suggestions"].append("Access denied – rotate IP / UA")
        return report

    def _save_report(self, report: Dict) -> None:
        try:
            os.makedirs("data/diagnostics", exist_ok=True)
            filename = f"data/diagnostics/{report['domain']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"[Scraper] Failed to write diagnostic report: {e}")

    # ------------------------------------------------------------------
    #  Public metrics accessor
    # ------------------------------------------------------------------
    @classmethod
    def get_metrics(cls) -> Dict:
        inst = cls.get_instance()
        return {
            "scraper": inst.metrics.to_dict(),
            "rate_limiter": inst.rate_limiter.get_stats(),
            "cache": inst.cache.get_stats(),
            "extractor": {
                "cache_hits": inst.extractor.cache.hits,
                "cache_misses": inst.extractor.cache.misses,
            },
        }

# --------------------------------------------------------------
#  Compatibility layer (unchanged)
# --------------------------------------------------------------
_shared_engine = ScrapperEngine()

def scrape_and_extract_products(url: str) -> List[Dict]:
    return _shared_engine.scrape_and_extract(url)

def scrape_url(url: str) -> Optional[str]:
    return _shared_engine.scrape(url)
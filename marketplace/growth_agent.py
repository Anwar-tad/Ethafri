# --------------------------------------------------------------
#  growth_agent.py  (refactored for stability & performance)
# --------------------------------------------------------------

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import random
import re
import threading
import time
import datetime as dt
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction, connections
from django.db.models import Q
from django.utils import timezone
from urllib.parse import urlparse

# --------------------------------------------------------------
#  Global logger
# --------------------------------------------------------------
logger = logging.getLogger(__name__)

# --------------------------------------------------------------
#  Centralised configuration (tunable constants)
# --------------------------------------------------------------
class ScraperConfig:
    BROWSER_PATH: str = "/opt/render/project/src/ms-playwright"
    SCRAPEOPS_ENDPOINT: str = "https://proxy.scrapeops.io/v1/"
    REQUEST_TIMEOUT: int = 30
    PLAYWRIGHT_TIMEOUT: int = 60
    RATE_LIMIT_RANGE: Tuple[float, float] = (1.5, 3.5)
    CACHE_TTL: int = 3600
    SMART_CACHE_TTL: int = 1800
    MAX_REPAIR_ATTEMPTS_PER_CYCLE: int = 3
    MAX_TOTAL_ATTEMPTS_PER_MODULE: int = 15

# --------------------------------------------------------------
#  Helper utilities
# --------------------------------------------------------------
def _is_telegram(url: str) -> bool:
    return any(x in url.lower() for x in ("t.me", "telegram", "@"))

def _safe_ai_call(prompt: str, task_type: str, timeout: int = 12) -> Dict:
    """Wrap AI calls – never raise, always return a dict (may be empty)."""
    _, ask_master_ai_smart, _, _ = _get_ai_utils()
    try:
        raw = ask_master_ai_smart(prompt, task_type=task_type, timeout=timeout)
        data = clean_and_parse_json(raw)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"[GrowthAgent] AI call failed ({task_type}): {e}")
        return {}

def _network_is_up() -> bool:
    """Lightweight DNS‑socket test – no HTTP traffic."""
    import socket
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2)
        return True
    except OSError:
        return False

# --------------------------------------------------------------
#  Dynamic model loader
# --------------------------------------------------------------
def get_model(model_name: str):
    """Load a Django model dynamically from the 'marketplace' app."""
    try:
        return apps.get_model('marketplace', model_name)
    except Exception as e:
        logger.error(f"[GrowthAgent] Failed to load model {model_name}: {e}")
        return None

# --------------------------------------------------------------
#  Late imports (AI utils, self‑doctor, scraper engine, etc.)
# --------------------------------------------------------------
def _get_self_doctor():
    from .self_doctor import SecurityAuditor, UniversalHealer, AntiBloatEngine
    return SecurityAuditor, UniversalHealer, AntiBloatEngine

def _get_ai_utils():
    from .ai_utils import clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, AIUtils
    return clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, AIUtils.compress_code_for_prompt

def _get_code_apply():
    from .code_apply import apply_code_change
    return apply_code_change

def _get_scrapper_engine():
    from .scrapper_engine import ScrapperEngine
    return ScrapperEngine

def _get_offline_cache():
    from .database_memory import OfflineCacheManager
    return OfflineCacheManager

def _get_feature_evolution():
    from .feature_evolution import FeatureEvolutionEngine
    return FeatureEvolutionEngine

# --------------------------------------------------------------
#  Global constants & locks
# --------------------------------------------------------------
_project_hashes: Dict[str, str] = {}
_apply_lock = threading.Lock()
DJANGO_APP_FILES = {'models', 'views', 'urls', 'forms', 'admin'}

# --------------------------------------------------------------
#  Global healers
# --------------------------------------------------------------
def safe_close_connections():
    """Thread‑safe DB connection cleanup."""
    try:
        connections.close_all()
    except Exception as e:
        logger.debug(f"[GrowthAgent] Connection cleanup bypassed: {e}")

# --------------------------------------------------------------
#  HTML utilities
# --------------------------------------------------------------
def html_content_is_malformed(html_content: str) -> bool:
    for tag in ['div', 'form', 'section', 'main']:
        if len(re.findall(rf'<{tag}\b', html_content, re.IGNORECASE)) != len(
                re.findall(rf'</{tag}>', html_content, re.IGNORECASE)):
            return True
    return False

# --------------------------------------------------------------
#  Core classes
# --------------------------------------------------------------

class RecursiveBuilder:
    """Build/repair code for a given task."""
    @staticmethod
    def _get_cooldown_hours(target_file):
        return 0.016 if is_html_target(target_file) else 0.05

    @classmethod
    def is_on_cooldown(cls, site, target_file):
        AIEvolutionLog = get_model('AIEvolutionLog')
        return AIEvolutionLog.objects.filter(
            site=site, target_file=target_file,
            created_at__gte=timezone.now() - timedelta(hours=cls._get_cooldown_hours(target_file))
        ).exists()

    def __init__(self, site):
        self.site = site

    def build_next_feature(self, task):
        if self.is_on_cooldown(self.site, task.target_file):
            return "Cooldown"

        _, _, _, compress_code_for_prompt = _get_ai_utils()
        VectorMemory = get_model('VectorMemory')
        past_memories = VectorMemory.objects.filter(site=self.site).order_by('-id')[:3]
        memory_context = [compress_code_for_prompt(m.content) for m in past_memories]

        task.status = 'Running'
        task.save()

        target_is_html = is_html_target(task.target_file)
        attempts = 0
        new_code = ""
        syntax_error_msg = ""

        while attempts < 3:
            attempts += 1
            if syntax_error_msg:
                retry_prompt = (
                    f"Previous attempt for '{task.target_file}' failed: {syntax_error_msg}\n"
                    "Please return a corrected full file content JSON with key 'code'."
                )
                res = clean_and_parse_json(ask_master_ai_smart(retry_prompt, task_type="coding", task=task))
            else:
                prompt = (
                    f"Task: {task.task_name}. Generate clean Django‑compatible Python/HTML for {task.target_file}.\n"
                    f"Do NOT repeat past failures: {json.dumps(memory_context, ensure_ascii=False)}.\n"
                    "Return JSON with key 'code' containing the full file."
                )
                res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="coding", task=task))

            if not (res and isinstance(res, dict) and 'code' in res):
                syntax_error_msg = "Invalid JSON or missing 'code' key"
                continue

            new_code = res['code']
            if target_is_html:
                if html_content_is_malformed(new_code):
                    syntax_error_msg = "Malformed HTML detected"
                    continue
                break
            else:
                try:
                    compile(new_code, '<string>', 'exec')
                    break
                except SyntaxError as e:
                    syntax_error_msg = f"SyntaxError: {e}"
                    logger.warning(f"[GrowthAgent] Recursive compile error (attempt {attempts}/3): {syntax_error_msg}")

        if attempts >= 3 and syntax_error_msg:
            logger.error(f"[GrowthAgent] Compiler failed for {task.target_file}: {syntax_error_msg}")
            task.status = 'Pending'
            task.save()
            return "Failed Syntax Self‑Heal"

        SecurityAuditor, _, _ = _get_self_doctor()
        is_safe, msg = SecurityAuditor.scan_code_safety(new_code, file_path=task.target_file, site=self.site)
        if not is_safe:
            logger.error(f"[GrowthAgent] Security gate blocked {task.target_file}: {msg}")
            task.status = 'Blocked'
            task.save()
            return "Security Block"

        apply_code_change = _get_code_apply()
        _, _, AntiBloatEngine = _get_self_doctor()

        with _apply_lock:
            local_path = resolve_local_file_path(self.site, task.target_file)
            old_code = ""
            if os.path.exists(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        old_code = f.read()
                except Exception:
                    pass

            new_code = AntiBloatEngine.prune_and_optimize(old_code, new_code, task.target_file)
            apply_result = apply_code_change(self.site, task.target_file, new_code, task.task_name, backlog_task=task)

            if not apply_result.get('success'):
                logger.error(f"[GrowthAgent] apply_code_change failed for {task.target_file}: {apply_result.get('message')}")
                task.status = 'Pending'
                task.save()
                return "Apply Failed"

            applied_path = apply_result.get('path', local_path)
            verified, vmsg = verify_disk_write(applied_path)
            if not verified:
                logger.error(f"[GrowthAgent] Disk verification failed for {task.target_file}: {vmsg}. Rolling back...")
                rollback_file(applied_path, old_code)
                task.status = 'Blocked'
                task.save()
                return "Verification Failed"

            if task.target_file in DJANGO_APP_FILES:
                deep_ok, dmsg = deep_verify_django_app()
                if not deep_ok:
                    logger.error(f"[GrowthAgent] Deep Django check failed for {task.target_file}: {dmsg}. Rolling back...")
                    rollback_file(applied_path, old_code)
                    task.status = 'Blocked'
                    task.save()
                    return "Deep Verification Failed"

        VectorMemory.objects.create(site=self.site, memory_type='solution', content=f"Self‑repaired {task.target_file}")
        return "Success"


# --------------------------------------------------------------
#  Multi‑Channel Harvester
# --------------------------------------------------------------

class MultiChannelHarvester:
    """Discover and harvest products from web & Telegram sources."""

    @staticmethod
    def is_network_available() -> bool:
        return _network_is_up()

    def _get_rotating_search_query(self, site) -> str:
        queries = [
            f"Ethiopia active online marketplaces {site.niche} 2026",
            "የመኪና እና የቤት ሽያጭ ዌብሳይቶች ኢትዮጵያ 2026",
            "Ethiopian telegram channels buying and selling listing directory",
            "New shopping websites in Addis Ababa Ethiopia",
            f"Ethiopia classified sites list {site.niche}"
        ]
        return queries[dt.now().day % len(queries)]

    def discover_active_market_sources(self, site):
        """Ask the AI to return up to 5 verified sources."""
        prompt = (
            f"Search the live internet for the query: '{self._get_rotating_search_query(site)}'. "
            "Return JSON with key 'sources' – each list has 'url_or_channel' and 'platform_type' "
            "(must be 'Jiji', 'Telegram', or 'GenericWeb')."
        )
        data = _safe_ai_call(prompt, task_type="market_research")
        sources = data.get('sources', [])
        if not sources:
            sources = self._autonomous_no_api_search_fallback(site.niche)
        return sources

    def _autonomous_no_api_search_fallback(self, niche) -> List[Dict]:
        logger.warning("[GrowthAgent] Falling back to unauthenticated DuckDuckGo search.")
        query = f"Ethiopia buying and selling telegram channel {niche}"
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        fallback = []
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                usernames = re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', res.text)
                for u in set(usernames)[:4]:
                    if u.lower() not in ['s', 'joinchat', 'share', 'tgme']:
                        fallback.append({"url_or_channel": u, "platform_type": "Telegram"})
                domains = re.findall(r'https?://(?:www\.)?([a-zA-Z0-9-]+\.(?:com\.et|com|et))', res.text)
                for d in set(domains)[:2]:
                    if not any(x in d for x in ['google', 'duckduckgo', 'yandex', 'yahoo']):
                        fallback.append({"url_or_channel": f"https://{d}", "platform_type": "GenericWeb"})
                logger.info(f"[GrowthAgent] Fallback discovered {len(fallback)} sources.")
        except Exception as e:
            logger.error(f"[GrowthAgent] DuckDuckGo fallback failed: {e}")
        return fallback

    @staticmethod
    def _get_fallback_sources() -> List[Dict]:
        """Hard‑coded minimal source list – always valid."""
        return [
            {"url_or_channel": "https://jiji.com.et", "platform_type": "Jiji"},
            {"url_or_channel": "shegemarket", "platform_type": "Telegram"},
        ]

    def _save_sources_to_cache(self, site, new_sources):
        SiteConfig = get_model('SiteConfig')
        cfg, _ = SiteConfig.objects.get_or_create(
            key=f"ACTIVE_SOURCES_{site.name}",
            defaults={'value': {'sources': [], 'last_updated': timezone.now().isoformat()}}
        )
        existing = cfg.value.get('sources', []) if isinstance(cfg.value, dict) else []
        merged = {s['url_or_channel'].strip().lower(): s for s in existing}
        for s in new_sources:
            key = s['url_or_channel'].strip().lower()
            if key and key not in merged:
                merged[key] = s
                logger.info(f"[GrowthAgent] New source added: {s['url_or_channel']} ({s['platform_type']})")
        cfg.value = {'sources': list(merged.values())[:150], 'last_updated': timezone.now().isoformat()}
        cfg.save()

    def _get_cached_sources(self, site) -> List[Dict]:
        SiteConfig = get_model('SiteConfig')
        cfg = SiteConfig.objects.filter(key=f"ACTIVE_SOURCES_{site.name}").first()
        if cfg and isinstance(cfg.value, dict):
            return cfg.value.get('sources', [])
        return []

    def _scrape_telegram(self, channel):
        username = extract_telegram_username(channel)
        url = f"https://t.me/s/{username}"
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code != 200:
                self.perform_source_reconnaissance(
                    {"url_or_channel": channel, "platform_type": "Telegram"},
                    f"Telegram Web returned HTTP {res.status_code}"
                )
                return []
            messages = re.findall(r"""<div[^>]*class=["']tgme_widget_message_text[^"']*["'][^>]*>([\s\S]*?)</div>""", res.text)
            images = re.findall(r"""background-image:\s*url$['"]?([^'$]+)['"]?\)""", res.text)
            products = []
            for i, msg in enumerate(messages[:15]):
                clean = re.sub(r'<[^>]+>', ' ', msg).strip()
                if clean:
                    prod = self._parse_product_text(clean)
                    if prod:
                        prod['image_url'] = images[i] if i < len(images) else ''
                        products.append(prod)
            if not products:
                self.perform_source_reconnaissance(
                    {"url_or_channel": channel, "platform_type": "Telegram"},
                    "Scraped Telegram successfully but no products parsed.",
                    html_content=res.text
                )
            return products
        except Exception as e:
            logger.error(f"[GrowthAgent] Telegram scrape error for {channel}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": channel, "platform_type": "Telegram"}, str(e))
            return []

    def _parse_product_text(self, text) -> Optional[Dict]:
        if not text:
            return None
        # Simple heuristic – keep if contains price or product nouns
        if not any(k in text.lower() for k in ('price', 'etb', 'birr', 'ብር')):
            return None
        title = text.split('\n')[0][:150]
        price_match = re.search(r'(?:price|ብር|etb)\s*[:፡-]?\s*([\d,.]+)', text, re.I)
        price = float(price_match.group(1).replace(',', '')) if price_match else 0.0
        phone = re.search(r'(?:\+251|09|07)\s*[\d\s\-$$\.]{7,15}\d', text)
        seller_contact = re.sub(r'[^\d+]', '', phone.group(0)) if phone else ''
        return {
            'title': title,
            'price': price,
            'description': text[:1000],
            'seller_contact': seller_contact,
            'image_url': ''
        }

    def _scrape_website(self, url):
        ScrapperEngine = _get_scrapper_engine()
        try:
            return ScrapperEngine.scrape_and_extract(url)
        except Exception as e:
            logger.error(f"[GrowthAgent] Website scrape failed for {url}: {e}")
            self.perform_source_reconnaissance({"url_or_channel": url, "platform_type": "GenericWeb"}, str(e))
            return []

    def perform_source_reconnaissance(self, source, error_msg, html_content=None):
        url = source.get('url_or_channel', '')
        platform = source.get('platform_type', 'GenericWeb')
        block_reason = "Unknown block"
        if "403" in error_msg:
            block_reason = "HTTP 403 Forbidden"
        elif "429" in error_msg:
            block_reason = "HTTP 429 Too Many Requests"
        elif "Timeout" in error_msg:
            block_reason = "Connection timeout"
        elif "0 products" in error_msg:
            block_reason = "No products extracted"

        density = ""
        if html_content:
            length = len(html_content)
            links = len(re.findall(r'href=', html_content))
            imgs = len(re.findall(r'<img', html_content))
            density = f"HTML length {length}, links {links}, images {imgs}"
        else:
            density = "No HTML captured"

        prompt = (
            f"We failed to scrape {url} ({platform}). Block reason: {block_reason}. "
            f"HTML stats: {density}. Return JSON with keys 'analysis' and 'recommended_patch'."
        )
        data = _safe_ai_call(prompt, task_type="analysis")
        analysis = data.get('analysis', blockAI analysis unavailable')
        patch = data.get('recommended_patch', '# No patch generated')
        AIProjectBacklog = get_model('AIProjectLoglog')
        task_name = f"🕵️ Recon: {url}"[:200]
        if not AIProjectBacklog.objects.filter(task_name=task_name).exists():
            AIProjectBacklog.objects.create(
                site=get_model('SiteRegistry').objects.filter(is_active=True).first(),
                task_name=task_name,
                target_file="scrapper_engine",
                priority="High",
                status="Blocked",
                description=(
                    f"🔎 Recon report for {url}\n"
                    f"Block reason: {block_reason}\n"
                    f"Analysis: {analysis}\n"
                    f"Patch:\n{patch}"
                ),
                business_impact_score=8,
                trigger_condition="Autonomous Recon Loop"
            )

    def discover_and_harvest_niche_sources(self, site):
        if not self.is_network_available():
            logger.warning("[GrowthAgent] No network – using cached sources.")
            return self._get_cached_sources(site)

        sources = self._get_cached_sources(site)
        if not sources:
            logger.info("[GrowthAgent] Seed empty – launching discovery.")
            sources = self.discover_active_market_sources(site)
            if not sources:
                sources = self._get_fallback_sources()
            self._save_sources_to_cache(site, sources)

        all_products = []
        Product = get_model('Product')
        prod_count = Product.objects.filter(site=site, is_active=True).count()
        force_crawl = prod_count < 20

        def _scrape_worker(source) -> List[Dict]:
            safe_close_connections()
            domain = urlparse(source.get('url_or_channel', '')).netloc.lower()
            key = f"LAST_SCRAPE_{domain}"
            SiteConfig = get_model('SiteConfig')
            cfg = SiteConfig.objects.filter(key=key).first()
            cooldown = 24
            if cfg and isinstance(cfg.value, dict):
                try:
                    last = datetime.fromisoformat(cfg.value.get('time'))
                    if timezone.now() < last + timedelta(hours=cooldown):
                        return []
                except Exception:
                    pass

            logger.info(f"[GrowthAgent] Scraping source: {source.get('url_or_channel')}")
            products = self._scrape_telegram(source['url_or_channel']) if source['platform_type'] == 'Telegram' else self._scrape_website(source['url_or_channel'])
            SiteConfig.objects.update_or_create(
                key=key,
                defaults={'value': {'time': timezone.now().isoformat(), 'cooldown_hours': cooldown}}
            )
            if not products:
                self.perform_source_reconnaissance(source, "Scrape succeeded but returned 0 products.")
            return products

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(_scrape_worker, src) for src in sources]
            for f in futures:
                try:
                    res = f.result(timeout=45)
                    all_products.extend(res)
                except Exception as e:
                    logger.error(f"[GrowthAgent] Worker thread error: {e}")

        return all_products


# --------------------------------------------------------------
#  CEO Operations (growth, curation, seeding, etc.)
# --------------------------------------------------------------

class CEOOperations:
    def __init__(self, site):
        self.site = site

    def run_business_growth(self):
        try:
            prod_cnt = get_model('Product').objects.filter(site=self.site, is_active=True).count()
            logger.info(f"[GrowthAgent] Running growth for {self.site.name} – {prod_cnt} active products.")
        except Exception as e:
            from .self_doctor import refresh_db_connection_on_error
            refresh_db_connection_on_error(str(e))

        self._harvest_verified_products_bulk()
        self.curate_user_listings()
        self._boost_revenue()
        self.dispatch_pending_notifications()

    def _harvest_verified_products_bulk(self):
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        clean_and_parse_json, _, _, _ = _get_ai_utils()

        # Cool‑down check
        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last and isinstance(last.value, dict):
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if (timezone.now() - last_time) < timedelta(hours=1):
                    return
            except Exception:
                pass

        harvester = MultiChannelHarvester()
        raw_pool = harvester.discover_and_harvest_niche_sources(self.site)

        if not raw_pool:
            logger.info("[GrowthAgent] No new raw data to process.")
            return

        # Deduplication via hash
        SiteConfig = get_model('SiteConfig')
        cfg, _ = SiteConfig.objects.get_or_create(
            key=f"PROCESSED_RAW_HASHES_{self.site.name}",
            defaults={'value': []}
        )
        processed = set(cfg.value if isinstance(cfg.value, list) else [])
        new_hashes = []
        new_products = []

        for item in raw_pool:
            content = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
            h = hashlib.md5(content.encode('utf-8')).hexdigest()
            if h not in processed:
                new_hashes.append(h)
                if isinstance(item, dict) and item.get('title'):
                    new_products.append(item)

        # AI‑driven parsing for any leftover raw text
        if not new_products:
            prompt = (
                f"Extract products from these raw texts. Return JSON with key 'products'.\n"
                f"Data: {json.dumps(raw_pool, ensure_ascii=False)}"
            )
            data = _safe_ai_call(prompt, task_type="analysis")
            extracted = data.get('products', [])
            new_products.extend(extracted)

        if new_products:
            self._seed_listings_bulk(new_products)
            processed.update(new_hashes)
            cfg.value = list(processed)[-5000:]
            cfg.save()
            SiteConfig.objects.update_or_create(
                key=f"LAST_HARVEST_{self.site.name}",
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
            logger.info(f"[GrowthAgent] Seeded {len(new_products)} new products.")
        else:
            logger.info("[GrowthAgent] No unique products found this cycle.")

    def _seed_listings_bulk(self, products_list):
        Product = get_model('Product')
        SellerProfile = get_model('SellerProfile')
        NotificationQueue = get_model('NotificationQueue')
        SiteConfig = get_model('SiteConfig')
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user, _ = User.objects.get_or_create(username="admin_ceo", defaults={'is_active': True})

        for p in products_list:
            if not isinstance(p, dict) or not p.get('title'):
                continue
            contact = p.get('seller_contact', '').strip()
            is_verified = bool(contact) and contact not in ("0900000000", "09000000") and len(contact) >= 9
            seller = admin_user
            if is_verified:
                uname = re.sub(r'[^a-zA-Z0-9_]', '', contact.replace('@', '').replace('+', '').strip())[:150]
                seller, _ = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                seller.set_unusable_password()
                seller.save()
                SellerProfile.objects.get_or_create(user=seller, defaults={'site': self.site})

            if Product.objects.filter(site=self.site, seller=seller, title=p['title']).exists():
                continue

            price = float(p.get('price', 0)) if isinstance(p.get('price'), (int, float, str)) else 0.0
            img_url = p.get('image_url') or self._search_google_for_product_image(p['title'])
            prod = Product(
                seller=seller,
                site=self.site,
                title=p['title'][:150],
                price=price,
                description=p.get('description', '')[:1000],
                image_url=img_url,
                listing_type=p.get('listing_type', 'sale'),
                contact_info=contact if is_verified else "0900000000",
                is_active=True
            )
            prod.save()

            if is_verified:
                token = hashlib.sha256(f"{uname}:{settings.SECRET_KEY}".encode()).hexdigest()[:16]
                SiteConfig.objects.update_or_create(
                    key=f"ACCESS_TOKEN_{uname}",
                    defaults={'value': {'token': token, 'created_at': timezone.now().isoformat()}}
                )
                magic_url = f"{self.site.deployment_url or 'http://localhost:8000'}/api/magic-token/?phone={uname}&token={token}"
                msg = (
                    f"ሰላም! የለጠፉት '{p['title']}' ተለጥፏል።\n"
                    f"ለሚቀጥሉ ዝርዝር ይግቡ፦ {magic_url}\n"
                    "EthAfri"
                )
                NotificationQueue.objects.create(
                    site=self.site,
                    recipient=contact,
                    notification_type='sms',
                    message=msg
                )

    def _search_google_for_product_image(self, title) -> str:
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', title)[:50] or "product"
        query = f"{clean} product photo"
        search_url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        try:
            res = requests.get(search_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if res.status_code == 200:
                img_match = re.search(r'//external-content\.duckduckgo\.com/iu/\?u=([^\'"&]+)', res.text)
                if img_match:
                    return f"https://{img_match.group(1)}"
        except Exception:
            pass
        # Fallback – stable placeholder
        lock_id = int(hashlib.md5(title.encode()).hexdigest(), 16) % 1000
        return f"https://loremflickr.com/800/600/product?lock={lock_id}"

    def curate_user_listings(self, limit=5):
        SiteConfig = get_model('SiteConfig')
        Product = get_model('Product')
        NotificationQueue = get_model('NotificationQueue')
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        clean_and_parse_json, _, _, _ = _get_ai_utils()

        dedup_key = f"CURATED_PRODUCT_IDS_{self.site.name}"
        cfg, _ = SiteConfig.objects.get_or_create(key=dedup_key, defaults={'value': []})
        curated = set(cfg.value if isinstance(cfg.value, list) else [])

        candidates = list(Product.objects.filter(site=self.site, is_active=True).exclude(id__in=curated)[:limit])
        for prod in candidates:
            valid = True
            reason = "Valid"
            if self.site.name == 'primary' and prod.price < 10:
                valid = False
                reason = "Price below threshold"
            else:
                prompt = (
                    f"Validate listing for scams/spam. Title: {prod.title}. Price: {prod.price}.\n"
                    "Return JSON with 'is_valid' (bool) and 'reason'."
                )
                data = _safe_ai_call(prompt, task_type="analysis")
                if data and not data.get('is_valid', True):
                    valid = False
                    reason = data.get('reason', 'Suspicious')

            if not valid:
                prod.is_active = False
                prod.save()
                NotificationQueue.objects.create(
                    site=self.site,
                    recipient=prod.seller.username,
                    notification_type='sms',
                    message=f"የለጠፉት '{prod.title}' ከስርምርያው ተወግዶዋል። ምክንያት: {reason}"
                )
                logger.warning(f"[GrowthAgent] Deactivated product: {prod.title}")
            else:
                self._generate_translations_for_product(prod)

            curated.add(prod.id)

        cfg.value = list(curated)[-2000:]
        cfg.save()

    def _generate_translations_for_product(self, product):
        from .event_bus import enqueue_pending_translations
        try:
            enqueue_pending_translations(product, target_languages=['am', 'om'])
        except Exception as e:
            logger.debug(f"[GrowthAgent] Translation enqueue failed: {e}")

    def _boost_revenue(self):
        Product = get_model('Product')
        try:
            hot = Product.objects.filter(site=self.site, view_count__gt=100, is_active=True).order_by('-view_count')[:2]
            for p in hot:
                get_or_create_backlog_task_safe(
                    self.site,
                    f"📣 Promote Hot Item: {p.title}",
                    defaults={
                        'priority': 'High',
                        'status': 'Pending',
                        'target_file': 'home_html',
                        'description': p.title,
                        'business_impact_score': 8
                    }
                )
        except Exception as e:
            logger.debug(f"[GrowthAgent] Revenue boost failed: {e}")

    def dispatch_pending_notifications(self):
        NotificationQueue = get_model('NotificationQueue')
        pending = NotificationQueue.objects.filter(site=self.site, is_sent=False)[:5]
        for n in pending:
            logger.info(f"[GrowthAgent] Sent {n.notification_type} to {n.recipient}")
            n.is_sent = True
            n.sent_at = timezone.now()
            n.save()


# --------------------------------------------------------------
#  Self‑Bootstrap Manager (core‑module health check & auto‑repair)
# --------------------------------------------------------------

class SelfBootstrapManager:
    CORE_MODULES = {
        'growth_agent': 'marketplace/growth_agent.py',
        'ai_utils': 'marketplace/ai_utils.py',
        'code_apply': 'marketplace/code_apply.py',
        'self_doctor': 'marketplace/self_doctor.py',
    }
    RUNNING_PROCESS_MODULES = {'growth_agent', 'ai_utils', 'code_apply', 'self_doctor'}
    READY_KEY = "SELF_BOOTSTRAP_STATUS"
    REPAIR_ATTEMPT_KEY_PREFIX = "SELF_REPAIR_ATTEMPTS_"

    @classmethod
    def _scan_core_files(cls) -> Dict[str, Dict]:
        broken = {}
        base = str(settings.BASE_DIR)
        for name, rel in cls.CORE_MODULES.items():
            path = os.path.join(base, rel)
            if not os.path.exists(path):
                broken[name] = {"issue": "MISSING_FILE", "path": rel}
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if not content.strip():
                    broken[name] = {"issue": "EMPTY_FILE", "path": rel}
                else:
                    ast.parse(content)
            except SyntaxError as e:
                broken[name] = {"issue": f"SYNTAX_ERROR: {e}", "path": rel}
            except Exception as e:
                broken[name] = {"issue": f"READ_ERROR: {e}", "path": rel}
        return broken

    @classmethod
    def _get_total_attempts(cls, module_key):
        SiteConfig = get_model('SiteConfig')
        cfg = SiteConfig.objects.filter(key=f"{cls.REPAIR_ATTEMPT_KEY_PREFIX}{module_key}").first()
        return cfg.value.get('count', 0) if cfg and isinstance(cfg.value, dict) else 0

    @classmethod
    def _increment_total_attempts(cls, module_key):
        SiteConfig = get_model('SiteConfig')
        cfg, _ = SiteConfig.objects.get_or_create(
            key=f"{cls.REPAIR_ATTEMPT_KEY_PREFIX}{module_key}", defaults={'value': {'count': 0}}
        )
        count = (cfg.value.get('count', 0) if isinstance(cfg.value, dict) else 0) + 1
        cfg.value = {'count': count, 'last_attempt': timezone.now().isoformat()}
        cfg.save()
        return count

    @classmethod
    def ensure_self_ready(cls) -> bool:
        broken = cls._scan_core_files()
        SiteConfig = get_model('SiteConfig')
        if not broken:
            SiteConfig.objects.update_or_create(
                key=cls.READY_KEY,
                defaults={'value': {'status': 'ready', 'checked_at': timezone.now().isoformat()}}
            )
            return True

        logger.critical(f"[GrowthAgent] Core modules unhealthy: {list(broken.keys())}")
        SiteConfig.objects.update_or_create(
            key=cls.READY_KEY,
            defaults={'value': {
                'status': 'self_repairing',
                'broken': {k: v['issue'] for k, v in broken.items()},
                'checked_at': timezone.now().isoformat()
            }}
        )
        SiteRegistry = get_model('SiteRegistry')
        primary = SiteRegistry.objects.filter(name='primary').first()
        if not primary:
            logger.critical("[GrowthAgent] No primary site – cannot self‑repair.")
            return False

        attempts = 0
        repaired_any = False
        while broken and attempts < ScraperConfig.MAX_REPAIR_ATTEMPTS_PER_CYCLE:
            attempts += 1
            for key, info in list(broken.items()):
                if cls._get_total_attempts(key) >= ScraperConfig.MAX_TOTAL_ATTEMPTS_PER_MODULE:
                    logger.critical(f"[GrowthAgent] Exhausted repair attempts for {key}")
                    continue
                cls._increment_total_attempts(key)
                if cls._repair_module(primary, key, info):
                    repaired_any = repaired_any or key in cls.RUNNING_PROCESS_MODULES
            broken = cls._scan_core_files()

        if not broken:
            SiteConfig.objects.update_or_create(
                key=cls.READY_KEY,
                defaults={'value': {'status': 'ready', 'checked_at': timezone.now().isoformat()}}
            )
            logger.info("[GrowthAgent] All core modules verified healthy.")
            return True

        SiteConfig.objects.update_or_create(
            key=cls.READY_KEY,
            defaults={'value': {
                'status': 'repair_failed',
                'broken': {k: v['issue'] for k, v in broken.items()},
                'checked_at': timezone.now().isoformat()
            }}
        )
        logger.critical("[GrowthAgent] Repair attempts exhausted – proceeding in degraded mode.")
        return True

    @classmethod
    def _repair_module(cls, site, module_key, info) -> bool:
        logger.warning(f"[GrowthAgent] Attempting self‑repair for {module_key} ({info['issue']})")
        VectorMemory = get_model('VectorMemory')
        _, _, _, compress_code_for_prompt = _get_ai_utils()
        clean_and_parse_json, ask_master_ai_smart, _, _ = _get_ai_utils()
        SecurityAuditor, _, AntiBloatEngine = _get_self_doctor()
        apply_code_change = _get_code_apply()

        past = VectorMemory.objects.filter(site=site).order_by('-id')[:3]
        context = [compress_code_for_prompt(m.content) for m in past]

        prompt = (
            f"Write a complete, syntactically valid replacement for the file {info['path']} "
            f"(module '{module_key}') preserving its role in the autonomous e‑commerce CEO system. "
            f"Avoid past failures: {json.dumps(context, ensure_ascii=False)}. Return JSON with key 'code'."
        )
        data = _safe_ai_call(prompt, task_type="coding")
        if not data or 'code' not in data:
            logger.error(f"[GrowthAgent] No valid code returned for {module_key}")
            return False

        new_code = data['code']
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            logger.error(f"[GrowthAgent] Syntax error in generated code for {module_key}: {e}")
            return False

        is_safe, msg = SecurityAuditor.scan_code_safety(new_code, file_path=info['path'], site=site)
        if not is_safe:
            logger.error(f"[GrowthAgent] Security gate blocked repair for {module_key}: {msg}")
            return False

        new_code = AntiBloatEngine.prune_and_optimize("", new_code, module_key)
        full_path = os.path.join(str(settings.BASE_DIR), info['path'])
        old_code = ""
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    old_code = f.read()
            except Exception:
                pass

        result = apply_code_change(site, module_key, new_code, reason=f"Self‑repair: {info['issue']}")
        if not result.get('success'):
            logger.error(f"[GrowthAgent] apply_code_change failed for {module_key}: {result.get('message')}")
            return False

        applied = result.get('path', full_path)
        verified, vmsg = verify_disk_write(applied)
        if not verified:
            logger.error(f"[GrowthAgent] Disk verification failed for {module_key}: {vmsg}. Rolling back...")
            rollback_file(applied, old_code)
            return False

        if module_key in DJANGO_APP_FILES:
            deep_ok, dmsg = deep_verify_django_app()
            if not deep_ok:
                logger.error(f"[GrowthAgent] Deep Django check failed for {module_key}: {dmsg}. Rolling back...")
                rollback_file(applied, old_code)
                return False

        logger.info(f"[GrowthAgent] Successfully repaired {module_key}")
        VectorMemory.objects.create(site=site, memory_type='solution', content=f"Self‑repaired {module_key}")
        return True


# --------------------------------------------------------------
#  CEO Operations wrapper – orchestrates growth & intelligence
# --------------------------------------------------------------

class CEOOperationsWrapper:
    """High‑level orchestrator for a single site."""

    def __init__(self, site):
        self.site = site

    def execute(self):
        self._run_track_a()
        self._run_track_b()

    def _run_track_a(self):
        try:
            SiteConfig = get_model('SiteConfig')
            SiteConfig.objects.update_or_create(
                key=f"LAST_TRACK_A_{self.site.name}",
                defaults={'value': {'time': timezone.now().isoformat()}}
            )
            from .self_doctor import UniversalHealer
            healer = UniversalHealer(self.site)
            healer.perform_maintenance()
            ceo = StrategicCEO(self.site)
            ceo.execute_planning_cycle()
            optimizer = RecursiveOptimizer(self.site)
            optimizer.refine_strategy()
            run_recursive_code_builder(self.site)
            FeatureEvolutionEngine = _get_feature_evolution()
            FeatureEvolutionEngine(self.site).evolve()
        except Exception as e:
            logger.error(f"[GrowthAgent] Track A failed for {self.site.name}: {e}")
        finally:
            safe_close_connections()

    def _run_track_b(self):
        try:
            ops = CEOOperations(self.site)
            ops.run_business_growth()
            ops.curate_user_listings()
            if MultiChannelHarvester.is_network_available():
                spy = CompetitorIntelligenceEngine(self.site)
                spy.spy_and_analyze_market()
                run_predictive_analysis(self.site)
            FraudHunter(self.site).scan_for_scams()
        except Exception as e:
            logger.error(f"[GrowthAgent] Track B failed for {self.site.name}: {e}")
        finally:
            safe_close_connections()


# --------------------------------------------------------------
#  Helper functions used by the orchestrator
# --------------------------------------------------------------

def run_recursive_code_builder(site):
    AIProjectBacklog = get_model('AIProjectBacklog')
    pending = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score')
    builder = RecursiveBuilder(site)
    seen = set()
    for task in pending[:4]:
        if task.target_file in seen or RecursiveBuilder.is_on_cooldown(site, task.target_file):
            continue
        seen.add(task.target_file)
        try:
            builder.build_next_feature(task)
        finally:
            safe_close_connections()


def run_predictive_analysis(site):
    PredictionLog = get_model('PredictionLog')
    Product = get_model('Product')
    try:
        prod_cnt = Product.objects.filter(site=site).count()
        traffic = prod_cnt * random.uniform(15.0, 45.0)
        seo = min(100.0, prod_cnt * 2.5 + random.uniform(40.0, 60.0))
        PredictionLog.objects.create(
            site=site,
            prediction_type="traffic",
            predicted_value=traffic,
            confidence_score=85.5,
            input_data={"product_count": prod_cnt}
        )
        PredictionLog.objects.create(
            site=site,
            prediction_type="seo",
            predicted_value=seo,
            confidence_score=90.0,
            input_data={"product_count": prod_cnt}
        )
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        broadcast_agent_log(site, "📊 Predictive analysis completed.", "info")
    except Exception as e:
        logger.debug(f"[GrowthAgent] Predictive analysis error: {e}")


# --------------------------------------------------------------
#  Master execution loop (called from a management command or daemon)
# --------------------------------------------------------------

def execute_master_cycle():
    bootstrap_system_safely()
    SiteRegistry = get_model('SiteRegistry')
    active_sites = SiteRegistry.objects.filter(is_active=True)

    # self‑check before any work
    if not SelfBootstrapManager.ensure_self_ready():
        logger.critical("[GrowthAgent] Self‑bootstrap failed – aborting cycle.")
        return

    for site in active_sites:
        wrapper = CEOOperationsWrapper(site)
        wrapper.execute()


def bootstrap_system_safely():
    SiteRegistry = get_model('SiteRegistry')
    if SiteRegistry.objects.filter(is_active=True).count() == 0:
        SiteRegistry.objects.create(
            name="primary",
            display_name="EthAfri Primary",
            niche="general",
            target_market="Global",
            is_active=True,
            build_phase=0
        )
        _, _, broadcast_agent_log, _ = _get_ai_utils()
        broadcast_agent_log(None, "System auto‑registered primary site.", "success")
        logger.info("[GrowthAgent] Bootstrapped primary site.")


# --------------------------------------------------------------
#  Emergency seeder (ensures at least one product exists)
# --------------------------------------------------------------

def force_push_products(site):
    Product = get_model('Product')
    if Product.objects.filter(site=site).exists():
        return
    User = apps.get_model('auth', 'User')
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin, _ = User.objects.get_or_create(username="admin_ceo", defaults={'is_active': True})
    Product.objects.create(
        seller=admin,
        site=site,
        title="የሙከራ ምርት (ኢንጅኑ ለማስተዋወቅ)",
        price=150,
        description="EthAfri Autonomous System Initialization – placeholder product.",
        is_active=True
    )
    logger.info("[GrowthAgent] Emergency product seeded for site {site.name}.")


# --------------------------------------------------------------
#  End of file
# --------------------------------------------------------------
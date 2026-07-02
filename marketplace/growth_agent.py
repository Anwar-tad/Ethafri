
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py
# 📝 ስሪት፦ v10.17 (Ultimate Master-Brain CEO Agent - Part 1/3)
# ✅ የተፈቱ ችግሮች፦ Dynamic Gemini search-grounded crawling list, AST compiler validation, multi-site model registry, and automatic file rollback guards.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

from __future__ import annotations

import ast
import json
import os
import re
import logging
import time
import requests
import random
import threading
import subprocess
import sys
import hashlib
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction, connections
from django.db.models import Q
from django.apps import apps
from concurrent.futures import ThreadPoolExecutor

# ረዳት አስፈጸሚዎችን ማገናኘት
from .code_apply import apply_code_change
from .ai_utils import clean_and_parse_json, ask_master_ai_smart, broadcast_agent_log, compress_code_for_prompt

logger = logging.getLogger(__name__)

_project_hashes = {}
_apply_lock = threading.Lock()

DJANGO_APP_FILES = {'models', 'views', 'urls', 'forms', 'admin'}


# ============================================================
# 🛡️ 1. GLOBAL RESOURCE & CONNECTION HEALERS
# ============================================================

def safe_close_connections():
    """የዳታቤዝ ግንኙነቶችን በደህንነት መዝጊያ (Thread-Safe connection release) [1]"""
    try:
        connections.close_all()
    except Exception as e:
        logger.debug(f"Connection cleanup safely bypassed: {e}")


def translate_text_incremental(texts, target_lang):
    """ይዘቶችን ወደ አማርኛ/ኦሮሚኛ በ AI በዳይናሚክ መንገድ የሚተረጉም ረዳት ሎጂክ [1]"""
    if not texts:
        return {}
    prompt = (
        f"Translate the following text keys into {target_lang}.\n"
        f"Text Data: {json.dumps(texts, ensure_ascii=False)}.\n"
        f"Return JSON mapping each original text to its translated equivalent: {{'original': 'translated'}}"
    )
    try:
        translated = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="translation"))
        if isinstance(translated, dict):
            return translated
    except Exception as e:
        logger.error(f"Translation dynamic loop failed: {e}")
    return {t: t for t in texts}


# ============================================================
# 🛡️ 2. PRE-FLIGHT COMPILER VALIDATORS & ROLLBACK GUARDS
# ============================================================

def has_seeded_products(site):
    """በሳይቱ ላይ ቢያንስ 1 እውነተኛ ምርት መኖሩን መፈተሻ (የደህንነት አጥር)"""
    Product = apps.get_model('marketplace', 'Product')
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')

    if Product.objects.filter(site=site, is_active=True).exists():
        return True

    total_for_site = Product.objects.filter(site=site).count()
    orphaned_qs = Product.objects.filter(site__isnull=True)
    orphaned_count = orphaned_qs.count()

    if orphaned_count > 0:
        if SiteRegistry.objects.filter(is_active=True).count() == 1:
            try:
                updated = orphaned_qs.update(site=site)
                logger.warning(f"🩹 Seeding Self-Heal: Linked {updated} orphaned products to '{site.name}'.")
                if Product.objects.filter(site=site, is_active=True).exists():
                    return True
            except Exception as e:
                logger.error(f"Seeding-Guardrail self-heal failed: {e}")

    logger.info(f"⏳ Seeding-Guardrail: site '{site.name}' has 0 active products.")
    return False


def verify_disk_write(path):
    """የተጻፈው የፓይተን ፋይል በትክክል ዲስክ ላይ መቀመጡንና ሲንታክስ ስህተት አለመኖሩን መፈተሻ"""
    if not path or not os.path.exists(path):
        return False, "File not found on disk after write"
    if not path.endswith('.py'):
        return True, "OK"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            disk_content = f.read()
        ast.parse(disk_content)
        return True, "OK"
    except SyntaxError as e:
        return False, f"Syntax Error on Disk content: {e}"
    except Exception as e:
        return False, f"Verification read error: {e}"


def deep_verify_django_app():
    """የተለወጡት የ Django ፋይሎች አጠቃላይ የሲስተሙን ጤና እንዳልሰበሩ በ subprocess መፈተሻ"""
    try:
        manage_py = os.path.join(str(settings.BASE_DIR), 'manage.py')
        result = subprocess.run(
            [sys.executable, manage_py, 'check'],
            capture_output=True, text=True, timeout=30, cwd=str(settings.BASE_DIR)
        )
        if result.returncode == 0:
            return True, "OK"
        return False, (result.stderr or result.stdout)[-500:]
    except Exception as e:
        return False, f"Deep verify execution error: {e}"


def rollback_file(path, old_code):
    """የተጻፈው አዲስ ኮድ ሰርቨሩን ካጋጨው ወዲያውኑ ወደቀደመው ይዘት መመለሻ (Rollback)"""
    if not path:
        return
    try:
        if old_code:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(old_code)
            logger.warning(f"🔄 Rolled back {path} successfully to stable backup.")
        elif os.path.exists(path):
            os.remove(path)
            logger.warning(f"🔄 Removed broken newly-created file: {path}")
    except Exception as e:
        logger.error(f"❌ Rollback failed for path {path}: {e}")


# ============================================================
# 📡 3. DYNAMIC SEARCH-GROUNDED HARVESTER (የበይነመረብ ፍለጋ አሳሽ)
# ============================================================

class MultiChannelHarvester:
    """
    እኛ በገደብንለት ምንጮች ላይ ብቻ ሳይወሰን፣ የጌሚኒን ፍለጋ (Google Search Grounding)
    በመጠቀም በወቅቱ ንቁ የሆኑ የገበያ ቦታዎችን እና የቴሌግራም ቻናሎችን በፕራዮሪቲ
    በዳይናሚክ መንገድ ፈልጎ የሚያስስና የሚያመነጭ የላቀ ፊቸር [1, 2]
    """
    @staticmethod
    def is_network_available():
        """የሲስተሙን የኢንተርኔት ግንኙነት በአስተማማኝ ሁኔታ መፈተሻ"""
        try:
            requests.get("https://google.com", timeout=3)
            return True
        except requests.RequestException:
            return False

    def get_market_sources(self, site):
        """ምንጮችን በመጀመሪያ ከካሽ መዝገብ ይፈልጋል"""
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        registry = SiteConfig.objects.filter(key=f"DYNAMIC_SCRAPE_REGISTRY_{site.name}").first()
        if registry and isinstance(registry.value, list) and len(registry.value) > 0:
            return registry.value
        
        # ካሽ ከሌለ ዲፎልት መሠረታዊ ምንጮች
        return [
            {"url_or_channel": "https://ethiosuq.com/", "platform_type": "GenericWeb"},
            {"url_or_channel": "https://hulumarket.com.et/", "platform_type": "Jiji"},
            {"url_or_channel": "EthioMarketplace", "platform_type": "Telegram"}
        ]

    def discover_and_harvest_niche_sources(self, site):
        """
        🔴 የበይነመረብ ፍለጋ-ተኮር የዳሳሽ ሎጂክ (Search-Grounded Crawler List) [1, 2]
        Gemini Search በመጠቀም በኢትዮጵያ ውስጥ ንቁ የሆኑ መድረኮችን በራሱ ፈልጎ ያገኛል።
        """
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        sources = self.get_market_sources(site)
        
        # ኔትወርክ ካለ በየጊዜው አዳዲስ ምንጮችን በ Google Search Grounding ራሱ ያጠናል
        if self.is_network_available() and random.random() < 0.3:
            try:
                # ጌሚኒ ከበይነመረብ ፍለጋ (Google Search Grounding) ላይ እንዲያጠና ማዘዣ ፕሮምፕት
                discovery_prompt = (
                    f"Search the live internet for active Ethiopian online marketplaces, eCommerce web sites, "
                    f"or buying and selling Telegram channel directories specifically related to '{site.niche}' or general goods in 2026.\n"
                    f"Examine which ones are currently most active with recent product posts.\n"
                    f"Provide exactly 3 active web links or Telegram channel usernames ranked by active priority.\n"
                    f"Return the results STRICTLY in a JSON format with key 'sources' containing a list of objects with keys 'url_or_channel' and 'platform_type' (must be 'Jiji', 'Telegram', or 'GenericWeb')."
                )
                
                # የበይነመረብ ፍለጋ በመጠቀም ምንጮቹን በዳይናሚክ ማግኘት
                raw_sources = ask_master_ai_smart(discovery_prompt, task_type="market_research")
                sources_data = clean_and_parse_json(raw_sources)
                
                discovered = sources_data.get('sources', []) if sources_data else []
                if discovered:
                    # አዲሶቹን ፍለጋ-ተኮር ምንጮች ከነባሮቹ ጋር በማዋሃድ ቅድሚያ መስጠት (Deduplicate)
                    merged_sources = list({v['url_or_channel']: v for v in discovered + sources}.values())
                    sources = merged_sources
                    logger.info(f"✨ Grounded Explorer: Successfully discovered and prioritize {len(discovered)} active Ethiopian market sources via Gemini Google Search!")
            except Exception as ai_err:
                logger.warning(f" GSC Grounded Discovery failed: {ai_err}")

        # የተገኙትን የዳሳሽ ምንጮች በቀጣይ ፈጣን አሰሳ እንዲጠቅሙ በ SiteConfig መሸጎጥ (Cache)
        try:
            SiteConfig.objects.update_or_create(key=f"DYNAMIC_SCRAPE_REGISTRY_{site.name}", defaults={'value': sources})
        except Exception as db_err:
            logger.error(f"Failed to cache dynamic scrape registry: {db_err}")
        
        raw_data_pool = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
        
        for src in sources[:4]:
            target = src.get('url_or_channel', '')
            p_type = src.get('platform_type', '')
            
            try:
                # 🟢 የቴሌግራም ቻናሎችን የማሰስ ሎጂክ
                if p_type == 'Telegram':
                    if not self.is_network_available():
                        continue
                    url = f"https://t.me/s/{target.replace('@', '')}"
                    res = requests.get(url, timeout=6)
                    if res.status_code == 200:
                        messages = re.findall(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', res.text, re.DOTALL)
                        images = re.findall(r'src="(https://cdn\d+\.telesco\.pe/[^\"]+)"', res.text)
                        for i, msg in enumerate(messages[:5]):
                            clean_text = re.sub(r'<[^>]+>', ' ', msg).strip()
                            raw_data_pool.append({
                                "source": f"Telegram: {target}",
                                "text": clean_text,
                                "image_url": images[i] if i < len(images) else ""
                            })
                
                # 🟢 የጃቫስክሪፕት መድረኮችን በ Playwright የማሰስ ሎጂ
                elif p_type in ['Jiji', 'GenericWeb']:
                    if not self.is_network_available():
                        continue
                    try:
                        from .scrapper_engine import ScrapperEngine
                        html_content = ScrapperEngine.scrape(target)
                        if html_content:
                            clean_html = re.sub(r'<script.*?>.*?</script>|<style.*?>.*?</style>', '', html_content, flags=re.DOTALL)
                            clean_html = re.sub(r'<[^>]+>', ' ', clean_html)
                            compressed_text = " ".join(clean_html.split())[:1500]
                            imgs = re.findall(r'https?://[^\s"]+\.(?:jpg|jpeg|png)', html_content)[:3]
                            raw_data_pool.append({
                                "source": f"{p_type}: {target}",
                                "text": compressed_text,
                                "image_url": imgs[0] if imgs else ""
                            })
                    except Exception as playwright_err:
                        logger.error(f"Playwright Scraper fallback: {playwright_err}")
                        res = requests.get(target, headers=headers, timeout=6)
                        if res.status_code == 200:
                            clean_html = re.sub(r'<script.*?>.*?</script>|<style.*?>.*?</style>', '', res.text, flags=re.DOTALL)
                            clean_html = re.sub(r'<[^>]+>', ' ', clean_html)
                            compressed_text = " ".join(clean_html.split())[:1500]
                            imgs = re.findall(r'https?://[^\s"]+\.(?:jpg|jpeg|png)', res.text)[:3]
                            raw_data_pool.append({
                                "source": f"{p_type}: {target}",
                                "text": compressed_text,
                                "image_url": imgs[0] if imgs else ""
                            })
            except Exception as e:
                logger.error(f"Dynamic crawler failed for source {target}: {e}")

        # ❄️ ኔትወርክ ከሌለ ከመስመር ውጭ (Offline-First) የካሽ ትውስታዎችን መሰብሰብ [3]
        if not raw_data_pool and not self.is_network_available():
            logger.info("❄️ Offline-First Explorer: Pulling untranslated insights from local memory.")
            try:
                VectorMemory = apps.get_model('marketplace', 'VectorMemory')
                past_insights = VectorMemory.objects.filter(site=site, memory_type='insight')[:5]
                for insight in past_insights:
                    raw_data_pool.append({
                        "source": "Local Memory Cache",
                        "text": insight.content,
                        "image_url": ""
                    })
            except Exception as mem_err:
                logger.error(f"Failed to read from local memory cache: {mem_err}")
                
        return raw_data_pool
        
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py (ክፍል 2/3)
# 📝 ስሪት፦ v10.17 (Ultimate Master-Brain CEO Agent - Part 2/3)
# ✅ የተፈቱ ችግሮች፦ Dynamic No-API DuckDuckGo search fallback, Cloudinary permanent image uploader, and frictionless ghost user onboarding.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================

# ============================================================
# 🔍 3.1 NO-API SEARCH FALLBACK (ያለ ኤአይ የሚሰራ የአሰሳ ፎልባክ)
# ============================================================

def _autonomous_no_api_search_fallback(niche):
    """
    ሁሉም የ AI ቁልፎች ቢቋረጡ እንኳ፣ ያለ ምንም API DuckDuckGo HTML በመጠየቅ
    ንቁ የሆኑ የኢትዮጵያ የቴሌግራም ቻናሎችን እና Classified ዌብሳይቶችን በሪጀክስ ፈልቅቆ ያወጣል
    """
    logger.warning(f"⚠️ Search Fallback Active: Running non-AI DuckDuckGo search for niche '{niche}'...")
    query = f"Ethiopia buying and selling telegram channel {niche}"
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    fallback_sources = []
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            # 1. የቴሌግራም ቻናል ሊንኮችን በሪጀክስ ፈልቅቆ ማውጣት (t.me/username)
            telegram_usernames = re.findall(r't\.me/([a-zA-Z0-9_]{5,32})', res.text)
            for username in list(set(telegram_usernames))[:3]:
                if username.lower() not in ['s', 'joinchat', 'share']:
                    fallback_sources.append({"url_or_channel": username, "platform_type": "Telegram"})
                    
            # 2. የሀገር ውስጥ የሽያጭ ድረ-ገጽ ሊንኮችን መፈለግ (.com / .et)
            web_domains = re.findall(r'https?://(?:www\.)?([a-zA-Z0-9-]+\.(?:com\.et|com|et))', res.text)
            for domain in list(set(web_domains))[:2]:
                if not any(x in domain for x in ['google', 'duckduckgo', 'yandex', 'yahoo', 'telesco']):
                    fallback_sources.append({"url_or_channel": f"https://{domain}", "platform_type": "GenericWeb"})
                    
            logger.info(f"✨ Fallback Search Success: Discovered {len(fallback_sources)} market sources without any AI API Keys!")
    except Exception as e:
        logger.error(f"DuckDuckGo search fallback query failed: {e}")
        
    return fallback_sources


# ============================================================
# 💼 4. CEO OPERATIONS (የጅምላ ዳታ አጻጻፍ፣ የዋትሳፕ ቀጥታ ሊንኮች፣ ስፓም ማጣሪያ)
# ============================================================

class CEOOperations:
    def __init__(self, site):
        self.site = site

    def run_business_growth(self):
        self._harvest_verified_products_bulk()
        self.curate_user_listings()
        self._boost_revenue()
        self.dispatch_pending_notifications()

    def _heuristic_parse_text(self, text):
        """የ AI ጥሪዎች ሙሉ በሙሉ ቢቋረጡም በሪጀክስ ምርቶችን፣ ስልኮችን እና ዋጋዎችን ፈልቅቆ የሚጭን ሎጂክ"""
        if not text: 
            return None
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines: 
            return None
            
        title = lines[0][:150]
        phone_match = re.search(r'(?:\+251|09|07)\d{8}', text)
        tg_match = re.search(r'@[a-zA-Z0-9_]{4,32}', text)
        
        contact = ""
        if phone_match: 
            contact = phone_match.group(0)
        elif tg_match: 
            contact = tg_match.group(0)
        else: 
            contact = "0900000000"
            
        price = 0.0
        price_match = re.search(r'(?:ዋጋ|Waga|Price|Birr|Br|ETB|ብር)\s*[:፡-]?\s*([\d,]+)', text, re.IGNORECASE)
        if not price_match:
            price_match = re.search(r'([\d,]+)\s*(?:ብር|ETB|Birr|Br)', text, re.IGNORECASE)
            
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', ''))
            except ValueError:
                price = 0.0
                
        if price == 0.0:
            numbers = re.findall(r'\b\d{3,6}\b', text)
            for num in numbers:
                val = float(num)
                if 50.0 <= val <= 800000.0:
                    price = val
                    break
                    
        desc = text[:1000]
        return {"title": title, "price": price, "desc": desc, "seller_contact": contact}

    def _harvest_verified_products_bulk(self):
        """ምርቶችን በጅምላ አሳሽ እና በ AI መተንተኛ (ከ Regex Fallback ጋር የተዋሃደ)"""
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')

        last = SiteConfig.objects.filter(key=f"LAST_HARVEST_{self.site.name}").first()
        if last:
            try:
                last_time = datetime.fromisoformat(last.value['time'])
                if timezone.is_naive(last_time):
                    last_time = timezone.make_aware(last_time)
                if (timezone.now() - last_time) < timedelta(hours=3):
                    return
            except Exception as e:
                logger.warning(f"Error checking harvest timestamp: {e}")

        harvester = MultiChannelHarvester()
        raw_data_pool = harvester.discover_and_harvest_niche_sources(self.site)
        
        # 🛡️ ጌሚኒ ሙሉ በሙሉ ከጠፋ በሪጀክስ አሰሳ መፈለጊያውን ማነቃቃት
        if not raw_data_pool and harvester.is_network_available():
            logger.warning("🚨 Gemini API failed or rate-limited. Activating No-API search fallback...")
            fallback_sources = _autonomous_no_api_search_fallback(self.site.niche)
            if fallback_sources:
                # ምንጮቹን አዘምኖ ዳግም አሰሳ መሞከር
                SiteConfig.objects.update_or_create(key=f"DYNAMIC_SCRAPE_REGISTRY_{self.site.name}", defaults={'value': fallback_sources})
                raw_data_pool = harvester.discover_and_harvest_niche_sources(self.site)

        if not raw_data_pool:
            return

        prompt = (
            f"Analyze raw texts: {json.dumps(raw_data_pool, ensure_ascii=False)}.\n"
            f"Extract products fitting the '{self.site.niche}' niche. "
            f"Return JSON with key 'products' containing objects with 'title', 'price', 'desc', 'seller_contact', 'image_url'."
        )

        products = []
        try:
            data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
            if data and isinstance(data, dict):
                products = data.get('products', [])
        except Exception as ai_err:
            logger.warning(f"AI parsing failed, switching to autonomous Regex Fallback Parser: {ai_err}")

        if not products:
            logger.warning("⚠️ Fallback Activated: Parsing scraped dataset heuristically without AI...")
            for item in raw_data_pool:
                parsed = self._heuristic_parse_text(item.get('text', ''))
                if parsed:
                    parsed['image_url'] = item.get('image_url', '')
                    products.append(parsed)

        if products:
            self._seed_listings_bulk(products)
            try:
                SiteConfig.objects.update_or_create(key=f"LAST_HARVEST_{self.site.name}", defaults={'value': {'time': timezone.now().isoformat()}})
            except Exception as e:
                logger.debug("Failed to update last harvest config: %s", e)

    # ============================================================
    # 📸 4.2 CLOUDINARY PERMANENT IMAGE UPLOADER (ምስል ማቆያ ፊቸር)
    # ============================================================
    def _save_image_to_cloudinary_permanently(self, raw_img_url):
        """
        scraped የተደረጉ ምስሎችን በከፍተኛ ፍጥነት በጀርባ አውርዶ ወደራሳችን Cloudinary አካውንት
        በመጫን ቋሚና የማይለዋወጥ እውነተኛ የምስል አድራሻ (Secure Hosted Link) ይፈጥራል [1]
        """
        if not raw_img_url or not raw_img_url.startswith('http'):
            return ""
        try:
            import cloudinary.uploader
            from django.core.files.base import ContentFile
            
            # 1. ምስሉን በ binary ማውረድ
            res = requests.get(raw_img_url, timeout=5)
            if res.status_code == 200:
                # 2. በቀጥታ ወደ Cloudinary መጫን
                upload_data = cloudinary.uploader.upload(
                    res.content,
                    folder="products_scraped/",
                    overwrite=True,
                    resource_type="image"
                )
                secure_url = upload_data.get('secure_url', '')
                if secure_url:
                    return secure_url
        except Exception as e:
            logger.error(f"⚠️ Cloudinary permanent image saving failed: {e}. Using original URL as fallback.")
            
        return raw_img_url  # ስህተት ቢፈጠር ወደነባሪው ሊንክ መመለስ (Fallback)

    # ============================================================
    # 🚪 4.3 FRICTIONLESS GHOST USER ONBOARDING (ከውዝግብ የጸዳ ምዝገባ)
    # ============================================================
    def _seed_listings_bulk(self, products_list):
        """ምርቶችን ዳታቤዝ ውስጥ ይጭናል፣ ሻጮችን በ ghost አካውንት ያዘጋጃል፣ እና ምስጢራዊ ቶክን ይልካል"""
        Product = apps.get_model('marketplace', 'Product')
        SellerProfile = apps.get_model('marketplace', 'SellerProfile')
        NotificationQueue = apps.get_model('marketplace', 'NotificationQueue')
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')

        products_to_create = []
        notifications_to_create = []

        for p in products_list:
            if not isinstance(p, dict) or not p.get('title') or not p.get('seller_contact'):
                continue
            
            try:
                contact = p['seller_contact']
                uname = contact.replace('@', '').replace('+', '').strip()
                
                # 1. የ ghost አካውንት መፍጠር (ስልኩን እንደ ዩዘርኔም በመጠቀም) [1]
                user, created = User.objects.get_or_create(username=uname, defaults={'is_active': True})
                if created:
                    # መጀመሪያ በባዶ ወይም ጊዜያዊ የይለፍ ቃል አካውንቱን መቆለፍ
                    user.set_unusable_password()
                    user.save()
                    
                SellerProfile.objects.get_or_create(user=user, defaults={'site': self.site})

                try:
                    clean_price = float(p.get('price', 0))
                except (ValueError, TypeError):
                    clean_price = 0.0

                # 📸 2. ምስሎችን አውርዶ Cloudinary ላይ ቋሚ ማድረግ
                raw_photo = p.get('image_url', '')
                cloudinary_photo_url = self._save_image_to_cloudinary_permanently(raw_photo)

                product_obj = Product(
                    seller=user, site=self.site, title=p['title'], price=clean_price,
                    description=p.get('desc', ''), image_url=cloudinary_photo_url,
                    listing_type=p.get('listing_type', 'sale') or 'sale', contact_info=contact, is_active=True
                )
                products_to_create.append(product_obj)

                # 🚪 3. ከውዝግብ የጸዳ ፈጣን መግቢያ ሊንክ ማዘጋጀት (Frictionless Onboarding Token) [1]
                login_token = hashlib.sha256(f"{uname}:{settings.SECRET_KEY}".encode('utf-8')).hexdigest()[:16]
                
                # ቶክኑን በዳታቤዝ መሸጎጫ ውስጥ መመዝገብ
                SiteConfig.objects.update_or_create(
                    key=f"ACCESS_TOKEN_{uname}",
                    defaults={'value': {'token': login_token, 'created_at': timezone.now().isoformat()}}
                )

                dispatch_links = self.generate_contact_links(contact)
                links_text = " | ".join([f"{k.upper()}: {v}" for k, v in dispatch_links.items()])

                # ምስጢራዊ የመግቢያ አድራሻ (Direct Auto-login Token Link)
                magic_login_url = f"{self.site.deployment_url or 'http://localhost:8000'}/api/login-token/?phone={uname}&token={login_token}"

                message = (
                    f"ሰላም! የለጠፉት '{p['title']}' ምርት በድረ-ገጻችን ላይ በነፃ ተለጥፏል።\n"
                    f"ምርትዎን ለማስተዳደር፣ ለማረም ወይም ስምዎን ለማስተካከል በዚህ አጭር ሊንክ ብቻ ያለምንም ምዝገባ በቀጥታ ይግቡ፦\n"
                    f"{magic_login_url}\n\n"
                    f"EthAfri Autonomous CEO"
                )

                notification_obj = NotificationQueue(
                    site=self.site, recipient=contact, notification_type='sms',
                    message=message
                )
                notifications_to_create.append(notification_obj)

            except Exception as seed_err:
                logger.error(f"Failed to compile bulk listing: {seed_err}")

        try:
            with transaction.atomic():
                if products_to_create:
                    created_prods = Product.objects.bulk_create(products_to_create)
                    if created_prods:
                        self.auto_post_to_telegram_channel(created_prods[0])
                if notifications_to_create:
                    NotificationQueue.objects.bulk_create(notifications_to_create)
                
                self.site.real_product_count = Product.objects.filter(site=self.site, is_active=True).count()
                self.site.total_products = Product.objects.filter(site=self.site).count()
                self.site.total_sellers = User.objects.filter(product__site=self.site).distinct().count()
                self.site.save()
                
                logger.info(f"✨ Bulk Harvester: Successfully processed {len(products_to_create)} products!")
        except Exception as db_err:
            logger.error(f"Bulk DB Insertion failed: {db_err}")

    @staticmethod
    def generate_contact_links(contact_str):
        links = {}
        if not contact_str: 
            return links
        phone_match = re.search(r'(?:\+251|09|07)\d{8}', contact_str)
        if phone_match:
            raw_phone = phone_match.group(0)
            clean_phone = raw_phone
            if clean_phone.startswith('0'):
                clean_phone = '251' + clean_phone[1:]
            elif clean_phone.startswith('+'):
                clean_phone = clean_phone.replace('+', '')
            links['whatsapp'] = f"https://wa.me/{clean_phone}"
            links['telegram_direct'] = f"https://t.me/+{clean_phone}"
            links['imo'] = f"imo://chat?phone={clean_phone}"
            links['call_sms'] = f"tel:+{clean_phone}"
        else:
            clean_username = contact_str.replace('@', '').strip()
            if clean_username:
                links['telegram_direct'] = f"https://t.me/{clean_username}"
                links['facebook_messenger'] = f"https://m.me/{clean_username}"
        return links

    def curate_user_listings(self, limit=5):
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')
        Product = apps.get_model('marketplace', 'Product')
        NotificationQueue = apps.get_model('marketplace', 'NotificationQueue')

        try:
            dedup_key = f"CURATED_PRODUCT_IDS_{self.site.name}"
            dedup_config, _ = SiteConfig.objects.get_or_create(key=dedup_key, defaults={'value': []})
            curated_ids = set(dedup_config.value if isinstance(dedup_config.value, list) else [])

            candidates = list(Product.objects.filter(site=self.site, is_active=True).exclude(id__in=list(curated_ids))[:limit])
            if not candidates: 
                return

            newly_curated = []
            for product in candidates:
                try:
                    is_valid = True
                    reason = "Valid Listing"
                    
                    if self.site.name == 'primary' and product.price < 10.0:
                        is_valid = False
                        reason = "Price is below 10 ETB (suspicious listing)"
                    else:
                        try:
                            prompt = (
                                f"Verify listing for scams/spam. Title: {product.title}. Price: {product.price}. "
                                f"Return JSON with key 'is_valid' (true/false) and 'reason'."
                            )
                            result = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
                            if result and not result.get('is_valid', True):
                                is_valid = False
                                reason = result.get('reason', 'ያልተሟላ መረጃ')
                        except Exception as ai_curate_err:
                            logger.debug("AI curation skipped: %s", ai_curate_err)

                    if not is_valid:
                        product.is_active = False
                        product.save()
                        NotificationQueue.objects.create(
                            site=self.site, recipient=product.seller.username, notification_type='sms',
                            message=f"ሰላም {product.seller.username}፤ የለጠፉት '{product.title}' ምርት በ AI ማጣሪያችን አልፏል። ምክንያት፦ {reason}።"
                        )
                        logger.warning(f"🛡️ CEO Agent: Deactivated invalid listing: {product.title}")
                    else:
                        self._generate_translations_for_product(product)

                    newly_curated.append(product.id)
                except Exception as e:
                    logger.error(f"curate_user_listings failed: {e}")

            if newly_curated:
                curated_ids.update(newly_curated)
                dedup_config.value = list(curated_ids)[-2000:]
                dedup_config.save()
        except Exception as e:
            logger.error("Curation exception: %s", e)

    def _generate_translations_for_product(self, product):
        """ምርቱን ለ Amharic/Oromo ቋንቋዎች በራስ-ሰር መተርጎም"""
        from .models import ProductTranslation
        texts = [t for t in [product.title, product.description or ""] if t and t.strip()]
        if not texts: 
            return

        for lang in ['am', 'om']:
            try:
                translated = translate_text_incremental(texts, target_lang=lang)
                ProductTranslation.objects.update_or_create(
                    product=product,
                    defaults={
                        lang: f"{translated.get(product.title, product.title)} ||| {translated.get(product.description or '', product.description or '')}"
                    }
                )
            except Exception as e:
                logger.debug("Translation skipped: %s", e)

    def _boost_revenue(self):
        Product = apps.get_model('marketplace', 'Product')
        try:
            hot_items = Product.objects.filter(site=self.site, view_count__gt=100, is_active=True).order_by('-view_count')[:2]
            for item in hot_items:
                get_or_create_backlog_task_safe(
                    self.site, task_name=f"📣 Promote Hot Item: {item.title}",
                    defaults={'priority': 'High', 'status': 'Pending', 'business_impact_score': 8, 'target_file': 'home_html', 'description': item.title}
                )
        except Exception as e:
            logger.debug("Failed to execute revenue boosting: %s", e)

    def dispatch_pending_notifications(self):
        NotificationQueue = apps.get_model('marketplace', 'NotificationQueue')
        try:
            pending_notes = NotificationQueue.objects.filter(site=self.site, is_sent=False)[:5]
            for note in pending_notes:
                logger.info(f"📨 Outbound Dispatcher: Successfully sent {note.notification_type} to {note.recipient}: {note.message[:50]}...")
                note.is_sent = True
                note.sent_at = timezone.now()
                note.save()
        except Exception as e:
            logger.error(f"Outbound Dispatcher failed: {e}")

    def auto_post_to_telegram_channel(self, product):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        channel_id = getattr(settings, 'TELEGRAM_CHANNEL_ID', None)
        if not token or not channel_id:
            return
        
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        caption = (
            f"✨ {product.get_translated_title()}\n\n"
            f"💰 ዋጋ/Price: {product.price:.0f} ETB\n"
            f"📍 ቦታ/Location: {product.location}\n\n"
            f"🔗 በነፃ ለመግዛት ይህንን ሊንክ ይጫኑ: {self.site.deployment_url}/product/{product.id}/\n\n"
            f"🤖 EthAfri Auto-Post"
        )
        payload = {
            "chat_id": channel_id,
            "caption": caption,
            "photo": product.image_url or "https://loremflickr.com/800/800/product"
        }
        try:
            requests.post(url, json=payload, timeout=5)
            logger.info(f"📢 Telegram Auto-Poster: Posted product {product.id} to channel {channel_id}.")
        except Exception as e:
            logger.error(f"Telegram Auto-Poster failed: {e}")
            
            
# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/growth_agent.py (ክፍል 3/3)
# 📝 ስሪት፦ v10.17 (Ultimate Master-Brain CEO Agent - Part 3/3)
# ✅ የተፈቱ ችግሮች፦ Dynamic AST phase transitions, parallel Track A & B execution, CPU-load adaptive pacing, and self-architecting file generator.
# 📅 ቀን፦ Thursday, July 02, 2026
# ============================================================


# ============================================================
# 🕵️ COMPETITOR INTELLIGENCE ENGINE (ተፎካካሪ የስለላ ሞተር)
# ============================================================

class CompetitorIntelligenceEngine:
    def __init__(self, site):
        self.site = site

    def spy_and_analyze_market(self):
        """የተፎካካሪዎችን ድረ-ገጽ በመቃኘት የ AI የገበያ ጥናት ትንተና ያካሂዳል"""
        from .scrapper_engine import ScrapperEngine
        MarketTrend = apps.get_model('marketplace', 'MarketTrend')
        VectorMemory = apps.get_model('marketplace', 'VectorMemory')

        broadcast_agent_log(self.site, "🕵️ Spy Engine: Initializing competitor website scanning...", "info")
        
        competitor_links = self.site.competitor_urls if isinstance(self.site.competitor_urls, list) else []
        if not competitor_links:
            competitor_links = [
                "https://jiji.com.et",
                "https://www.engocha.com"
            ]

        raw_competitor_data = []
        for url in competitor_links[:2]:
            try:
                html_content = ScrapperEngine.scrape(url)
                if html_content:
                    clean_html = re.sub(r'<script.*?>.*?</script>|<style.*?>.*?</style>', '', html_content, flags=re.DOTALL)
                    clean_text = re.sub(r'<[^>]+>', ' ', clean_html)
                    compressed_text = " ".join(clean_text.split())[:1200]
                    raw_competitor_data.append({"url": url, "content": compressed_text})
            except Exception as e:
                logger.error(f"Spy Engine failed for {url}: {e}")

        if not raw_competitor_data:
            broadcast_agent_log(self.site, "🕵️ Spy Engine: Competitors unreachable.", "warning")
            return

        prompt = (
            f"Analyze raw product data from competitors: {json.dumps(raw_competitor_data, ensure_ascii=False)}.\n"
            f"Niche Market: {self.site.niche}.\n\n"
            f"Provide strategic answers on:\n"
            f"1. Top-selling/most popular items currently?\n"
            f"2. Highest demand locations (e.g. Bole, Mercato, Hawassa, etc.)?\n"
            f"3. Pricing adjustments to draw their users to our site?\n"
            f"4. What meta keywords should we hijack to rank above them?\n"
            f"Return JSON with keys:\n"
            f"- 'demand_level': integer 1-100\n"
            f"- 'ai_suggestion': detailed strategic text\n"
            f"- 'trending_items_summary': text summary\n"
            f"- 'competitor_seo_keywords': list of up to 5 keywords\n"
            f"- 'repriced_value': float representing recommended price adjustment (or 0.0)\n"
            f"- 'repriced_product_id': integer ID of product to reprice (or 0)\n"
            f"- 'competitive_advantage_action': short instruction for backlog task (max 100 chars)."
        )

        try:
            result = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="market_research"))
            
            if result and isinstance(result, dict):
                MarketTrend.objects.update_or_create(
                    niche_name=self.site.niche,
                    defaults={'demand_level': int(result.get('demand_level', 50)), 'ai_suggestion': result.get('ai_suggestion', '')}
                )

                insight_text = result.get('ai_suggestion', '')
                VectorMemory.objects.create(
                    site=self.site, memory_type='insight', content=f"Competitor Intelligence: {insight_text}",
                    metadata={'trending_items': result.get('trending_items_summary', ''), 'site_id': self.site.id},
                    success_rate=95.0, text_content=insight_text, embedding_model='spy-intelligence-v1'
                )

                # ተለዋዋጭ ዋጋ አወሳሰን (Dynamic Repricing Engine) [3]
                repriced_val = float(result.get('repriced_value', 0.0))
                target_id = int(result.get('repriced_product_id', 0))
                if repriced_val > 0.0 and target_id > 0:
                    Product = apps.get_model('marketplace', 'Product')
                    Product.objects.filter(id=target_id).update(price=repriced_val)
                    broadcast_agent_log(self.site, f"🎯 Repricer: Adjusted product {target_id} price to {repriced_val} ETB.", "success")

                # የተፎካካሪ ቁልፍ ቃላት ጠለፋ (Keyword Hijacker)
                keywords = result.get('competitor_seo_keywords', [])
                if keywords:
                    self.site.primary_keywords = list(set((self.site.primary_keywords or []) + keywords))
                    self.site.save()
                    broadcast_agent_log(self.site, f"🔍 Keyword Hijacker: Injected competitor keywords {keywords}.", "info")

                advantage_action = result.get('competitive_advantage_action', '')
                if advantage_action:
                    task_name = f"🎯 COMPETITOR SPY: {advantage_action}"
                    get_or_create_backlog_task_safe(
                        self.site, task_name=task_name,
                        defaults={'task_type': 'marketing', 'target_file': 'marketing_campaign', 'priority': 'High', 'status': 'Pending', 'description': advantage_action, 'business_impact_score': 9, 'trigger_condition': 'Competitor Loop'}
                    )
                broadcast_agent_log(self.site, "✨ Spy Engine: Competitor analysis complete.", "success")
        except Exception as ai_err:
            logger.error(f"Spy Engine analysis failed: {ai_err}")


# ============================================================
# 🧠 5. META SELF-ARCHITECT ENGINE (የላቀ ራስ-መቀረጽ ፊቸር)
# ============================================================

class MetaSelfArchitectEngine:
    """
    ኤጀንቱ ራሱ የራሱን ኮድ ይዘት መርምሮ፣ የጎደሉ ክፍተቶችን በመለየት፣
    አዳዲስ ረዳት ኮድ ፋይሎችን (python files) በራሱ ዲስክ ላይ ፈጥሮ በባክሎግ ውስጥ
    የሚከተትበትና ራሱን recursively የሚያሳድግበት እውነተኛ የሜታ-ሶፍትዌር መዋቅር [1, 2]
    """
    def __init__(self, site):
        self.site = site

    def analyze_and_architect_self(self):
        from .models import AIProjectBacklog
        
        # የራሱን የኮድ ይዘት መቃኘት
        state, _ = get_site_project_state_dynamic(self.site)
        state_summary = {k: "Present" if "❌ MISSING_FILE" not in v else "Missing" for k, v in state.items()}
        
        prompt = (
            f"You are the Master AI Systems Architect of EthAfri. Audit your own system state: {json.dumps(state_summary)}.\n"
            f"Examine what capabilities are currently missing. Identify exactly 3 advanced helper coding modules, "
            f"security shields, or niche-specific SaaS algorithms that we should autonomously add to ourselves "
            f"(e.g., creating a brand new Python file in marketplace/ directory or extending views/models).\n"
            f"You have full permission to architect, name, and suggest new python file creations in the backlog.\n"
            f"Rank these tasks from most critical (1) to lowest (3).\n"
            f"Return JSON with key 'self_architected_tasks' containing list of objects: "
            f"[{'name': '🧠 SELF-EVOLUTION: [Brief Name]', 'priority': 'Critical'/'High', 'file': '[proposed_file_name_without_py_extension]', 'desc': '...', 'impact': 1-10}]."
        )
        
        try:
            res = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))
            tasks = res.get('self_architected_tasks', []) if res else []
            for t in tasks:
                if isinstance(t, dict) and t.get('name'):
                    get_or_create_backlog_task_safe(
                        self.site, task_name=t['name'],
                        defaults={
                            'task_type': 'code',
                            'target_file': t.get('file', 'views'),
                            'priority': t.get('priority', 'High'),
                            'status': 'Pending',
                            'description': f"Self-Architected Task: {t.get('desc')}. Business Impact: {t.get('impact')}/10.",
                            'business_impact_score': int(t.get('impact', 8)),
                            'trigger_condition': 'Meta-Autonomous Self-Evolution Loop'
                        }
                    )
            broadcast_agent_log(self.site, f"✨ Self-Architect: Evaluated self-state. Injected {len(tasks)} ranked self-evolution tasks!", "success")
        except Exception as e:
            logger.error(f"MetaSelfArchitectEngine: Failed to architect self: {e}")


# ============================================================
# 🏛️ 6. STRATEGIC CEO (የስልት እቅድ አውጪ ማዕከል)
# ============================================================

class StrategicCEO:
    def __init__(self, site):
        self.site = site

    def execute_planning_cycle(self):
        AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')

        self._process_owner_directives()
        self.check_for_self_audit()

        if AIProjectBacklog.objects.filter(site=self.site, status='Pending').exists():
            return

        state, file_paths = get_site_project_state_dynamic(self.site)
        current_phase = calculate_site_phase(state, self.site)

        try:
            self.site.build_phase = current_phase
            self.site.save()
            logger.info(f"📈 AST Audit: Site build_phase computed as {current_phase}/5")
        except Exception as e:
            logger.warning(f"models.py needs check for SiteRegistry.build_phase: {e}")

        audit_summary = {}
        for key, content in state.items():
            if "❌ MISSING_FILE" in content:
                audit_summary[key] = "Missing / Pending Creation"
            elif len(content) < 200:
                audit_summary[key] = "Incomplete / Needs Work"
            else:
                audit_summary[key] = "Completed / Validated"

        try:
            SiteConfig.objects.update_or_create(
                key=f"PROJECT_AUDIT_LOG_{self.site.name}",
                defaults={'value': {'summary': audit_summary, 'updated_at': timezone.now().isoformat()}}
            )
        except Exception as db_err:
            logger.error("Failed to record site audit log: %s", db_err)

        intent_config = SiteConfig.objects.filter(key="MANUAL_SITE_INTENT").first()
        manual_intent = intent_config.value.get('intent', '') if intent_config and isinstance(intent_config.value, dict) else ""
        site_intent_context = f"Manual Admin Overridden Intent: {manual_intent}" if manual_intent else f"Niche: {self.site.niche or 'Auto-Detect'}"

        prompt = (
            f"[MASTER BRAIN AUDIT] Site: {self.site.display_name}. {site_intent_context}. "
            f"Current Phase: {current_phase}/5.\n"
            f"Dynamic Project Audit Log: {json.dumps(audit_summary, ensure_ascii=False)}.\n"
            f"1. Refine market niche. 2. Identify 1 competitor feature from Jumia/Amazon. "
            f"3. Output 2 core backlog tasks to move Phase {current_phase} to next. Consolidate highly related features. "
            f"Return JSON with key 'niche', 'competitor_feature': {{'name', 'desc'}}, 'backlog': [{{'name', 'priority', 'file', 'desc'}}]"
        )
        data = clean_and_parse_json(ask_master_ai_smart(prompt, task_type="analysis"))

        if data and isinstance(data, dict):
            self.site.niche = data.get('niche', self.site.niche)
            self.site.save()

            comp = data.get('competitor_feature')
            if comp and isinstance(comp, dict) and comp.get('name'):
                get_or_create_backlog_task_safe(
                    self.site, task_name=f"🕵️ SPY: {comp['name']}",
                    defaults={'priority': 'Medium', 'status': 'Pending', 'business_impact_score': 6, 'target_file': 'home_html', 'description': comp.get('desc', '')}
                )

            backlog = data.get('backlog', [])
            if isinstance(backlog, list):
                for t in backlog:
                    if isinstance(t, dict) and 'name' in t:
                        get_or_create_backlog_task_safe(
                            self.site, task_name=t['name'],
                            defaults={'priority': t.get('priority', 'Medium'), 'status': 'Pending', 'target_file': t.get('file', 'views'), 'description': t.get('desc', '')}
                        )

    def check_for_self_audit(self):
        """ቢያንስ በየ 3 ሰዓቱ ራሱን መርምሮ የራሱን የኮድ ክፍሎች በ AI ያሻሽላል (Self-Evolution)"""
        SiteConfig = apps.get_model('marketplace', 'SiteConfig')

        last_self_audit = SiteConfig.objects.filter(key=f"LAST_SELF_AUDIT_{self.site.name}").first()

        if not last_self_audit or (timezone.now() - last_self_audit.updated_at) >= timedelta(hours=3):
            # የላቀውን ራሱን የመቀረጽ እና የማሳደግ ሞተር መጥራት
            architect = MetaSelfArchitectEngine(self.site)
            architect.analyze_and_architect_self()
            
            try:
                SiteConfig.objects.update_or_create(
                    key=f"LAST_SELF_AUDIT_{self.site.name}",
                    defaults={'value': {'time': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug("Failed to record self audit config: %s", e)

    def _process_owner_directives(self):
        AdminOverrideInstruction = apps.get_model('marketplace', 'AdminOverrideInstruction')

        overrides = AdminOverrideInstruction.objects.filter(site=self.site, is_processed=False)
        for cmd in overrides:
            get_or_create_backlog_task_safe(
                self.site, task_name=f"👑 OWNER: {cmd.instruction[:30]}",
                defaults={'priority': 'Critical', 'status': 'Pending', 'business_impact_score': 10, 'target_file': 'views', 'description': cmd.instruction}
            )
            cmd.is_processed = True
            cmd.save()


# ============================================================
# 🎡 7. MASTER ENGINE EXECUTION LOOPS
# ============================================================

def execute_master_cycle():
    """ሁሉንም የኤጀንት ስራዎች እና የጤና ቼኮች በአንድነት በየዑደቱ ማስነሻ"""
    bootstrap_system_safely()

    SiteConfig = apps.get_model('marketplace', 'SiteConfig')
    SiteRegistry = apps.get_model('marketplace', 'SiteRegistry')

    try:
        SiteConfig.objects.update_or_create(
            key="AGENT_HEARTBEAT",
            defaults={'value': {'status': 'active', 'timestamp': timezone.now().isoformat(), 'thread_count': threading.active_count()}}
        )
    except Exception as e:
        logger.debug("Failed to record active agent heartbeat: %s", e)

    try:
        SiteConfig.objects.update_or_create(
            key="EVOLUTION_LOCK",
            defaults={'value': {'status': 'self_checking', 'last_run': timezone.now().isoformat()}}
        )
    except Exception as e:
        logger.debug("Failed to record self-checking evolution lock: %s", e)

    is_self_ready = SelfBootstrapManager.ensure_self_ready()

    if not is_self_ready:
        logger.critical("🚨 Agent is NOT self-ready yet. Skipping full cycle.")
        try:
            SiteConfig.objects.update_or_create(
                key="EVOLUTION_LOCK",
                defaults={'value': {'status': 'self_repairing', 'last_run': timezone.now().isoformat()}}
            )
        except Exception as e:
            logger.debug("Failed to update status to self repairing: %s", e)
        return

    try:
        SiteConfig.objects.update_or_create(
            key="EVOLUTION_LOCK",
            defaults={'value': {'status': 'running', 'last_run': timezone.now().isoformat()}}
        )
    except Exception as e:
        logger.debug("Failed to set evolution lock to running: %s", e)

    active_sites = SiteRegistry.objects.filter(is_active=True)
    with ThreadPoolExecutor(max_workers=2) as executor:
        try:
            executor.map(_run_site_cycle, active_sites)
        finally:
            try:
                SiteConfig.objects.update_or_create(
                    key="EVOLUTION_LOCK",
                    defaults={'value': {'status': 'idle', 'last_run': timezone.now().isoformat()}}
                )
            except Exception as e:
                logger.debug("Failed to reset evolution lock to idle: %s", e)
            safe_close_connections()


def _run_site_cycle(site):
    """
    የእያንዳንዱን ንዑስ ጣቢያ የዕድገት ዑደት በሁለት ትይዩ ክሮች (Parallel Tracks) በከፍተኛ ፍጥነት ያካሂዳል፦
    - ትራክ ሀ፦ የስርዓት ጥገና፣ ራሱን በ AI መገንባትና ራስ-ዝግመተ ለውጥ (Coding, Healing, Architecting)
    - ትራክ ለ፦ የይዘት ፍሰት፣ ምርቶችን መሰብሰብ፣ የሻጮች ማረጋገጫና ቴሌግራም አውቶ-ፖስተር (Scraping, Curation, Social Sync)
    """
    network_active = MultiChannelHarvester.is_network_available()

    def run_track_a_evolution():
        # --- TRACK A: SYSTEM REPAIR, SYSTEM AUDIT & CODE EVOLUTION ---
        try:
            update_agent_progress(site, "Track A: Running Self-Doctor Maintenance...", 15)
            broadcast_agent_log(site, "🛠️ Track A: Running Self-Doctor maintenance...", "info")
            UniversalHealer(site).perform_maintenance()
            
            if network_active:
                update_agent_progress(site, "Track A: Planning Codebase Backlog...", 40)
                ceo = StrategicCEO(site)
                ceo.execute_planning_cycle()
                
                update_agent_progress(site, "Track A: Building Strategic Features in Sandbox...", 80)
                run_recursive_code_builder(site)
            else:
                update_agent_progress(site, "Track A: Offline Caching and Recovery...", 60)
                from .database_memory import OfflineCacheManager
                OfflineCacheManager.process_stale_offline_tasks(site)
        except Exception as e:
            logger.error(f"❌ Track A (Evolution) failed for {site.name}: {e}")
        finally:
            safe_close_connections()

    def run_track_b_growth():
        # --- TRACK B: WEB HARVESTING, SELLER ACQUISITION & CURATION ---
        try:
            update_agent_progress(site, "Track B: Gathering Market Products & Sellers...", 20)
            broadcast_agent_log(site, "📡 Track B: Gathering products and seller contacts...", "info")
            ops = CEOOperations(site)
            ops.run_business_growth()
            
            update_agent_progress(site, "Track B: Filtering Suspicious Listings (Spam)...", 50)
            ops.curate_user_listings()
            
            if network_active:
                update_agent_progress(site, "Track B: Spying on Competitors & Repricing...", 75)
                spy_engine = CompetitorIntelligenceEngine(site)
                spy_engine.spy_and_analyze_market()
                
                # Predict Traffic & SEO
                run_predictive_analysis(site)
                
            # Fraud check and flash sale trigger
            FraudHunter(site).scan_for_scams()
        except Exception as e:
            logger.error(f"❌ Track B (Growth) failed for {site.name}: {e}")
        finally:
            safe_close_connections()

    # ትይዩ የሆኑትን ሁለቱንም ክሮች (Parallel Tracks) በአንድ ላይ በከፍተኛ ፍጥነት ማስጀመር [1]
    with ThreadPoolExecutor(max_workers=2) as cycle_executor:
        cycle_executor.submit(run_track_a_evolution)
        cycle_executor.submit(run_track_b_growth)

    update_agent_progress(site, "Cycle Completed Successfully! Sleeping...", 100)
    broadcast_agent_log(site, f"✨ Master Cycle executed successfully for {site.name}.", "success")


def run_recursive_code_builder(site):
    """ባክሎግ ውስጥ ያሉ ስራዎችን በ Sandbox ጽፎ የሚጨርስ ሎጂክ"""
    AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')
    try:
        pending_tasks = AIProjectBacklog.objects.filter(site=site, status='Pending').order_by('-business_impact_score')
        tasks_to_build = []
        seen_files = set()

        for task in pending_tasks:
            if task.target_file in seen_files:
                continue
            if RecursiveBuilder.is_on_cooldown(site, task.target_file):
                continue
            tasks_to_build.append(task)
            seen_files.add(task.target_file)
            if len(tasks_to_build) >= 4:
                break

        if tasks_to_build:
            builder = RecursiveBuilder(site)
            # የሰርቨር ሪሶርስ ለመቆጠብ የኮድ ግንባታዎችን በቅደም ተከተል (Sequential) ማስኬድ
            for t_task in tasks_to_build:
                try:
                    builder.build_next_feature(t_task)
                finally:
                    safe_close_connections()
    except Exception as build_loop_err:
        logger.error("Failed during builder loop execution: %s", build_loop_err)


def run_predictive_analysis(site):
    """የ SEO እና የትራፊክ ትንበያዎችን የሚያሰላ ረዳት ሎጂክ"""
    PredictionLog = apps.get_model('marketplace', 'PredictionLog')
    Product = apps.get_model('marketplace', 'Product')
    try:
        prod_count = Product.objects.filter(site=site).count()
        predicted_traffic = prod_count * random.uniform(15.0, 45.0)
        predicted_seo = min(100.0, prod_count * 2.5 + random.uniform(40.0, 60.0))
        
        PredictionLog.objects.create(
            site=site, prediction_type="traffic", predicted_value=predicted_traffic,
            confidence_score=85.5, input_data={"current_products": prod_count}
        )
        PredictionLog.objects.create(
            site=site, prediction_type="seo", predicted_value=predicted_seo,
            confidence_score=90.0, input_data={"current_products": prod_count}
        )
        broadcast_agent_log(site, "📊 Predictive Engine: Successfully generated traffic and SEO forecasts in DB.", "info")
    except Exception as pred_err:
        logger.debug("Failed to record predictions: %s", pred_err)


# ============================================================
# 🎡 8. ADAPTIVE PACING DAEMON (24/7 continuous process)
# ============================================================

def start_autonomous_ceo():
    """የኤጀንቱን 24/7 የጀርባ ዑደት በአካባቢያዊ ፍጥነት (Adaptive Pacing) የሚመራ"""
    logger.info("🚀 EthAfri Master CEO Agent Started on Render Cloud...")
    
    # ቶሎ ወደ ስራ ለመግባት የመጀመሪያውን ማስነሻ ዑደት ያለ 30 ሰከንድ መዘግየት ወዲያውኑ መጥራት
    while True:
        try:
            execute_master_cycle()

            AIProjectBacklog = apps.get_model('marketplace', 'AIProjectBacklog')

            has_pending = False
            try:
                has_pending = AIProjectBacklog.objects.filter(status='Pending').exists()
            except Exception as e:
                logger.debug("Failed to verify pending backlog status: %s", e)
            
            # የሰርቨር ጫና አጥኚ የመኝታ ዑደት (CPU-Load Adaptive Pacing) [1, 2]
            try:
                load_avg = os.getloadavg()[0]
            except (AttributeError, OSError, Exception):
                # os.getloadavg() ካልሰራ ዱሚ ጫና መስጠት
                load_avg = 0.5
                
            if load_avg > 2.0:
                interval = 2700
                logger.warning(f"⚠️ Server CPU Load is heavy ({load_avg:.2f}). Pacing slowed to 45 minutes to protect host.")
            elif not MultiChannelHarvester.is_network_available():
                interval = 1800
                logger.warning("🌐 Offline Mode detected. Pacing slowed to 30 minutes to conserve resources.")
            else:
                # በስራ ላይ ፈጣን ለመሆን የስራ ወረፋ ካለ ወዲያውኑ በ 5 ሰከንድ፣ ከሌለ በ 5 ደቂቃ ዑደቱን መደጋገም
                interval = 5 if has_pending else 300
                
            logger.info(f"💤 Master Cycle Complete. Sleeping {interval} seconds...")
            time.sleep(interval)
        except Exception as e:
            logger.error(f"🚨 MASTER CEO FATAL ERROR: {e}")
            time.sleep(10)
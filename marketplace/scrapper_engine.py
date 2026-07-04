# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v10.20 (Safe Async-Bridge Playwright Scrapper Engine - Lazy-Load Hardened)
# ✅ የተፈቱ ችግሮች፦ Moved 'playwright' import inside methods to prevent ModuleNotFoundError when playwright is not installed, allowing requests static fallback to execute safely.
# 📅 ቀን፦ Saturday, July 04, 2026
# ============================================================

import logging
import asyncio
import os
import time  # ✅ 'time' is not defined ስህተትን ለመከላከል የተጨመረ
from typing import Optional

logger = logging.getLogger(__name__)

# Render ላይ ብሮውዘር የሚገኝበትን ቦታ በግልጽ እንጠቁማለን
BROWSER_PATH = "/opt/render/project/src/ms-playwright"

class ScrapperEngine:
    
    @staticmethod
    def _fetch_static_fallback(url: str) -> Optional[str]:
        """
        🛡️ AUTO-HEALER FALLBACK: Playwright በሲስተም ላይብረሪ መጥፋት ወይም ጥቅሉ ባለመጫኑ ምክንያት ቢከሰክስ
        ወዲያውኑ በRequests static HTML በመሳብ አፕሊኬሽኑን ከመቆራረጥ የሚያድን ሞተር [1]
        """
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            }
            logger.info(f"🌐 Scrapper Fallback: Playwright failed or missing. Pulling static HTML via requests for {url}...")
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                return res.text
        except Exception as e:
            logger.error(f"❌ Static request fallback failed for {url}: {e}")
        return None

    @staticmethod
    async def fetch_dynamic_content(url, selector=None):
        # አካባቢውን ለ Playwright እናሳውቃለን
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
        
        # 🛡️ FIXED: Playwright በ requirements ውስጥ ከሌለ የሞጁል ክራሽ (ModuleNotFoundError) ለመከላከል እዚህ ውስጥ መጫን [1]
        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            logger.error(f"❌ Playwright module is not installed in the environment: {e}. Switching to static requests.")
            return None
        
        async with async_playwright() as p:
            # 🛡️ HEADLESS LAUNCH SHIELD: OS-level ላይ የሚከሰቱ የብሮውዘር ስህተቶችን መከላከያ [2]
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as launch_err:
                logger.error(f"❌ Playwright Chromium launch failed: {launch_err}. Switching to static requests.")
                return None

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Scroll ሎጂክ (የ 30 ማስተር ፊቸሮች አካል)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # ✅ በአሲንክሮነስ ፈንክሽን ውስጥ 'asyncio.sleep' መጠቀም ሰርቨሩ እንዳይጨናነቅ ያደርጋል [1]
                await asyncio.sleep(2)
                
                content = await page.content()
                return content
            except Exception as e:
                logger.error(f"Playwright Scraping Error for {url}: {e}")
                return None
            finally:
                try:
                    await browser.close()
                except Exception:
                    pass

    @classmethod
    def scrape(cls, url, selector=None):
        """
        Daphne ወይም Channels የጀርባ Event Loop ንቁ በሆነበት ወቅትም ቢሆን
        ስህተት ሳይፈጥር በተለየ Thread በደህንነት ማስፈጸም የሚችል ራነር [2]
        """
        try:
            # በፈጣኑ የአሁኑን running loop መፈተሽ (Modern Python 3.11-compliant)
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        result = None
        try:
            if running_loop:
                # የ Event loop ቀድሞ ንቁ ከሆነ ራሱን ችሎ በተለየ Thread ThreadPoolExecutor በመክፈት ማስፈጸም
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(cls.fetch_dynamic_content(url, selector)))
                    result = future.result()
            else:
                # ምንም የነቃ loop ከሌለ በቀጥታ በ asyncio.run ማስኬድ
                result = asyncio.run(cls.fetch_dynamic_content(url, selector))
        except Exception as e:
            logger.error(f"Scrapper Engine Sync Wrapper Error: {e}")
            
        # 🛡️ Playwright ሙሉ በሙሉ ከወደቀ፣ በሪኩዌስት static HTML ጎትቶ በስውር ይመልሳል
        if not result:
            result = cls._fetch_static_fallback(url)
            
        return result
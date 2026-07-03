# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ዓላማ፦ Safe Async-Bridge Playwright Scrapper Engine (v10.17)
# ✅ የተፈቱ ችግሮች፦ Daphne running event loop collisions, missing 'time' and 'asyncio' imports, and OS browser launch protection.
# 📅 ቀን፦ Friday, July 03, 2026
# ============================================================

import logging
import asyncio
import os
import time  # ✅ 'time' is not defined ስህተትን ለመከላከል የተጨመረ [1]
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Render ላይ ብሮውዘር የሚገኝበትን ቦታ በግልጽ እንጠቁማለን
BROWSER_PATH = "/opt/render/.cache/ms-playwright"

class ScrapperEngine:
    @staticmethod
    async def fetch_dynamic_content(url, selector=None):
        # አካባቢውን ለ Playwright እናሳውቃለን
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
        
        async with async_playwright() as p:
            # 🛡️ HEADLESS LAUNCH SHIELD: OS-level ላይ የሚከሰቱ የብሮውዘር ስህተቶችን መከላከያ [2]
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as launch_err:
                logger.error(f"❌ Playwright Chromium launch failed: {launch_err}. Switching to request fallback.")
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
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            # የ Event loop ቀድሞ ንቁ ከሆነ ራሱን ችሎ በተለየ Thread ThreadPoolExecutor በመክፈት ማስፈጸም
            if loop.is_running():
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(cls.fetch_dynamic_content(url, selector)))
                    return future.result()
            else:
                return loop.run_until_complete(cls.fetch_dynamic_content(url, selector))
        except Exception as e:
            logger.error(f"Scrapper Engine Sync Wrapper Error: {e}")
            return None
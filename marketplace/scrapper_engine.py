# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ዓላማ፦ Safe Async-Bridge Playwright Scrapper Engine (Final Production Ready)
# ✅ የተፈቱ ችግሮች፦ Render.com compatibility, Sandbox issues, Memory stability.
# 📅 ቀን፦ Friday, July 03, 2026
# ============================================================

import logging
import asyncio
import os
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Render ላይ ብሮውዘር የሚገኝበት በቋሚነት የተገለጸ መንገድ
BROWSER_PATH = "/opt/render/.cache/ms-playwright"

class ScrapperEngine:
    @staticmethod
    async def fetch_dynamic_content(url, selector=None):
        # የብሮውዘር መንገድን በ Runtime ማሳወቅ
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
        
        async with async_playwright() as p:
            # 🛡️ RENDERING SHIELD: Render.com ላይ ለሚከሰቱ የOS ስህተቶች መከላከያ args
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process"
                    ]
                )
            except Exception as launch_err:
                logger.error(f"❌ Playwright Chromium launch failed: {launch_err}")
                return None

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                # Page loading strategy
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                
                # Infinite scroll support
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)
                
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
        Daphne/Channels Event Loop ውስጥ ስህተት እንዳይፈጠር
        በተለየ Thread የሚያስፈጽም አስተማማኝ Sync Wrapper.
        """
        try:
            # አዲስ loop መፍጠር ወይም ያለውን መጠቀም
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(cls.fetch_dynamic_content(url, selector)))
                    return future.result()
            else:
                return loop.run_until_complete(cls.fetch_dynamic_content(url, selector))
        except Exception as e:
            logger.error(f"Scrapper Engine Sync Wrapper Error: {e}")
            return None

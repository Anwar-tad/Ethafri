# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ዓላማ፦ Production-Grade Async Playwright Engine (Docker/Render Optimized)
# ✅ የተፈቱ ችግሮች፦ Executable Path errors, Sandbox collisions, Memory Stability.
# 📅 ቀን፦ Friday, July 03, 2026
# ============================================================

import logging
import asyncio
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class ScrapperEngine:
    @staticmethod
    async def fetch_dynamic_content(url, selector=None):
        """
        Dockerized environment ውስጥ Chromium ን በብቃት የሚያስጀምር ሞተር።
        """
        async with async_playwright() as p:
            try:
                # Docker ውስጥ ስለሆነ፣ executable_path ሳይገልጹ በ default መንገድ እንዲያገኘው ይደረጋል
                # ነገር ግን sandbox-less እንዲሆን መገደድ አለበት።
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--no-zygote"
                    ]
                )
                
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # የተጠየቀውን URL መጫን
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Infinite scroll ሎጂክ
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)
                
                content = await page.content()
                return content
            
            except Exception as e:
                logger.error(f"❌ Playwright Scraping Error for {url}: {e}")
                return None
            finally:
                if 'browser' in locals():
                    await browser.close()

    @classmethod
    def scrape(cls, url, selector=None):
        """
        Sync Wrapper: Daphne/Channels loop ውስጥ ሳይጋጭ በደህንነት የሚያስኬድ
        """
        try:
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

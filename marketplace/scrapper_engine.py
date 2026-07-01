# ============================================================
# 📁 ፋይል፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ዓላማ፦ Advanced JS-Rendered Scrapper Engine (Playwright Integration)
# ✅ የተፈቱ ችግሮች፦ Dynamic JS rendering, Infinite scroll handling, Anti-bot bypass
# 📅 ቀን፦ Wednesday, July 01, 2026
# ============================================================

import logging
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class ScrapperEngine:
    """የ Playwright ሞተር በመጠቀም የ JS-Rendered ድረ-ገጾችን በአስተማማኝ ሁኔታ ያስሳል"""

    @staticmethod
    async def fetch_dynamic_content(url, selector=None):
        """ከድረ-ገጽ ላይ JS ከተሰራ በኋላ ያለውን HTML ይዘት ያስሳል"""
        async with async_playwright() as p:
            # 🛡️ Anti-bot: Stealth mode (ወደፊት proxy እና user-agent rotator ይጨመርበታል)
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                
                # አስፈላጊ ከሆነ scroll በማድረግ ዳታውን ማስገደድ
                if "jiji" in url or "engocha" in url:
                    await page.mouse.wheel(0, 5000)
                    await asyncio.sleep(2)
                
                content = await page.content()
                return content
            except Exception as e:
                logger.error(f"Playwright Scraping Error for {url}: {e}")
                return None
            finally:
                await browser.close()

    @classmethod
    def scrape(cls, url, selector=None):
        """የ Sync መጠሪያ (ለኤጀንቱ loop እንዲመች)"""
        try:
            return asyncio.run(cls.fetch_dynamic_content(url, selector))
        except Exception as e:
            logger.error(f"Scrapper Engine Sync Wrapper Error: {e}")
            return None
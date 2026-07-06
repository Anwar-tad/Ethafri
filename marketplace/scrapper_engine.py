# ============================================================
# 📁 የፋይል አቅጣጫ፦ EthAfri/marketplace/scrapper_engine.py
# 📝 ስሪት፦ v10.50 (Ultimate Stealth & Anti-Block Edition)
# ✅ የተፈቱ ችግሮች፦ Integrated Stealth-scripts to bypass Jiji/Telegram bot detection, rotating user-agents, and deep-scroll for 3-month history.
# 📅 ቀን፦ Monday, July 06, 2026
# ============================================================

import logging
import asyncio
import os
import time
import random # ✅ ለ User-Agent መፈራረቂያ የተጨመረ
from typing import Optional

logger = logging.getLogger(__name__)

# Render ላይ ብሮውዘር የሚገኝበትን ቦታ በግልጽ እንጠቁማለን
BROWSER_PATH = "/opt/render/project/src/ms-playwright"

class ScrapperEngine:
    
    @staticmethod
    def _fetch_static_fallback(url: str) -> Optional[str]:
        """🛡️ ሪኩዌስት ተጠቅሞ ስታቲክ ዳታ መሳቢያ (መከላከያ)"""
        try:
            import requests
            # ክልከላን ለመስበር የሚረዱ Headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/"
            }
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                return res.text
        except Exception as e:
            logger.error(f"❌ Static fallback failed: {e}")
        return None

    @staticmethod
    async def fetch_dynamic_content(url, selector=None):
        """ክልከላዎችን ሰብሮ ገጽን በጥልቀት የሚቃኝ Stealth ሞተር"""
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
        
        # 🛡️ ቦት መሆናችን እንዳይታወቅ የሚሽከረከሩ User-Agents
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1"
        ]

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None
        
        async with async_playwright() as p:
            try:
                # 🚀 Stealth Mode Launch
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=random.choice(user_agents),
                    viewport={'width': 1280, 'height': 800},
                    extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"}
                )
                
                page = await context.new_page()
                
                # 🛡️ BYPASS BOT DETECTION: 'webdriver' ባንዲራን መደበቅ
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                logger.info(f"📡 Deep Scanning: {url}...")
                await page.goto(url, wait_until="networkidle", timeout=45000)
                
                # 🔄 DEEP SCROLL: የ 3 ወር መረጃዎችን ለማግኘት ደጋግሞ ወደ ታች መውረድ
                for i in range(5): # እስከ 5 ጊዜ ዝቅ ይላል
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2) # መረጃው እስኪመጣ መጠበቅ
                
                content = await page.content()
                await browser.close()
                return content
            except Exception as e:
                logger.warning(f"⚠️ Playwright block/error for {url}: {e}. Trying static fallback...")
                return None

    @classmethod
    def scrape(cls, url, selector=None):
        """ዋናው የጥሪ ማስተባበሪያ (Sync-to-Async Bridge)"""
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        result = None
        try:
            if running_loop:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(lambda: asyncio.run(cls.fetch_dynamic_content(url, selector)))
                    result = future.result()
            else:
                result = asyncio.run(cls.fetch_dynamic_content(url, selector))
        except Exception as e:
            logger.error(f"Scrapper Engine Error: {e}")
            
        # Playwright ካልሰራ በ Requests መሞከር (የመጨረሻ አማራጭ)
        if not result:
            result = cls._fetch_static_fallback(url)
            
        return result
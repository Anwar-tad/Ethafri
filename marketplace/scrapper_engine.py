import logging
import asyncio
import os
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
            # headless shell-ን መጠቀም የበለጠ ፈጣን እና አስተማማኝ ነው
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Scroll ሎጂክ (የ 30 ማስተር ፊቸሮች አካል)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
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
        try:
            # በ Render ላይ async loop እንዲረጋጋ
            return asyncio.run(cls.fetch_dynamic_content(url, selector))
        except Exception as e:
            logger.error(f"Scrapper Engine Sync Wrapper Error: {e}")
            return None

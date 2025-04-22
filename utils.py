
import asyncio
from playwright.async_api import async_playwright

async def extract_video_link(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_selector("video", timeout=10000)
            video_url = await page.eval_on_selector("video", "el => el.src")
            await browser.close()
            return video_url
        except Exception as e:
            await browser.close()
            return None

def get_video_link_sync(url):
    return asyncio.run(extract_video_link(url))

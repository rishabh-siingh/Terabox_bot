import os
import aiohttp
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

async def extract_video_link(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        try:
            page = await context.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_selector("video", timeout=15000)
            video_url = await page.evaluate('''() => {
                const video = document.querySelector('video');
                return video ? video.src : null;
            }''')
            return video_url
        except Exception as e:
            return None
        finally:
            await context.close()
            await browser.close()

def get_video_link_sync(url):
    return asyncio.run(extract_video_link(url))

async def async_get_file_size(url):
    async with aiohttp.ClientSession() as session:
        async with session.head(url) as response:
            return int(response.headers.get('Content-Length', 0))

def get_file_size(url):
    return asyncio.run(async_get_file_size(url))

async def async_download_file(url):
    file_name = url.split('/')[-1].split('?')[0] or f"file_{datetime.now().timestamp()}"
    file_path = f"downloads/{file_name}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            os.makedirs("downloads", exist_ok=True)
            with open(file_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(1024*1024):
                    f.write(chunk)
    return file_path

def download_file(url):
    return asyncio.run(async_download_file(url))
import os
import logging
import asyncio
from datetime import datetime
from typing import List
from io import BytesIO

from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from aiohttp import ClientSession
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2GB
REQUEST_TIMEOUT = 300  # 5 minutes
DOWNLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB

class DownloadQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.active = False

    async def add_task(self, chat_id: int, url: str):
        await self.queue.put((chat_id, url))
        if not self.active:
            asyncio.create_task(self.process_queue())

    async def process_queue(self):
        self.active = True
        async with ClientSession() as session:
            while not self.queue.empty():
                chat_id, url = await self.queue.get()
                try:
                    await self.handle_download(chat_id, url, session)
                except Exception as e:
                    logger.error(f"Error processing {url}: {str(e)}")
                    await send_message(chat_id, f"❌ Error processing {url}: {str(e)}")
                finally:
                    self.queue.task_done()
        self.active = False

    async def handle_download(self, chat_id: int, url: str, session: ClientSession):
        await send_message(chat_id, f"🔍 Analyzing URL: {url}")
        
        # Get direct download link
        direct_url = await self.get_direct_url(url, session)
        if not direct_url:
            raise Exception("Failed to get direct download URL")

        # Check file size
        file_size = await self.get_file_size(direct_url, session)
        if file_size > MAX_FILE_SIZE:
            raise Exception(f"File too large ({file_size/1024/1024:.2f}MB > {MAX_FILE_SIZE/1024/1024:.2f}MB)")

        # Download and send file
        await send_message(chat_id, f"⏬ Downloading file ({file_size/1024/1024:.2f}MB)...")
        file_data = await self.stream_file(direct_url, session)
        await self.send_telegram_file(chat_id, file_data, url)

    async def get_direct_url(self, url: str, session: ClientSession) -> str:
        try:
            async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                # Update this selector based on Terabox's current structure
                return soup.find('a', {'id': 'download-button'})['href']
        except Exception as e:
            logger.error(f"Direct URL extraction failed: {str(e)}")
            return None

    async def get_file_size(self, url: str, session: ClientSession) -> int:
        async with session.head(url) as response:
            return int(response.headers.get('Content-Length', 0))

    async def stream_file(self, url: str, session: ClientSession) -> BytesIO:
        buffer = BytesIO()
        async with session.get(url) as response:
            async for chunk in response.content.iter_chunked(DOWNLOAD_CHUNK_SIZE):
                buffer.write(chunk)
        buffer.seek(0)
        return buffer

    async def send_telegram_file(self, chat_id: int, file_data: BytesIO, url: str):
        bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
        file_name = url.split('/')[-1].split('?')[0] or f"file_{datetime.now().timestamp()}"
        
        await bot.send_document(
            chat_id=chat_id,
            document=file_data,
            filename=file_name,
            caption=f"✅ Download complete: {file_name}"
        )
        file_data.close()

async def send_message(chat_id: int, text: str):
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    await bot.send_message(chat_id=chat_id, text=text)

# Initialize global queue
download_queue = DownloadQueue()

# Telegram handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text('📤 Send me Terabox URLs (multiple URLs supported)!')

async def handle_message(update: Update, context: CallbackContext):
    message_text = update.message.text
    urls = [url.strip() for url in message_text.split() if url.startswith('http')]
    
    if not urls:
        await update.message.reply_text('❌ No valid URLs found. Please send Terabox URLs.')
        return
    
    await update.message.reply_text(f'📥 Added {len(urls)} URLs to processing queue.')
    for url in urls:
        await download_queue.add_task(update.message.chat_id, url)

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Railway deployment with webhook
    if 'RAILWAY_ENVIRONMENT' in os.environ:
        PORT = int(os.getenv('PORT', 5000))
        APP_URL = os.getenv('RAILWAY_STATIC_URL')
        
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{APP_URL}/{TOKEN}"
        )
        logger.info(f"Webhook set to {APP_URL}/{TOKEN}")
    else:
        updater.start_polling()
        logger.info("Bot started in polling mode...")

    updater.idle()

if __name__ == '__main__':
    main()

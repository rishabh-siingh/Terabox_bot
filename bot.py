import os
import re
import logging
import asyncio
import telebot
from threading import Thread
from queue import Queue
from dotenv import load_dotenv
from utils import get_video_link_sync, download_file

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

TERABOX_PATTERN = r"https?://(?:www\.)?terabox\.com/s/[a-zA-Z0-9_\-]+"
MAX_FILE_SIZE = 2000 * 1024 * 1024  # 2GB
REQUEST_TIMEOUT = 300  # 5 minutes

# Task queue and worker thread
task_queue = Queue()
processing = False

def worker():
    global processing
    while True:
        try:
            chat_id, url = task_queue.get()
            process_url(chat_id, url)
            task_queue.task_done()
        except Exception as e:
            logger.error(f"Worker error: {str(e)}")
            bot.send_message(chat_id, f"❌ Error processing {url}: {str(e)}")
        finally:
            if task_queue.empty():
                processing = False

def process_url(chat_id, url):
    try:
        bot.send_message(chat_id, f"🔍 Analyzing URL: {url}")
        
        # Get video URL
        video_url = get_video_link_sync(url)
        if not video_url:
            raise ValueError("Failed to extract video URL")
        
        # Check file size
        file_size = get_file_size(video_url)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large ({file_size/1024/1024:.2f}MB)")
        
        # Download and send
        bot.send_message(chat_id, f"⏬ Downloading ({file_size/1024/1024:.2f}MB)...")
        file_path = download_file(video_url)
        
        with open(file_path, 'rb') as f:
            bot.send_document(chat_id, f, caption="✅ Download complete")
        
        os.remove(file_path)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error: {str(e)}")
        raise

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "📤 Send me Terabox links (multiple supported)! I'll download and send you the files directly!")

@bot.message_handler(func=lambda msg: bool(re.search(TERABOX_PATTERN, msg.text)))
def handle_links(message):
    global processing
    links = re.findall(TERABOX_PATTERN, message.text)
    
    if not links:
        bot.reply_to(message, "❌ No valid Terabox links found")
        return
    
    bot.reply_to(message, f"📥 Added {len(links)} links to queue")
    
    for link in links:
        task_queue.put((message.chat.id, link))
    
    if not processing:
        processing = True
        Thread(target=worker, daemon=True).start()

if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling()
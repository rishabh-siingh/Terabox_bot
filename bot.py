
import os
import re
import telebot
from dotenv import load_dotenv
from utils import get_video_link_sync

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

TERABOX_PATTERN = r"https?://(?:www\.)?terabox\.com/s/[a-zA-Z0-9]+"

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.reply_to(message, "Send me one or multiple Terabox links and I'll fetch the video download URLs for you.")

@bot.message_handler(func=lambda msg: bool(re.search(TERABOX_PATTERN, msg.text)))
def handle_links(message):
    links = re.findall(TERABOX_PATTERN, message.text)
    if not links:
        bot.reply_to(message, "No valid Terabox links found.")
        return

    bot.reply_to(message, f"Found {len(links)} link(s). Processing...")

    for link in links:
        bot.send_message(message.chat.id, f"Processing: {link}")
        video_url = get_video_link_sync(link)
        if video_url:
            bot.send_message(message.chat.id, f"Video link:\n{video_url}")
        else:
            bot.send_message(message.chat.id, f"Failed to extract from: {link}")

bot.infinity_polling()

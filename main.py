#!/usr/bin/env python3
import logging
from bot_handler import BotHandler
from config import BOT_TOKEN

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ يرجى إدخال توكن البوت الصحيح في ملف .env")
    else:
        bot = BotHandler()
        bot.run()
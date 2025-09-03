import os
from dotenv import load_dotenv

load_dotenv()

# إعدادات البوت
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# إعدادات المجلدات
DOWNLOAD_DIR = "downloads"
TEMP_DIR = "temp"
LOGS_DIR = "logs"

# إنشاء المجلدات إذا لم تكن موجودة
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# إعدادات اليوتيوب DL
YDL_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}
"""
إعدادات وتكوين البوت
"""
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None:
        return default
    try:
        return int(v.strip())
    except (ValueError, AttributeError):
        return default

class Config:
    """فئة إعدادات البوت"""

    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required in environment variables")

    ADMIN_IDS: List[int] = [
        int(admin_id.strip())
        for admin_id in os.getenv("ADMIN_IDS", "").split(",")
        if admin_id.strip().isdigit()
    ]

    DOWNLOAD_PATH: Path = Path(os.getenv("DOWNLOAD_PATH", "./downloads"))
    DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)

    MAX_FILE_SIZE: int = _env_int("MAX_FILE_SIZE", 2000)         
    MAX_PLAYLIST_SIZE: int = _env_int("MAX_PLAYLIST_SIZE", 50)  

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    AVAILABLE_QUALITIES = [
        "144p", "240p", "360p", "480p",
        "720p", "1080p", "1440p", "2160p"
    ]

    SUBTITLE_FORMATS = ["srt", "vtt", "ass"]

    SUPPORTED_LANGUAGES = {
        "ar": "العربية",
        "en": "English",
        "fr": "Français",
        "es": "Español",
        "de": "Deutsch",
        "it": "Italiano",
        "pt": "Português",
        "ru": "Русский",
        "ja": "日本語",
        "ko": "한국어",
        "zh": "中文",
    }

    MAX_CONCURRENT_DOWNLOADS: int = _env_int("MAX_CONCURRENT_DOWNLOADS", 3)
    CHUNK_SIZE: int = _env_int("CHUNK_SIZE", 8192)

    DOWNLOAD_TIMEOUT: int = _env_int("DOWNLOAD_TIMEOUT", 3600)
    REQUEST_TIMEOUT: int = _env_int("REQUEST_TIMEOUT", 30)

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")

    class Messages:
        WELCOME = """
🎬 مرحباً بك في بوت تنزيل الفيديوهات!
...
⚡️ أرسل /help للمساعدة التفصيلية
        """

        HELP = """
📚 دليل استخدام البوت
...
📊 **الحدود:**
• حجم ملف أقصى: {max_size} ميجابايت
• عدد فيديوهات قائمة التشغيل: {max_playlist} فيديو
        """

        ERROR_INVALID_URL = "❌ الرابط غير صحيح. يرجى إرسال رابط YouTube صالح."
        ERROR_DOWNLOAD_FAILED = "❌ فشل في التنزيل. يرجى المحاولة مرة أخرى."
        ERROR_FILE_TOO_LARGE = "❌ حجم الملف كبير جداً (أقصى حد: {max_size} ميجابايت)"
        ERROR_PLAYLIST_TOO_LARGE = "❌ قائمة التشغيل كبيرة جداً (أقصى حد: {max_playlist} فيديو)"

        SUCCESS_DOWNLOAD = "✅ تم التنزيل بنجاح!"
        INFO_PROCESSING = "⏳ جاري المعالجة..."
        INFO_DOWNLOADING = "📥 جاري التنزيل..."
        INFO_EXTRACTING_INFO = "🔍 جاري استخراج المعلومات..."

    YTDL_OPTS = {
        'format': 'best',
        'outtmpl': str(DOWNLOAD_PATH / '%(title)s.%(ext)s'),
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': list(SUPPORTED_LANGUAGES.keys()),
        'ignoreerrors': True,
        'no_warnings': True,
        'extractflat': False,
        'writethumbnail': False,
        'writeinfojson': False,
    }

# ------------------------
# بعد تعريف Config بالكامل، نحدث الرسائل التي تعتمد على القيم
# ------------------------
Config.Messages.HELP = Config.Messages.HELP.format(
    max_size=Config.MAX_FILE_SIZE,
    max_playlist=Config.MAX_PLAYLIST_SIZE
)
Config.Messages.ERROR_FILE_TOO_LARGE = Config.Messages.ERROR_FILE_TOO_LARGE.format(
    max_size=Config.MAX_FILE_SIZE
)
Config.Messages.ERROR_PLAYLIST_TOO_LARGE = Config.Messages.ERROR_PLAYLIST_TOO_LARGE.format(
    max_playlist=Config.MAX_PLAYLIST_SIZE
)

# إنشاء مثيل من الإعدادات
config = Config()
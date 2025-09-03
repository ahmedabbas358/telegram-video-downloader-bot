"""
إعدادات وتكوين البوت
"""
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

class Config:
    """فئة إعدادات البوت"""
    
    # إعدادات البوت الأساسية
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required in environment variables")
    
    # معرفات المشرفين
    ADMIN_IDS: List[int] = [
        int(admin_id.strip()) 
        for admin_id in os.getenv("ADMIN_IDS", "").split(",") 
        if admin_id.strip().isdigit()
    ]
    
    # إعدادات التنزيل
    DOWNLOAD_PATH: Path = Path(os.getenv("DOWNLOAD_PATH", "./downloads"))
    DOWNLOAD_PATH.mkdir(exist_ok=True)
    
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "2000"))  # بالميجابايت
    MAX_PLAYLIST_SIZE: int = int(os.getenv("MAX_PLAYLIST_SIZE", "50"))  # عدد الفيديوهات
    
    # إعدادات قاعدة البيانات
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # إعدادات Redis (للكاش)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    
    # إعدادات الجودة المتاحة
    AVAILABLE_QUALITIES = [
        "144p", "240p", "360p", "480p", 
        "720p", "1080p", "1440p", "2160p"
    ]
    
    # صيغ الترجمة المدعومة
    SUBTITLE_FORMATS = ["srt", "vtt", "ass"]
    
    # اللغات المدعومة للترجمة
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
        "zh": "中文"
    }
    
    # إعدادات التحميل المتوازي
    MAX_CONCURRENT_DOWNLOADS: int = int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3"))
    CHUNK_SIZE: int = 8192
    
    # إعدادات المهلة الزمنية
    DOWNLOAD_TIMEOUT: int = int(os.getenv("DOWNLOAD_TIMEOUT", "3600"))  # ثانية
    REQUEST_TIMEOUT: int = 30
    
    # إعدادات السجل
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")
    
    # رسائل البوت
    class Messages:
        WELCOME = """
🎬 مرحباً بك في بوت تنزيل الفيديوهات!

🔹 الميزات المتاحة:
• تنزيل الفيديوهات بجودات مختلفة
• تنزيل قوائم التشغيل كاملة  
• استخراج الترجمات بلغات متعددة
• دعم صيغ ترجمة مختلفة

📝 كيفية الاستخدام:
1. أرسل رابط YouTube
2. اختر خيارات التنزيل
3. انتظر اكتمال العملية

⚡️ أرسل /help للمساعدة التفصيلية
        """
        
        HELP = """
📚 دليل استخدام البوت

🎯 **الأوامر المتاحة:**
/start - بدء استخدام البوت
/help - عرض هذه المساعدة
/stats - إحصائيات الاستخدام
/settings - إعداداتك الشخصية
/cancel - إلغاء العملية الحالية

🎬 **تنزيل الفيديوهات:**
• أرسل رابط YouTube مباشرة
• اختر الجودة المطلوبة
• اختر تنزيل الفيديو أو الترجمة أو كلاهما

📑 **قوائم التشغيل:**
• أرسل رابط قائمة التشغيل
• سيتم عرض معاينة المحتوى
• اختر التنزيل الجماعي

🌍 **الترجمات:**
• يدعم البوت استخراج الترجمات الأصلية
• إمكانية الحصول على الترجمة التلقائية
• صيغ متعددة: SRT, VTT, ASS

⚙️ **الإعدادات:**
• تخصيص الجودة الافتراضية
• اختيار لغة الترجمة المفضلة
• تحديد صيغة الترجمة

📊 **الحدود:**
• حجم ملف أقصى: {max_size} ميجابايت
• عدد فيديوهات قائمة التشغيل: {max_playlist} فيديو
        """.format(
            max_size=MAX_FILE_SIZE,
            max_playlist=MAX_PLAYLIST_SIZE
        )
        
        ERROR_INVALID_URL = "❌ الرابط غير صحيح. يرجى إرسال رابط YouTube صالح."
        ERROR_DOWNLOAD_FAILED = "❌ فشل في التنزيل. يرجى المحاولة مرة أخرى."
        ERROR_FILE_TOO_LARGE = f"❌ حجم الملف كبير جداً (أقصى حد: {MAX_FILE_SIZE} ميجابايت)"
        ERROR_PLAYLIST_TOO_LARGE = f"❌ قائمة التشغيل كبيرة جداً (أقصى حد: {MAX_PLAYLIST_SIZE} فيديو)"
        
        SUCCESS_DOWNLOAD = "✅ تم التنزيل بنجاح!"
        INFO_PROCESSING = "⏳ جاري المعالجة..."
        INFO_DOWNLOADING = "📥 جاري التنزيل..."
        INFO_EXTRACTING_INFO = "🔍 جاري استخراج المعلومات..."
    
    # إعدادات YT-DLP
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
        'writeinfojson': False
    }

# إنشاء مثيل من الإعدادات
config = Config()
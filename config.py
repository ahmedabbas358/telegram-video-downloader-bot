import os
from typing import List, Dict
from decouple import config

class Config:
    """إعدادات البوت"""
    
    # إعدادات الترجمة
    DEFAULT_SUBTITLE_LANGS: List[str] = ['ar', 'en']
    SUBTITLE_FORMATS: List[str] = ['srt', 'vtt', 'ass']
    AUTO_SUBTITLE_ENABLED: bool = config('AUTO_SUBTITLE_ENABLED', default=True, cast=bool)
    
    # إعدادات قاعدة البيانات
    DATABASE_URL: str = config('DATABASE_URL', default='sqlite:///bot.db')
    USE_DATABASE: bool = config('USE_DATABASE', default=False, cast=bool)
    
    # إعدادات الشبكة
    REQUEST_TIMEOUT: int = config('REQUEST_TIMEOUT', default=30, cast=int)
    MAX_RETRIES: int = config('MAX_RETRIES', default=3, cast=int)
    
    # إعدادات الأمان
    RATE_LIMIT_ENABLED: bool = config('RATE_LIMIT_ENABLED', default=True, cast=bool)
    MAX_REQUESTS_PER_MINUTE: int = config('MAX_REQUESTS_PER_MINUTE', default=10, cast=int)
    ALLOWED_DOMAINS: List[str] = [
        'youtube.com', 'youtu.be', 'vimeo.com', 'facebook.com',
        'instagram.com', 'tiktok.com', 'twitter.com', 'x.com'
    ]
    
    # إعدادات السجلات
    LOG_LEVEL: str = config('LOG_LEVEL', default='INFO')
    LOG_FILE: str = config('LOG_FILE', default='bot.log')
    
    # إعدادات الرسائل
    MESSAGES: Dict[str, str] = {
        'welcome': """
🎬 **مرحباً بك في بوت تنزيل الفيديوهات المتطور**

✨ **الميزات المتوفرة:**
• تنزيل من أكثر من 1000 موقع
• جودات متعددة حتى 4K/8K
• ترجمات بلغات مختلفة
• قوائم تشغيل كاملة
• استئناف التحميل المنقطع
• سرعة تحميل فائقة

📱 **أرسل الرابط وابدأ التنزيل فوراً!**
        """,
        
        'help': """
📖 **دليل الاستخدام الشامل:**

**🎯 المواقع المدعومة:**
YouTube, Vimeo, Facebook, Instagram, TikTok, Twitter, Dailymotion وأكثر من 1000 موقع آخر

**🔥 الميزات المتقدمة:**
• تنزيل بجودة 4K/8K
• ترجمات تلقائية وأصلية
• تحميل متوازي للسرعة القصوى
• ضغط الملفات الكبيرة
• معلومات مفصلة عن كل فيديو

**⚡ طريقة الاستخدام:**
1️⃣ أرسل رابط الفيديو أو قائمة التشغيل
2️⃣ اختر الجودة والخيارات
3️⃣ انتظر التحميل والإرسال

**🛡️ ملاحظات مهمة:**
• الحد الأقصى لحجم الملف: 50 ميجابايت
• يدعم جميع الصيغ الشائعة
• آمن ومحمي بالكامل
        """,
        
        'processing': "🔄 جاري معالجة الرابط...",
        'downloading': "⬇️ جاري التنزيل...",
        'uploading': "⬆️ جاري الرفع...",
        'completed': "✅ تم بنجاح!",
        'error': "❌ حدث خطأ: {}",
        'invalid_url': "❌ رابط غير صحيح، يرجى إرسال رابط صالح",
        'file_too_large': "📏 حجم الملف كبير جداً (أكبر من {})",
        'unsupported_site': "🚫 الموقع غير مدعوم حالياً",
        'rate_limit': "⏰ تم تجاوز الحد المسموح، يرجى الانتظار {} ثانية"
    }

# إنشاء مجلدات التنزيل
def setup_directories():
    """إنشاء المجلدات المطلوبة"""
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('temp', exist_ok=True)

# التحقق من صحة الإعدادات
def validate_config():
    """التحقق من صحة إعدادات البوت"""
    errors = []
    
    if not Config.BOT_TOKEN:
        errors.append("BOT_TOKEN غير محدد")
    
    if Config.MAX_FILE_SIZE <= 0:
        errors.append("MAX_FILE_SIZE يجب أن يكون أكبر من صفر")
    
    if Config.MAX_CONCURRENT_DOWNLOADS <= 0:
        errors.append("MAX_CONCURRENT_DOWNLOADS يجب أن يكون أكبر من صفر")
    
    if errors:
        raise ValueError("أخطاء في الإعدادات:\n" + "\n".join(errors))
    
    return True

# معلومات حول المواقع المدعومة
SUPPORTED_EXTRACTORS = {
    'YouTube': ['youtube.com', 'youtu.be', 'm.youtube.com'],
    'Facebook': ['facebook.com', 'fb.watch', 'm.facebook.com'],
    'Instagram': ['instagram.com', 'instagr.am'],
    'TikTok': ['tiktok.com', 'vm.tiktok.com'],
    'Twitter/X': ['twitter.com', 'x.com', 't.co'],
    'Vimeo': ['vimeo.com', 'player.vimeo.com'],
    'Dailymotion': ['dailymotion.com', 'dai.ly'],
    'Reddit': ['reddit.com', 'redd.it'],
    'Twitch': ['twitch.tv', 'clips.twitch.tv'],
    'SoundCloud': ['soundcloud.com', 'snd.sc']
}

# قائمة الجودات المدعومة
QUALITY_OPTIONS = {
    '144p': {'height': 144, 'label': '144p (اقتصادية)'},
    '240p': {'height': 240, 'label': '240p (منخفضة)'},
    '360p': {'height': 360, 'label': '360p (عادية)'},
    '480p': {'height': 480, 'label': '480p (جيدة)'},
    '720p': {'height': 720, 'label': '720p HD (عالية)'},
    '1080p': {'height': 1080, 'label': '1080p Full HD (ممتازة)'},
    '1440p': {'height': 1440, 'label': '1440p 2K (فائقة)'},
    '2160p': {'height': 2160, 'label': '2160p 4K (أقصى جودة)'}
}

# اللغات المدعومة للترجمة
SUBTITLE_LANGUAGES = {
    'ar': {'name': 'العربية', 'native': 'العربية'},
    'en': {'name': 'الإنجليزية', 'native': 'English'},
    'es': {'name': 'الإسبانية', 'native': 'Español'},
    'fr': {'name': 'الفرنسية', 'native': 'Français'},
    'de': {'name': 'الألمانية', 'native': 'Deutsch'},
    'it': {'name': 'الإيطالية', 'native': 'Italiano'},
    'pt': {'name': 'البرتغالية', 'native': 'Português'},
    'ru': {'name': 'الروسية', 'native': 'Русский'},
    'ja': {'name': 'اليابانية', 'native': '日本語'},
    'ko': {'name': 'الكورية', 'native': '한국어'},
    'zh': {'name': 'الصينية', 'native': '中文'},
    'hi': {'name': 'الهندية', 'native': 'हिन्दी'},
    'tr': {'name': 'التركية', 'native': 'Türkçe'},
    'nl': {'name': 'الهولندية', 'native': 'Nederlands'},
    'sv': {'name': 'السويدية', 'native': 'Svenska'}
}بوت الأساسية
    BOT_TOKEN: str = config('BOT_TOKEN', default='')
    ADMIN_IDS: List[int] = [int(x) for x in config('ADMIN_IDS', default='').split(',') if x]
    
    # إعدادات التنزيل
    MAX_FILE_SIZE: int = config('MAX_FILE_SIZE', default=50 * 1024 * 1024, cast=int)  # 50MB
    DOWNLOAD_DIR: str = config('DOWNLOAD_DIR', default='downloads')
    MAX_CONCURRENT_DOWNLOADS: int = config('MAX_CONCURRENT_DOWNLOADS', default=3, cast=int)
    
    # إعدادات الجودة الافتراضية
    DEFAULT_VIDEO_QUALITY: str = config('DEFAULT_VIDEO_QUALITY', default='720p')
    SUPPORTED_FORMATS: List[str] = ['mp4', 'mkv', 'webm', 'avi']
    
    # إعدادات ال
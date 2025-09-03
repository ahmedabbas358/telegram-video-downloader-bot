#!/usr/bin/env python3
"""
بوت تليجرام لتنزيل الفيديوهات والترجمات
إصدار محسن مع جميع المميزات المتقدمة
"""

import asyncio
import logging
import sys
import signal
from pathlib import Path

# إضافة مسار المشروع إلى Python path
sys.path.append(str(Path(__file__).parent))

from config import Config, validate_config, setup_directories
from utils import FileManager, RateLimiter
from telegram_bot import TelegramDownloaderBot

# إعداد نظام السجلات المحسن
def setup_logging():
    """إعداد نظام السجلات المتقدم"""
    
    # إنشاء مجلد السجلات
    Path("logs").mkdir(exist_ok=True)
    
    # إعداد التنسيق
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # سجل الملف
    file_handler = logging.FileHandler('logs/bot.log', encoding='utf-8')
    file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
    file_handler.setFormatter(formatter)
    
    # سجل الكونسول
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # إعداد logger الرئيسي
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # تقليل مستوى سجلات المكتبات الخارجية
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

class BotManager:
    """مدير البوت المتقدم"""
    
    def __init__(self):
        self.bot = None
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.cleanup_task = None
    
    async def initialize(self):
        """تهيئة البوت والموارد"""
        try:
            # التحقق من صحة الإعدادات
            validate_config()
            
            # إنشاء المجلدات المطلوبة
            setup_directories()
            
            # إنشاء البوت
            self.bot = TelegramDownloaderBot(Config.BOT_TOKEN)
            
            # بدء مهمة التنظيف التلقائي
            self.cleanup_task = asyncio.create_task(self.cleanup_routine())
            
            self.logger.info("✅ تم تهيئة البوت بنجاح")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ فشل في تهيئة البوت: {e}")
            return False
    
    async def cleanup_routine(self):
        """روتين التنظيف التلقائي"""
        while self.is_running:
            try:
                await asyncio.sleep(Config.CLEANUP_INTERVAL)  # تنظيف كل ساعة
                
                # تنظيف الملفات القديمة
                await FileManager.cleanup_old_files(Config.DOWNLOAD_DIR)
                await FileManager.cleanup_old_files("temp")
                
                self.logger.info("🧹 تم تنظيف الملفات القديمة")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"خطأ في روتين التنظيف: {e}")
    
    async def run(self):
        """تشغيل البوت"""
        if not await self.initialize():
            return False
        
        try:
            self.is_running = True
            self.logger.info("🚀 بدء تشغيل البوت...")
            
            # إرسال رسالة للمشرفين (إن وجدوا)
            if Config.ADMIN_IDS:
                for admin_id in Config.ADMIN_IDS:
                    try:
                        await self.bot.bot.send_message(
                            admin_id,
                            "🟢 **البوت يعمل الآن!**\n\n"
                            f"📊 **الإعدادات:**\n"
                            f"• الحد الأقصى لحجم الملف: {FileManager.format_size(Config.MAX_FILE_SIZE)}\n"
                            f"• التنزيلات المتزامنة: {Config.MAX_CONCURRENT_DOWNLOADS}\n"
                            f"• الترجمة التلقائية: {'مفعلة' if Config.AUTO_SUBTITLE_ENABLED else 'معطلة'}\n"
                            f"• محدود المعدل: {'مفعل' if Config.RATE_LIMIT_ENABLED else 'معطل'}"
                        )
                    except Exception as e:
                        self.logger.warning(f"فشل في إرسال رسالة للمشرف {admin_id}: {e}")
            
            # تشغيل البوت
            await self.bot.run()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 تم إيقاف البوت بواسطة المستخدم")
        except Exception as e:
            self.logger.error(f"❌ خطأ في تشغيل البوت: {e}")
            return False
        finally:
            await self.cleanup()
        
        return True
    
    async def cleanup(self):
        """تنظيف الموارد"""
        self.logger.info("🧹 بدء تنظيف الموارد...")
        
        self.is_running = False
        
        # إلغاء مهمة التنظيف
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # إغلاق البوت
        if self.bot:
            try:
                await self.bot.bot.session.close()
            except Exception as e:
                self.logger.error(f"خطأ في إغلاق جلسة البوت: {e}")
        
        # تنظيف الملفات المؤقتة
        try:
            temp_files = Path("temp").glob("*")
            for temp_file in temp_files:
                if temp_file.is_file():
                    temp_file.unlink()
        except Exception as e:
            self.logger.error(f"خطأ في تنظيف الملفات المؤقتة: {e}")
        
        self.logger.info("✅ تم تنظيف الموارد بنجاح")

def signal_handler(signum, frame):
    """معالج إشارات النظام"""
    logger = logging.getLogger(__name__)
    logger.info(f"تم استلام الإشارة {signum}، جاري الإغلاق الآمن...")
    
    # إيقاف حلقة الأحداث
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.stop()

async def health_check():
    """فحص صحة النظام"""
    logger = logging.getLogger(__name__)
    
    try:
        # فحص التوكن
        if not Config.BOT_TOKEN or Config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            logger.error("❌ توكن البوت غير محدد أو غير صحيح")
            return False
        
        # فحص المساحة المتوفرة
        import shutil
        free_space = shutil.disk_usage(".").free
        if free_space < 100 * 1024 * 1024:  # أقل من 100 ميجا
            logger.warning(f"⚠️ مساحة تخزين قليلة: {FileManager.format_size(free_space)}")
        
        # فحص إمكانية إنشاء الملفات
        test_file = Path("test_write.tmp")
        test_file.write_text("test")
        test_file.unlink()
        
        logger.info("✅ فحص صحة النظام مكتمل")
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل في فحص صحة النظام: {e}")
        return False

async def main():
    """الدالة الرئيسية"""
    
    # إعداد السجلات
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("🎬 بوت تليجرام لتنزيل الفيديوهات والترجمات")
    logger.info("=" * 60)
    
    # تسجيل معالجات الإشارات
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    # فحص صحة النظام
    if not await health_check():
        logger.error("❌ فشل فحص صحة النظام، يتم إيقاف البرنامج")
        sys.exit(1)
    
    # إنشاء وتشغيل مدير البوت
    bot_manager = BotManager()
    
    try:
        success = await bot_manager.run()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت بواسطة المستخدم")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # التأكد من إصدار Python
    if sys.version_info < (3, 8):
        print("❌ يتطلب Python 3.8 أو أحدث")
        sys.exit(1)
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ خطأ في بدء البرنامج: {e}")
        sys.exit(1)
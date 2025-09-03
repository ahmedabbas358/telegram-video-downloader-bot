# main.py
#!/usr/bin/env python3
"""
الملف الرئيسي لبوت تليجرام لتنزيل الفيديوهات
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from datetime import datetime

# إعداد المسار لاستيراد الوحدات
sys.path.append(str(Path(__file__).parent))

from config import config
from bot_handler import bot_handler
from database import db
from downloader import downloader
import uvloop

# إعداد نظام السجلات
def setup_logging():
    """إعداد نظام السجلات"""
    
    # إنشاء مجلد السجلات
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # تكوين السجل الأساسي
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(filename)s:%(lineno)d - %(message)s"
    )
    
    # إعداد معالجات السجل
    handlers = [
        logging.StreamHandler(sys.stdout),  # الطباعة في وحدة التحكم
        logging.FileHandler(
            log_dir / f"bot_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
    ]
    
    # تطبيق الإعدادات
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format=log_format,
        handlers=handlers,
        force=True
    )
    
    # تقليل مستوى السجل للمكتبات الخارجية
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    return logger

class BotApplication:
    """التطبيق الرئيسي للبوت"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.running = False
        self.cleanup_task = None
    
    async def startup(self):
        """بدء تشغيل التطبيق"""
        try:
            self.logger.info("🚀 Starting Telegram Bot...")
            
            # التحقق من الإعدادات المطلوبة
            self._validate_config()
            
            # تهيئة قاعدة البيانات
            self.logger.info("📊 Initializing database...")
            await db.init_db()
            
            # عرض إحصائيات البدء
            await self._show_startup_stats()
            
            # بدء مهمة تنظيف الملفات القديمة
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            self.running = True
            self.logger.info("✅ Bot application started successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start application: {e}")
            raise
    
    async def shutdown(self):
        """إغلاق التطبيق"""
        try:
            self.logger.info("🛑 Shutting down bot application...")
            
            self.running = False
            
            # إلغاء مهمة التنظيف
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # إغلاق البوت
            await bot_handler.stop()
            
            # تنظيف أخير للملفات المؤقتة
            await self._final_cleanup()
            
            self.logger.info("✅ Bot application shut down successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
    
    def _validate_config(self):
        """التحقق من صحة الإعدادات"""
        if not config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        
        if not config.DOWNLOAD_PATH.exists():
            config.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"📁 Created download directory: {config.DOWNLOAD_PATH}")
        
        self.logger.info("✅ Configuration validated")
    
    async def _show_startup_stats(self):
        """عرض إحصائيات البدء"""
        try:
            stats = await db.get_global_stats()
            
            self.logger.info("📊 Startup Statistics:")
            self.logger.info(f"   👥 Total Users: {stats.get('total_users', 0)}")
            self.logger.info(f"   📥 Total Downloads: {stats.get('total_downloads', 0)}")
            self.logger.info(f"   💾 Max File Size: {config.MAX_FILE_SIZE} MB")
            self.logger.info(f"   📑 Max Playlist Size: {config.MAX_PLAYLIST_SIZE} videos")
            self.logger.info(f"   🌍 Supported Languages: {len(config.SUPPORTED_LANGUAGES)}")
            
        except Exception as e:
            self.logger.warning(f"Could not retrieve startup stats: {e}")
    
    async def _periodic_cleanup(self):
        """تنظيف دوري للملفات القديمة"""
        while self.running:
            try:
                await asyncio.sleep(24 * 3600)  # كل 24 ساعة
                
                if self.running:
                    self.logger.info("🧹 Starting periodic cleanup...")
                    await downloader.cleanup_old_files(days=3)
                    self.logger.info("✅ Periodic cleanup completed")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Periodic cleanup error: {e}")
    
    async def _final_cleanup(self):
        """تنظيف نهائي قبل الإغلاق"""
        try:
            # تنظيف الملفات المؤقتة
            temp_files = list(config.DOWNLOAD_PATH.rglob("*.tmp"))
            for temp_file in temp_files:
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            
            if temp_files:
                self.logger.info(f"🧹 Cleaned up {len(temp_files)} temporary files")
                
        except Exception as e:
            self.logger.error(f"Final cleanup error: {e}")

# معالجة الإشارات للإغلاق الآمن
async def signal_handler(app: BotApplication):
    """معالج إشارات النظام للإغلاق الآمن"""
    logger = logging.getLogger(__name__)
    
    def handle_signal(signum, frame):
        logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(app.shutdown())
    
    # تسجيل معالجات الإشارات
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, handle_signal)

async def main():
    """الدالة الرئيسية"""
    logger = logging.getLogger(__name__)
    app = BotApplication()
    
    try:
        # تثبيت uvloop للأداء الأفضل (إذا كان متاحاً)
        if sys.platform != 'win32':
            try:
                uvloop.install()
                logger.info("🚀 Using uvloop for better performance")
            except ImportError:
                logger.info("⚠️ uvloop not available, using default event loop")
        
        # إعداد معالج الإشارات
        await signal_handler(app)
        
        # بدء التطبيق
        await app.startup()
        
        # بدء البوت
        try:
            await bot_handler.start_polling()
        except KeyboardInterrupt:
            logger.info("👋 Received keyboard interrupt")
        except Exception as e:
            logger.error(f"❌ Bot polling error: {e}")
            raise
        
    except Exception as e:
        logger.error(f"💥 Critical error: {e}")
        return 1
    
    finally:
        # تنظيف نهائي
        try:
            await app.shutdown()
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
import os
import asyncio
import logging
from urllib.parse import urlparse
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
from telegram.ext import filters

from config import BOT_TOKEN, DOWNLOAD_DIR
from database import Database
from downloader import Downloader

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BotHandler:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.db = Database()
        self.downloader = Downloader()
        self.setup_handlers()
    
    def setup_handlers(self):
        """تكوين معالجات الأوامر"""
        self.application.add_handler(CommandHandler("start", self.start_handler))
        self.application.add_handler(CommandHandler("help", self.help_handler))
        self.application.add_handler(CommandHandler("stats", self.stats_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.url_handler))
        self.application.add_handler(CallbackQueryHandler(self.callback_handler))
    
    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر البدء"""
        user = update.effective_user
        
        # تسجيل المستخدم في قاعدة البيانات
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        self.db.add_user(user_data)
        
        welcome_text = """
🎬 **مرحباً بك في بوت تنزيل الفيديوهات**

✨ **الميزات المتوفرة:**
• تنزيل الفيديوهات بجودات مختلفة
• تنزيل قوائم التشغيل كاملة  
• تنزيل الترجمات بلغات متعددة
• عرض تقدم التحميل المباشر
• إحصاءات شخصية عن التنزيلات

📝 **كيفية الاستخدام:**
فقط أرسل رابط الفيديو أو قائمة التشغيل

🔗 **المواقع المدعومة:**
YouTube, Vimeo, Facebook, Twitter, Instagram, TikTok وأكثر من 1000 موقع آخر

للمساعدة: /help
للإحصائيات: /stats
        """
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
    
    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر المساعدة"""
        help_text = """
📖 **دليل الاستخدام التفصيلي:**

**1. تنزيل فيديو مفرد:**
• أرسل رابط الفيديو
• اختر الجودة المطلوبة
• اختياري: تنزيل الترجمة

**2. تنزيل قائمة تشغيل:**
• أرسل رابط قائمة التشغيل
• اختر الجودة لجميع الفيديوهات
• اختياري: تنزيل ترجمات جميع الفيديوهات

**3. خيارات الترجمة:**
• ترجمات أصلية (إن وجدت)
• ترجمات تلقائية من YouTube
• صيغ متعددة: SRT, VTT

**4. معلومات إضافية:**
• عرض الحجم قبل التنزيل
• تقدم التحميل المباشر
• تقرير مفصل عند الانتهاء

🚀 **لبدء التنزيل، أرسل الرابط الآن!**
        """
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def stats_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصائيات المستخدم"""
        user_id = update.effective_user.id
        user_stats = self.db.get_user_stats(user_id)
        
        if user_stats:
            stats_text = f"""
📊 **إحصائياتك الشخصية:**

👤 **المستخدم:** {user_stats['first_name']}
📥 **عدد التنزيلات:** {user_stats['downloads_count']}
📅 **تاريخ الانضمام:** {user_stats['join_date'].split()[0]}
🕒 **آخر تنزيل:** {user_stats['last_download'].split()[0] if user_stats['last_download'] else 'لا يوجد'}
            """
            await update.message.reply_text(stats_text, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ لم يتم العثور على إحصائيات للمستخدم")
    
    async def url_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الروابط"""
        url = update.message.text.strip()
        
        if not self.is_valid_url(url):
            await update.message.reply_text("❌ الرجاء إرسال رابط صحيح")
            return
        
        # إرسال رسالة الانتظار
        status_msg = await update.message.reply_text("🔄 جاري تحليل الرابط...")
        
        try:
            video_info = await self.downloader.get_video_info(url)
            await status_msg.delete()
            
            if video_info['is_playlist']:
                await self.handle_playlist(update, video_info)
            else:
                await self.handle_single_video(update, video_info)
                
        except Exception as e:
            await status_msg.edit_text(f"❌ خطأ في تحليل الرابط: {str(e)}")
            logger.error(f"Error processing URL: {e}")
    
    def is_valid_url(self, url: str) -> bool:
        """التحقق من صحة الرابط"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def handle_single_video(self, update: Update, video_info: Dict):
        """معالجة الفيديو المفرد"""
        duration_str = self.downloader.format_duration(video_info['duration'])
        
        info_text = f"""
📹 **معلومات الفيديو:**

🏷️ **العنوان:** {video_info['title']}
⏱️ **المدة:** {duration_str}
🌐 **الموقع:** {urlparse(video_info['url']).netloc}

اختر نوع التنزيل:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎥 تنزيل الفيديو", callback_data="download_video")],
            [InlineKeyboardButton("📝 تنزيل الترجمة فقط", callback_data="download_subs_only")],
            [InlineKeyboardButton("📦 تنزيل الفيديو + الترجمة", callback_data="download_both")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(info_text, parse_mode="Markdown", reply_markup=reply_markup)
        
        # حفظ معلومات الفيديو في السياق للمرحلة القادمة
        context.user_data['video_info'] = video_info
    
    async def handle_playlist(self, update: Update, video_info: Dict):
        """معالجة قائمة التشغيل"""
        info_text = f"""
📂 **معلومات قائمة التشغيل:**

🏷️ **العنوان:** {video_info['title']}
📊 **عدد الفيديوهات:** {video_info['playlist_count']}
🌐 **الموقع:** {urlparse(video_info['url']).netloc}

اختر نوع التنزيل:
        """
        
        keyboard = [
            [InlineKeyboardButton("🎬 تنزيل جميع الفيديوهات", callback_data="download_playlist_videos")],
            [InlineKeyboardButton("📝 تنزيل جميع الترجمات", callback_data="download_playlist_subs")],
            [InlineKeyboardButton("📦 تنزيل الكل", callback_data="download_playlist_all")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(info_text, parse_mode="Markdown", reply_markup=reply_markup)
        
        # حفظ معلومات الفيديو في السياق للمرحلة القادمة
        context.user_data['video_info'] = video_info
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الاستدعاء"""
        query = update.callback_query
        await query.answer()
        
        video_info = context.user_data.get('video_info')
        if not video_info:
            await query.message.edit_text("❌ خطأ: لم يتم العثور على معلومات الفيديو")
            return
        
        if query.data == "download_video":
            await self.show_video_formats(query, video_info)
        elif query.data == "download_subs_only":
            await self.show_subtitle_options(query, video_info)
        elif query.data == "download_both":
            await self.show_video_formats(query, video_info, include_subs=True)
        elif query.data.startswith("format_"):
            await self.download_with_format(query, video_info, context)
        elif query.data.startswith("sub_"):
            await self.download_subtitles(query, video_info)
        elif query.data.startswith("download_playlist"):
            await self.handle_playlist_download(query, video_info)
    
    async def show_video_formats(self, query, video_info: Dict, include_subs: bool = False):
        """عرض جودات الفيديو المتوفرة"""
        # تحليل الصيغ المتاحة
        formats = self.downloader.get_available_formats(video_info.get('formats', []))
        
        if not formats:
            await query.message.edit_text("❌ لم يتم العثور على صيغ متوفرة للتنزيل")
            return
        
        keyboard = []
        for fmt in formats:
            size_info = f" ({fmt['filesize_str']})" if fmt['filesize_str'] else ""
            button_text = f"{fmt['quality']} - {fmt['ext'].upper()}{size_info}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"format_{fmt['format_id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🎥 **اختر جودة الفيديو:**\n\n"
        if include_subs:
            text += "📝 سيتم تنزيل الترجمة أيضاً إن وجدت\n\n"
        
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=reply_markup)
        
        # حفظ معلومات إضافية في السياق
        context.user_data['include_subs'] = include_subs
    
    async def show_subtitle_options(self, query, video_info: Dict):
        """عرض خيارات الترجمة"""
        subtitles = video_info.get('subtitles', {})
        
        if not subtitles:
            await query.message.edit_text("❌ لا توجد ترجمات متوفرة لهذا الفيديو")
            return
        
        keyboard = []
        for lang_code, subs in subtitles.items():
            lang_name = self.downloader.get_language_name(lang_code)
            for sub in subs:
                ext = sub.get('ext', 'srt')
                button_text = f"{lang_name} ({ext.upper()})"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"sub_{lang_code}_{ext}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.edit_text("📝 **اختر الترجمة:**", parse_mode="Markdown", reply_markup=reply_markup)
    
    async def download_with_format(self, query, video_info: Dict, context: ContextTypes.DEFAULT_TYPE):
        """تنزيل الفيديو بالجودة المحددة"""
        format_id = query.data.split('_')[1]
        include_subs = context.user_data.get('include_subs', False)
        
        progress_msg = await query.message.edit_text("🚀 بدء التنزيل...")
        
        try:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    asyncio.create_task(progress_msg.edit_text(
                        f"⬇️ **جاري التنزيل...**\n\n"
                        f"📊 التقدم: {d.get('_percent_str', '0%')}\n"
                        f"🚀 السرعة: {d.get('_speed_str', 'N/A')}"
                    ))
                elif d['status'] == 'finished':
                    asyncio.create_task(progress_msg.edit_text("✅ تم التنزيل! جاري المعالجة..."))
            
            file_path = await self.downloader.download_video(
                video_info['url'], 
                format_id, 
                query.message.chat.id,
                progress_hook,
                include_subs
            )
            
            if file_path:
                # تحديث إحصائيات المستخدم
                self.db.increment_download_count(query.from_user.id)
                
                # تسجيل في سجل التنزيلات
                download_data = {
                    'user_id': query.from_user.id,
                    'url': video_info['url'],
                    'title': video_info['title'],
                    'quality': format_id,
                    'file_size': os.path.getsize(file_path),
                    'status': 'completed'
                }
                self.db.add_download_history(download_data)
                
                await self.send_downloaded_file(query.message, file_path)
            else:
                await progress_msg.edit_text("❌ فشل في التنزيل")
                
        except Exception as e:
            await progress_msg.edit_text(f"❌ خطأ في التنزيل: {str(e)}")
            logger.error(f"Download error: {e}")
    
    async def send_downloaded_file(self, message, file_path: str):
        """إرسال الملف المُنزل"""
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            if file_size > 50 * 1024 * 1024:  # أكبر من 50 ميجا
                await message.reply_text(
                    f"📁 **تم التنزيل بنجاح!**\n\n"
                    f"📄 اسم الملف: {file_name}\n"
                    f"📊 الحجم: {self.downloader.format_filesize(file_size)}\n\n"
                    f"⚠️ الملف كبير جداً لإرساله عبر تليجرام. "
                    f"يمكنك العثور عليه في مجلد التنزيل."
                )
            else:
                await message.reply_document(
                    document=open(file_path, 'rb'),
                    caption=f"✅ تم التنزيل بنجاح!\n📊 الحجم: {self.downloader.format_filesize(file_size)}"
                )
            
            # حذف الملف بعد الإرسال
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await message.reply_text("❌ خطأ في إرسال الملف")
    
    async def handle_playlist_download(self, query, video_info: Dict):
        """معالجة تنزيل قائمة التشغيل"""
        progress_msg = await query.message.edit_text("📥 جاري تحضير قائمة التشغيل للتنزيل...")
        
        try:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    asyncio.create_task(progress_msg.edit_text(
                        f"⬇️ **جاري تنزيل قائمة التشغيل...**\n\n"
                        f"📊 التقدم: {d.get('_percent_str', '0%')}\n"
                        f"🚀 السرعة: {d.get('_speed_str', 'N/A')}"
                    ))
            
            success_count = await self.downloader.download_playlist(
                video_info['url'],
                query.message.chat.id,
                progress_hook
            )
            
            await progress_msg.edit_text(f"✅ تم تنزيل {success_count} من أصل {video_info['playlist_count']} فيديو بنجاح!")
            
            # تحديث إحصائيات المستخدم
            self.db.increment_download_count(query.from_user.id)
            
        except Exception as e:
            await progress_msg.edit_text(f"❌ خطأ في تنزيل قائمة التشغيل: {str(e)}")
            logger.error(f"Playlist download error: {e}")
    
    async def download_subtitles(self, query, video_info: Dict):
        """تنزيل الترجمات"""
        parts = query.data.split('_')
        lang_code = parts[1]
        ext = parts[2]
        
        progress_msg = await query.message.edit_text("📝 جاري تنزيل الترجمة...")
        
        try:
            subtitle_path = await self.downloader.download_subtitles(
                video_info['url'],
                lang_code,
                ext,
                query.message.chat.id
            )
            
            if subtitle_path:
                await query.message.reply_document(
                    document=open(subtitle_path, 'rb'),
                    caption=f"📝 ترجمة {self.downloader.get_language_name(lang_code)} ({ext.upper()})"
                )
                os.remove(subtitle_path)
            else:
                await progress_msg.edit_text("❌ فشل في تنزيل الترجمة")
                
        except Exception as e:
            await progress_msg.edit_text(f"❌ خطأ في تنزيل الترجمة: {str(e)}")
    
    def run(self):
        """تشغيل البوت"""
        self.application.run_polling()
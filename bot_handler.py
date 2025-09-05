"""
معالج البوت والأوامر
"""
import asyncio
import os
from typing import Dict, Any, Optional
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    BufferedInputFile, FSInputFile
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest
import humanize
from config import config
from database import db
from downloader import downloader, DownloadProgress
import logging

logger = logging.getLogger(__name__)

class DownloadStates(StatesGroup):
    """حالات التنزيل"""
    waiting_url = State()
    choosing_type = State()
    choosing_quality = State()
    choosing_subtitle_lang = State()
    choosing_subtitle_format = State()
    downloading = State()
    playlist_confirm = State()

class TelegramBot:
    """فئة البوت الرئيسية"""
    
    def __init__(self):
        self.bot = Bot(token=config.BOT_TOKEN)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self.router = Router()
        self.user_sessions: Dict[int, Dict] = {}
        self.setup_handlers()
    
    def setup_handlers(self):
        """إعداد معالجات الأوامر"""
        
        # الأوامر الأساسية
        self.router.message(Command("start"))(self.cmd_start)
        self.router.message(Command("help"))(self.cmd_help)
        self.router.message(Command("stats"))(self.cmd_stats)
        self.router.message(Command("settings"))(self.cmd_settings)
        self.router.message(Command("cancel"))(self.cmd_cancel)
        
        # معالجة الروابط
        self.router.message(F.text.contains("youtube.com") | F.text.contains("youtu.be"))(self.handle_url)
        
        # معالجة الأزرار
        self.router.callback_query(F.data.startswith("download_"))(self.handle_download_callback)
        self.router.callback_query(F.data.startswith("quality_"))(self.handle_quality_callback)
        self.router.callback_query(F.data.startswith("subtitle_"))(self.handle_subtitle_callback)
        self.router.callback_query(F.data.startswith("playlist_"))(self.handle_playlist_callback)
        self.router.callback_query(F.data.startswith("settings_"))(self.handle_settings_callback)
        
        # تسجيل الموجه
        self.dp.include_router(self.router)
    
    async def cmd_start(self, message: Message, state: FSMContext):
        """أمر البدء"""
        user_data = {
            'id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
            'language_code': message.from_user.language_code
        }
        
        await db.create_or_update_user(user_data)
        await state.clear()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 المساعدة", callback_data="help")],
            [InlineKeyboardButton(text="⚙️ الإعدادات", callback_data="settings_main")],
            [InlineKeyboardButton(text="📊 الإحصائيات", callback_data="stats")]
        ])
        
        await message.answer(config.Messages.WELCOME, reply_markup=keyboard)
    
    async def cmd_help(self, message: Message):
        """أمر المساعدة"""
        await message.answer(config.Messages.HELP)
    
    async def cmd_stats(self, message: Message):
        """أمر الإحصائيات"""
        user_stats = await db.get_user_stats(message.from_user.id)
        
        if not user_stats:
            await message.answer("❌ لم يتم العثور على بيانات المستخدم")
            return
        
        stats_text = f"""
📊 **إحصائياتك الشخصية:**

📥 إجمالي التنزيلات: `{user_stats['total_downloads']}`
📁 التنزيلات الأخيرة: `{user_stats['recent_downloads']}`
💾 إجمالي البيانات: `{user_stats['total_size']}`
📅 عضو منذ: `{user_stats['member_since']}`
🕐 آخر نشاط: `{user_stats['last_activity']}`
        """
        
        await message.answer(stats_text, parse_mode="Markdown")
    
    async def cmd_settings(self, message: Message):
        """أمر الإعدادات"""
        await self.show_settings_menu(message.from_user.id, message)
    
    async def cmd_cancel(self, message: Message, state: FSMContext):
        """إلغاء العملية الحالية"""
        await state.clear()
        if message.from_user.id in self.user_sessions:
            del self.user_sessions[message.from_user.id]
        
        await message.answer("❌ تم إلغاء العملية الحالية")
    
    async def handle_url(self, message: Message, state: FSMContext):
        """معالجة الروابط"""
        url = message.text.strip()
        
        if not downloader.is_valid_url(url):
            await message.answer(config.Messages.ERROR_INVALID_URL)
            return
        
        # إظهار رسالة المعالجة
        processing_msg = await message.answer(config.Messages.INFO_EXTRACTING_INFO)
        
        try:
            if downloader.is_playlist_url(url):
                await self.handle_playlist_url(message, url, state, processing_msg)
            else:
                await self.handle_video_url(message, url, state, processing_msg)
        
        except Exception as e:
            logger.error(f"Error handling URL: {e}")
            await processing_msg.edit_text("❌ حدث خطأ أثناء معالجة الرابط")
    
    async def handle_video_url(self, message: Message, url: str, state: FSMContext, processing_msg: Message):
        """معالجة رابط فيديو"""
        video_info = await downloader.extract_video_info(url)
        
        if not video_info:
            await processing_msg.edit_text("❌ فشل في استخراج معلومات الفيديو")
            return
        
        # حفظ معلومات الجلسة
        self.user_sessions[message.from_user.id] = {
            'url': url,
            'video_info': video_info,
            'type': 'video'
        }
        
        # إنشاء معاينة الفيديو
        duration_str = self._format_duration(video_info.duration)
        view_count_str = humanize.intcomma(video_info.view_count) if video_info.view_count else "غير متاح"
        
        video_preview = f"""
🎬 **{video_info.title}**

👤 **القناة:** {video_info.uploader}
⏱ **المدة:** {duration_str}  
👁 **المشاهدات:** {view_count_str}

**اختر نوع التنزيل:**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📹 فيديو فقط", callback_data="download_video")],
            [InlineKeyboardButton(text="📝 ترجمة فقط", callback_data="download_subtitle")],
            [InlineKeyboardButton(text="📹📝 فيديو + ترجمة", callback_data="download_both")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel")]
        ])
        
        await processing_msg.edit_text(video_preview, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(DownloadStates.choosing_type)
    
    async def handle_playlist_url(self, message: Message, url: str, state: FSMContext, processing_msg: Message):
        """معالجة رابط قائمة التشغيل"""
        playlist_info = await downloader.extract_playlist_info(url)
        
        if not playlist_info:
            await processing_msg.edit_text("❌ فشل في استخراج معلومات قائمة التشغيل")
            return
        
        total_videos = len(playlist_info.entries) if playlist_info.entries else 0
        
        if total_videos > config.MAX_PLAYLIST_SIZE:
            await processing_msg.edit_text(config.Messages.ERROR_PLAYLIST_TOO_LARGE)
            return
        
        # حفظ معلومات الجلسة
        self.user_sessions[message.from_user.id] = {
            'url': url,
            'playlist_info': playlist_info,
            'type': 'playlist'
        }
        
        # إنشاء معاينة قائمة التشغيل
        playlist_preview = f"""
📑 **قائمة التشغيل:** {playlist_info.title}

👤 **المنشئ:** {playlist_info.uploader}
🎬 **عدد الفيديوهات:** {total_videos}

⚠️ **تنبيه:** سيتم تنزيل جميع الفيديوهات في قائمة التشغيل

**هل تريد المتابعة؟**
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأكيد التنزيل", callback_data="playlist_confirm")],
            [InlineKeyboardButton(text="👁 معاينة الفيديوهات", callback_data="playlist_preview")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel")]
        ])
        
        await processing_msg.edit_text(playlist_preview, reply_markup=keyboard, parse_mode="Markdown")
        await state.set_state(DownloadStates.playlist_confirm)
    
    async def handle_download_callback(self, callback: CallbackQuery, state: FSMContext):
        """معالجة اختيار نوع التنزيل"""
        user_id = callback.from_user.id
        download_type = callback.data.split("_")[1]
        
        if user_id not in self.user_sessions:
            await callback.answer("❌ الجلسة منتهية الصلاحية، يرجى إرسال الرابط مرة أخرى")
            return
        
        session = self.user_sessions[user_id]
        session['download_type'] = download_type
        
        video_info = session.get('video_info')
        if not video_info:
            await callback.message.edit_text("❌ لا يمكن العثور على معلومات الفيديو")
            return
        
        if download_type == "video":
            await self.show_quality_selection(callback, video_info)
        elif download_type == "subtitle":
            await self.show_subtitle_language_selection(callback, video_info)
        elif download_type == "both":
            await self.show_quality_selection(callback, video_info, include_subtitle=True)
        
        await callback.answer()
    
    async def show_quality_selection(self, callback: CallbackQuery, video_info, include_subtitle=False):
        """عرض اختيار الجودة"""
        if not video_info:
            await callback.message.edit_text("❌ لا يمكن الحصول على معلومات الفيديو")
            return
        
        qualities = downloader.get_available_qualities(video_info)
        
        if not qualities:
            await callback.message.edit_text("❌ لا توجد جودات متاحة لهذا الفيديو")
            return
        
        keyboard_buttons = []
        for quality_info in qualities:
            size_str = humanize.naturalsize(quality_info['filesize']) if quality_info.get('filesize') else "غير محدد"
            button_text = f"{quality_info['quality']} ({size_str})"
            callback_data = f"quality_{quality_info['quality']}"
            keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_type")])
        keyboard_buttons.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        text = "📊 **اختر الجودة المطلوبة:**\n\n"
        if include_subtitle:
            text += "ℹ️ ستتمكن من اختيار الترجمة بعد تحديد الجودة"
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def handle_quality_callback(self, callback: CallbackQuery, state: FSMContext):
        """معالجة اختيار الجودة"""
        user_id = callback.from_user.id
        quality = callback.data.split("_")[1]
        
        if user_id not in self.user_sessions:
            await callback.answer("❌ الجلسة منتهية الصلاحية")
            return
        
        session = self.user_sessions[user_id]
        session['quality'] = quality
        
        if session.get('download_type') == "both":
            video_info = session.get('video_info')
            if not video_info:
                await callback.message.edit_text("❌ لا يمكن العثور على معلومات الفيديو")
                return
            await self.show_subtitle_language_selection(callback, video_info)
        else:
            await self.start_download(callback, state)
        
        await callback.answer()
    
    async def show_subtitle_language_selection(self, callback: CallbackQuery, video_info):
        """عرض اختيار لغة الترجمة"""
        if not video_info:
            await callback.message.edit_text("❌ لا يمكن الحصول على معلومات الفيديو")
            return
        
        available_subs = downloader.get_available_subtitles(video_info)
        
        if not available_subs:
            await callback.message.edit_text("❌ لا توجد ترجمات متاحة لهذا الفيديو")
            return
        
        keyboard_buttons = []
        for lang_code, sub_info in available_subs.items():
            sub_type = "🔄" if sub_info.get('type') == 'auto' else "✅"
            language_name = sub_info.get('language', 'غير معروف')
            button_text = f"{sub_type} {language_name}"
            callback_data = f"subtitle_lang_{lang_code}"
            keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_quality")])
        keyboard_buttons.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        text = """
🌍 **اختر لغة الترجمة:**

✅ = ترجمة أصلية
🔄 = ترجمة تلقائية
        """
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    async def handle_subtitle_callback(self, callback: CallbackQuery, state: FSMContext):
        """معالجة اختيار الترجمة"""
        user_id = callback.from_user.id
        action = callback.data.split("_")[1]
        
        if user_id not in self.user_sessions:
            await callback.answer("❌ الجلسة منتهية الصلاحية")
            return
        
        session = self.user_sessions[user_id]
        
        if action == "lang":
            lang_code = callback.data.split("_")[2]
            session['subtitle_lang'] = lang_code
            await self.show_subtitle_format_selection(callback)
        elif action == "format":
            format_type = callback.data.split("_")[2]
            session['subtitle_format'] = format_type
            await self.start_download(callback, state)
        
        await callback.answer()
    
    async def show_subtitle_format_selection(self, callback: CallbackQuery):
        """عرض اختيار صيغة الترجمة"""
        keyboard_buttons = []
        for fmt in config.SUBTITLE_FORMATS:
            button_text = fmt.upper()
            callback_data = f"subtitle_format_{fmt}"
            keyboard_buttons.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_subtitle_lang")])
        keyboard_buttons.append([InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text("📄 **اختر صيغة الترجمة:**", reply_markup=keyboard)
    
    async def handle_playlist_callback(self, callback: CallbackQuery, state: FSMContext):
        """معالجة قوائم التشغيل"""
        user_id = callback.from_user.id
        action = callback.data.split("_")[1]
        
        if user_id not in self.user_sessions:
            await callback.answer("❌ الجلسة منتهية الصلاحية")
            return
        
        session = self.user_sessions[user_id]
        
        if action == "confirm":
            await self.show_quality_selection(callback, None)
        elif action == "preview":
            playlist_info = session.get('playlist_info')
            if not playlist_info:
                await callback.message.edit_text("❌ لا يمكن العثور على معلومات قائمة التشغيل")
                return
            await self.show_playlist_preview(callback, playlist_info)
        
        await callback.answer()
    
    async def show_playlist_preview(self, callback: CallbackQuery, playlist_info):
        """عرض معاينة قائمة التشغيل"""
        entries = playlist_info.entries[:10] if playlist_info.entries else []
        preview_text = f"📑 **معاينة قائمة التشغيل:** {playlist_info.title}\n\n"
        
        for i, entry in enumerate(entries, 1):
            title = entry.get('title', 'عنوان غير متاح')[:50]
            duration = self._format_duration(entry.get('duration', 0))
            preview_text += f"{i}. {title} ({duration})\n"
        
        if playlist_info.entries and len(playlist_info.entries) > 10:
            preview_text += f"\n... و {len(playlist_info.entries) - 10} فيديوهات أخرى"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ تأكيد التنزيل", callback_data="playlist_confirm")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_playlist")],
            [InlineKeyboardButton(text="❌ إلغاء", callback_data="cancel")]
        ])
        
        await callback.message.edit_text(preview_text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def start_download(self, callback: CallbackQuery, state: FSMContext):
        """بدء عملية التنزيل"""
        user_id = callback.from_user.id
        if user_id not in self.user_sessions:
            await callback.message.edit_text("❌ الجلسة منتهية الصلاحية")
            return
        
        session = self.user_sessions[user_id]
        
        # تحديث الرسالة لإظهار بدء التنزيل
        await callback.message.edit_text(config.Messages.INFO_DOWNLOADING)
        
        try:
            if session.get('type') == 'video':
                await self.download_video(callback, session, state)
            elif session.get('type') == 'playlist':
                await self.download_playlist(callback, session, state)
        
        except Exception as e:
            logger.error(f"Download error: {e}")
            await callback.message.edit_text(f"❌ فشل في التنزيل: {str(e)}")
        
        # تنظيف الجلسة
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        
        await state.clear()
    
    async def download_video(self, callback: CallbackQuery, session: Dict, state: FSMContext):
        """تنزيل فيديو واحد"""
        user_id = callback.from_user.id
        progress_msg = None
        
        async def progress_callback(progress: DownloadProgress):
            nonlocal progress_msg
            try:
                percent = progress.percent if progress.percent else 0
                speed_str = humanize.naturalsize(progress.speed) if progress.speed else "0"
                downloaded_str = humanize.naturalsize(progress.downloaded_bytes)
                total_str = humanize.naturalsize(progress.total_bytes) if progress.total_bytes else "غير محدد"
                
                progress_text = f"""
⬇️ **جاري التنزيل...**

📊 التقدم: {percent:.1f}%
📥 تم تنزيل: {downloaded_str} / {total_str}
🚀 السرعة: {speed_str}/ث
                """
                
                if progress_msg:
                    try:
                        await progress_msg.edit_text(progress_text, parse_mode="Markdown")
                    except TelegramBadRequest:
                        pass  # تجاهل الأخطاء إذا كان النص مطابق
                else:
                    progress_msg = await callback.message.edit_text(progress_text, parse_mode="Markdown")
                    
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
        
        # تنزيل الفيديو
        if session.get('download_type') in ['video', 'both']:
            if not session.get('quality'):
                await callback.message.edit_text("❌ لم يتم تحديد جودة الفيديو")
                return
            
            file_path = await downloader.download_video(
                session['url'],
                session['quality'],
                user_id,
                progress_callback
            )
            
            if file_path and os.path.exists(file_path):
                await self.send_file(callback.message, file_path, "video")
        
        # تنزيل الترجمة
        if session.get('download_type') in ['subtitle', 'both']:
            if not session.get('subtitle_lang'):
                await callback.message.edit_text("❌ لم يتم تحديد لغة الترجمة")
                return
            if not session.get('subtitle_format'):
                await callback.message.edit_text("❌ لم يتم تحديد صيغة الترجمة")
                return
            
            subtitle_path = await downloader.download_subtitle(
                session['url'],
                session['subtitle_lang'],
                session['subtitle_format'],
                user_id
            )
            
            if subtitle_path and os.path.exists(subtitle_path):
                await self.send_file(callback.message, subtitle_path, "document")
        
        await callback.message.edit_text(config.Messages.SUCCESS_DOWNLOAD)
    
    async def download_playlist(self, callback: CallbackQuery, session: Dict, state: FSMContext):
        """تنزيل قائمة التشغيل"""
        user_id = callback.from_user.id
        progress_msg = None
        
        async def progress_callback(message: str):
            nonlocal progress_msg
            try:
                if progress_msg:
                    await progress_msg.edit_text(f"📥 {message}")
                else:
                    progress_msg = await callback.message.edit_text(f"📥 {message}")
            except TelegramBadRequest:
                pass
        
        if not session.get('quality'):
            await callback.message.edit_text("❌ لم يتم تحديد جودة الفيديو")
            return
        
        result = await downloader.download_playlist(
            session['url'],
            session['quality'],
            user_id,
            progress_callback=progress_callback
        )
        
        if result.get('status') == 'failed':
            await callback.message.edit_text(f"❌ فشل تنزيل قائمة التشغيل: {result.get('error', 'خطأ غير محدد')}")
            return
        
        # إرسال ملخص النتائج
        summary = f"""
✅ **تم الانتهاء من تنزيل قائمة التشغيل**

📊 **النتائج:**
• العدد الكلي: {result.get('total_videos', 0)}
• تم بنجاح: {result.get('completed', 0)}
• فشل: {result.get('failed', 0)}

📁 تم حفظ الملفات في مجلد منفصل
        """
        
        await callback.message.edit_text(summary, parse_mode="Markdown")
        
        # إرسال الملفات (الأوائل فقط لتجنب الحد الأقصى)
        for file_path in result.get('downloaded_files', [])[:5]:
            if os.path.exists(file_path):
                await self.send_file(callback.message, file_path, "video")
        
        if len(result.get('downloaded_files', [])) > 5:
            await callback.message.answer(f"📁 تم تنزيل {len(result['downloaded_files']) - 5} ملفات إضافية")
    
    async def send_file(self, message: Message, file_path: str, file_type: str):
        """إرسال الملف للمستخدم"""
        try:
            if not os.path.exists(file_path):
                await message.answer("❌ الملف غير موجود")
                return
                
            file_size = os.path.getsize(file_path)
            
            # التحقق من حجم الملف (حد تليجرام 50 ميجا للبوت)
            if file_size > 50 * 1024 * 1024:
                await message.answer(f"❌ الملف كبير جداً للإرسال: {humanize.naturalsize(file_size)}")
                return
            
            file_name = os.path.basename(file_path)
            
            if file_type == "video":
                await message.answer_video(
                    FSInputFile(file_path),
                    caption=f"🎬 {file_name}"
                )
            else:
                await message.answer_document(
                    FSInputFile(file_path),
                    caption=f"📄 {file_name}"
                )
            
            # حذف الملف بعد الإرسال
            os.remove(file_path)
            
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await message.answer(f"❌ فشل في إرسال الملف: {os.path.basename(file_path) if file_path else 'غير معروف'}")
    
    async def show_settings_menu(self, user_id: int, message: Message):
        """عرض قائمة الإعدادات"""
        user = await db.get_user(user_id)
        
        if not user:
            await message.answer("❌ لم يتم العثور على بيانات المستخدم")
            return
        
        settings_text = f"""
⚙️ **إعداداتك الحالية:**

🎥 الجودة المفضلة: `{user.preferred_quality}`
🌍 لغة الترجمة: `{config.SUPPORTED_LANGUAGES.get(user.preferred_subtitle_lang, 'غير محدد')}`
📄 صيغة الترجمة: `{user.preferred_subtitle_format.upper()}`
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎥 تغيير الجودة", callback_data="settings_quality")],
            [InlineKeyboardButton(text="🌍 تغيير لغة الترجمة", callback_data="settings_subtitle_lang")],
            [InlineKeyboardButton(text="📄 تغيير صيغة الترجمة", callback_data="settings_subtitle_format")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="back_to_main")]
        ])
        
        await message.answer(settings_text, reply_markup=keyboard, parse_mode="Markdown")
    
    async def handle_settings_callback(self, callback: CallbackQuery):
        """معالجة إعدادات المستخدم"""
        user_id = callback.from_user.id
        setting_type = callback.data.split("_")[1]
        
        # هنا يمكن إضافة معالجة تغيير الإعدادات
        await callback.answer("🔧 هذه الميزة قيد التطوير")
    
    def _format_duration(self, seconds: int) -> str:
        """تنسيق المدة الزمنية"""
        if not seconds:
            return "غير محدد"
            
        if seconds < 60:
            return f"{seconds}ث"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}د {secs}ث"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}س {minutes}د"
    
    async def start_polling(self):
        """بدء استقبال الرسائل"""
        await db.init_db()
        logger.info("Bot started polling...")
        await self.dp.start_polling(self.bot)
    
    async def stop(self):
        """إيقاف البوت"""
        await self.bot.session.close()
        await db.close()

# مثيل عام من البوت
bot_handler = TelegramBot()
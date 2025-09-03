import os
import re
import asyncio
import hashlib
import mimetypes
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, List, Tuple, Any
import aiofiles
import logging

logger = logging.getLogger(__name__)

class FileManager:
    """إدارة الملفات والتنزيلات"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """تنظيف اسم الملف من الأحرف غير المسموحة"""
        # إزالة الأحرف الخطيرة
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # تقصير الاسم إذا كان طويل جداً
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:200-len(ext)] + ext
        return filename.strip()
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """الحصول على حجم الملف"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0
    
    @staticmethod
    def format_size(size_bytes: int) -> str:
        """تنسيق حجم الملف بوحدات مناسبة"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        return f"{size:.1f} {units[unit_index]}"
    
    @staticmethod
    async def cleanup_old_files(directory: str, max_age_hours: int = 24):
        """تنظيف الملفات القديمة"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        logger.info(f"Deleted old file: {filename}")
                        
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")
    
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """الحصول على نوع الملف"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'

class URLValidator:
    """التحقق من صحة الروابط"""
    
    SUPPORTED_DOMAINS = [
        'youtube.com', 'youtu.be', 'm.youtube.com',
        'facebook.com', 'fb.watch', 'm.facebook.com',
        'instagram.com', 'instagr.am',
        'tiktok.com', 'vm.tiktok.com',
        'twitter.com', 'x.com', 't.co',
        'vimeo.com', 'player.vimeo.com',
        'dailymotion.com', 'dai.ly',
        'twitch.tv', 'clips.twitch.tv'
    ]
    
    @classmethod
    def is_valid_url(cls, url: str) -> bool:
        """التحقق من صحة الرابط"""
        try:
            parsed = urlparse(url)
            return all([
                parsed.scheme in ('http', 'https'),
                parsed.netloc,
                cls.is_supported_domain(parsed.netloc)
            ])
        except Exception:
            return False
    
    @classmethod
    def is_supported_domain(cls, domain: str) -> bool:
        """التحقق من دعم النطاق"""
        domain = domain.lower()
        for supported in cls.SUPPORTED_DOMAINS:
            if domain == supported or domain.endswith(f'.{supported}'):
                return True
        return False
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """استخراج معرف الفيديو من رابط YouTube"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def is_playlist_url(url: str) -> bool:
        """التحقق من كون الرابط قائمة تشغيل"""
        playlist_indicators = ['playlist?list=', '&list=', 'watch?list=']
        return any(indicator in url for indicator in playlist_indicators)

class ProgressTracker:
    """تتبع تقدم التنزيل"""
    
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.start_time = datetime.now()
        self.last_update = self.start_time
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed = 0
    
    def update(self, downloaded: int, total: int):
        """تحديث حالة التنزيل"""
        now = datetime.now()
        time_diff = (now - self.last_update).total_seconds()
        
        if time_diff >= 1:  # تحديث كل ثانية
            bytes_diff = downloaded - self.downloaded_bytes
            self.speed = bytes_diff / time_diff if time_diff > 0 else 0
            
            self.downloaded_bytes = downloaded
            self.total_bytes = total
            self.last_update = now
    
    def get_progress_info(self) -> Dict[str, Any]:
        """الحصول على معلومات التقدم"""
        percentage = (self.downloaded_bytes / self.total_bytes * 100) if self.total_bytes > 0 else 0
        elapsed_time = datetime.now() - self.start_time
        
        return {
            'percentage': round(percentage, 1),
            'downloaded': FileManager.format_size(self.downloaded_bytes),
            'total': FileManager.format_size(self.total_bytes),
            'speed': FileManager.format_size(self.speed) + '/s',
            'elapsed_time': str(elapsed_time).split('.')[0],
            'eta': self._calculate_eta() if self.speed > 0 else 'غير محدد'
        }
    
    def _calculate_eta(self) -> str:
        """حساب الوقت المتبقي"""
        if self.speed <= 0 or self.total_bytes <= self.downloaded_bytes:
            return 'غير محدد'
        
        remaining_bytes = self.total_bytes - self.downloaded_bytes
        eta_seconds = remaining_bytes / self.speed
        eta_delta = timedelta(seconds=int(eta_seconds))
        
        return str(eta_delta)

class RateLimiter:
    """محدود المعدل لمنع الإفراط في الاستخدام"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: Dict[int, List[datetime]] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """التحقق من السماح بالطلب"""
        now = datetime.now()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # تنظيف الطلبات القديمة
        cutoff_time = now - timedelta(seconds=self.time_window)
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > cutoff_time
        ]
        
        # التحقق من تجاوز الحد
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # إضافة الطلب الجديد
        self.requests[user_id].append(now)
        return True
    
    def get_wait_time(self, user_id: int) -> int:
        """الحصول على وقت الانتظار بالثواني"""
        if user_id not in self.requests or not self.requests[user_id]:
            return 0
        
        oldest_request = min(self.requests[user_id])
        wait_until = oldest_request + timedelta(seconds=self.time_window)
        wait_seconds = (wait_until - datetime.now()).total_seconds()
        
        return max(0, int(wait_seconds))

class TextFormatter:
    """تنسيق النصوص والرسائل"""
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """تجنب أحرف Markdown الخاصة"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """تنسيق مدة الفيديو"""
        if seconds <= 0:
            return "غير محدد"
        
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 50) -> str:
        """تقصير النص"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def create_progress_bar(percentage: float, length: int = 20) -> str:
        """إنشاء شريط التقدم"""
        filled = int(percentage / 100 * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}] {percentage:.1f}%"

class DatabaseHelper:
    """مساعد قاعدة البيانات (للمميزات المستقبلية)"""
    
    @staticmethod
    async def init_db():
        """تهيئة قاعدة البيانات"""
        # يمكن تطوير هذا لاحقاً لحفظ إحصائيات المستخدمين
        pass
    
    @staticmethod
    async def log_download(user_id: int, url: str, file_size: int):
        """تسجيل عملية التنزيل"""
        # يمكن تطوير هذا لاحقاً لتتبع الاستخدام
        pass

class SecurityHelper:
    """مساعد الأمان"""
    
    @staticmethod
    def generate_hash(text: str) -> str:
        """توليد hash للنص"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """التحقق من أمان اسم الملف"""
        dangerous_patterns = [
            r'\.\./', r'\.\.\\', r'^/', r'^\\',
            r'<script', r'javascript:', r'data:',
            r'\.exe$', r'\.bat$', r'\.cmd$'
        ]
        
        filename_lower = filename.lower()
        return not any(re.search(pattern, filename_lower) for pattern in dangerous_patterns)
    
    @staticmethod
    def sanitize_user_input(text: str) -> str:
        """تنظيف مدخلات المستخدم"""
        # إزالة الأحرف الخطيرة
        text = re.sub(r'[<>"\']', '', text)
        # تقصير النص إذا كان طويل جداً
        if len(text) > 500:
            text = text[:500]
        return text.strip()

# وظائف مساعدة عامة
async def retry_async(func, max_retries: int = 3, delay: float = 1.0):
    """إعادة المحاولة للوظائف غير المتزامنة"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(delay * (attempt + 1))

def get_video_info_summary(info: Dict) -> str:
    """ملخص معلومات الفيديو"""
    title = info.get('title', 'بدون عنوان')
    duration = info.get('duration', 0)
    uploader = info.get('uploader', 'غير معروف')
    view_count = info.get('view_count', 0)
    
    summary = f"🎬 **{TextFormatter.escape_markdown(title)}**\n"
    summary += f"👤 **القناة:** {TextFormatter.escape_markdown(uploader)}\n"
    summary += f"⏱️ **المدة:** {TextFormatter.format_duration(duration)}\n"
    
    if view_count > 0:
        summary += f"👁️ **المشاهدات:** {view_count:,}\n"
    
    return summary
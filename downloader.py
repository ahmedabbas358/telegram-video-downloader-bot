import os
import asyncio
import math
import re
from typing import Dict, List, Optional, Callable
import yt_dlp
from config import DOWNLOAD_DIR, YDL_OPTIONS

class Downloader:
    @staticmethod
    def format_filesize(size_bytes: int) -> str:
        """تنسيق حجم الملف"""
        if not size_bytes:
            return "غير معروف"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """تنسيق مدة الفيديو"""
        if not seconds:
            return "غير معروف"
        
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def get_language_name(lang_code: str) -> str:
        """الحصول على اسم اللغة"""
        languages = {
            'ar': 'العربية', 'en': 'الإنجليزية', 'fr': 'الفرنسية',
            'es': 'الإسبانية', 'de': 'الألمانية', 'it': 'الإيطالية',
            'ru': 'الروسية', 'ja': 'اليابانية', 'ko': 'الكورية',
            'zh': 'الصينية'
        }
        return languages.get(lang_code, lang_code.upper())
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """تنظيف اسم الملف من الأحرف غير المسموح بها"""
        cleaned = re.sub(r'[<>:"/\\|?*]', '', filename)
        if len(cleaned) > 100:
            cleaned = cleaned[:100]
        return cleaned
    
    @staticmethod
    def get_available_formats(formats: List[Dict]) -> List[Dict]:
        """استخراج وتنظيم الصيغ المتاحة"""
        video_formats = []
        
        for fmt in formats:
            if fmt.get('vcodec') != 'none':  # فقط الفيديو
                height = fmt.get('height', 0)
                filesize = fmt.get('filesize') or fmt.get('filesize_approx', 0)
                
                # تحديد تسمية الجودة
                if height >= 2160:
                    quality = "4K"
                elif height >= 1440:
                    quality = "2K"
                elif height >= 1080:
                    quality = "1080p"
                elif height >= 720:
                    quality = "720p"
                elif height >= 480:
                    quality = "480p"
                elif height >= 360:
                    quality = "360p"
                else:
                    quality = f"{height}p" if height else "غير محدد"
                
                video_formats.append({
                    'format_id': fmt['format_id'],
                    'quality': quality,
                    'ext': fmt.get('ext', 'mp4'),
                    'filesize': filesize,
                    'filesize_str': Downloader.format_filesize(filesize),
                    'height': height
                })
        
        # ترتيب حسب الجودة (من الأعلى إلى الأدنى)
        video_formats.sort(key=lambda x: x['height'], reverse=True)
        return video_formats[:10]  # أفضل 10 جودات
    
    async def get_video_info(self, url: str) -> Dict:
        """استخراج معلومات الفيديو"""
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                
                if 'entries' in info:  # قائمة تشغيل
                    return {
                        'title': info.get('title', 'قائمة تشغيل'),
                        'url': url,
                        'duration': 0,
                        'formats': [],
                        'subtitles': info.get('subtitles', {}),
                        'is_playlist': True,
                        'playlist_count': len(info['entries'])
                    }
                else:  # فيديو مفرد
                    return {
                        'title': info.get('title', 'بدون عنوان'),
                        'url': url,
                        'duration': info.get('duration', 0),
                        'formats': info.get('formats', []),
                        'subtitles': info.get('subtitles', {}),
                        'is_playlist': False
                    }
            except Exception as e:
                raise Exception(f"فشل في استخراج المعلومات: {str(e)}")
    
    async def download_video(self, url: str, format_id: str, chat_id: int, 
                           progress_callback: Callable, include_subs: bool = False) -> Optional[str]:
        """تنزيل الفيديو"""
        output_path = os.path.join(DOWNLOAD_DIR, f"{chat_id}_%(title)s.%(ext)s")
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'progress_hooks': [progress_callback],
        }
        
        if include_subs:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['ar', 'en']
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])
                
                # البحث عن الملف المُنزل
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.startswith(f"{chat_id}_"):
                        return os.path.join(DOWNLOAD_DIR, file)
                return None
                
        except Exception as e:
            raise Exception(f"فشل في التنزيل: {str(e)}")
    
    async def download_subtitles(self, url: str, lang: str, ext: str, chat_id: int) -> Optional[str]:
        """تنزيل ملف الترجمة"""
        output_path = os.path.join(DOWNLOAD_DIR, f"{chat_id}_subtitle.{ext}")
        
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang],
            'subtitlesformat': ext,
            'skip_download': True,
            'outtmpl': output_path.replace(f'.{ext}', '')
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])
                
                # البحث عن ملف الترجمة
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.startswith(f"{chat_id}_subtitle") and file.endswith(f".{lang}.{ext}"):
                        return os.path.join(DOWNLOAD_DIR, file)
                return None
                
        except Exception as e:
            raise Exception(f"فشل في تنزيل الترجمة: {str(e)}")
    
    async def download_playlist(self, url: str, chat_id: int, progress_callback: Callable) -> int:
        """تنزيل قائمة تشغيل كاملة"""
        output_path = os.path.join(DOWNLOAD_DIR, f"{chat_id}_%(playlist_index)s_%(title)s.%(ext)s")
        
        ydl_opts = {
            'outtmpl': output_path,
            'progress_hooks': [progress_callback],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])
                
                # حساب عدد الملفات المنزلة
                success_count = 0
                for file in os.listdir(DOWNLOAD_DIR):
                    if file.startswith(f"{chat_id}_"):
                        success_count += 1
                
                return success_count
                
        except Exception as e:
            raise Exception(f"فشل في تنزيل قائمة التشغيل: {str(e)}")
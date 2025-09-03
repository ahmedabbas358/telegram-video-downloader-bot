"""
محرك التنزيل الرئيسي
"""
import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
import yt_dlp
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import validators
import humanize
from config import config
from database import db, Download, PlaylistDownload
import logging

logger = logging.getLogger(__name__)

@dataclass
class VideoInfo:
    """معلومات الفيديو"""
    id: str
    title: str
    duration: int
    uploader: str
    upload_date: str
    view_count: int
    like_count: Optional[int]
    formats: List[Dict]
    subtitles: Dict[str, List]
    automatic_captions: Dict[str, List]
    thumbnail: str
    description: str
    url: str
    webpage_url: str

@dataclass
class PlaylistInfo:
    """معلومات قائمة التشغيل"""
    id: str
    title: str
    uploader: str
    entries: List[Dict]
    webpage_url: str

@dataclass
class DownloadProgress:
    """معلومات تقدم التنزيل"""
    downloaded_bytes: int
    total_bytes: int
    speed: float
    eta: int
    percent: float
    filename: str

class YouTubeDownloader:
    """فئة تنزيل الفيديوهات من YouTube"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_DOWNLOADS)
        self.active_downloads: Dict[int, bool] = {}
        
    def _get_ytdl_opts(self, custom_opts: Dict = None) -> Dict:
        """الحصول على خيارات YT-DLP"""
        opts = config.YTDL_OPTS.copy()
        if custom_opts:
            opts.update(custom_opts)
        return opts
    
    async def extract_video_info(self, url: str) -> Optional[VideoInfo]:
        """استخراج معلومات الفيديو"""
        try:
            loop = asyncio.get_event_loop()
            
            opts = self._get_ytdl_opts({
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            })
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(
                    self.executor,
                    lambda: ydl.extract_info(url, download=False)
                )
            
            if not info:
                return None
            
            return VideoInfo(
                id=info.get('id', ''),
                title=info.get('title', 'Unknown'),
                duration=info.get('duration', 0),
                uploader=info.get('uploader', 'Unknown'),
                upload_date=info.get('upload_date', ''),
                view_count=info.get('view_count', 0),
                like_count=info.get('like_count'),
                formats=info.get('formats', []),
                subtitles=info.get('subtitles', {}),
                automatic_captions=info.get('automatic_captions', {}),
                thumbnail=info.get('thumbnail', ''),
                description=info.get('description', ''),
                url=url,
                webpage_url=info.get('webpage_url', url)
            )
            
        except Exception as e:
            logger.error(f"Failed to extract video info: {e}")
            return None
    
    async def extract_playlist_info(self, url: str) -> Optional[PlaylistInfo]:
        """استخراج معلومات قائمة التشغيل"""
        try:
            loop = asyncio.get_event_loop()
            
            opts = self._get_ytdl_opts({
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True
            })
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(
                    self.executor,
                    lambda: ydl.extract_info(url, download=False)
                )
            
            if not info or info.get('_type') != 'playlist':
                return None
            
            return PlaylistInfo(
                id=info.get('id', ''),
                title=info.get('title', 'Unknown Playlist'),
                uploader=info.get('uploader', 'Unknown'),
                entries=info.get('entries', []),
                webpage_url=info.get('webpage_url', url)
            )
            
        except Exception as e:
            logger.error(f"Failed to extract playlist info: {e}")
            return None
    
    def _format_size(self, size_bytes: int) -> str:
        """تنسيق حجم الملف"""
        if size_bytes == 0:
            return "0B"
        return humanize.naturalsize(size_bytes, binary=True)
    
    def _format_duration(self, seconds: int) -> str:
        """تنسيق المدة الزمنية"""
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
    
    def get_available_qualities(self, video_info: VideoInfo) -> List[Dict]:
        """الحصول على الجودات المتاحة"""
        qualities = []
        seen_heights = set()
        
        for fmt in video_info.formats:
            height = fmt.get('height')
            if height and height not in seen_heights:
                quality = f"{height}p"
                if quality in config.AVAILABLE_QUALITIES:
                    qualities.append({
                        'quality': quality,
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext', 'mp4'),
                        'filesize': fmt.get('filesize', 0),
                        'fps': fmt.get('fps'),
                        'vcodec': fmt.get('vcodec'),
                        'acodec': fmt.get('acodec')
                    })
                    seen_heights.add(height)
        
        # ترتيب حسب الجودة
        quality_order = {q: i for i, q in enumerate(config.AVAILABLE_QUALITIES)}
        qualities.sort(key=lambda x: quality_order.get(x['quality'], 999))
        
        return qualities
    
    def get_available_subtitles(self, video_info: VideoInfo) -> Dict[str, List]:
        """الحصول على الترجمات المتاحة"""
        available_subs = {}
        
        # الترجمات الأصلية
        for lang, subs in video_info.subtitles.items():
            if lang in config.SUPPORTED_LANGUAGES:
                available_subs[lang] = {
                    'type': 'manual',
                    'language': config.SUPPORTED_LANGUAGES[lang],
                    'formats': [sub.get('ext', 'srt') for sub in subs]
                }
        
        # الترجمات التلقائية
        for lang, subs in video_info.automatic_captions.items():
            if lang in config.SUPPORTED_LANGUAGES and lang not in available_subs:
                available_subs[lang] = {
                    'type': 'auto',
                    'language': config.SUPPORTED_LANGUAGES[lang],
                    'formats': [sub.get('ext', 'srt') for sub in subs]
                }
        
        return available_subs
    
    async def download_video(
        self,
        url: str,
        quality: str,
        user_id: int,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> Optional[str]:
        """تنزيل الفيديو"""
        
        download_record = None
        try:
            # استخراج معلومات الفيديو
            video_info = await self.extract_video_info(url)
            if not video_info:
                raise Exception("Failed to extract video information")
            
            # إنشاء سجل التنزيل
            download_record = await db.create_download({
                'user_id': user_id,
                'url': url,
                'title': video_info.title,
                'video_id': video_info.id,
                'quality': quality,
                'duration': video_info.duration,
                'download_type': 'video',
                'metadata': {
                    'uploader': video_info.uploader,
                    'view_count': video_info.view_count,
                    'upload_date': video_info.upload_date
                }
            })
            
            # تحديث حالة التنزيل
            await db.update_download_status(download_record.id, 'downloading')
            
            # تحديد مجلد التنزيل
            user_dir = config.DOWNLOAD_PATH / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # إعداد خيارات التنزيل
            output_template = str(user_dir / f"{video_info.title}.%(ext)s")
            
            # تنظيف اسم الملف
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_info.title)
            output_template = str(user_dir / f"{safe_title}.%(ext)s")
            
            opts = self._get_ytdl_opts({
                'format': f'best[height<={quality[:-1]}]' if quality != 'best' else 'best',
                'outtmpl': output_template,
                'writesubtitles': False,
                'writeautomaticsub': False
            })
            
            # إضافة callback للتقدم
            if progress_callback:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        progress = DownloadProgress(
                            downloaded_bytes=d.get('downloaded_bytes', 0),
                            total_bytes=d.get('total_bytes', 0),
                            speed=d.get('speed', 0),
                            eta=d.get('eta', 0),
                            percent=d.get('_percent_str', '0%').replace('%', ''),
                            filename=d.get('filename', '')
                        )
                        asyncio.create_task(self._async_progress_callback(progress_callback, progress))
                
                opts['progress_hooks'] = [progress_hook]
            
            # تنزيل الفيديو
            loop = asyncio.get_event_loop()
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                await loop.run_in_executor(
                    self.executor,
                    lambda: ydl.download([url])
                )
            
            # البحث عن الملف المُنزل
            downloaded_files = list(user_dir.glob(f"{safe_title}.*"))
            if not downloaded_files:
                raise Exception("Downloaded file not found")
            
            file_path = downloaded_files[0]
            file_size = file_path.stat().st_size
            
            # التحقق من حجم الملف
            if file_size > config.MAX_FILE_SIZE * 1024 * 1024:
                file_path.unlink()  # حذف الملف
                raise Exception(f"File too large: {self._format_size(file_size)}")
            
            # تحديث سجل التنزيل
            await db.update_download_status(
                download_record.id,
                'completed',
                file_path=str(file_path),
                file_size=file_size
            )
            
            # تحديث إحصائيات المستخدم
            await db.increment_download_count(user_id, file_size)
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            if download_record:
                await db.update_download_status(
                    download_record.id,
                    'failed',
                    error_message=str(e)
                )
            return None
    
    async def download_subtitle(
        self,
        url: str,
        language: str,
        subtitle_format: str,
        user_id: int
    ) -> Optional[str]:
        """تنزيل الترجمة"""
        
        download_record = None
        try:
            # استخراج معلومات الفيديو
            video_info = await self.extract_video_info(url)
            if not video_info:
                raise Exception("Failed to extract video information")
            
            # إنشاء سجل التنزيل
            download_record = await db.create_download({
                'user_id': user_id,
                'url': url,
                'title': video_info.title,
                'video_id': video_info.id,
                'download_type': 'subtitle',
                'metadata': {
                    'language': language,
                    'format': subtitle_format,
                    'uploader': video_info.uploader
                }
            })
            
            await db.update_download_status(download_record.id, 'downloading')
            
            # تحديد مجلد التنزيل
            user_dir = config.DOWNLOAD_PATH / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # تنظيف اسم الملف
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_info.title)
            
            # إعداد خيارات التنزيل
            opts = self._get_ytdl_opts({
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': [language],
                'subtitlesformat': subtitle_format,
                'outtmpl': str(user_dir / f"{safe_title}.%(ext)s")
            })
            
            # تنزيل الترجمة
            loop = asyncio.get_event_loop()
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                await loop.run_in_executor(
                    self.executor,
                    lambda: ydl.download([url])
                )
            
            # البحث عن ملف الترجمة
            subtitle_files = list(user_dir.glob(f"{safe_title}.{language}.{subtitle_format}"))
            if not subtitle_files:
                # البحث عن ترجمة تلقائية
                auto_files = list(user_dir.glob(f"{safe_title}.{language}.*.{subtitle_format}"))
                if auto_files:
                    subtitle_files = auto_files
            
            if not subtitle_files:
                raise Exception("Subtitle file not found")
            
            file_path = subtitle_files[0]
            file_size = file_path.stat().st_size
            
            # تحديث سجل التنزيل
            await db.update_download_status(
                download_record.id,
                'completed',
                file_path=str(file_path),
                file_size=file_size
            )
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Subtitle download failed: {e}")
            if download_record:
                await db.update_download_status(
                    download_record.id,
                    'failed',
                    error_message=str(e)
                )
            return None
    
    async def download_playlist(
        self,
        url: str,
        quality: str,
        user_id: int,
        max_videos: Optional[int] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """تنزيل قائمة التشغيل"""
        
        playlist_record = None
        try:
            # استخراج معلومات قائمة التشغيل
            playlist_info = await self.extract_playlist_info(url)
            if not playlist_info:
                raise Exception("Failed to extract playlist information")
            
            total_videos = len(playlist_info.entries)
            if max_videos:
                total_videos = min(total_videos, max_videos)
            
            # التحقق من الحد الأقصى
            if total_videos > config.MAX_PLAYLIST_SIZE:
                raise Exception(f"Playlist too large: {total_videos} videos (max: {config.MAX_PLAYLIST_SIZE})")
            
            # إنشاء سجل قائمة التشغيل
            playlist_record = await db.create_playlist_download({
                'user_id': user_id,
                'playlist_url': url,
                'playlist_title': playlist_info.title,
                'playlist_id': playlist_info.id,
                'total_videos': total_videos,
                'quality': quality
            })
            
            # تحديد مجلد التنزيل
            user_dir = config.DOWNLOAD_PATH / str(user_id) / f"playlist_{playlist_info.id}"
            user_dir.mkdir(parents=True, exist_ok=True)
            
            downloaded_files = []
            completed = 0
            failed = 0
            
            # تنزيل الفيديوهات
            for i, entry in enumerate(playlist_info.entries[:total_videos]):
                try:
                    if progress_callback:
                        await progress_callback(f"تنزيل فيديو {i+1}/{total_videos}: {entry.get('title', 'Unknown')}")
                    
                    video_url = entry.get('webpage_url') or f"https://youtube.com/watch?v={entry.get('id')}"
                    file_path = await self.download_video(video_url, quality, user_id)
                    
                    if file_path:
                        downloaded_files.append(file_path)
                        completed += 1
                    else:
                        failed += 1
                    
                    # تحديث التقدم
                    await db.update_playlist_progress(playlist_record.id, 1 if file_path else 0, 1 if not file_path else 0)
                    
                except Exception as e:
                    logger.error(f"Failed to download video {i+1}: {e}")
                    failed += 1
                    await db.update_playlist_progress(playlist_record.id, 0, 1)
            
            # تحديث حالة قائمة التشغيل
            status = 'completed' if failed == 0 else 'partial' if completed > 0 else 'failed'
            await db.update_download_status(playlist_record.id, status)
            
            return {
                'playlist_id': playlist_record.id,
                'total_videos': total_videos,
                'completed': completed,
                'failed': failed,
                'downloaded_files': downloaded_files,
                'status': status
            }
            
        except Exception as e:
            logger.error(f"Playlist download failed: {e}")
            if playlist_record:
                await db.update_download_status(playlist_record.id, 'failed', error_message=str(e))
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    async def _async_progress_callback(self, callback: Callable, progress: DownloadProgress):
        """معالج غير متزامن للتقدم"""
        try:
            await callback(progress)
        except Exception as e:
            logger.error(f"Progress callback error: {e}")
    
    def is_valid_url(self, url: str) -> bool:
        """التحقق من صحة الرابط"""
        if not validators.url(url):
            return False
        
        # التحقق من أن الرابط من YouTube
        youtube_patterns = [
            r'youtube\.com/watch\?v=',
            r'youtu\.be/',
            r'youtube\.com/playlist\?list=',
            r'm\.youtube\.com',
            r'music\.youtube\.com'
        ]
        
        return any(re.search(pattern, url) for pattern in youtube_patterns)
    
    def is_playlist_url(self, url: str) -> bool:
        """التحقق من أن الرابط لقائمة تشغيل"""
        return 'playlist' in url or 'list=' in url
    
    async def cleanup_old_files(self, days: int = 7):
        """تنظيف الملفات القديمة"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 3600)
            
            for user_dir in config.DOWNLOAD_PATH.iterdir():
                if user_dir.is_dir():
                    for file_path in user_dir.rglob('*'):
                        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                            file_path.unlink()
                            logger.info(f"Deleted old file: {file_path}")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

# مثيل عام من المنزل
downloader = YouTubeDownloader()
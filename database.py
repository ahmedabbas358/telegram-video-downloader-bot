"""
إدارة قاعدة البيانات والمستخدمين
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, BigInteger, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func, update, delete
from config import config
import logging

logger = logging.getLogger(__name__)

# قاعدة البيانات
Base = declarative_base()

class User(Base):
    """جدول المستخدمين"""
    __tablename__ = 'users'
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), default='ar')
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    last_activity = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    # إعدادات المستخدم
    preferred_quality = Column(String(10), default='720p')
    preferred_subtitle_lang = Column(String(10), default='ar')
    preferred_subtitle_format = Column(String(10), default='srt')
    download_count = Column(Integer, default=0)
    total_size_downloaded = Column(BigInteger, default=0)  # بالبايت

class Download(Base):
    """جدول التنزيلات"""
    __tablename__ = 'downloads'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    video_id = Column(String(20), nullable=True)
    quality = Column(String(10), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    duration = Column(Integer, nullable=True)  # بالثواني
    download_type = Column(String(20), default='video')  # video, subtitle, playlist
    status = Column(String(20), default='pending')  # pending, downloading, completed, failed
    file_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    file_metadata = Column(JSON, nullable=True)  # ✅ تم تغيير الاسم من metadata
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

class PlaylistDownload(Base):
    """جدول تنزيلات قوائم التشغيل"""
    __tablename__ = 'playlist_downloads'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    playlist_url = Column(Text, nullable=False)
    playlist_title = Column(Text, nullable=True)
    playlist_id = Column(String(50), nullable=True)
    total_videos = Column(Integer, default=0)
    completed_videos = Column(Integer, default=0)
    failed_videos = Column(Integer, default=0)
    quality = Column(String(10), nullable=True)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

class DatabaseManager:
    """مدير قاعدة البيانات"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
    
    async def init_db(self):
        """تهيئة قاعدة البيانات"""
        try:
            # إنشاء محرك قاعدة البيانات
            if config.DATABASE_URL.startswith('sqlite'):
                db_url = config.DATABASE_URL.replace('sqlite://', 'sqlite+aiosqlite://')
            else:
                db_url = config.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
            
            self.engine = create_async_engine(
                db_url,
                echo=False,
                pool_pre_ping=True
            )
            
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        if self.engine:
            await self.engine.dispose()
    
    async def get_session(self) -> AsyncSession:
        return self.async_session()
    
    # إدارة المستخدمين
    async def get_user(self, user_id: int) -> Optional[User]:
        async with self.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
    
    async def create_or_update_user(self, user_data: Dict[str, Any]) -> User:
        async with self.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_data['id']))
            user = result.scalar_one_or_none()
            
            if user:
                user.username = user_data.get('username', user.username)
                user.first_name = user_data.get('first_name', user.first_name)
                user.last_name = user_data.get('last_name', user.last_name)
                user.language_code = user_data.get('language_code', user.language_code)
                user.last_activity = datetime.now(timezone.utc)
            else:
                user = User(
                    id=user_data['id'],
                    username=user_data.get('username'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    language_code=user_data.get('language_code', 'ar')
                )
                session.add(user)
            
            await session.commit()
            await session.refresh(user)
            return user
    
    async def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        async with self.get_session() as session:
            await session.execute(update(User).where(User.id == user_id).values(**settings))
            await session.commit()
            return True
    
    async def increment_download_count(self, user_id: int, file_size: int = 0):
        async with self.get_session() as session:
            await session.execute(
                update(User).where(User.id == user_id).values(
                    download_count=User.download_count + 1,
                    total_size_downloaded=User.total_size_downloaded + file_size
                )
            )
            await session.commit()
    
    # إدارة التنزيلات
    async def create_download(self, download_data: Dict[str, Any]) -> Download:
        async with self.get_session() as session:
            download = Download(**download_data)
            session.add(download)
            await session.commit()
            await session.refresh(download)
            return download
    
    async def update_download_status(self, download_id: int, status: str, **kwargs):
        async with self.get_session() as session:
            update_data = {'status': status}
            if status == 'completed':
                update_data['completed_at'] = datetime.now(timezone.utc)
            update_data.update(kwargs)
            await session.execute(update(Download).where(Download.id == download_id).values(**update_data))
            await session.commit()
    
    async def get_user_downloads(self, user_id: int, limit: int = 20) -> List[Download]:
        async with self.get_session() as session:
            result = await session.execute(
                select(Download)
                .where(Download.user_id == user_id)
                .order_by(Download.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
    
    # إدارة قوائم التشغيل
    async def create_playlist_download(self, playlist_data: Dict[str, Any]) -> PlaylistDownload:
        async with self.get_session() as session:
            playlist = PlaylistDownload(**playlist_data)
            session.add(playlist)
            await session.commit()
            await session.refresh(playlist)
            return playlist
    
    async def update_playlist_progress(self, playlist_id: int, completed: int = 0, failed: int = 0):
        async with self.get_session() as session:
            await session.execute(
                update(PlaylistDownload).where(PlaylistDownload.id == playlist_id).values(
                    completed_videos=PlaylistDownload.completed_videos + completed,
                    failed_videos=PlaylistDownload.failed_videos + failed
                )
            )
            await session.commit()
    
    # إحصائيات
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        async with self.get_session() as session:
            user = await self.get_user(user_id)
            if not user:
                return {}
            
            result = await session.execute(
                select(func.count(Download.id))
                .where(Download.user_id == user_id)
                .where(Download.status == 'completed')
            )
            recent_downloads = result.scalar() or 0
            
            size_mb = user.total_size_downloaded / (1024 * 1024)
            size_str = f"{size_mb:.1f} ميجابايت" if size_mb < 1024 else f"{size_mb / 1024:.1f} جيجابايت"
            
            return {
                'total_downloads': user.download_count,
                'recent_downloads': recent_downloads,
                'total_size': size_str,
                'member_since': user.created_at.strftime('%Y-%m-%d'),
                'last_activity': user.last_activity.strftime('%Y-%m-%d %H:%M')
            }
    
    async def get_global_stats(self) -> Dict[str, Any]:
        async with self.get_session() as session:
            users_result = await session.execute(select(func.count(User.id)).where(User.is_active == True))
            total_users = users_result.scalar() or 0
            
            downloads_result = await session.execute(select(func.count(Download.id)).where(Download.status == 'completed'))
            total_downloads = downloads_result.scalar() or 0
            
            return {
                'total_users': total_users,
                'total_downloads': total_downloads
            }

# مثيل عام من مدير قاعدة البيانات
db = DatabaseManager()
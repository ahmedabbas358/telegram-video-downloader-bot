import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name="bot_database.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()
    
    def create_tables(self):
        """إنشاء الجداول إذا لم تكن موجودة"""
        cursor = self.conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                downloads_count INTEGER DEFAULT 0,
                last_download TIMESTAMP
            )
        ''')
        
        # جدول سجل التنزيلات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                quality TEXT,
                file_size TEXT,
                download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed'
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_data):
        """إضافة مستخدم جديد"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_data['user_id'], user_data.get('username'), 
              user_data.get('first_name'), user_data.get('last_name')))
        self.conn.commit()
    
    def get_user_stats(self, user_id):
        """الحصول على إحصائيات المستخدم"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT user_id, username, first_name, downloads_count, join_date, last_download
            FROM users WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'username': row[1],
                'first_name': row[2],
                'downloads_count': row[3],
                'join_date': row[4],
                'last_download': row[5]
            }
        return None
    
    def increment_download_count(self, user_id):
        """زيادة عداد تنزيلات المستخدم"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET downloads_count = downloads_count + 1, last_download = ?
            WHERE user_id = ?
        ''', (datetime.now(), user_id))
        self.conn.commit()
    
    def add_download_history(self, download_data):
        """إضافة سجل تنزيل"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO download_history (user_id, url, title, quality, file_size, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            download_data['user_id'],
            download_data['url'],
            download_data.get('title'),
            download_data.get('quality'),
            download_data.get('file_size'),
            download_data.get('status', 'completed')
        ))
        self.conn.commit()
    
    def close(self):
        """إغلاق الاتصال بقاعدة البيانات"""
        self.conn.close()
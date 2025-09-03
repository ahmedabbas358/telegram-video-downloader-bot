# telegram-video-downloader-bot


# 🎬 بوت تليجرام لتنزيل الفيديوهات والترجمات

بوت تليجرام احترافي ومتطور لتنزيل الفيديوهات وقوائم التشغيل والترجمات من أكثر من 1000 موقع مختلف.

## ✨ المميزات الرئيسية

### 🎥 تنزيل الفيديوهات
- دعم أكثر من 1000 موقع (YouTube, Facebook, Instagram, TikTok, Twitter, Vimeo وغيرها)
- جودات متعددة من 144p حتى 4K/8K
- تنزيل سريع ومتوازي
- استئناف التحميل المنقطع
- ضغط تلقائي للملفات الكبيرة

### 📝 تنزيل الترجمات
- ترجمات أصلية وتلقائية
- دعم 15+ لغة مختلفة
- صيغ متعددة: SRT, VTT, ASS
- تنزيل مستقل أو مع الفيديو

### 📂 قوائم التشغيل
- تنزيل قوائم تشغيل كاملة
- الحفاظ على أسماء الملفات والترتيب
- تنزيل جماعي للترجمات
- معلومات تفصيلية قبل التنزيل

### 🚀 مميزات متقدمة
- واجهة سهلة بأزرار تفاعلية
- عرض تقدم التحميل المباشر
- حماية من تجاوز الحدود
- تنظيف تلقائي للملفات القديمة
- سجلات مفصلة للأخطاء

## 📋 المتطلبات

- Python 3.8 أو أحدث
- توكن بوت تليجرام
- مساحة تخزين كافية
- اتصال إنترنت مستقر

## 🔧 التثبيت

### 1. تحميل المشروع
```bash
git clone https://github.com/yourusername/telegram-video-downloader-bot.git
cd telegram-video-downloader-bot
```

### 2. إنشاء البيئة الافتراضية
```bash
python -m venv venv

# على Windows:
venv\\Scripts\\activate

# على Linux/Mac:
source venv/bin/activate
```

### 3. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 4. إعداد المتغيرات البيئية
```bash
# انسخ ملف الإعدادات
cp .env.example .env

# عدّل الملف وأضف توكن البوت
nano .env
```

### 5. تشغيل البوت
```bash
python main.py
```

## ⚙️ الإعداد والتخصيص

### إعداد التوكن

1. تحدث مع [@BotFather](https://t.me/botfather) على تليجرام
2. أنشئ بوت جديد باستخدام `/newbot`
3. احفظ التوكن في ملف `.env`:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

### إعدادات متقدمة

```env
# حد أقصى لحجم الملف (بايت)
MAX_FILE_SIZE=52428800

# عدد التحميلات المتزامنة
MAX_CONCURRENT_DOWNLOADS=3

# تفعيل الترجمة التلقائية
AUTO_SUBTITLE_ENABLED=true

# حد الطلبات في الدقيقة
MAX_REQUESTS_PER_MINUTE=10
```

## 🚀 النشر على السيرفر

### نشر على VPS

1. **تحديث النظام:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

2. **تحميل المشروع:**
```bash
git clone https://github.com/yourusername/telegram-video-downloader-bot.git
cd telegram-video-downloader-bot
```

3. **إعداد البيئة:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **إنشاء خدمة systemd:**
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

```ini
[Unit]
Description=Telegram Video Downloader Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/telegram-video-downloader-bot
Environment=PATH=/path/to/telegram-video-downloader-bot/venv/bin
ExecStart=/path/to/telegram-video-downloader-bot/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

5. **تشغيل الخدمة:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### نشر على Heroku

1. **إنشاء Procfile:**
```
worker: python main.py
```

2. **إعداد متغيرات البيئة في Heroku:**
```bash
heroku config:set BOT_TOKEN=your_bot_token_here
heroku config:set MAX_FILE_SIZE=52428800
```

3. **النشر:**
```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### نشر باستخدام Docker

1. **إنشاء Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

2. **بناء وتشغيل Container:**
```bash
docker build -t telegram-video-bot .
docker run -d --env-file .env telegram-video-bot
```

## 📱 كيفية الاستخدام

### للمستخدمين

1. **ابدأ محادثة مع البوت:**
   - أرسل `/start` لعرض الترحيب
   - أرسل `/help` للمساعدة

2. **تنزيل فيديو مفرد:**
   - أرسل رابط الفيديو
   - اختر الجودة المطلوبة
   - اختر الترجمة (اختياري)
   - انتظر التحميل والإرسال

3. **تنزيل قائمة تشغيل:**
   - أرسل رابط قائمة التشغيل
   - اختر نوع التحميل (فيديوهات/ترجمات/الكل)
   - اختر الجودة
   - انتظر التحميل

### للمطورين

#### إضافة موقع جديد
```python
# في ملف extractors.py
class CustomExtractor:
    def extract_info(self, url):
        # منطق استخراج المعلومات
        pass
```

#### تخصيص الرسائل
```python
# في config.py
MESSAGES = {
    'welcome': 'رسالة ترحيب مخصصة',
    'help': 'رسالة مساعدة مخصصة'
}
```

## 🛠️ حل المشاكل الشائعة

### مشكلة: "البوت لا يستجيب"
**الحل:**
```bash
# تحقق من حالة البوت
systemctl status telegram-bot

# اعرض السجلات
journalctl -u telegram-bot -f
```

### مشكلة: "خطأ في تنزيل الفيديو"
**الحل:**
```bash
# تحديث yt-dlp
pip install --upgrade yt-dlp

# تحقق من الشبكة
curl -I https://youtube.com
```

### مشكلة: "الملف كبير جداً"
**الحل:**
```env
# زيادة حد حجم الملف
MAX_FILE_SIZE=104857600  # 100MB
```

### مشكلة: "نفاد مساحة التخزين"
**الحل:**
```bash
# تنظيف الملفات القديمة
find downloads/ -type f -mtime +1 -delete

# تفعيل التنظيف التلقائي
echo "0 2 * * * find /path/to/downloads -type f -mtime +1 -delete" | crontab -
```

## 📊 المراقبة والصيانة

### عرض الإحصائيات
```bash
# عرض استخدام المساحة
du -sh downloads/

# عرض استخدام الذاكرة
ps aux | grep python

# عرض السجلات
tail -f logs/bot.log
```

### النسخ الاحتياطي
```bash
# نسخ احتياطية للإعدادات
tar -czf backup-$(date +%Y%m%d).tar.gz .env config.py

# نسخ احتياطية للسجلات
cp logs/bot.log logs/bot-$(date +%Y%m%d).log
```

## 🔒 الأمان

### حماية التوكن
- لا تشارك توكن البوت مع أحد
- استخدم متغيرات البيئة فقط
- غيّر التوكن إذا تسرب

### حماية السيرفر
```bash
# تحديث النظام
sudo apt update && sudo apt upgrade

# إعداد جدار حماية
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

### مراقبة الاستخدام
```bash
# مراقبة العمليات
htop

# مراقبة الشبكة
iftop

# مراقبة القرص
iostat
```

## 🤝 المساهمة

نرحب بمساهماتكم! يرجى:

1. Fork المشروع
2. إنشاء فرع جديد (`git checkout -b feature/amazing-feature`)
3. Commit التغييرات (`git commit -m 'Add amazing feature'`)
4. Push للفرع (`git push origin feature/amazing-feature`)
5. فتح Pull Request

## 📝 الترخيص

هذا المشروع مرخص تحت [MIT License](LICENSE).



## 📈 خارطة الطريق

### الإصدار القادم (v2.0)
- [ ] دعم البث المباشر
- [ ] ضغط الفيديوهات
- [ ] قاعدة بيانات للإحصائيات
- [ ] واجهة ويب للإدارة
- [ ] دعم التحميل السحابي
- [ ] تنزيل متعدد الأجزاء

### المميزات المطلوبة
- [ ] دعم المزيد من المواقع
- [ ] ترجمة واجهة البوت
- [ ] تحسينات الأداء
- [ ] وضع المطور المتقدم

## 🙏 شكر خاص

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - مكتبة تنزيل الفيديوهات
- [aiogram](https://github.com/aiogram/aiogram) - مكتبة Telegram Bot API
- جميع المساهمين والمطورين

---

**ملاحظة:** يرجى استخدام البوت بمسؤولية واحترام حقوق الطبع والنشر. المطورون غير مسؤولون عن سوء الاستخدام. 
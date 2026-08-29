# Atomic Donate

درگاه دونیت شخصی با زرین‌پال + آلارم OBS. نسخه تک‌نفره از چیزی شبیه ریمیت: صفحه حمایت، گیف دونیت، لیست حامیان و نوار هدف.

## اجرا روی ویندوز

1. مرچنت زرین‌پال را در `.env` بگذار.
2. در پوشه پروژه:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py bootstrap
python manage.py runserver
```

- درگاه: http://127.0.0.1:8000/
- پنل: http://127.0.0.1:8000/panel/  (کاربر `admin` و رمزی که در `.env` نوشتی)
- آلارم و صدا: http://127.0.0.1:8000/panel/alert/
- ابزارهای OBS: http://127.0.0.1:8000/panel/tools/
- آلارم تست را از پنل بزن تا بدون پرداخت، گیف و صدا روی OBS پخش شود.

اگر `venv` نبود:

```powershell
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

## OBS

در پنل، صفحه «ابزارهای OBS» چهار لینک Browser Source و یک لینک Dock دارد:

- آلارم گیف و صدا: Width 800 / Height 450 — Control audio via OBS روشن
- لیست حامیان: ۳۸۰×۵۲۰
- نوار هدف: ۵۲۰×۱۶۰
- بزرگ‌ترین حامی: ۳۸۰×۲۲۰
- کنترل استریم: View → Docks → Custom Browser Dock

تیک Shutdown source when not visible را بردار. گیف و فایل صدا را از «آلارم و صدا» آپلود کن؛ حجم را همان‌جا کم و زیاد کن.

## VPS

روی سرور لینوکس:

```bash
sudo mkdir -p /opt/atomic-donate
# فایل‌ها را کپی کن، بعد:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # دامنه، مرچنت، رمز ادمین
python manage.py migrate
python manage.py bootstrap
python manage.py collectstatic --noinput
```

سپس `deploy/nginx.conf` و `deploy/atomic-donate.service` را با دامنه و مسیر خودت تنظیم کن:

```bash
sudo cp deploy/atomic-donate.service /etc/systemd/system/
sudo systemctl enable --now atomic-donate
sudo certbot --nginx -d donate.example.com
```

`PUBLIC_BASE_URL` باید همان آدرس HTTPS عمومی باشد، وگرنه زرین‌پال بعد از پرداخت برنمی‌گردد.

## نکته مبلغ

زرین‌پال مبلغ را به **ریال** می‌گیرد. این پروژه تومان می‌گیرد و ×۱۰ می‌کند. حداقل را در پنل عوض کن.

پلن اول فقط برای خودت است: درگاه، آلارم، لیست، هدف، تست، TTS. چیزهایی مثل صرافی، ساب توییچ یا هاب تعمداً نیستند.

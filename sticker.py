"""
ارسال تصویر روزانه به کانال — دو بار در روز:
 - ۱۰ صبح: لوگو + تاریخ شمسی
 - ۱۰ شب:  لوگو + جمله شب‌بخیر
"""

import os
import io
import requests
import jdatetime
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta

TEHRAN_TZ    = timezone(timedelta(hours=3, minutes=30))
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")
LOGO_PATH    = os.path.join(os.path.dirname(__file__), "logo.png")
FONT_BOLD    = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
FONT_REG     = "/usr/share/fonts/truetype/freefont/FreeSans.ttf"

JALALI_MONTHS   = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                    "مهر","آبان","آذر","دی","بهمن","اسفند"]
JALALI_WEEKDAYS = ["شنبه","یک‌شنبه","دوشنبه","سه‌شنبه","چهارشنبه","پنج‌شنبه","جمعه"]
PERSIAN         = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("❌ BOT_TOKEN و CHANNEL_ID باید تنظیم شوند.")

def jalali_today() -> str:
    now     = datetime.now(TEHRAN_TZ)
    j       = jdatetime.datetime.fromgregorian(datetime=now)
    d       = str(j.day).translate(PERSIAN)
    y       = str(j.year).translate(PERSIAN)
    weekday = JALALI_WEEKDAYS[j.weekday()]
    month   = JALALI_MONTHS[j.month - 1]
    return f"{weekday} {d} {month} {y}"

def current_slot() -> str:
    """morning (10 AM) یا evening (10 PM) بر اساس ساعت تهران."""
    hour = datetime.now(TEHRAN_TZ).hour
    return "evening" if hour >= 18 else "morning"

def draw_centered(draw, text: str, y: int, font, color):
    W = draw.im.size[0]
    bbox = draw.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, y), text, font=font, fill=color)

def create_image(slot: str) -> bytes:
    img = Image.open(LOGO_PATH).convert("RGBA")
    img = img.resize((800, 800), Image.LANCZOS)
    W, H = img.size

    # نوار نیمه‌شفاف پایین تصویر
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    band    = ImageDraw.Draw(overlay)
    band.rectangle([0, H - 220, W, H], fill=(0, 0, 0, 170))
    img  = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    font_big = ImageFont.truetype(FONT_BOLD, 54)
    font_med = ImageFont.truetype(FONT_REG,  38)

    if slot == "morning":
        main_text  = jalali_today()
        main_color = (255, 215, 50)       # طلایی
    else:
        main_text  = "با آرزوی شبی آرام"
        main_color = (160, 200, 255)      # آبی ملایم

    draw_centered(draw, main_text,    H - 195, font_big, main_color)
    draw_centered(draw, "@coredollar", H - 110, font_med, (210, 210, 210))

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=92)
    buf.seek(0)
    return buf.read()

def send_photo(data: bytes):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    r   = requests.post(url, files={"photo": ("sticker.jpg", data, "image/jpeg")},
                        data={"chat_id": CHANNEL_ID}, timeout=30)
    if r.status_code != 200:
        print(f"❌ تلگرام خطا : {r.text}")
    r.raise_for_status()
    print("✅ تصویر ارسال شد.")

def main():
    slot = current_slot()
    print(f"نوع : {slot}")
    data = create_image(slot)
    send_photo(data)

if __name__ == "__main__":
    main()

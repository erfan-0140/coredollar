"""
بات tgju - سه پست جداگانه (کریپتو + فلزات + ارز)
"""

import os
import re
import time
import requests
import jdatetime
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

PROFILE_BASE = "https://www.tgju.org/profile/"
TEHRAN_TZ = ZoneInfo("Asia/Tehran")

CHANNEL_ID = '@coredollar'
CHANNEL_LINK = '@coredollar'
BOT_TOKEN = '8915418054:AAH_U0jBWvdk7Qp79qULnS_PMPEoeSGr1qU'   # ← توکنت

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

RATE_PATTERN = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

def now_jalali_date() -> str:
    now_gregorian = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=now_gregorian)
    day = str(j.day).translate(PERSIAN_DIGITS)
    year = str(j.year).translate(PERSIAN_DIGITS)
    month_name = JALALI_MONTHS[j.month - 1]
    return f"{day} {month_name} {year}"

def fetch_price(row_id: str) -> str | None:
    try:
        resp = requests.get(f"{PROFILE_BASE}{row_id}", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = RATE_PATTERN.search(text)
        return match.group(1) if match else None
    except:
        return None

def send_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

# ====================== پست ۱: کریپتو ======================
def post_crypto():
    coins = ["تتر","بیتکوین","اتریوم","کاردانو","شیبا","گرام","بایننس","استلار","ریپل","دوج","ترون","سولانا","اتریوم کلاسیک","چین لینک","لایت کوین","آوالانچ","زدکش","مونرو","پای"]
    emojis = ["🔴","🟡","🟢","⚪️"]
    
    msg = "<b>کریپتو کارنسی</b>\n\n"
    msg += f"🕒 {now_jalali_date()}\n\n"
    
    columns = [[], [], [], []]
    for i, name in enumerate(coins):
        price = "N/A"
        row_id = f"crypto-{name.lower().replace(' ', '-')}"
        p = fetch_price(row_id)
        if p:
            price = f"{int(float(p.replace(',',''))/10):,}"
        columns[i%4].append(f"{emojis[i%4]} <b>{name}</b>: <b>{price}</b>")
    
    for row in zip(*columns):
        msg += "   ".join(row) + "\n"
    
    msg += f"\n<b>———————————————</b>\n🔗 {CHANNEL_LINK}"
    send_message(msg)

# ====================== پست ۲: فلزات ======================
def post_gold():
    gold_ids = {
        "ons": "انس طلا",
        "mesghal": "مثقال طلا",
        "geram18": "طلای ۱۸ عیار",
        "geram24": "طلای ۲۴ عیار",
        "silver_999": "گرم نقره ۹۹۹",
        "sekee": "سکه امامی",
        "sekeb": "سکه بهار آزادی",
        "nim": "نیم سکه",
        "rob": "ربع سکه",
        "gerami": "سکه گرمی"
    }
    
    msg = "<b>فلزات گرانبها</b>\n\n"
    msg += f"🕒 {now_jalali_date()}\n\n"
    
    # طلاها
    for rid, name in [("ons","انس طلا"), ("mesghal","مثقال طلا"), ("geram18","طلای ۱۸ عیار"), ("geram24","طلای ۲۴ عیار")]:
        p = fetch_price(rid) or "به‌روزرسانی"
        msg += f"💛 <b>{name}</b>: <b>{p}</b>\n"
    
    # نقره
    silver = fetch_price("silver_999") or "به‌روزرسانی"
    msg += f"🤍 <b>گرم نقره ۹۹۹</b>: <b>{silver}</b>\n\n"
    
    # سکه‌ها
    msg += "<b>🟠 سکه‌ها:</b>\n"
    for rid, name in [("sekee","سکه امامی"), ("sekeb","سکه بهار آزادی"), ("nim","نیم سکه"), ("rob","ربع سکه"), ("gerami","سکه گرمی")]:
        p = fetch_price(rid) or "به‌روزرسانی"
        msg += f"🟠 <b>{name}</b>: <b>{p}</b>\n"
    
    # حباب‌ها
    msg += "\n<b>🫧 حباب‌ها:</b>\n"
    for name in ["حباب سکه امامی", "حباب سکه بهار آزادی", "حباب نیم سکه", "حباب ربع سکه", "حباب سکه گرمی"]:
        msg += f"🫧 <b>{name}</b>: <b>به‌روزرسانی</b>\n"
    
    msg += f"\n<b>———————————————</b>\n🔗 {CHANNEL_LINK}"
    send_message(msg)

# ====================== پست ۳: ارز ======================
def post_currency():
    msg = "<b>ارزهای آزاد</b>\n\n"
    msg += f"🕒 {now_jalali_date()}\n\n"
    
    currencies = [
        ("price_dollar_rl", "🇺🇸 دلار آمریکا"),
        ("price_eur", "🇪🇺 یورو"),
        ("price_gbp", "🇬🇧 پوند انگلیس"),
        ("price_aed", "🇦🇪 درهم امارات"),
        ("price_try", "🇹🇷 لیر ترکیه"),
        ("price_cny", "🇨🇳 یوان چین"),
        ("price_cad", "🇨🇦 دلار کانادا"),
        ("price_aud", "🇦🇺 دلار استرالیا"),
        ("price_iqd", "🇮🇶 دینار عراق"),
        # بقیه را هم می‌توانی اضافه کنی
    ]
    
    for rid, name in currencies:
        p = fetch_price(rid) or "به‌روزرسانی"
        if p != "به‌روزرسانی":
            p = f"{int(float(p.replace(',',''))/10):,}"
        msg += f"{name.split()[0]} <b>{name}</b>: <b>{p}</b>\n"
    
    msg += f"\n<b>———————————————</b>\n🔗 {CHANNEL_LINK}"
    send_message(msg)

# ====================== اجرا ======================
def main():
    print("🤖 بات tgju شروع به کار کرد...")
    while True:
        print(f"🔄 چرخه جدید - {datetime.now()}")
        
        post_crypto()
        time.sleep(3)
        post_gold()
        time.sleep(3)
        post_currency()
        
        print("✅ سه پست ارسال شد")
        time.sleep(1800)  # ۳۰ دقیقه

if __name__ == "__main__":
    main()

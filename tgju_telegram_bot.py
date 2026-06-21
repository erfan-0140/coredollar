"""
بات قیمت ارز و طلا - گرفتن قیمت از tgju.org و ارسال به کانال تلگرام
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

# ارزها
CURRENCY_ITEMS = [
    ("price_dollar_rl", "دلار آمریکا"),
    ("price_eur", "یورو"),
    ("price_gbp", "پوند انگلیس"),
    ("price_aed", "درهم امارات"),
    ("price_try", "لیر ترکیه"),
]

# طلا و سکه
GOLD_ITEMS = [
    ("geram18", "طلای ۱۸ عیار (هر گرم)"),
    ("mesghal", "مثقال طلا"),
    ("rob", "ربع سکه"),
    ("nim", "نیم سکه"),
    ("sekee", "سکه تمام (امامی)"),
    ("ons", "انس جهانی طلا"),
]

ALL_ITEMS = CURRENCY_ITEMS + GOLD_ITEMS

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

RATE_PATTERN = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")

SEPARATOR = "-" * 56

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def now_jalali_str() -> str:
    """تاریخ و ساعت فعلی به وقت تهران، به شمسی و با اعداد فارسی."""
    now_gregorian = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=now_gregorian)
    day = str(j.day).translate(PERSIAN_DIGITS)
    year = str(j.year).translate(PERSIAN_DIGITS)
    month_name = JALALI_MONTHS[j.month - 1]
    hour = str(now_gregorian.hour).zfill(2).translate(PERSIAN_DIGITS)
    minute = str(now_gregorian.minute).zfill(2).translate(PERSIAN_DIGITS)
    return f"{day} {month_name} {year} - ساعت {hour}:{minute}"


def fetch_price(row_id: str) -> str | None:
    """صفحه‌ی اختصاصی یک آیتم رو می‌گیره و مقدار "نرخ فعلی" رو استخراج می‌کنه."""
    url = f"{PROFILE_BASE}{row_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    match = RATE_PATTERN.search(text)
    return match.group(1) if match else None


def fetch_all_prices() -> dict:
    results = {}
    for row_id, fa_name in ALL_ITEMS:
        try:
            price = fetch_price(row_id)
            if price:
                results[row_id] = price
            else:
                print(f"قیمتی برای {fa_name} ({row_id}) پیدا نشد.")
        except Exception as e:
            print(f"خطا در گرفتن {fa_name} ({row_id}): {e}")
        time.sleep(0.5)
    return results


def build_message(prices: dict) -> str:
    date_str = now_jalali_str()
    lines = [f"قیمت لحظه‌ای ارز و طلا - {date_str}", SEPARATOR]

    for row_id, fa_name in CURRENCY_ITEMS:
        if row_id in prices:
            lines.append(f"{fa_name}: {prices[row_id]}")

    lines.append(SEPARATOR)

    for row_id, fa_name in GOLD_ITEMS:
        if row_id in prices:
            lines.append(f"{fa_name}: {prices[row_id]}")

    lines.append(SEPARATOR)
    lines.append("منبع: tgju.org")

    body = "\n".join(lines)
    return f"<b>{body}</b>"


def send_to_telegram(text: str, bot_token: str, chat_id: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    resp = requests.post(url, data=payload, timeout=15)
    if resp.status_code != 200:
        print("پاسخ تلگرام:", resp.text)
    resp.raise_for_status()
    return resp.json()


def main():
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHANNEL_ID")
    if not bot_token or not chat_id:
        raise SystemExit("متغیرهای محیطی BOT_TOKEN و CHANNEL_ID باید تنظیم شده باشن.")

    prices = fetch_all_prices()
    if not prices:
        raise SystemExit(
            "هیچ قیمتی استخراج نشد. احتمالا ساختار صفحات tgju.org تغییر کرده."
        )

    message = build_message(prices)
    send_to_telegram(message, bot_token, chat_id)
    print("پیام با موفقیت ارسال شد.")


if __name__ == "__main__":
    main()

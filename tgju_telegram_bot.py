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

# ارزها به‌صورت جفت برای نمایش دو ستونی
CURRENCY_PAIRS = [
    (("price_dollar_rl", "🇺🇸"), ("price_eur",  "🇪🇺")),
    (("price_gbp",       "🇬🇧"), ("price_aed",  "🇦🇪")),
    (("price_try",       "🇹🇷"), ("price_cad",  "🇨🇦")),
    (("price_cny",       "🇨🇳"), ("price_rub",  "🇷🇺")),
]

GOLD_ITEMS = [
    ("geram18", "💛 طلای ۱۸ عیار (هر گرم)"),
    ("mesghal", "💛 مثقال طلا"),
    ("rob",     "💛 ربع سکه"),
    ("nim",     "💛 نیم سکه"),
    ("sekee",   "💛 سکه تمام (امامی)"),
    ("sekeb",   "💛 سکه بهار آزادی"),
    ("ons",     "💛 انس جهانی طلا"),
    ("silver_999", "🩶 نقره (هر گرم)"),
]

CRYPTO_ITEMS = [
    ("crypto-tether",      "⚛️ ₮"),
    ("crypto-bitcoin",     "⚛️ ₿"),
    ("crypto-ethereum",    "⚛️ Ξ"),
    ("crypto-ripple",      "⚛️ XRP"),
    ("crypto-tron",        "⚛️ TRX"),
    ("crypto-dogecoin",    "⚛️ Ð"),
    ("crypto-gram",        "⚛️ GRAM"),
    ("crypto-tether-gold", "⚛️ XAUT"),
]

CURRENCY_IDS = [pid for pair in CURRENCY_PAIRS for (pid, _) in pair]
ALL_ITEMS = (
    [(pid, pid) for pid in CURRENCY_IDS]
    + GOLD_ITEMS
    + [(pid, pid) for pid, _ in CRYPTO_ITEMS]
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

RATE_PATTERN = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")

SEP = "┄" * 18
CHANNEL_HANDLE = "@coredollar"

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def now_jalali_date() -> str:
    now_gregorian = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=now_gregorian)
    day = str(j.day).translate(PERSIAN_DIGITS)
    year = str(j.year).translate(PERSIAN_DIGITS)
    month_name = JALALI_MONTHS[j.month - 1]
    return f"{day} {month_name} {year}"


def to_toman(price_str: str) -> str:
    digits = price_str.replace(",", "")
    try:
        value = float(digits)
    except ValueError:
        return price_str
    toman = round(value / 10)
    return f"{toman:,}"


def usd_to_toman(usd_str: str, dollar_toman: float) -> str:
    digits = usd_str.replace(",", "")
    try:
        usd = float(digits)
    except ValueError:
        return usd_str
    toman = round(usd * dollar_toman)
    return f"{toman:,}"


def fetch_price(row_id: str) -> str | None:
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
                print(f"قیمتی برای {fa_name} پیدا نشد.")
        except Exception as e:
            print(f"خطا در گرفتن {fa_name}: {e}")
        time.sleep(0.5)
    return results


def build_message(prices: dict) -> str:
    dollar_toman = 0.0
    if "price_dollar_rl" in prices:
        try:
            dollar_toman = float(prices["price_dollar_rl"].replace(",", "")) / 10
        except ValueError:
            pass

    lines = [now_jalali_date(), f"<b>{SEP}</b>"]

    # ارزها در دو ستون با فرمت <pre> برای تراز درست
    currency_rows = []
    for (id1, flag1), (id2, flag2) in CURRENCY_PAIRS:
        p1 = to_toman(prices[id1]) if id1 in prices else "—"
        p2 = to_toman(prices[id2]) if id2 in prices else "—"
        col1 = f"{p1} {flag1}"
        col2 = f"{p2} {flag2}"
        currency_rows.append(f"{col1:<20}{col2}")

    lines.append("<pre>" + "\n".join(currency_rows) + "</pre>")
    lines.append(f"<b>{SEP}</b>")

    for row_id, fa_name in GOLD_ITEMS:
        if row_id in prices:
            value = prices[row_id] if row_id == "ons" else to_toman(prices[row_id])
            lines.append(f"<b>{fa_name}: {value}</b>")

    lines.append(f"<b>{SEP}</b>")

    for pid, symbol in CRYPTO_ITEMS:
        if pid in prices:
            value = usd_to_toman(prices[pid], dollar_toman) if dollar_toman > 0 else prices[pid]
            lines.append(f"<b>{symbol}: {value}</b>")

    lines.append(f"<b>{SEP}</b>")
    lines.append(f"<b>{CHANNEL_HANDLE}</b>")

    return "\n".join(lines)


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
        raise SystemExit("هیچ قیمتی استخراج نشد.")

    message = build_message(prices)
    send_to_telegram(message, bot_token, chat_id)
    print("پیام با موفقیت ارسال شد.")


if __name__ == "__main__":
    main()

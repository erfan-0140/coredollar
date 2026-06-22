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

# ارزها - قیمت به ریاله، تبدیل به تومان میشه
CURRENCY_ITEMS = [
    ("price_dollar_rl", "🇺🇸"),
    ("price_eur", "🇪🇺"),
    ("price_gbp", "🇬🇧"),
    ("price_aed", "🇦🇪"),
    ("price_try", "🇹🇷"),
    ("price_cad", "🇨🇦"),
    ("price_cny", "🇨🇳"),
    ("price_rub", "🇷🇺"),
]

# طلا و سکه - قیمت به ریاله، تبدیل به تومان میشه (به‌جز ons که دلاره)
GOLD_ITEMS = [
    ("geram18", "طلای ۱۸ عیار (هر گرم)"),
    ("geram-naqre", "نقره (هر گرم)"),
    ("mesghal", "مثقال طلا"),
    ("rob", "ربع سکه"),
    ("nim", "نیم سکه"),
    ("sekee", "سکه تمام (امامی)"),
    ("sekeb", "سکه بهار آزادی"),
    ("ons", "انس جهانی طلا"),
]

# ارزهای دیجیتال - قیمت به ریاله، تبدیل به تومان میشه
CRYPTO_ITEMS = [
    ("crypto-tether", "تتر (USDT)"),
    ("crypto-bitcoin", "بیتکوین (BTC)"),
    ("crypto-ethereum", "اتریوم (ETH)"),
    ("crypto-ripple", "ریپل (XRP)"),
    ("crypto-tron", "ترون (TRX)"),
    ("crypto-dogecoin", "دوج کوین (DOGE)"),
    ("crypto-gram", "گرام (GRAM)"),
    ("crypto-tether-gold", "تتر گلد (XAUT)"),
]

ALL_ITEMS = (
    [(pid, pid) for pid, _ in CURRENCY_ITEMS]
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

SEPARATOR = "\u200f" + "━" * 18
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
    lines = [now_jalali_date(), SEPARATOR, "💵 ارزها", ""]

    for pid, flag in CURRENCY_ITEMS:
        if pid in prices:
            lines.append(f"{flag} {to_toman(prices[pid])}")

    lines.append("")
    lines.append(SEPARATOR)
    lines.append("🥇 طلا و سکه")
    lines.append("")

    for row_id, fa_name in GOLD_ITEMS:
        if row_id in prices:
            value = prices[row_id] if row_id == "ons" else to_toman(prices[row_id])
            lines.append(f"{fa_name}: {value}")

    lines.append("")
    lines.append(SEPARATOR)
    lines.append("🪙 ارزهای دیجیتال")
    lines.append("")

    for pid, fa_name in CRYPTO_ITEMS:
        if pid in prices:
            lines.append(f"{fa_name}: {to_toman(prices[pid])}")

    lines.append("")
    lines.append(SEPARATOR)
    lines.append(CHANNEL_HANDLE)

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

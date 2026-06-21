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

# سه گروهِ شش‌تایی ارز - هر گروه یک ستون. ستون اول سمت راستِ پست قرار می‌گیره.
GROUP1 = [  # ستون راست
    ("price_dollar_rl", "🇺🇸"),
    ("price_eur", "🇪🇺"),
    ("price_gbp", "🇬🇧"),
    ("price_aed", "🇦🇪"),
    ("price_try", "🇹🇷"),
    ("price_cad", "🇨🇦"),
]
GROUP2 = [  # ستون وسط
    ("price_cny", "🇨🇳"),
    ("price_omr", "🇴🇲"),
    ("price_iqd", "🇮🇶"),
    ("price_sar", "🇸🇦"),
    ("price_rub", "🇷🇺"),
    ("price_afn", "🇦🇫"),
]
GROUP3 = [  # ستون چپ
    ("price_amd", "🇦🇲"),
    ("price_sek", "🇸🇪"),
    ("price_qar", "🇶🇦"),
    ("price_myr", "🇲🇾"),
    ("price_thb", "🇹🇭"),
    ("price_gel", "🇬🇪"),
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

CURRENCY_IDS = [pid for pid, _ in GROUP1 + GROUP2 + GROUP3]
ALL_ITEMS = [(pid, pid) for pid in CURRENCY_IDS] + GOLD_ITEMS

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

RATE_PATTERN = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")

SEPARATOR = "\u200f" + "-" * 30
CHANNEL_HANDLE = "@coredollar"
COL_WIDTH = 15

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def now_jalali_date() -> str:
    """تاریخ امروز به وقت تهران، به شمسی و با اعداد فارسی (بدون ساعت)."""
    now_gregorian = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=now_gregorian)
    day = str(j.day).translate(PERSIAN_DIGITS)
    year = str(j.year).translate(PERSIAN_DIGITS)
    month_name = JALALI_MONTHS[j.month - 1]
    return f"{day} {month_name} {year}"


def to_toman(price_str: str) -> str:
    """قیمت ریالی tgju (با کاما) رو به تومان تبدیل می‌کنه."""
    digits = price_str.replace(",", "")
    try:
        value = float(digits)
    except ValueError:
        return price_str
    toman = round(value / 10)
    return f"{toman:,}"


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
                print(f"قیمتی برای {fa_name} پیدا نشد.")
        except Exception as e:
            print(f"خطا در گرفتن {fa_name}: {e}")
        time.sleep(0.5)
    return results


def fmt_cell(item: tuple, prices: dict, pad: bool = True) -> str:
    pid, flag = item
    price = to_toman(prices[pid]) if pid in prices else "-"
    cell = f"{flag} {price}"
    return cell.ljust(COL_WIDTH) if pad else cell


def build_currency_grid(prices: dict) -> str:
    rows = []
    for i in range(6):
        c3 = fmt_cell(GROUP3[i], prices)
        c2 = fmt_cell(GROUP2[i], prices)
        c1 = fmt_cell(GROUP1[i], prices, pad=False)
        rows.append(f"{c3}{c2}{c1}")
    return "\n".join(rows)


def build_message(prices: dict) -> str:
    header = f"<b>{now_jalali_date()}\n{SEPARATOR}</b>"
    grid = f"<pre>{build_currency_grid(prices)}</pre>"

    gold_lines = []
    for row_id, fa_name in GOLD_ITEMS:
        if row_id in prices:
            value = prices[row_id] if row_id == "ons" else to_toman(prices[row_id])
            gold_lines.append(f"{fa_name}: {value}")

    footer = "<b>" + SEPARATOR + "\n" + "\n".join(gold_lines) + "\n" + SEPARATOR + "\n" + CHANNEL_HANDLE + "</b>"

    return f"{header}\n{grid}\n{footer}"


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

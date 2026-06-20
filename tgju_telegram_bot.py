"""
بات قیمت ارز و طلا - گرفتن قیمت از tgju.org و ارسال به کانال تلگرام
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TGJU_URL = "https://www.tgju.org/"

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
    ("sekeb", "سکه تمام بهار آزادی"),
    ("ons", "انس جهانی طلا"),
]

ALL_ITEMS = CURRENCY_ITEMS + GOLD_ITEMS

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_prices() -> dict:
    """صفحه‌ی اصلی tgju.org رو می‌گیره و قیمت آیتم‌های موردنظر رو استخراج می‌کنه.
    خروجی: دیکشنری {row_id: قیمت}
    """
    resp = requests.get(TGJU_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = {}
    for row_id, _ in ALL_ITEMS:
        row = soup.find("tr", attrs={"data-market-row": row_id})
        if not row:
            continue
        price_cell = row.find("td", class_="nf")
        if not price_cell:
            continue
        results[row_id] = price_cell.get_text(strip=True)
    return results


def build_message(prices: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"قیمت لحظه‌ای ارز و طلا - {now}", ""]

    for row_id, fa_name in CURRENCY_ITEMS:
        if row_id in prices:
            lines.append(f"- {fa_name}: {prices[row_id]}")

    lines.append("----------------------------")

    for row_id, fa_name in GOLD_ITEMS:
        if row_id in prices:
            lines.append(f"- {fa_name}: {prices[row_id]}")

    lines.append("")
    lines.append("منبع: tgju.org")
    return "\n".join(lines)


def send_to_telegram(text: str, bot_token: str, chat_id: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
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

    prices = fetch_prices()
    if not prices:
        raise SystemExit(
            "هیچ قیمتی استخراج نشد. احتمالا ساختار صفحه‌ی tgju.org تغییر کرده "
            "و باید شناسه‌های موجود در CURRENCY_ITEMS / GOLD_ITEMS بازبینی بشن."
        )

    message = build_message(prices)
    send_to_telegram(message, bot_token, chat_id)
    print("پیام با موفقیت ارسال شد.")


if __name__ == "__main__":
    main()

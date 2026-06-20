"""
بات قیمت ارز و طلا - گرفتن قیمت از tgju.org و ارسال به کانال تلگرام
"""

import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TGJU_URL = "https://www.tgju.org/"

# نگاشت شناسه‌ی هر ردیف در جدول سایت tgju.org به نام فارسی
# نکته: اگر سایت ساختارش رو عوض کنه، ممکنه نیاز به تنظیم این شناسه‌ها باشه.
ITEMS = {
    "price_dollar_rl": "دلار آمریکا",
    "price_eur": "یورو",
    "price_gbp": "پوند انگلیس",
    "price_aed": "درهم امارات",
    "price_try": "لیر ترکیه",
    "geram18": "طلای ۱۸ عیار (هر گرم)",
    "mesghal": "مثقال طلا",
    "sekee": "سکه امامی",
    "sekeb": "سکه بهار آزادی",
    "nim": "نیم سکه",
    "rob": "ربع سکه",
    "ons": "انس جهانی طلا",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def fetch_prices() -> dict:
    """صفحه‌ی اصلی tgju.org رو می‌گیره و قیمت آیتم‌های موردنظر رو استخراج می‌کنه."""
    resp = requests.get(TGJU_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    results = {}
    for row_id, fa_name in ITEMS.items():
        row = soup.find("tr", attrs={"data-market-row": row_id})
        if not row:
            continue
        price_cell = row.find("td", class_="nf")
        if not price_cell:
            continue
        results[fa_name] = price_cell.get_text(strip=True)
    return results


def build_message(results: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"قیمت لحظه‌ای ارز و طلا - {now}", ""]
    for name, price in results.items():
        lines.append(f"- {name}: {price}")
    lines.append("")
    lines.append("منبع: tgju.org")
    return "\n".join(lines)


def send_to_telegram(text: str, bot_token: str, chat_id: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, data=payload, timeout=15)
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
            "و باید شناسه‌های موجود در دیکشنری ITEMS بازبینی بشن."
        )

    message = build_message(prices)
    send_to_telegram(message, bot_token, chat_id)
    print("پیام با موفقیت ارسال شد.")


if __name__ == "__main__":
    main()

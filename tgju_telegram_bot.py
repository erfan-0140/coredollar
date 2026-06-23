"""
بات قیمت ارز، طلا و کریپتو - tgju.org → کانال تلگرام
سه پست مجزا: کریپتو | فلزات گرانبها | ارزهای آزاد
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
TEHRAN_TZ    = ZoneInfo("Asia/Tehran")
CHANNEL_LINK = "t.me/coredollar"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
RATE_PATTERN = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")
SEP = "<b>" + "┄" * 22 + "</b>"

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS  = [
    "فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
    "مهر","آبان","آذر","دی","بهمن","اسفند",
]

# ─── کریپتو ─────────────────────────────────────────────────────────────────
# چهار ستون × پنج ردیف = ۲۰ ارز دیجیتال
# هر ستون: (شناسه‌ی tgju، نام فارسی کوتاه)
COL1 = [  # 🔴
    ("crypto-tether",          "تتر"),
    ("crypto-bitcoin",         "بیتکوین"),
    ("crypto-ethereum",        "اتریوم"),
    ("crypto-cardano",         "کاردانو"),
    ("crypto-shiba-inu",       "شیبا"),
]
COL2 = [  # 🟡
    ("crypto-gram",            "گرام"),
    ("crypto-binancecoin",     "بایننس"),
    ("crypto-stellar",         "استلار"),
    ("crypto-ripple",          "ریپل"),
    ("crypto-dogecoin",        "دوج"),
]
COL3 = [  # 🟢
    ("crypto-tron",            "ترون"),
    ("crypto-solana",          "سولانا"),
    ("crypto-ethereum-classic","ETCلاسیک"),
    ("crypto-chainlink",       "چین‌لینک"),
    ("crypto-tether-gold",     "تترگلد"),
]
COL4 = [  # ⚪️
    ("crypto-litecoin",        "لایت"),
    ("crypto-avalanche-2",     "آوالانچ"),
    ("crypto-zcash",           "زدکش"),
    ("crypto-monero",          "مونرو"),
    ("crypto-pi-network",      "پای"),
]

# ─── فلزات گرانبها ──────────────────────────────────────────────────────────
PRECIOUS_METALS = [
    ("ons",       "💛 انس جهانی طلا"),
    ("mesghal",   "💛 مثقال طلا"),
    ("geram18",   "💛 طلای ۱۸ عیار (هر گرم)"),
    ("geram24",   "💛 طلای ۲۴ عیار (هر گرم)"),
    ("silver_999","🩶 گرم نقره ۹۹۹"),
]
# سکه‌ها و حباب متناظرشان (coin_id, bubble_id, نام)
COIN_BUBBLE = [
    ("sekee",        "habbab-sekee",  "سکه امامی"),
    ("sekeb",        "habbab-sekeb",  "سکه بهار آزادی"),
    ("nim",          "habbab-nim",    "نیم سکه"),
    ("rob",          "habbab-rob",    "ربع سکه"),
    ("seke-gerami",  "habbab-gerami", "سکه گرمی"),
]

# ─── ارزهای آزاد ────────────────────────────────────────────────────────────
CURRENCIES = [
    ("price_dollar_rl", "🇺🇸"), ("price_eur",  "🇪🇺"),
    ("price_gbp",       "🇬🇧"), ("price_aed",  "🇦🇪"),
    ("price_try",       "🇹🇷"), ("price_cny",  "🇨🇳"),
    ("price_cad",       "🇨🇦"), ("price_aud",  "🇦🇺"),
    ("price_iqd",       "🇮🇶"), ("price_rub",  "🇷🇺"),
    ("price_sek",       "🇸🇪"), ("price_sar",  "🇸🇦"),
    ("price_myr",       "🇲🇾"), ("price_thb",  "🇹🇭"),
    ("price_amd",       "🇦🇲"), ("price_azn",  "🇦🇿"),
    ("price_gel",       "🇬🇪"), ("price_afn",  "🇦🇫"),
    ("price_qar",       "🇶🇦"), ("price_omr",  "🇴🇲"),
]

# ─── همه‌ی شناسه‌ها برای دریافت قیمت ──────────────────────────────────────
ALL_IDS = (
    [pid for col in (COL1,COL2,COL3,COL4) for pid,_ in col]
    + [pid for pid,_ in PRECIOUS_METALS]
    + [cid for cid,_,_ in COIN_BUBBLE]
    + [bid for _,bid,_ in COIN_BUBBLE]
    + [pid for pid,_ in CURRENCIES]
)

# ─── توابع کمکی ─────────────────────────────────────────────────────────────
def now_jalali_date() -> str:
    g = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=g)
    d = str(j.day).translate(PERSIAN_DIGITS)
    y = str(j.year).translate(PERSIAN_DIGITS)
    return f"{d} {JALALI_MONTHS[j.month-1]} {y}"

def to_toman(s: str) -> str:
    try:
        return f"{round(float(s.replace(',','')) / 10):,}"
    except ValueError:
        return s

def fetch_price(row_id: str) -> str | None:
    try:
        r = requests.get(f"{PROFILE_BASE}{row_id}", headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        m = RATE_PATTERN.search(soup.get_text(" ", strip=True))
        return m.group(1) if m else None
    except Exception as e:
        print(f"خطا ({row_id}): {e}")
        return None

def fetch_all(ids: list) -> dict:
    seen, results = set(), {}
    for row_id in ids:
        if row_id in seen:
            continue
        seen.add(row_id)
        p = fetch_price(row_id)
        if p:
            results[row_id] = p
        else:
            print(f"یافت نشد: {row_id}")
        time.sleep(0.4)
    return results

def send_msg(text: str, token: str, chat: str):
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    if r.status_code != 200:
        print("خطای تلگرام:", r.text)
    r.raise_for_status()

# ─── ساخت پست‌ها ─────────────────────────────────────────────────────────────
def build_crypto(prices: dict) -> str:
    # نرخ دلار برای تبدیل
    usd_toman = 0.0
    if "price_dollar_rl" in prices:
        try:
            usd_toman = float(prices["price_dollar_rl"].replace(",","")) / 10
        except ValueError:
            pass

    def crypto_val(pid):
        if pid not in prices:
            return "—"
        raw = float(prices[pid].replace(",",""))
        if usd_toman > 0:
            return f"{round(raw * usd_toman):,}"
        return prices[pid]

    lines = [f"<b>🪙 کریپتوکارنسی</b>", SEP]
    for i in range(5):
        r1 = f"🔴 {COL1[i][1]}: {crypto_val(COL1[i][0])}" if i < len(COL1) else ""
        r2 = f"🟡 {COL2[i][1]}: {crypto_val(COL2[i][0])}" if i < len(COL2) else ""
        r3 = f"🟢 {COL3[i][1]}: {crypto_val(COL3[i][0])}" if i < len(COL3) else ""
        r4 = f"⚪️ {COL4[i][1]}: {crypto_val(COL4[i][0])}" if i < len(COL4) else ""
        lines.append(f"<b>{r1}</b>")
        lines.append(f"<b>{r2}</b>")
        lines.append(f"<b>{r3}</b>")
        lines.append(f"<b>{r4}</b>")
        if i < 4:
            lines.append("")
    lines += [SEP, f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)


def build_metals(prices: dict) -> str:
    lines = [f"<b>🏅 فلزات گرانبها</b>", SEP]
    for pid, fa in PRECIOUS_METALS:
        if pid in prices:
            val = prices[pid] if pid == "ons" else to_toman(prices[pid])
            lines.append(f"<b>{fa}: {val}</b>")
    lines.append(SEP)
    for cid, bid, name in COIN_BUBBLE:
        c = to_toman(prices[cid]) if cid in prices else "—"
        b = to_toman(prices[bid]) if bid in prices else "—"
        lines.append(f"<b>🟠 {name}: {c}    🫧 حباب: {b}</b>")
    lines += [SEP, f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)


def build_currency(prices: dict) -> str:
    lines = [f"<b>💵 ارزهای آزاد</b>", SEP]
    pairs = [(CURRENCIES[i], CURRENCIES[i+1]) for i in range(0, len(CURRENCIES)-1, 2)]
    if len(CURRENCIES) % 2 == 1:
        pairs.append((CURRENCIES[-1], None))
    for (id1, fl1), pair2 in pairs:
        p1 = to_toman(prices[id1]) if id1 in prices else "—"
        if pair2:
            id2, fl2 = pair2
            p2 = to_toman(prices[id2]) if id2 in prices else "—"
            lines.append(f"<b>{fl1} {p1}      {fl2} {p2}</b>")
        else:
            lines.append(f"<b>{fl1} {p1}</b>")
    lines += [SEP, f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)


def main():
    token   = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHANNEL_ID")
    if not token or not chat_id:
        raise SystemExit("BOT_TOKEN و CHANNEL_ID باید تنظیم شده باشن.")

    prices = fetch_all(ALL_IDS)
    if not prices:
        raise SystemExit("هیچ قیمتی دریافت نشد.")

    send_msg(build_crypto(prices),   token, chat_id)
    time.sleep(1)
    send_msg(build_metals(prices),   token, chat_id)
    time.sleep(1)
    send_msg(build_currency(prices), token, chat_id)
    print("هر سه پست با موفقیت ارسال شد.")


if __name__ == "__main__":
    main()

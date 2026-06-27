"""
بات قیمت ارز، طلا و کریپتو — نسخه حرفه‌ای
منابع: tgju.org (scraping موازی) + CoinGecko API
حباب سکه: محاسباتی (نه scraping)
"""

import os
import re
import time
import logging
import requests
import jdatetime
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

# ─── تنظیمات ─────────────────────────────────────────────────────────────────
TEHRAN_TZ    = timezone(timedelta(hours=3, minutes=30))
CHANNEL_LINK = "@coredollar"
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("❌ BOT_TOKEN و CHANNEL_ID باید در Environment Variables تنظیم شوند.")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9",
}

PRICE_PATTERNS = [
    re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)"),
    re.compile(r"قیمت لحظه.ای[:\s]*([\d,]+(?:\.\d+)?)"),
    re.compile(r'"price"\s*:\s*"?([\d,]+(?:\.\d+)?)"?'),
]

SEP = "┄" * 22

JALALI_MONTHS = [
    "فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
    "مهر","آبان","آذر","دی","بهمن","اسفند",
]
PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ─── ارزها ───────────────────────────────────────────────────────────────────
CURRENCIES = [
    ("price_dollar_rl", "🇺🇸 دلار"),    ("price_eur",  "🇪🇺 یورو"),
    ("price_gbp",       "🇬🇧 پوند"),    ("price_aed",  "🇦🇪 درهم"),
    ("price_try",       "🇹🇷 لیر"),     ("price_cny",  "🇨🇳 یوان"),
    ("price_cad",       "🇨🇦 کانادا"),  ("price_aud",  "🇦🇺 استرالیا"),
    ("price_iqd",       "🇮🇶 دینار"),   ("price_rub",  "🇷🇺 روبل"),
    ("price_sek",       "🇸🇪 کرون"),    ("price_sar",  "🇸🇦 ریال سعودی"),
    ("price_myr",       "🇲🇾 رینگیت"),  ("price_thb",  "🇹🇭 بات"),
    ("price_amd",       "🇦🇲 درام"),    ("price_azn",  "🇦🇿 منات"),
    ("price_gel",       "🇬🇪 لاری"),    ("price_afn",  "🇦🇫 افغانی"),
    ("price_qar",       "🇶🇦 ریال قطر"),("price_omr",  "🇴🇲 ریال عمان"),
]

# ─── طلا و نقره ──────────────────────────────────────────────────────────────
# (tgju_id، نام، آیا ریال است؟)
METALS = [
    ("ons",        "💛 انس جهانی طلا",      False),  # دلار
    ("mesghal",    "💛 مثقال طلا",            True),
    ("geram18",    "💛 طلای ۱۸ عیار (گرم)",  True),
    ("geram24",    "💛 طلای ۲۴ عیار (گرم)",  True),
    ("silver_999", "🩶 نقره ۹۹۹ (گرم)",      True),
]

# ─── سکه ─────────────────────────────────────────────────────────────────────
# (tgju_id، وزن به گرم، نام)
# حباب از فرمول محاسبه میشه، نه scraping
COINS = [
    ("sekee",       8.133,   "🟠 سکه امامی"),
    ("sekeb",       8.133,   "🟠 سکه بهار آزادی"),
    ("nim",         4.0665,  "🟠 نیم سکه"),
    ("rob",         2.03325, "🟠 ربع سکه"),
    ("seke-gerami", 1.01,    "🟠 سکه گرمی"),
]

# ─── کریپتو ──────────────────────────────────────────────────────────────────
# (CoinGecko ID، نام فارسی، ایموجی ستون)
CRYPTOS = [
    ("tether",           "تتر",      "🔴"),
    ("bitcoin",          "بیتکوین",  "🔴"),
    ("ethereum",         "اتریوم",   "🔴"),
    ("cardano",          "کاردانو",  "🔴"),
    ("shiba-inu",        "شیبا",     "🔴"),
    ("the-open-network", "گرام",     "🟡"),
    ("binancecoin",      "بایننس",   "🟡"),
    ("stellar",          "استلار",   "🟡"),
    ("ripple",           "ریپل",     "🟡"),
    ("dogecoin",         "دوج",      "🟡"),
    ("tron",             "ترون",     "🟢"),
    ("solana",           "سولانا",   "🟢"),
    ("ethereum-classic", "ETC",      "🟢"),
    ("chainlink",        "LINK",     "🟢"),
    ("tether-gold",      "تترگلد",   "🟢"),
    ("litecoin",         "لایت",     "⚪️"),
    ("avalanche-2",      "آوالانچ",  "⚪️"),
    ("zcash",            "زدکش",     "⚪️"),
    ("monero",           "مونرو",    "⚪️"),
    ("pi-network",       "پای",      "⚪️"),
]

# ─── توابع کمکی ──────────────────────────────────────────────────────────────
def safe_float(s) -> Optional[float]:
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return None

def to_toman(s) -> str:
    """ریال به تومان با فرمت عددی."""
    v = safe_float(s)
    return f"{round(v / 10):,}" if v is not None else "—"

def fmt_num(s) -> str:
    """فرمت عدد: اعشاری اگه کوچک‌تر از ۱۰۰، وگرنه صحیح."""
    v = safe_float(s)
    if v is None:
        return "—"
    return f"{v:,.2f}" if v < 100 else f"{round(v):,}"

def jalali_now() -> str:
    now = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=now)
    d = str(j.day).translate(PERSIAN)
    y = str(j.year).translate(PERSIAN)
    return f"{d} {JALALI_MONTHS[j.month - 1]} {y}"

def calc_bubble(coin_rial: str, geram18_rial: str, weight: float) -> str:
    """
    حباب سکه = قیمت سکه (تومان) - ارزش ذاتی (تومان)
    ارزش ذاتی = گرم طلای ۱۸ عیار (تومان) × ۱.۲ × وزن سکه
    """
    coin = safe_float(coin_rial)
    g18  = safe_float(geram18_rial)
    if coin is None or g18 is None:
        return "—"
    coin_t     = coin / 10
    g18_t      = g18 / 10
    intrinsic  = g18_t * 1.2 * weight
    bubble     = round(coin_t - intrinsic)
    sign       = "+" if bubble >= 0 else ""
    return f"{sign}{bubble:,}"

# ─── دریافت قیمت‌ها ──────────────────────────────────────────────────────────
def scrape_one(row_id: str, retries: int = 2) -> tuple[str, Optional[str]]:
    """یک صفحه tgju را scrape می‌کند با retry خودکار."""
    url = f"https://www.tgju.org/profile/{row_id}"
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
            for pat in PRICE_PATTERNS:
                m = pat.search(text)
                if m:
                    return row_id, m.group(1)
            return row_id, None
        except Exception as e:
            if attempt == retries:
                log.warning(f"  ✗ {row_id}: {type(e).__name__}: {e}")
                return row_id, None
            time.sleep(0.5 * (attempt + 1))  # exponential backoff
    return row_id, None

def fetch_tgju_parallel(ids: list, workers: int = 8) -> dict:
    """همه شناسه‌ها را به‌صورت موازی دریافت می‌کند."""
    unique = list(dict.fromkeys(ids))
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as exe:
        futures = {exe.submit(scrape_one, rid): rid for rid in unique}
        for future in as_completed(futures):
            rid, val = future.result()
            if val:
                results[rid] = val
    return results

def fetch_crypto(dollar_toman: float) -> dict:
    """قیمت کریپتو از CoinGecko — یک درخواست برای همه، با retry."""
    ids_str = ",".join(c[0] for c in CRYPTOS)
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={ids_str}&vs_currencies=usd"
    )
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 60))
                log.warning(f"  CoinGecko rate limit — {wait}s صبر...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            out = {}
            for cid, _, _ in CRYPTOS:
                usd = data.get(cid, {}).get("usd")
                if usd is None:
                    out[cid] = "N/A"
                    continue
                if dollar_toman > 0:
                    out[cid] = f"{round(float(usd) * dollar_toman):,}"
                else:
                    out[cid] = fmt_num(usd) + " $"
            return out
        except Exception as e:
            log.error(f"  CoinGecko خطا (تلاش {attempt + 1}): {e}")
            time.sleep(5 * (attempt + 1))
    return {}

def send(text: str):
    """ارسال پیام به تلگرام."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        r.raise_for_status()
    except Exception as e:
        log.error(f"  ❌ تلگرام خطا: {e}")

# ─── ساخت پست‌ها ─────────────────────────────────────────────────────────────
def post_crypto(cp: dict) -> str:
    lines = [f"<b>🪙 کریپتوکارنسی</b>", f"<b>{SEP}</b>"]
    for cid, name, emoji in CRYPTOS:
        v = cp.get(cid, "N/A")
        lines.append(f"<b>{emoji} {name}: {v}</b>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

def post_metals(prices: dict) -> str:
    geram18_rial = prices.get("geram18")
    lines = [f"<b>🏅 فلزات گرانبها</b>", f"<b>{SEP}</b>"]

    for k, fa, is_rial in METALS:
        if k not in prices:
            continue
        v = to_toman(prices[k]) if is_rial else fmt_num(prices[k])
        lines.append(f"<b>{fa}: {v}</b>")

    lines.append(f"<b>{SEP}</b>")

    for coin_id, weight, name in COINS:
        if coin_id not in prices:
            continue
        price_str   = to_toman(prices[coin_id])
        bubble_str  = calc_bubble(prices[coin_id], geram18_rial, weight) \
                      if geram18_rial else "—"
        lines.append(f"<b>{name}: {price_str}    🫧 {bubble_str}</b>")

    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

def post_currency(prices: dict) -> str:
    lines = [f"<b>💵 ارزهای آزاد</b>", f"<b>{SEP}</b>"]
    for k, label in CURRENCIES:
        v = to_toman(prices[k]) if k in prices else "—"
        lines.append(f"<b>{label}: {v}</b>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── اجرا ────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    tgju_ids = list(dict.fromkeys(
        [k for k, _ in CURRENCIES]
        + [k for k, _, _ in METALS]
        + [cid for cid, _, _ in COINS]
    ))

    log.info(f"⬇ دریافت موازی {len(tgju_ids)} آیتم از tgju...")
    prices = fetch_tgju_parallel(tgju_ids, workers=8)
    log.info(f"  ✓ {len(prices)}/{len(tgju_ids)} آیتم ({time.time() - t0:.1f}s)")

    dollar_raw   = prices.get("price_dollar_rl")
    dollar_toman = (safe_float(dollar_raw) / 10) if dollar_raw else 0.0
    if dollar_toman:
        log.info(f"  دلار: {dollar_toman:,.0f} تومان")
    else:
        log.warning("  ⚠ نرخ دلار دریافت نشد — کریپتو به دلار نمایش داده می‌شود")

    log.info("⬇ دریافت کریپتو از CoinGecko...")
    cp = fetch_crypto(dollar_toman)
    log.info(f"  ✓ {len(cp)}/{len(CRYPTOS)} کریپتو ({time.time() - t0:.1f}s)")

    log.info("📤 ارسال پست‌ها...")
    send(post_crypto(cp));       time.sleep(1)
    send(post_metals(prices));   time.sleep(1)
    send(post_currency(prices))
    log.info(f"✅ هر سه پست ارسال شد ({time.time() - t0:.1f}s)")

if __name__ == "__main__":
    main()

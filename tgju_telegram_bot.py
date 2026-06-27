"""
بات قیمت ارز، طلا و کریپتو — نسخه حرفه‌ای
منبع: tgju.org (scraping موازی) + CoinGecko (قیمت USD کریپتو)
تبدیل کریپتو: USD × قیمت تتر از tgju (نه دلار بازار آزاد)
حباب سکه: محاسباتی با فرمول دقیق
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

JALALI_MONTHS = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                  "مهر","آبان","آذر","دی","بهمن","اسفند"]
PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ─── ارزها ── ۲ ستون × ۱۰ ردیف ──────────────────────────────────────────────
CUR_PAIRS = [
    (("price_dollar_rl","🇺🇸"), ("price_eur",  "🇪🇺")),
    (("price_gbp",      "🇬🇧"), ("price_aed",  "🇦🇪")),
    (("price_try",      "🇹🇷"), ("price_cny",  "🇨🇳")),
    (("price_cad",      "🇨🇦"), ("price_aud",  "🇦🇺")),
    (("price_iqd",      "🇮🇶"), ("price_rub",  "🇷🇺")),
    (("price_sek",      "🇸🇪"), ("price_sar",  "🇸🇦")),
    (("price_myr",      "🇲🇾"), ("price_thb",  "🇹🇭")),
    (("price_amd",      "🇦🇲"), ("price_azn",  "🇦🇿")),
    (("price_gel",      "🇬🇪"), ("price_afn",  "🇦🇫")),
    (("price_qar",      "🇶🇦"), ("price_omr",  "🇴🇲")),
]

# ─── طلا و نقره ──────────────────────────────────────────────────────────────
METALS = [
    ("ons",        "💛 انس جهانی طلا",     False),  # دلار جهانی
    ("mesghal",    "💛 مثقال طلا",           True),
    ("geram18",    "💛 طلای ۱۸ عیار (گرم)", True),
    ("geram24",    "💛 طلای ۲۴ عیار (گرم)", True),
    ("silver_999", "🩶 نقره ۹۹۹ (گرم)",     True),
]

# ─── سکه ── حباب با فرمول محاسبه میشه ───────────────────────────────────────
COINS = [
    ("sekee",       8.133,   "سکه امامی"),
    ("sekeb",       8.133,   "سکه بهار آزادی"),
    ("nim",         4.0665,  "نیم سکه"),
    ("rob",         2.03325, "ربع سکه"),
    ("seke-gerami", 1.01,    "سکه گرمی"),
]

# ─── کریپتو ── ۳ گروه × ۶ = ۱۸ ارز ──────────────────────────────────────────
# قیمت USD از CoinGecko × قیمت تتر از tgju = تومان
# شیبا و پای حذف شدن
CRYPTOS = [
    # (CoinGecko ID، نام فارسی، گروه رنگی)
    ("tether",           "تتر",            "🔴"),
    ("bitcoin",          "بیتکوین",        "🔴"),
    ("ethereum",         "اتریوم",         "🔴"),
    ("cardano",          "کاردانو",        "🔴"),
    ("the-open-network", "گرام",           "🔴"),
    ("binancecoin",      "بایننس",         "🔴"),
    ("stellar",          "استلار",         "🟡"),
    ("ripple",           "ریپل",           "🟡"),
    ("dogecoin",         "دوج",            "🟡"),
    ("tron",             "ترون",           "🟡"),
    ("solana",           "سولانا",         "🟡"),
    ("ethereum-classic", "اتریوم کلاسیک", "🟡"),
    ("chainlink",        "چین‌لینک",       "🟢"),
    ("tether-gold",      "تترگلد",         "🟢"),
    ("litecoin",         "لایت‌کوین",      "🟢"),
    ("avalanche-2",      "آوالانچ",        "🟢"),
    ("zcash",            "زدکش",           "🟢"),
    ("monero",           "مونرو",          "🟢"),
]

# ─── توابع کمکی ──────────────────────────────────────────────────────────────
def safe_float(s) -> Optional[float]:
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return None

def to_toman(s) -> str:
    v = safe_float(s)
    return f"{round(v / 10):,}" if v is not None else "—"

def fmt_num(s) -> str:
    v = safe_float(s)
    if v is None:
        return "—"
    return f"{v:,.2f}" if v < 100 else f"{round(v):,}"

def jalali_now() -> str:
    now = datetime.now(TEHRAN_TZ)
    j   = jdatetime.datetime.fromgregorian(datetime=now)
    d   = str(j.day).translate(PERSIAN)
    y   = str(j.year).translate(PERSIAN)
    return f"{d} {JALALI_MONTHS[j.month - 1]} {y}"

def calc_bubble(coin_rial: str, geram18_rial: str, weight: float) -> str:
    """حباب = قیمت سکه (تومان) − (گرم۱۸ × ۱.۲ × وزن)"""
    coin = safe_float(coin_rial)
    g18  = safe_float(geram18_rial)
    if coin is None or g18 is None:
        return "—"
    bubble = round(coin / 10 - g18 / 10 * 1.2 * weight)
    return f"{'+' if bubble >= 0 else ''}{bubble:,}"

# ─── دریافت داده‌های tgju ─────────────────────────────────────────────────────
def scrape_one(row_id: str, retries: int = 2) -> tuple[str, Optional[str]]:
    url = f"https://www.tgju.org/profile/{row_id}"
    for attempt in range(retries + 1):
        try:
            r    = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
            for pat in PRICE_PATTERNS:
                m = pat.search(text)
                if m:
                    return row_id, m.group(1)
            return row_id, None
        except Exception as e:
            if attempt == retries:
                log.warning(f"  ✗ {row_id}: {type(e).__name__}")
                return row_id, None
            time.sleep(0.5 * (attempt + 1))
    return row_id, None

def fetch_tgju_parallel(ids: list, workers: int = 10) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=workers) as exe:
        futures = {exe.submit(scrape_one, rid): rid
                   for rid in list(dict.fromkeys(ids))}
        for f in as_completed(futures):
            rid, val = f.result()
            if val:
                results[rid] = val
    return results

def fetch_crypto_prices(usdt_toman: float) -> dict:
    """
    قیمت کریپتو از CoinGecko (USD) × قیمت تتر (تومان از tgju) = تومان
    یک درخواست برای همه، با retry و مدیریت rate limit.
    """
    ids_str = ",".join(c[0] for c in CRYPTOS)
    url     = (f"https://api.coingecko.com/api/v3/simple/price"
               f"?ids={ids_str}&vs_currencies=usd")
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
            out  = {}
            for cid, _, _ in CRYPTOS:
                usd = data.get(cid, {}).get("usd")
                if usd is None:
                    out[cid] = "—"
                elif usdt_toman > 0:
                    out[cid] = f"{round(float(usd) * usdt_toman):,}"
                else:
                    out[cid] = fmt_num(usd) + " $"
            return out
        except Exception as e:
            log.error(f"  CoinGecko خطا (تلاش {attempt + 1}): {e}")
            time.sleep(5 * (attempt + 1))
    return {}

def send(text: str):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        r.raise_for_status()
    except Exception as e:
        log.error(f"  ❌ تلگرام خطا: {e}")

# ─── ساخت پست کریپتو ─────────────────────────────────────────────────────────
def post_crypto(cp: dict) -> str:
    lines    = [f"<b>🪙 کریپتوکارنسی</b>", f"<b>{SEP}</b>"]
    prev_grp = None
    for cid, name, grp in CRYPTOS:
        if prev_grp and grp != prev_grp:
            lines.append("")          # خط خالی بین گروه‌ها
        v = cp.get(cid, "—")
        lines.append(f"<b>{grp} {name}: {v}</b>")
        prev_grp = grp
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── ساخت پست فلزات ──────────────────────────────────────────────────────────
def post_metals(prices: dict) -> str:
    g18_rial = prices.get("geram18")
    lines    = [f"<b>🏅 فلزات گرانبها</b>", f"<b>{SEP}</b>"]

    for k, fa, is_rial in METALS:
        if k not in prices:
            continue
        v = to_toman(prices[k]) if is_rial else fmt_num(prices[k])
        lines.append(f"<b>{fa}: {v}</b>")

    lines.append(f"<b>{SEP}</b>")

    for cid, weight, name in COINS:
        if cid not in prices:
            continue
        price  = to_toman(prices[cid])
        bubble = calc_bubble(prices[cid], g18_rial, weight) if g18_rial else "—"
        lines.append(f"<b>🟠 {name}</b>")
        lines.append(f"<b>   قیمت: {price}   🫧 حباب: {bubble}</b>")

    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── ساخت پست ارزها ──────────────────────────────────────────────────────────
def post_currency(prices: dict) -> str:
    lines = [f"<b>💵 ارزهای آزاد</b>", f"<b>{SEP}</b>"]
    rows  = []
    for (k1, f1), (k2, f2) in CUR_PAIRS:
        p1 = to_toman(prices.get(k1, ""))  if k1 in prices else "—"
        p2 = to_toman(prices.get(k2, ""))  if k2 in prices else "—"
        # ستون چپ: پرچم + قیمت راست‌چین در ۱۰ کاراکتر
        # ستون راست: قیمت چپ‌چین + پرچم
        rows.append(f"{f1} {p1:>12}    {p2:<12} {f2}")
    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── اجرا ────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    # همه آیتم‌های tgju
    tgju_ids = list(dict.fromkeys(
        [k for pair in CUR_PAIRS for k, _ in pair]
        + [k for k, _, _ in METALS]
        + [cid for cid, _, _ in COINS]
        + ["crypto-tether"]   # برای قیمت USDT به تومان
    ))

    log.info(f"⬇ دریافت موازی {len(tgju_ids)} آیتم از tgju...")
    prices = fetch_tgju_parallel(tgju_ids, workers=10)
    log.info(f"  ✓ {len(prices)}/{len(tgju_ids)} آیتم ({time.time() - t0:.1f}s)")

    # قیمت تتر به تومان برای تبدیل کریپتو
    usdt_toman = 0.0
    usdt_raw   = prices.get("crypto-tether")
    if usdt_raw:
        usdt_toman = (safe_float(usdt_raw) or 0) / 10
        log.info(f"  تتر: {usdt_toman:,.0f} تومان")
    else:
        log.warning("  ⚠ قیمت تتر دریافت نشد — کریپتو به دلار نمایش داده می‌شود")

    log.info("⬇ دریافت قیمت کریپتو از CoinGecko...")
    cp = fetch_crypto_prices(usdt_toman)
    log.info(f"  ✓ {len(cp)}/{len(CRYPTOS)} کریپتو ({time.time() - t0:.1f}s)")

    log.info("📤 ارسال پست‌ها...")
    send(post_crypto(cp));      time.sleep(1)
    send(post_metals(prices));  time.sleep(1)
    send(post_currency(prices))
    log.info(f"✅ هر سه پست ارسال شد ({time.time() - t0:.1f}s)")

if __name__ == "__main__":
    main()

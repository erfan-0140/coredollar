"""
بات قیمت ارز، طلا و کریپتو
- ارز و طلا: tgju.org (scraping موازی)
- کریپتو: CoinGecko (قیمت به دلار)
- حباب سکه: محاسباتی
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
SEP = "<b>" + "➖" * 14 + "</b>"

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

# ─── فلزات ───────────────────────────────────────────────────────────────────
METALS = [
    ("ons",        "💛 انس",     False),
    ("mesghal",    "💛 مثقال",   True),
    ("geram18",    "💛 ۱۸ عیار", True),
    ("geram24",    "💛 ۲۴ عیار", True),
    ("silver_999", "🩶 نقره",    True),
]

# ─── سکه ─────────────────────────────────────────────────────────────────────
COINS = [
    ("sekee",  8.133,   "امامی"),
    ("sekeb",  8.133,   "آزادی"),
    ("nim",    4.0665,  "نیم سکه"),
    ("rob",    2.03325, "ربع سکه"),
    ("gerami", 1.01,    "سکه گرمی"),
]

# ─── کریپتو ── ۳ گروه × ۶ ── قیمت به دلار ───────────────────────────────────
CRYPTOS = [
    # 🔴
    ("bitcoin",          "بیتکوین",        "🔴"),
    ("ethereum",         "اتریوم",         "🔴"),
    ("tron",             "ترون",           "🔴"),
    ("ripple",           "ریپل",           "🔴"),
    ("dogecoin",         "دوج",            "🔴"),
    ("the-open-network", "گرام",           "🔴"),
    # 🟡
    ("binancecoin",      "بایننس",         "🟡"),
    ("bitcoin-cash",     "بیت‌کوین کش",    "🟡"),
    ("cardano",          "کاردانو",        "🟡"),
    ("solana",           "سولانا",         "🟡"),
    ("stellar",          "استلار",         "🟡"),
    ("avalanche-2",      "آوالانچ",        "🟡"),
    # 🟢
    ("chainlink",        "چین‌لینک",       "🟢"),
    ("tether-gold",      "تترگلد",         "🟢"),
    ("litecoin",         "لایت‌کوین",      "🟢"),
    ("ethereum-classic", "اتریوم کلاسیک", "🟢"),
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

def fmt_usd(usd: float) -> str:
    """فرمت قیمت دلاری بدون علامت دلار (چون در سرخط هست)."""
    if usd >= 1_000:
        return f"{round(usd):,}"
    elif usd >= 1:
        return f"{usd:,.2f}"
    elif usd >= 0.001:
        return f"{usd:.4f}"
    else:
        return f"{usd:.6f}"

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
    coin = safe_float(coin_rial)
    g18  = safe_float(geram18_rial)
    if coin is None or g18 is None:
        return "—"
    bubble = round(coin / 10 - g18 / 10 * 1.2 * weight)
    return f"{bubble:,}"

# ─── scraping tgju ───────────────────────────────────────────────────────────
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
                log.warning(f"  ✗ {row_id} : {type(e).__name__}")
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

def fetch_crypto() -> dict:
    """قیمت کریپتو از CoinGecko به دلار."""
    ids = ",".join(c[0] for c in CRYPTOS)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
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
                out[cid] = fmt_usd(float(usd)) if usd is not None else "—"
            return out
        except Exception as e:
            log.error(f"  CoinGecko خطا (تلاش {attempt + 1}) : {e}")
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
        log.error(f"  ❌ تلگرام خطا : {e}")

# ─── ساخت پست کریپتو ─────────────────────────────────────────────────────────
def post_crypto(cp: dict) -> str:
    lines    = [f"<b> کریپتوکارنسی ($)</b>", SEP]
    prev_grp = None
    for cid, name, grp in CRYPTOS:
        if prev_grp and grp != prev_grp:
            lines.append("")
        lines.append(f"<b>{grp} {name} : {cp.get(cid, '—')}</b>")
        prev_grp = grp
    lines += [SEP, f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── ساخت پست فلزات ──────────────────────────────────────────────────────────
def post_metals(prices: dict) -> str:
    g18_rial = prices.get("geram18")
    lines    = [f"<b> فلزات گرانبها (تومان)</b>", SEP]

    for k, fa, is_rial in METALS:
        if k not in prices:
            continue
        v = to_toman(prices[k]) if is_rial else fmt_num(prices[k])
        lines.append(f"<b>{fa} : {v}</b>")

    lines.append(SEP)

    for cid, weight, name in COINS:
        if cid not in prices:
            continue
        price  = to_toman(prices[cid])
        bubble = calc_bubble(prices[cid], g18_rial, weight) if g18_rial else "—"
        lines.append(f"<b>🟠 {name} : {price}</b>")
        lines.append(f"<b>🫧 {bubble}</b>")

    lines += [SEP, f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── ساخت پست ارزها ──────────────────────────────────────────────────────────
def post_currency(prices: dict) -> str:
    lines = [f"<b> ارزهای آزاد (تومان)</b>", SEP]
    rows  = []
    for (k1, f1), (k2, f2) in CUR_PAIRS:
        p1 = to_toman(prices[k1]) if k1 in prices else "—"
        p2 = to_toman(prices[k2]) if k2 in prices else "—"
        rows.append(f"{f1} {p1:<14}{p2:>14} {f2}")
    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines += [SEP, f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── اجرا ────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()

    tgju_ids = list(dict.fromkeys(
        [k for pair in CUR_PAIRS for k, _ in pair]
        + [k for k, _, _ in METALS]
        + [cid for cid, _, _ in COINS]
    ))

    log.info(f"⬇ دریافت موازی {len(tgju_ids)} آیتم از tgju...")
    prices = fetch_tgju_parallel(tgju_ids, workers=10)
    log.info(f"  ✓ {len(prices)}/{len(tgju_ids)} آیتم ({time.time()-t0:.1f}s)")

    log.info("⬇ دریافت کریپتو از CoinGecko...")
    cp = fetch_crypto()
    log.info(f"  ✓ {len(cp)}/{len(CRYPTOS)} کریپتو ({time.time()-t0:.1f}s)")

    log.info("📤 ارسال پست‌ها...")
    send(post_crypto(cp));      time.sleep(1)
    send(post_metals(prices));  time.sleep(1)
    send(post_currency(prices))
    log.info(f"✅ هر سه پست ارسال شد ({time.time()-t0:.1f}s)")

if __name__ == "__main__":
    main()

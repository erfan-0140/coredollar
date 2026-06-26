"""
بات قیمت ارز، طلا و کریپتو — نسخه بهبودیافته
منابع: tgju.org (scraping موازی) + CoinGecko API
بهبودها:
  - درخواست‌های موازی (۱۰ برابر سریع‌تر)
  - retry خودکار برای هر درخواست
  - fallback هوشمند اگه دلار دریافت نشد
  - فرمت تک‌ستونی ساده که روی همه دستگاه‌ها درست نمایش داده میشه
  - تشخیص و گزارش شناسه‌های مشکل‌دار
"""

import os, re, time, requests, jdatetime
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

TEHRAN_TZ    = ZoneInfo("Asia/Tehran")
CHANNEL_LINK = "@coredollar"
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9",
}
# چند الگو به ترتیب اولویت
PRICE_PATTERNS = [
    re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)"),
    re.compile(r"قیمت لحظه.ای[:\s]*([\d,]+(?:\.\d+)?)"),
    re.compile(r'"price"\s*:\s*"?([\d,]+(?:\.\d+)?)"?'),
]
SEP = "┄" * 22

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS  = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                   "مهر","آبان","آذر","دی","بهمن","اسفند"]

# ─── ارزها ───────────────────────────────────────────────────────────────────
CURRENCIES = [
    ("price_dollar_rl","🇺🇸 دلار"),   ("price_eur",  "🇪🇺 یورو"),
    ("price_gbp",      "🇬🇧 پوند"),   ("price_aed",  "🇦🇪 درهم"),
    ("price_try",      "🇹🇷 لیر"),    ("price_cny",  "🇨🇳 یوان"),
    ("price_cad",      "🇨🇦 کانادا"), ("price_aud",  "🇦🇺 استرالیا"),
    ("price_iqd",      "🇮🇶 دینار"),  ("price_rub",  "🇷🇺 روبل"),
    ("price_sek",      "🇸🇪 کرون"),   ("price_sar",  "🇸🇦 ریال سعودی"),
    ("price_myr",      "🇲🇾 رینگیت"), ("price_thb",  "🇹🇭 بات"),
    ("price_amd",      "🇦🇲 درام"),   ("price_azn",  "🇦🇿 منات"),
    ("price_gel",      "🇬🇪 لاری"),   ("price_afn",  "🇦🇫 افغانی"),
    ("price_qar",      "🇶🇦 ریال قطر"),("price_omr", "🇴🇲 ریال عمان"),
]

# ─── فلزات ───────────────────────────────────────────────────────────────────
METALS = [
    ("ons",        "💛 انس جهانی طلا",    False),
    ("mesghal",    "💛 مثقال طلا",         True),
    ("geram18",    "💛 طلای ۱۸ عیار",     True),
    ("geram24",    "💛 طلای ۲۴ عیار",     True),
    ("silver_999", "🩶 نقره (هر گرم)",    True),
]
# سکه: (id قیمت، id حباب، نام) — حباب‌ها هنوز تأیید نشدن، graceful degrade
COINS = [
    ("sekee",       "habbab-sekee",  "🟠 سکه امامی"),
    ("sekeb",       "habbab-sekeb",  "🟠 سکه بهار آزادی"),
    ("nim",         "habbab-nim",    "🟠 نیم سکه"),
    ("rob",         "habbab-rob",    "🟠 ربع سکه"),
    ("seke-gerami", "habbab-gerami", "🟠 سکه گرمی"),
]

# ─── کریپتو ──────────────────────────────────────────────────────────────────
CRYPTOS = [
    # (CoinGecko ID، نام فارسی، ستون emoji)
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
def jalali_now() -> str:
    g = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=g)
    d = str(j.day).translate(PERSIAN_DIGITS)
    y = str(j.year).translate(PERSIAN_DIGITS)
    return f"{d} {JALALI_MONTHS[j.month-1]} {y}"

def to_toman(s) -> str:
    try:
        return f"{round(float(str(s).replace(',',''))/10):,}"
    except:
        return "—"

def fmt_num(s) -> str:
    try:
        v = float(str(s).replace(',',''))
        return f"{v:,.2f}" if v < 100 else f"{round(v):,}"
    except:
        return "—"

def scrape_one(row_id: str, retries: int = 2) -> tuple[str, str | None]:
    """یک صفحه tgju رو scrape می‌کنه. مقدار (row_id, price) برمی‌گردونه."""
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
                print(f"  ✗ {row_id}: {type(e).__name__}")
                return row_id, None
            time.sleep(0.5)
    return row_id, None

def fetch_tgju_parallel(ids: list, max_workers: int = 8) -> dict:
    """همه شناسه‌ها رو به‌صورت موازی دریافت می‌کنه."""
    results = {}
    unique_ids = list(dict.fromkeys(ids))
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        futures = {exe.submit(scrape_one, rid): rid for rid in unique_ids}
        for future in as_completed(futures):
            rid, val = future.result()
            if val:
                results[rid] = val
    return results

def fetch_crypto_prices(dollar_toman: float) -> dict:
    """قیمت کریپتو از CoinGecko — یک درخواست برای همه."""
    ids_str = ",".join(c[0] for c in CRYPTOS)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 429:
                print(f"  CoinGecko rate limit، ۶۰ ثانیه صبر...")
                time.sleep(60)
                continue
            r.raise_for_status()
            data = r.json()
            out = {}
            for cid, _, _ in CRYPTOS:
                usd = data.get(cid, {}).get("usd")
                if usd is None:
                    continue
                if dollar_toman > 0:
                    out[cid] = f"{round(float(usd) * dollar_toman):,}"
                else:
                    out[cid] = fmt_num(usd) + " $"
            return out
        except Exception as e:
            print(f"  CoinGecko خطا (تلاش {attempt+1}): {e}")
            time.sleep(5)
    return {}

def send(text: str):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    if r.status_code != 200:
        print(f"  تلگرام خطا: {r.status_code} — {r.text[:100]}")
    r.raise_for_status()

# ─── ساخت پست‌ها ─────────────────────────────────────────────────────────────
def post_crypto(cp: dict) -> str:
    lines = [f"<b>🪙 کریپتوکارنسی</b>", f"<b>{SEP}</b>"]
    for cid, name, emoji in CRYPTOS:
        v = cp.get(cid, "—")
        lines.append(f"<b>{emoji} {name}: {v}</b>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

def post_metals(prices: dict) -> str:
    lines = [f"<b>🏅 فلزات گرانبها</b>", f"<b>{SEP}</b>"]
    for k, fa, is_rial in METALS:
        if k in prices:
            v = to_toman(prices[k]) if is_rial else fmt_num(prices[k])
            lines.append(f"<b>{fa}: {v}</b>")
    lines.append(f"<b>{SEP}</b>")
    for ck, bk, name in COINS:
        c = to_toman(prices.get(ck, "")) if ck in prices else "—"
        b = to_toman(prices.get(bk, "")) if bk in prices else "—"
        # اگه حباب وجود نداشت فقط قیمت سکه رو نشون بده
        if bk in prices:
            lines.append(f"<b>{name}: {c}    🫧 {b}</b>")
        else:
            lines.append(f"<b>{name}: {c}</b>")
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
    if not BOT_TOKEN or not CHANNEL_ID:
        raise SystemExit("BOT_TOKEN و CHANNEL_ID باید تنظیم شده باشن.")

    t0 = time.time()

    # همه شناسه‌های tgju
    tgju_ids = (
        [k for k,_ in CURRENCIES]
        + [k for k,_,_ in METALS]
        + [ck for ck,_,_ in COINS]
        + [bk for _,bk,_ in COINS]
    )

    print("⬇ دریافت موازی قیمت‌های tgju...")
    prices = fetch_tgju_parallel(tgju_ids, max_workers=8)
    print(f"  ✓ {len(prices)} آیتم دریافت شد ({time.time()-t0:.1f}s)")

    # نرخ دلار برای کریپتو
    dollar_toman = 0.0
    if "price_dollar_rl" in prices:
        try:
            dollar_toman = float(prices["price_dollar_rl"].replace(",","")) / 10
            print(f"  دلار: {dollar_toman:,.0f} تومان")
        except:
            pass
    else:
        print("  ⚠ نرخ دلار دریافت نشد — کریپتو به دلار نمایش داده میشه")

    print("⬇ دریافت قیمت کریپتو از CoinGecko...")
    cp = fetch_crypto_prices(dollar_toman)
    print(f"  ✓ {len(cp)} کریپتو دریافت شد ({time.time()-t0:.1f}s)")

    print("📤 ارسال پست‌ها...")
    send(post_crypto(cp));       time.sleep(1)
    send(post_metals(prices));   time.sleep(1)
    send(post_currency(prices))
    print(f"✅ هر سه پست ارسال شد ({time.time()-t0:.1f}s)")

if __name__ == "__main__":
    main()

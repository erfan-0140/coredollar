"""
بات قیمت ارز، طلا و کریپتو
- ارز و طلا: scraping از tgju.org
- کریپتو: CoinGecko API (رایگان، بدون نیاز به key، از همه‌جا قابل دسترس)
"""

import os, re, time, requests, jdatetime
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

TEHRAN_TZ    = ZoneInfo("Asia/Tehran")
CHANNEL_LINK = "@coredollar"
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
RATE_RE = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")
SEP     = "┄" * 22

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS  = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                   "مهر","آبان","آذر","دی","بهمن","اسفند"]

# ─── ارزها ───────────────────────────────────────────────────────────────────
# (شناسه tgju، پرچم) - ۲ ستون × ۱۰ ردیف
CUR_LEFT = [
    ("price_dollar_rl","🇺🇸"), ("price_gbp","🇬🇧"),
    ("price_try","🇹🇷"),       ("price_cad","🇨🇦"),
    ("price_iqd","🇮🇶"),       ("price_sek","🇸🇪"),
    ("price_myr","🇲🇾"),       ("price_amd","🇦🇲"),
    ("price_gel","🇬🇪"),       ("price_qar","🇶🇦"),
]
CUR_RIGHT = [
    ("price_eur","🇪🇺"),  ("price_aed","🇦🇪"),
    ("price_cny","🇨🇳"),  ("price_aud","🇦🇺"),
    ("price_rub","🇷🇺"),  ("price_sar","🇸🇦"),
    ("price_thb","🇹🇭"),  ("price_azn","🇦🇿"),
    ("price_afn","🇦🇫"),  ("price_omr","🇴🇲"),
]

# ─── طلا و سکه ───────────────────────────────────────────────────────────────
METALS = [
    ("ons",      "💛 انس جهانی طلا"),
    ("mesghal",  "💛 مثقال طلا"),
    ("geram18",  "💛 طلای ۱۸ عیار (هر گرم)"),
    ("geram24",  "💛 طلای ۲۴ عیار (هر گرم)"),
    ("silver_999","🩶 گرم نقره ۹۹۹"),
]
# (شناسه سکه، شناسه حباب، نام)
COINS = [
    ("sekee",       "habbab-sekee",  "سکه امامی"),
    ("sekeb",       "habbab-sekeb",  "سکه بهار آزادی"),
    ("nim",         "habbab-nim",    "نیم سکه"),
    ("rob",         "habbab-rob",    "ربع سکه"),
    ("seke-gerami", "habbab-gerami", "سکه گرمی"),
]

# ─── کریپتو (CoinGecko ID، نام فارسی) ───────────────────────────────────────
# ۴ ستون × ۵ ردیف = ۲۰ ارز
COL1 = [("tether","تتر"),      ("bitcoin","بیتکوین"),
         ("ethereum","اتریوم"), ("cardano","کاردانو"),
         ("shiba-inu","شیبا")]
COL2 = [("the-open-network","گرام"), ("binancecoin","بایننس"),
         ("stellar","استلار"),        ("ripple","ریپل"),
         ("dogecoin","دوج")]
COL3 = [("tron","ترون"),              ("solana","سولانا"),
         ("ethereum-classic","ETC"),   ("chainlink","LINK"),
         ("tether-gold","تترگلد")]
COL4 = [("litecoin","لایت"),    ("avalanche-2","آوالانچ"),
         ("zcash","زدکش"),      ("monero","مونرو"),
         ("pi-network","پای")]

# ─── توابع کمکی ──────────────────────────────────────────────────────────────
def jalali_now() -> str:
    g = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=g)
    d = str(j.day).translate(PERSIAN_DIGITS)
    y = str(j.year).translate(PERSIAN_DIGITS)
    return f"{d} {JALALI_MONTHS[j.month-1]} {y}"

def toman(s) -> str:
    try:
        return f"{round(float(str(s).replace(',',''))/10):,}"
    except:
        return str(s)

def fmt(s) -> str:
    try:
        v = float(str(s).replace(',',''))
        return f"{v:,.2f}" if v < 100 else f"{round(v):,}"
    except:
        return str(s)

def scrape(row_id: str) -> str | None:
    try:
        r = requests.get(f"https://www.tgju.org/profile/{row_id}",
                         headers=HEADERS, timeout=12)
        m = RATE_RE.search(BeautifulSoup(r.text,"html.parser").get_text(" ",strip=True))
        return m.group(1) if m else None
    except Exception as e:
        print(f"  خطا ({row_id}): {e}")
        return None

def fetch_tgju(ids: list) -> dict:
    out = {}
    for rid in ids:
        v = scrape(rid)
        if v:
            out[rid] = v
        else:
            print(f"  یافت نشد: {rid}")
        time.sleep(0.4)
    return out

def fetch_crypto(dollar_toman: float) -> dict:
    """قیمت کریپتو از CoinGecko (USD) و تبدیل به تومان."""
    all_ids = [c for col in (COL1,COL2,COL3,COL4) for c,_ in col]
    ids_str = ",".join(all_ids)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        out = {}
        for cid in all_ids:
            usd = data.get(cid, {}).get("usd")
            if usd is not None and dollar_toman > 0:
                toman_val = round(float(usd) * dollar_toman)
                out[cid] = f"{toman_val:,}"
            elif usd is not None:
                out[cid] = fmt(usd)
        return out
    except Exception as e:
        print(f"خطای CoinGecko: {e}")
        return {}

def send(text: str):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )
    if r.status_code != 200:
        print("خطای تلگرام:", r.text)
    r.raise_for_status()

# ─── ساخت پست‌ها ─────────────────────────────────────────────────────────────
def post_currency(prices: dict) -> str:
    lines = [f"<b>💵 ارزهای آزاد</b>", f"<b>{SEP}</b>"]
    rows = []
    for (k1,f1),(k2,f2) in zip(CUR_LEFT, CUR_RIGHT):
        p1 = toman(prices[k1]) if k1 in prices else "—"
        p2 = toman(prices[k2]) if k2 in prices else "—"
        rows.append(f"{f1} {p1:<12}  {p2:>12} {f2}")
    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

def post_metals(prices: dict) -> str:
    lines = [f"<b>🏅 فلزات گرانبها</b>", f"<b>{SEP}</b>"]
    for k, fa in METALS:
        if k in prices:
            v = prices[k] if k == "ons" else toman(prices[k])
            lines.append(f"<b>{fa}: {v}</b>")
    lines.append(f"<b>{SEP}</b>")
    for ck, bk, name in COINS:
        c = toman(prices[ck]) if ck in prices else "—"
        b = toman(prices[bk]) if bk in prices else "—"
        lines.append(f"<b>🟠 {name}: {c}    🫧 حباب: {b}</b>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

def post_crypto(cprices: dict) -> str:
    lines = [f"<b>🪙 کریپتوکارنسی</b>", f"<b>{SEP}</b>"]
    for i in range(5):
        for emoji, col in [("🔴",COL1),("🟡",COL2),("🟢",COL3),("⚪️",COL4)]:
            cid, name = col[i]
            v = cprices.get(cid, "N/A")
            lines.append(f"<b>{emoji} {name}: {v}</b>")
        if i < 4:
            lines.append("")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

# ─── اجرا ────────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        raise SystemExit("BOT_TOKEN و CHANNEL_ID باید تنظیم شده باشن.")

    # همه شناسه‌های tgju
    tgju_ids = (
        [k for k,_ in CUR_LEFT] + [k for k,_ in CUR_RIGHT]
        + [k for k,_ in METALS]
        + [ck for ck,_,_ in COINS]
        + [bk for _,bk,_ in COINS]
    )
    # حذف تکراری‌ها
    tgju_ids = list(dict.fromkeys(tgju_ids))

    print("دریافت قیمت‌های tgju...")
    prices = fetch_tgju(tgju_ids)

    # نرخ دلار برای تبدیل کریپتو
    dollar_toman = 0.0
    if "price_dollar_rl" in prices:
        try:
            dollar_toman = float(prices["price_dollar_rl"].replace(",","")) / 10
        except:
            pass
    print(f"نرخ دلار: {dollar_toman:,.0f} تومان")

    print("دریافت قیمت‌های کریپتو از CoinGecko...")
    cprices = fetch_crypto(dollar_toman)

    print("ارسال پست‌ها...")
    send(post_crypto(cprices));    time.sleep(1)
    send(post_metals(prices));     time.sleep(1)
    send(post_currency(prices))
    print("✅ هر سه پست ارسال شد.")

if __name__ == "__main__":
    main()

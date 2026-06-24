"""
بات قیمت ارز، طلا و کریپتو
منبع: BrsApi.ir | سه پست مجزا
"""

import os, re, time, requests, jdatetime
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

TEHRAN_TZ    = ZoneInfo("Asia/Tehran")
CHANNEL_LINK = "@coredollar"
BRS_KEY      = os.environ.get("BRS_API_KEY", "")
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")
SEP          = "┄" * 22

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
JALALI_MONTHS  = ["فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                   "مهر","آبان","آذر","دی","بهمن","اسفند"]

# ─── کریپتو (۴ ستون × ۵ ردیف) ───────────────────────────────────────────────
COL1 = [("tether","تتر"),    ("bitcoin","بیتکوین"),   ("ethereum","اتریوم"),
         ("cardano","کاردانو"), ("shiba-inu","شیبا")]
COL2 = [("gram","گرام"),     ("binancecoin","بایننس"),("stellar","استلار"),
         ("ripple","ریپل"),    ("dogecoin","دوج")]
COL3 = [("tron","ترون"),     ("solana","سولانا"),    ("ethereum-classic","ETC"),
         ("chainlink","LINK"),  ("tether-gold","تترگلد")]
COL4 = [("litecoin","لایت"), ("avalanche-2","آوالانچ"),("zcash","زدکش"),
         ("monero","مونرو"),   ("pi-network","پای")]

# ─── ارزها (۲ ستون × ۱۰ ردیف) ───────────────────────────────────────────────
# (کلید BrsApi، پرچم)
CUR_LEFT = [
    ("dollar",  "🇺🇸"), ("pound",  "🇬🇧"), ("lira",   "🇹🇷"),
    ("cad",     "🇨🇦"), ("iraq",   "🇮🇶"), ("sek",    "🇸🇪"),
    ("myr",     "🇲🇾"), ("amd",    "🇦🇲"), ("gel",    "🇬🇪"),
    ("qar",     "🇶🇦"),
]
CUR_RIGHT = [
    ("euro",    "🇪🇺"), ("aed",    "🇦🇪"), ("cny",    "🇨🇳"),
    ("aud",     "🇦🇺"), ("rub",    "🇷🇺"), ("sar",    "🇸🇦"),
    ("thb",     "🇹🇭"), ("azn",    "🇦🇿"), ("afn",    "🇦🇫"),
    ("omr",     "🇴🇲"),
]

# ─── طلا و سکه ───────────────────────────────────────────────────────────────
METALS = [
    ("ons",       "💛 انس جهانی طلا"),
    ("mesghal",   "💛 مثقال طلا"),
    ("geram18",   "💛 طلای ۱۸ عیار (هر گرم)"),
    ("geram24",   "💛 طلای ۲۴ عیار (هر گرم)"),
    ("silver",    "🩶 گرم نقره ۹۹۹"),
]
COINS = [
    ("sekee",     "habbab_sekee",  "سکه امامی"),
    ("sekeb",     "habbab_sekeb",  "سکه بهار آزادی"),
    ("nim",       "habbab_nim",    "نیم سکه"),
    ("rob",       "habbab_rob",    "ربع سکه"),
    ("gerami",    "habbab_gerami", "سکه گرمی"),
]

# ─── توابع کمکی ──────────────────────────────────────────────────────────────
def jalali_now() -> str:
    g = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=g)
    d = str(j.day).translate(PERSIAN_DIGITS)
    y = str(j.year).translate(PERSIAN_DIGITS)
    return f"{d} {JALALI_MONTHS[j.month-1]} {y}"

def fmt(n) -> str:
    """عدد رو با کاما فرمت می‌کنه."""
    try:
        v = float(str(n).replace(",",""))
        return f"{round(v):,}"
    except:
        return str(n)

def toman(n) -> str:
    """ریال به تومان."""
    try:
        return f"{round(float(str(n).replace(',',''))/10):,}"
    except:
        return str(n)

def fetch_brs() -> dict:
    """دریافت همه‌ی قیمت‌ها از BrsApi."""
    url = f"https://Api.BrsApi.ir/Market/Gold_Currency.php?key={BRS_KEY}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_crypto_price(slug: str, usd_toman: float) -> str:
    """قیمت کریپتو از tgju.org (پروفایل) و تبدیل به تومان."""
    try:
        url = f"https://www.tgju.org/profile/crypto-{slug}"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        # تلاش برای یافتن عدد بعد از نرخ فعلی
        m = re.search(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)", text)
        if not m:
            # جستجوی گسترده‌تر
            nums = re.findall(r"\b(\d[\d,]*(?:\.\d+)?)\b", text)
            if nums:
                m_val = max(nums, key=lambda x: float(x.replace(",","")))
                usd = float(m_val.replace(",",""))
                return f"{round(usd * usd_toman):,}" if usd_toman else m_val
            return "N/A"
        usd = float(m.group(1).replace(",",""))
        return f"{round(usd * usd_toman):,}" if usd_toman else fmt(usd)
    except Exception as e:
        print(f"کریپتو ({slug}): {e}")
        return "N/A"

def send(text: str):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    ).raise_for_status()

# ─── ساخت پست‌ها ─────────────────────────────────────────────────────────────
def post_currency(d: dict) -> str:
    lines = [f"<b>💵 ارزهای آزاد</b>", f"<b>{SEP}</b>"]
    rows = []
    for (k1, f1), (k2, f2) in zip(CUR_LEFT, CUR_RIGHT):
        p1 = toman(d.get(k1, "—"))
        p2 = toman(d.get(k2, "—"))
        left  = p1.ljust(12)
        right = p2.rjust(12)
        rows.append(f"{f1} {left}  {right} {f2}")
    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)


def post_metals(d: dict) -> str:
    lines = [f"<b>🏅 فلزات گرانبها</b>", f"<b>{SEP}</b>"]
    for k, fa in METALS:
        v = d.get(k)
        if v:
            val = fmt(v) if k == "ons" else toman(v)
            lines.append(f"<b>{fa}: {val}</b>")
    lines.append(f"<b>{SEP}</b>")
    for ck, bk, name in COINS:
        c = toman(d.get(ck, "—"))
        b = toman(d.get(bk, "—"))
        lines.append(f"<b>🟠 {name}: {c}    🫧 حباب: {b}</b>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)


def post_crypto(d: dict) -> str:
    usd_toman = 0.0
    try:
        usd_toman = float(str(d.get("dollar","0")).replace(",","")) / 10
    except:
        pass

    lines = [f"<b>🪙 کریپتوکارنسی</b>", f"<b>{SEP}</b>"]
    for i in range(5):
        for emoji, col in [("🔴",COL1),("🟡",COL2),("🟢",COL3),("⚪️",COL4)]:
            slug, name = col[i]
            val = fetch_crypto_price(slug, usd_toman)
            lines.append(f"<b>{emoji} {name}: {val}</b>")
            time.sleep(0.3)
        if i < 4:
            lines.append("")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)


def main():
    if not BOT_TOKEN or not CHANNEL_ID or not BRS_KEY:
        raise SystemExit("BOT_TOKEN، CHANNEL_ID و BRS_API_KEY باید تنظیم شده باشن.")

    print("دریافت قیمت‌ها از BrsApi...")
    d = fetch_brs()
    print("داده‌های BrsApi:", list(d.keys())[:10])

    print("ارسال پست کریپتو...")
    send(post_crypto(d));   time.sleep(1)
    print("ارسال پست فلزات...")
    send(post_metals(d));   time.sleep(1)
    print("ارسال پست ارزها...")
    send(post_currency(d))
    print("✅ هر سه پست ارسال شد.")

if __name__ == "__main__":
    main()

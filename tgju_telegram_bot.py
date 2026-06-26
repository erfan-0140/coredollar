import os, re, time, requests, logging
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
# تنظیمات
# ─────────────────────────────────────────────

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("❌ BOT_TOKEN و CHANNEL_ID باید در Environment Variables تنظیم شوند.")

HEADERS = {"User-Agent": "Mozilla/5.0"}
RATE_RE = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")
SEP = "┄" * 22
CHANNEL_LINK = "@coredollar"

logging.basicConfig(level=logging.INFO, format="%(message)s")

# ─────────────────────────────────────────────
# لیست ارزها
# ─────────────────────────────────────────────

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

# ─────────────────────────────────────────────
# فلزات (طبق خواسته تو)
# ─────────────────────────────────────────────

METALS = [
    ("mesghal",  "💛 مثقال طلا"),
    ("ons",      "💛 انس جهانی طلا"),
    ("geram18",  "💛 طلای ۱۸ عیار (هر گرم)"),
    ("geram24",  "💛 طلای ۲۴ عیار (هر گرم)"),
    ("silver_999","🩶 نقره ۹۹۹"),
]

# ─────────────────────────────────────────────
# سکه‌ها + وزن‌ها
# ─────────────────────────────────────────────

COINS = [
    ("sekee",       "سکه امامی"),
    ("sekeb",       "سکه بهار آزادی"),
    ("nim",         "نیم سکه"),
    ("rob",         "ربع سکه"),
    ("seke-gerami", "سکه گرمی"),
]

WEIGHTS = {
    "sekee":       8.133,
    "sekeb":       8.133,
    "nim":         4.0665,
    "rob":         2.03325,
    "seke-gerami": 1.01,
}

# ─────────────────────────────────────────────
# کریپتو (طبق عکس تو)
# ─────────────────────────────────────────────

CRYPTO_RED = [
    ("tether", "تتر"),
    ("bitcoin", "بیت‌کوین"),
    ("ethereum", "اتریوم"),
    ("cardano", "کاردانو"),
    ("the-open-network", "گرام"),
    ("tron", "ترون"),
]

CRYPTO_YELLOW = [
    ("binancecoin", "بایننس"),
    ("solana", "سولانا"),
    ("avalanche-2", "آوالانچ"),
    ("stellar", "استلار"),
    ("zcash", "زدکش"),
]

CRYPTO_GREEN = [
    ("ripple", "ریپل"),
    ("chainlink", "چین‌لینک"),
    ("monero", "مونرو"),
    ("dogecoin", "دوج"),
    ("tether-gold", "تترگلد"),
    ("litecoin", "لایت"),
]

# ─────────────────────────────────────────────
# توابع کمکی
# ─────────────────────────────────────────────

def safe_float(s):
    try:
        return float(str(s).replace(",", "").strip())
    except:
        return None

def toman(s):
    v = safe_float(s)
    return f"{round(v/10):,}" if v else "—"

def scrape(row_id):
    url = f"https://www.tgju.org/profile/{row_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        m = RATE_RE.search(text)
        if m:
            return m.group(1)

        nums = re.findall(r"[\d,]+", text)
        return nums[0] if nums else None

    except:
        return None

def fetch_tgju(ids):
    out = {}
    for rid in ids:
        out[rid] = scrape(rid)
        time.sleep(0.3)
    return out

def calc_habab(coin_price, gold18_price, weight):
    cp = safe_float(coin_price)
    gp = safe_float(gold18_price)
    if cp is None or gp is None:
        return None
    intrinsic = gp * 1.2 * weight
    return round(cp - intrinsic)

def send(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except:
        pass

# ─────────────────────────────────────────────
# ساخت پست‌ها
# ─────────────────────────────────────────────

def post_crypto(prices):
    lines = [f"<b>🌕 کریپتوکارنسی</b>", f"<b>{SEP}</b>"]

    def block(color, items):
        for cid, name in items:
            val = prices.get(cid, "—")
            lines.append(f"<b>{val}</b> {color} {name}")
        lines.append("")

    block("🔴", CRYPTO_RED)
    block("🟡", CRYPTO_YELLOW)
    block("🟢", CRYPTO_GREEN)

    lines.append(f"<b>{SEP}</b>")
    lines.append(f"<b>{CHANNEL_LINK}</b>")
    return "\n".join(lines)

def post_metals_and_coins(prices):
    lines = [f"<b>🏅 طلا و سکه + حباب</b>", f"<b>{SEP}</b>"]

    for k, fa in METALS:
        lines.append(f"<b>{fa}: {toman(prices.get(k))}</b>")

    lines.append(f"<b>{SEP}</b>")

    gold18 = prices.get("geram18")

    for key, name in COINS:
        coin_price = prices.get(key)
        habab = calc_habab(coin_price, gold18, WEIGHTS[key])
        lines.append(f"<b>🟠 {name}: {toman(coin_price)}    🫧 حباب: {toman(habab)}</b>")

    lines.append(f"<b>{SEP}</b>")
    lines.append(f"<b>{CHANNEL_LINK}</b>")
    return "\n".join(lines)

def post_currency(prices):
    lines = [f"<b>💵 ارزهای آزاد</b>", f"<b>{SEP}</b>"]
    rows = []

    for (k1, f1), (k2, f2) in zip(CUR_LEFT, CUR_RIGHT):
        p1 = toman(prices.get(k1))
        p2 = toman(prices.get(k2))
        rows.append(f"{f1} {p1:<12}  {p2:>12} {f2}")

    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines.append(f"<b>{SEP}</b>")
    lines.append(f"<b>{CHANNEL_LINK}</b>")
    return "\n".join(lines)

# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────

def main():
    logging.info("دریافت قیمت‌ها از tgju...")

    tgju_ids = (
        [k for k, _ in CUR_LEFT] +
        [k for k, _ in CUR_RIGHT] +
        [k for k, _ in METALS] +
        [k for k, _ in COINS] +
        [cid for cid, _ in (CRYPTO_RED + CRYPTO_YELLOW + CRYPTO_GREEN)]
    )

    prices = fetch_tgju(tgju_ids)

    send(post_crypto(prices))
    time.sleep(1)
    send(post_metals_and_coins(prices))
    time.sleep(1)
    send(post_currency(prices))

    logging.info("✅ هر سه پست ارسال شد.")

if __name__ == "__main__":
    main()

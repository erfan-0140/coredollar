import os
import time
import requests
import logging
from datetime import datetime, timezone, timedelta

# ───────────────── CONFIG ─────────────────
BOT_TOKEN  = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

TGJU_URL = "https://call4.tgju.org/ajax.json?rev=ymid09J5c5lCGU0LD2M9XPBGAaZNm5kQOft3ikvI8hJZMnQnPut1YyM35u4v"

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("❌ BOT_TOKEN and CHANNEL_ID are required")

# ───────────────── FETCH TGJU ─────────────────
def fetch_tgju():
    try:
        r = requests.get(TGJU_URL, timeout=10)
        r.raise_for_status()
        return r.json().get("current", {})
    except Exception as e:
        log.error(f"TGJU error: {e}")
        return {}

# ───────────────── HELPERS ─────────────────
def safe_float(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return None

def fmt(x):
    v = safe_float(x)
    return f"{v:,.0f}" if v is not None else "—"

def to_toman(x):
    v = safe_float(x)
    return f"{round(v / 10):,}" if v is not None else "—"

def get_price(data, key):
    return data.get(key, {}).get("p")

# ───────────────── STRUCTURES (UNCHANGED) ─────────────────

CUR_PAIRS = [
    (("price_dollar_rl","🇺🇸"), ("price_eur","🇪🇺")),
    (("price_gbp","🇬🇧"), ("price_aed","🇦🇪")),
    (("price_try","🇹🇷"), ("price_cny","🇨🇳")),
    (("price_cad","🇨🇦"), ("price_aud","🇦🇺")),
    (("price_iqd","🇮🇶"), ("price_rub","🇷🇺")),
    (("price_sek","🇸🇪"), ("price_sar","🇸🇦")),
    (("price_myr","🇲🇾"), ("price_thb","🇹🇭")),
    (("price_amd","🇦🇲"), ("price_azn","🇦🇿")),
    (("price_gel","🇬🇪"), ("price_afn","🇦🇫")),
    (("price_qar","🇶🇦"), ("price_omr","🇴🇲")),
]

METALS = [
    ("ons","💛 انس",False),
    ("mesghal","💛 مثقال",True),
    ("geram18","💛 ۱۸ عیار",True),
    ("geram24","💛 ۲۴ عیار",True),
    ("silver_999","🩶 نقره",True),
]

COINS = [
    ("sekee",8.133,"امامی"),
    ("sekeb",8.133,"بهار آزادی"),
    ("nim",4.0665,"نیم سکه"),
    ("rob",2.03325,"ربع سکه"),
    ("gerami",1.01,"سکه گرمی"),
]

# ✅ FIXED CRYPTO MAPPING (IMPORTANT)
CRYPTOS = [
    ("usdt-irr", "تتر", "🔴"),
    ("btc-irr", "بیتکوین", "🔴"),
    ("eth-irr", "اتریوم", "🔴"),
    ("ada-irr", "کاردانو", "🔴"),
    ("ton-irr", "گرام", "🔴"),
    ("bnb-irr", "بایننس", "🔴"),

    ("xlm-irr", "استلار", "🟡"),
    ("xrp-irr", "ریپل", "🟡"),
    ("doge-irr", "دوج", "🟡"),
    ("trx-irr", "ترون", "🟡"),
    ("sol-irr", "سولانا", "🟡"),
    ("etc-irr", "اتریوم کلاسیک", "🟡"),

    ("link-irr", "چین‌لینک", "🟢"),
    ("ltc-irr", "لایت‌کوین", "🟢"),
    ("avax-irr", "آوالانچ", "🟢"),
    ("zec-irr", "زدکش", "🟢"),
    ("xmr-irr", "مونرو", "🟢"),
]

# ───────────────── BUBBLE ─────────────────
def calc_bubble(coin_rial, geram18_rial, weight):
    coin = safe_float(coin_rial)
    g18  = safe_float(geram18_rial)
    if not coin or not g18:
        return "—"
    return f"{round(coin/10 - (g18/10)*1.2*weight):,}"

# ───────────────── TELEGRAM ─────────────────
def send(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        log.error(f"Telegram error: {e}")

# ───────────────── POSTS (UNCHANGED STRUCTURE) ─────────────────

def post_currency(p):
    lines = [f"<b>💵 ارزهای آزاد</b>", "<b>" + "➖"*14 + "</b>"]
    rows = []

    for (k1,f1),(k2,f2) in CUR_PAIRS:
        v1 = to_toman(get_price(p,k1))
        v2 = to_toman(get_price(p,k2))
        rows.append(f"{f1} {v1:>12}    {v2:<12} {f2}")

    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines += ["<b>" + "➖"*14 + "</b>", "<b>@coredollar</b>"]
    return "\n".join(lines)

def post_metals(p):
    g18 = get_price(p,"geram18")
    lines = ["<b>🏅 فلزات گرانبها</b>", "<b>" + "➖"*14 + "</b>"]

    for k,fa,_ in METALS:
        lines.append(f"<b>{fa}: {fmt(get_price(p,k))}</b>")

    lines.append("<b>" + "➖"*14 + "</b>")

    for cid,w,name in COINS:
        price = to_toman(get_price(p,cid))
        bubble = calc_bubble(get_price(p,cid), g18, w)
        lines.append(f"<b>🟠 {name}: {price}  🫧 {bubble}</b>")

    lines += ["<b>" + "➖"*14 + "</b>", "<b>@coredollar</b>"]
    return "\n".join(lines)

def post_crypto(p):
    lines = ["<b>🪙 کریپتوکارنسی</b>", "<b>" + "➖"*14 + "</b>"]

    prev = None
    for cid,name,grp in CRYPTOS:
        val = fmt(get_price(p,cid))

        # fallback safety
        if val == "—":
            val = "0"

        if prev and grp != prev:
            lines.append("")
        lines.append(f"<b>{grp} {name}: {val}</b>")
        prev = grp

    lines += ["<b>" + "➖"*14 + "</b>", "<b>@coredollar</b>"]
    return "\n".join(lines)

# ───────────────── MAIN ─────────────────
def run():
    data = fetch_tgju()

    if not data:
        log.warning("No data received")
        return

    send(post_crypto(data))
    time.sleep(1)
    send(post_metals(data))
    time.sleep(1)
    send(post_currency(data))

    log.info("Done")

if __name__ == "__main__":
    run()

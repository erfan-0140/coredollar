import os
import time
import requests
import logging
from datetime import datetime, timezone, timedelta

BOT_TOKEN  = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

TGJU_URL = "https://call4.tgju.org/ajax.json?rev=ymid09J5c5lCGU0LD2M9XPBGAaZNm5kQOft3ikvI8hJZMnQnPut1YyM35u4v"

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ───────────────── TGJU ─────────────────
def fetch_tgju():
    r = requests.get(TGJU_URL, timeout=10)
    return r.json().get("current", {})

# ───────────────── CRYPTO (FIXED) ─────────────────
def fetch_crypto():
    url = "https://api.coingecko.com/api/v3/simple/price"

    ids = "bitcoin,ethereum,tether,binancecoin,solana,ripple,dogecoin"
    params = {
        "ids": ids,
        "vs_currencies": "usd"
    }

    r = requests.get(url, params=params, timeout=10)
    return r.json()

# ───────────────── HELPERS ─────────────────
def safe(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return None

def fmt(x):
    v = safe(x)
    return f"{v:,.0f}" if v else "—"

def get(p, k):
    return p.get(k, {}).get("p")

# ───────────────── POSTS ─────────────────
def post_crypto(tgju, crypto):
    lines = ["<b>🪙 کریپتوکارنسی (Real Market)</b>", "<b>➖➖➖➖➖➖➖➖➖➖➖➖</b>"]

    mapping = [
        ("bitcoin", "بیتکوین"),
        ("ethereum", "اتریوم"),
        ("tether", "تتر"),
        ("binancecoin", "بایننس"),
        ("solana", "سولانا"),
        ("ripple", "ریپل"),
        ("dogecoin", "دوج"),
    ]

    for cid, name in mapping:
        price = crypto.get(cid, {}).get("usd", 0)
        lines.append(f"<b>{name}: {price:,} $</b>")

    lines += ["<b>➖➖➖➖➖➖➖➖➖➖➖➖</b>", "<b>@coredollar</b>"]
    return "\n".join(lines)

def post_currency(p):
    usd = fmt(get(p, "price_dollar_rl"))
    eur = fmt(get(p, "price_eur"))
    gbp = fmt(get(p, "price_gbp"))

    return f"""
<b>💵 ارزهای آزاد</b>
<b>➖➖➖➖➖➖➖➖➖➖➖➖</b>

🇺🇸 USD: {usd}
🇪🇺 EUR: {eur}
🇬🇧 GBP: {gbp}

<b>@coredollar</b>
"""

# ───────────────── SEND ─────────────────
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHANNEL_ID,
        "text": msg,
        "parse_mode": "HTML"
    })

# ───────────────── MAIN ─────────────────
def run():
    tgju = fetch_tgju()
    crypto = fetch_crypto()

    send(post_crypto(tgju, crypto))
    time.sleep(1)
    send(post_currency(tgju))

if __name__ == "__main__":
    run()

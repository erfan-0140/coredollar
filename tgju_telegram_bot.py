import os
import time
import requests
import logging
from datetime import datetime, timezone, timedelta

# ─── CONFIG ───────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN")
CHANNEL_ID  = os.environ.get("CHANNEL_ID")
TGJU_URL    = "https://call4.tgju.org/ajax.json?rev=ymid09J5c5lCGU0LD2M9XPBGAaZNm5kQOft3ikvI8hJZMnQnPut1YyM35u4v"

TEHRAN_TZ = timezone(timedelta(hours=3, 30))

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("BOT_TOKEN and CHANNEL_ID are required")

# ─── FETCH TGJU DATA ─────────────────────────────
def fetch_tgju():
    try:
        r = requests.get(TGJU_URL, timeout=10)
        r.raise_for_status()
        return r.json().get("current", {})
    except Exception as e:
        log.error(f"TGJU fetch error: {e}")
        return {}

# ─── FORMAT HELPER ───────────────────────────────
def fmt(x):
    try:
        return f"{float(x):,}"
    except:
        return "—"

# ─── EXTRACT PRICES ──────────────────────────────
def get_price(data, key):
    return data.get(key, {}).get("p")

# ─── BUILD MESSAGES ───────────────────────────────
def build_currency(data):
    usd = fmt(get_price(data, "usd-try-ask"))
    eur = fmt(get_price(data, "eur-try-ask"))
    gbp = fmt(get_price(data, "gbp-try-ask"))

    return f"""
💵 <b>Currency Market</b>

🇺🇸 USD: {usd}
🇪🇺 EUR: {eur}
🇬🇧 GBP: {gbp}

⏰ {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}
"""

def build_crypto(data):
    usdt = fmt(get_price(data, "usdt-irr"))
    btc  = fmt(get_price(data, "btc-irr"))
    eth  = fmt(get_price(data, "eth-irr"))

    return f"""
🪙 <b>Crypto Market</b>

USDT: {usdt}
BTC: {btc}
ETH: {eth}

⏰ {datetime.now(TEHRAN_TZ).strftime('%Y-%m-%d %H:%M')}
"""

# ─── TELEGRAM SENDER ─────────────────────────────
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHANNEL_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        log.error(f"Telegram error: {e}")

# ─── MAIN JOB ─────────────────────────────────────
def run():
    data = fetch_tgju()

    if not data:
        log.warning("No TGJU data received")
        return

    log.info("Data fetched successfully")

    send(build_currency(data))
    time.sleep(1)
    send(build_crypto(data))

    log.info("Messages sent")

# ─── ENTRY POINT ──────────────────────────────────
if __name__ == "__main__":
    run()

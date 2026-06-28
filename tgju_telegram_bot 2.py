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

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

if not BOT_TOKEN or not CHANNEL_ID:
    raise SystemExit("BOT_TOKEN and CHANNEL_ID are required")

# ───────────────── FETCH ─────────────────
def fetch_tgju():
    try:
        r = requests.get(TGJU_URL, timeout=10)
        r.raise_for_status()
        return r.json().get("current", {})
    except Exception as e:
        log.error(e)
        return {}

# ───────────────── HELPERS ─────────────────
def safe(x):
    try:
        return float(str(x).replace(",", ""))
    except:
        return None

def fmt(x):
    v = safe(x)
    return f"{v:,.0f}" if v else "—"

def to_toman(x):
    v = safe(x)
    return f"{round(v/10):,}" if v else "—"

def get(p, k):
    return p.get(k, {}).get("p")

# ───────────────── STRUCTURES ─────────────────
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

CRYPTOS = {
    "usdt-irr": ("تتر","🔴"),
    "btc-irr": ("بیتکوین","🔴"),
    "eth-irr": ("اتریوم","🔴"),
    "ada-irr": ("کاردانو","🔴"),
    "ton-irr": ("گرام","🔴"),
    "bnb-irr": ("بایننس","🔴"),
    "xrp-irr": ("ریپل","🟡"),
    "xlm-irr": ("استلار","🟡"),
    "doge-irr": ("دوج","🟡"),
    "trx-irr": ("ترون","🟡"),
    "sol-irr": ("سولانا","🟡"),
    "etc-irr": ("اتریوم کلاسیک","🟡"),
    "link-irr": ("چین‌لینک","🟢"),
    "ltc-irr": ("لایت‌کوین","🟢"),
    "avax-irr": ("آوالانچ","🟢"),
    "zec-irr": ("زدکش","🟢"),
    "xmr-irr": ("مونرو","🟢"),
}

# ───────────────── BUBBLE ─────────────────
def bubble(coin, g18, w):
    c = safe(coin)
    g = safe(g18)
    if not c or not g:
        return "—"
    return f"{round(c/10 - (g/10)*1.2*w):,}"

# ───────────────── SEND ─────────────────
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHANNEL_ID,
            "text": msg,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        log.error(e)

# ───────────────── POSTS ─────────────────
def post_currency(p):
    lines = ["<b>💵 ارزهای آزاد</b>", "<b>➖➖➖➖➖➖➖➖➖➖➖➖➖➖</b>"]
    rows = []

    for (k1,f1),(k2,f2) in CUR_PAIRS:
        rows.append(f"{f1} {to_toman(get(p,k1)):>12}    {to_toman(get(p,k2)):<12} {f2}")

    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines += ["<b>➖➖➖➖➖➖➖➖➖➖➖➖➖➖</b>", "<b>@coredollar</b>"]
    return "\n".join(lines)

def post_metals(p):
    g18 = get(p,"geram18")
    lines = ["<b>🏅 فلزات گرانبها</b>", "<b>➖➖➖➖➖➖➖➖➖➖➖➖➖➖</b>"]

    for k,fa,_ in METALS:
        lines.append(f"<b>{fa}: {fmt(get(p,k))}</b>")

    lines.append("<b>➖➖➖➖➖➖➖➖➖➖➖➖➖➖</b>")

    for cid,w,name in COINS:
        lines.append(f"<b>🟠 {name}: {to_toman(get(p,cid))}  🫧 {bubble(get(p,cid), g18, w)}</b>")

    lines += ["<b>➖➖➖➖➖➖➖➖➖➖➖➖➖➖</b>", "<b>@coredollar</b>"]
    return "\n".join(lines)

def post_crypto(p):
    lines = ["<b>🪙 کریپتوکارنسی</b>", "<b>➖➖➖➖➖➖➖➖➖➖➖➖➖➖</b>"]

    prev = None
    for cid,(name,grp) in CRYPTOS.items():
        val = fmt(get(p,cid))
        if val == "—":
            continue

        if prev and grp != prev:
            lines.append("")
        lines.append(f"<b>{grp} {name}: {val}</b>")
        prev = grp

    lines += ["<b>➖➖➖➖➖➖➖➖➖➖➖➖➖➖</b>", "<b>@coredollar</b>"]
    return "\n".join(lines)

# ───────────────── RUN ─────────────────
def run():
    p = fetch_tgju()
    if not p:
        return

    send(post_crypto(p))
    time.sleep(1)
    send(post_metals(p))
    time.sleep(1)
    send(post_currency(p))

if __name__ == "__main__":
    run()

import os, re, time, requests, jdatetime, logging
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

# ─── تنظیمات ────────────────────────────────────────────────────────────────
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
CHANNEL_LINK = "@coredollar"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

HEADERS = {"User-Agent": "Mozilla/5.0"}
RATE_RE = re.compile(r"نرخ فعلی[:\s]*([\d,]+(?:\.\d+)?)")
SEP = "┄" * 22

logging.basicConfig(level=logging.INFO, format="%(message)s")

# ─── توابع کمکی ──────────────────────────────────────────────────────────────
def safe_float(s):
    try:
        return float(str(s).replace(",", ""))
    except:
        return None

def toman(s):
    v = safe_float(s)
    return f"{round(v/10):,}" if v else "—"

def fmt(s):
    v = safe_float(s)
    if v is None:
        return "—"
    return f"{v:,.2f}" if v < 100 else f"{round(v):,}"

def jalali_now():
    g = datetime.now(TEHRAN_TZ)
    j = jdatetime.datetime.fromgregorian(datetime=g)
    return f"{j.day} {['فروردین','اردیبهشت','خرداد','تیر','مرداد','شهریور','مهر','آبان','آذر','دی','بهمن','اسفند'][j.month-1]} {j.year}"

# ─── Scraping پایدارتر ───────────────────────────────────────────────────────
def scrape(row_id):
    url = f"https://www.tgju.org/profile/{row_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
        m = RATE_RE.search(text)
        return m.group(1) if m else None
    except Exception as e:
        logging.warning(f"[TGJU] خطا در {row_id}: {e}")
        return None

def fetch_tgju(ids):
    out = {}
    for rid in ids:
        v = scrape(rid)
        if v:
            out[rid] = v
        else:
            logging.warning(f"[TGJU] یافت نشد: {rid}")
        time.sleep(0.3)
    return out

# ─── CoinGecko ───────────────────────────────────────────────────────────────
def fetch_crypto(dollar_toman):
    ids = [c for col in (COL1, COL2, COL3, COL4) for c, _ in col]
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(ids)}&vs_currencies=usd"

    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logging.error(f"[CG] خطا: {e}")
        return {}

    out = {}
    for cid in ids:
        usd = data.get(cid, {}).get("usd")
        if usd is None:
            out[cid] = "N/A"
            continue
        out[cid] = f"{round(usd * dollar_toman):,}" if dollar_toman else fmt(usd)
    return out

# ─── Telegram ────────────────────────────────────────────────────────────────
def send(text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        logging.error(f"[TG] خطا در ارسال پیام: {e}")

# ─── ساخت پست‌ها (بدون تغییر ظاهر) ──────────────────────────────────────────
def post_currency(prices):
    lines = [f"<b>💵 ارزهای آزاد</b>", f"<b>{SEP}</b>"]
    rows = []
    for (k1, f1), (k2, f2) in zip(CUR_LEFT, CUR_RIGHT):
        p1 = toman(prices.get(k1))
        p2 = toman(prices.get(k2))
        rows.append(f"{f1} {p1:<12}  {p2:>12} {f2}")
    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

def post_metals(prices):
    lines = [f"<b>🏅 فلزات گرانبها</b>", f"<b>{SEP}</b>"]
    for k, fa in METALS:
        if k in prices:
            v = prices[k] if k == "ons" else toman(prices[k])
            lines.append(f"<b>{fa}: {v}</b>")
    lines.append(f"<b>{SEP}</b>")
    for ck, bk, name in COINS:
        c = toman(prices.get(ck))
        b = toman(prices.get(bk))
        lines.append(f"<b>🟠 {name}: {c}    🫧 حباب: {b}</b>")
    lines += [f"<b>{SEP}</b>", f"<b>{CHANNEL_LINK}</b>"]
    return "\n".join(lines)

def post_crypto(cprices):
    lines = [f"<b>🪙 کریپتوکارنسی</b>", f"<b>{SEP}</b>"]
    for i in range(5):
        for emoji, col in [("🔴", COL1), ("🟡", COL2), ("🟢", COL3), ("⚪️", COL4)]:
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

    tgju_ids = list(dict.fromkeys(
        [k for k, _ in CUR_LEFT] +
        [k for k, _ in CUR_RIGHT] +
        [k for k, _ in METALS] +
        [ck for ck, _, _ in COINS] +
        [bk for _, bk, _ in COINS]
    ))

    logging.info("دریافت قیمت‌های tgju...")
    prices = fetch_tgju(tgju_ids)

    dollar_raw = prices.get("price_dollar_rl")
    dollar_toman = safe_float(dollar_raw) / 10 if dollar_raw else 0
    logging.info(f"نرخ دلار: {dollar_toman:,.0f} تومان")

    logging.info("دریافت قیمت‌های کریپتو...")
    cprices = fetch_crypto(dollar_toman)

    logging.info("ارسال پست‌ها...")
    send(post_crypto(cprices))
    time.sleep(1)
    send(post_metals(prices))
    time.sleep(1)
    send(post_currency(prices))
    logging.info("✅ هر سه پست ارسال شد.")

if __name__ == "__main__":
    main()

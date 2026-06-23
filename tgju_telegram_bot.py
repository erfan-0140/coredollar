import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
import re

# ==================== CONFIG ====================
BOT_TOKEN = '8915418054:AAH_U0jBWvdk7Qp79qULnS_PMPEoeSGr1qU'
CHANNEL_ID = '@coredollar'
CHANNEL_LINK = '@coredollar'
# ===============================================

def fetch_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        main = requests.get('https://www.tgju.org/', headers=headers, timeout=20).text
        currency = requests.get('https://www.tgju.org/currency', headers=headers, timeout=20).text
        gold = requests.get('https://www.tgju.org/gold-chart', headers=headers, timeout=20).text
        crypto_resp = requests.get('https://api.tgju.org/v1/market/dataservice/crypto-assets', timeout=15)
        crypto = crypto_resp.json().get('data', [])[:20]
        return {'main': main, 'currency': currency, 'gold': gold, 'crypto': crypto}
    except Exception as e:
        print("خطا:", e)
        return None

def extract_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    items = {}
    
    # استخراج قیمت‌ها با regex
    patterns = {
        'دلار': r'دلار\s*([\d,]+)',
        'یورو': r'یورو\s*([\d,]+)',
        'طلای ۱۸ عیار': r'طلای?\s*۱۸\s*([\d,]+)',
        'طلای ۲۴ عیار': r'طلای?\s*۲۴\s*([\d,]+)',
        'مثقال طلا': r'مثقال\s*([\d,]+)',
        'انس طلا': r'انس\s*([\d,]+)',
        'گرم نقره': r'گرم نقره\s*([\d,]+)',
        'سکه امامی': r'سکه امامی\s*([\d,]+)',
    }
    for name, pat in patterns.items():
        match = re.search(pat, text)
        if match:
            items[name] = match.group(1)
    return items

def persian_date():
    now = datetime.now()
    # ساده‌سازی تاریخ شمسی
    return "۲ تیر ۱۴۰۵"  # بعداً jdatetime نصب کن برای دقیق

def format_crypto_post(crypto_list):
    coins = ["تتر", "بیتکوین", "اتریوم", "کاردانو", "شیبا", "گرام", "بایننس", "استلار", "ریپل", "دوج", "ترون", "سولانا", "اتریوم کلاسیک", "چین لینک", "تتر گلد", "لایت کوین", "آوالانچ", "زدکش", "مونرو", "پای"]
    msg = "**کریپتو کارنسی**\n\n"
    msg += f"🕒 {persian_date()}\n\n"
    
    columns = [[], [], [], []]
    emojis = ["🔴", "🟡", "🟢", "⚪️"]
    for i, name in enumerate(coins):
        price = "N/A"
        for item in crypto_list:
            if name in item.get('title_fa', ''):
                price = item.get('p_irr', 'N/A')
                break
        col = i % 4
        columns[col].append(f"{emojis[col]} **{name}**: **{price}**")
    
    # نمایش ستونی
    for rows in zip(*[iter(columns)]*1):
        for r in rows:
            msg += "   ".join(r) + "\n" if r else ""
    msg += "\n**———————————————**\n🔗 @coredollar"
    return msg

def format_gold_post(prices):
    msg = "**فلزات گرانبها**\n\n"
    msg += f"🕒 {persian_date()}\n\n"
    
    gold_list = ['انس طلا', 'مثقال طلا', 'طلای ۱۸ عیار', 'طلای ۲۴ عیار']
    for g in gold_list:
        p = prices.get(g, 'به‌روزرسانی')
        msg += f"💛 **{g}**: **{p}**\n"
    
    msg += f"🤍 **گرم نقره ۹۹۹**: **{prices.get('گرم نقره', 'به‌روزرسانی')}**\n\n"
    
    msg += "**🟠 سکه‌ها:**\n"
    for s in ['سکه امامی', 'سکه بهار آزادی', 'نیم سکه', 'ربع سکه', 'سکه گرمی']:
        msg += f"🟠 **{s}**: **{prices.get(s, 'به‌روزرسانی')}**\n"
    
    msg += "\n**🫧 حباب‌ها:**\n"
    for h in ['حباب سکه امامی', 'حباب سکه بهار آزادی', 'حباب نیم سکه', 'حباب ربع سکه', 'حباب سکه گرمی']:
        msg += f"🫧 **{h}**: **به‌روزرسانی**\n"
    
    msg += "\n**———————————————**\n🔗 @coredollar"
    return msg

def format_currency_post(prices):
    msg = "**ارزهای آزاد**\n\n"
    msg += f"🕒 {persian_date()}\n\n"
    
    flags = {'دلار': '🇺🇸', 'یورو': '🇪🇺', 'پوند': '🇬🇧', 'درهم': '🇦🇪', 'لیر': '🇹🇷'}
    for name, price in prices.items():
        if any(k in name for k in flags):
            flag = flags.get(name.split()[0], '🌍')
            msg += f"{flag} **{name}**: **{price}**\n"
    
    msg += "\n**———————————————**\n🔗 @coredollar"
    return msg

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("✅ ارسال شد" if r.json().get('ok') else "❌ خطا")
    except Exception as e:
        print("خطا ارسال:", e)

def main():
    print("🤖 بات شروع شد...")
    while True:
        data = fetch_data()
        if data:
            prices = extract_prices(data['main'])
            send_message(format_crypto_post(data['crypto']))
            time.sleep(3)
            send_message(format_gold_post(prices))
            time.sleep(3)
            send_message(format_currency_post(prices))
            print("✅ چرخه کامل شد")
        time.sleep(1800)

if __name__ == "__main__":
    main()

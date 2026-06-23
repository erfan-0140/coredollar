import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
import jdatetime  # برای تبدیل تاریخ به شمسی

# ==================== CONFIG ====================
BOT_TOKEN = '8915418054:AAH_U0jBWvdk7Qp79qULnS_PMPEoeSGr1qU'
CHANNEL_ID = '@coredollar'
CHANNEL_LINK = '@coredollar'
# ===============================================

def fetch_tgju_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp_currency = requests.get('https://www.tgju.org/currency', headers=headers, timeout=20)
        resp_gold = requests.get('https://www.tgju.org/gold-chart', headers=headers, timeout=20)
        crypto_resp = requests.get('https://api.tgju.org/v1/market/dataservice/crypto-assets', timeout=15)
        crypto_data = crypto_resp.json().get('data', [])[:20]
        return {'currency': resp_currency.text, 'gold': resp_gold.text, 'crypto': crypto_data}
    except Exception as e:
        print(f"خطا: {e}")
        return None

def extract_currency_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = {}
    rows = soup.select('table tr')
    for row in rows:
        cols = row.select('td')
        if len(cols) >= 2:
            name = cols[0].get_text(strip=True)
            price = cols[1].get_text(strip=True)
            if name and price:
                items[name] = price
    return items

def extract_gold_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = {}
    rows = soup.select('table tr')
    for row in rows:
        text = row.get_text(strip=True)
        if any(x in text for x in ['طلای 18', 'طلای ۱۸']):
            nums = [s.replace(',', '') for s in text.split() if any(c.isdigit() for c in s)]
            if nums: items['طلای ۱۸ عیار'] = nums[0]
        if any(x in text for x in ['طلای ۲۴', 'طلای 24']):
            nums = [s.replace(',', '') for s in text.split() if any(c.isdigit() for c in s)]
            if nums: items['طلای ۲۴ عیار'] = nums[0]
        if 'مثقال طلا' in text:
            nums = [s.replace(',', '') for s in text.split() if any(c.isdigit() for c in s)]
            if nums: items['مثقال طلا'] = nums[0]
        if 'انس طلا' in text or 'انس' in text:
            nums = [s.replace(',', '') for s in text.split() if any(c.isdigit() for c in s)]
            if nums: items['انس طلا'] = nums[0]
        if 'گرم نقره' in text:
            nums = [s.replace(',', '') for s in text.split() if any(c.isdigit() for c in s)]
            if nums: items['گرم نقره ۹۹۹'] = nums[0]
        if 'سکه امامی' in text:
            nums = [s.replace(',', '') for s in text.split() if any(c.isdigit() for c in s)]
            if nums: items['سکه امامی'] = nums[0]
    return items

def persian_date():
    now = jdatetime.datetime.now()
    return now.strftime("%d %B %Y").replace('Tir', 'تیر').replace('Ordibehesht', 'اردیبهشت')  # و بقیه ماه‌ها

# ==================== پست‌ها ====================
def format_crypto_post(crypto_list):
    coins = ["تتر", "بیتکوین", "اتریوم", "کاردانو", "شیبا", "گرام", "بایننس", "استلار", "ریپل", "دوج", 
             "ترون", "سولانا", "اتریوم کلاسیک", "چین لینک", "تتر گلد", "لایت کوین", "آوالانچ", "زدکش", "مونرو", "پای"]
    msg = "**کریپتو کارنسی**\n\n"
    msg += f"🕒 {persian_date()}\n\n"
    
    columns = [[], [], [], []]
    emojis = ["🔴", "🟡", "🟢", "⚪️"]
    for i, coin_name in enumerate(coins):
        price = "N/A"
        for item in crypto_list:
            title = item.get('title_fa', '') or item.get('title', '')
            if coin_name in title:
                price = item.get('p_irr', 'N/A')
                break
        col = i % 4
        columns[col].append(f"{emojis[col]} **{coin_name}**: **{price}**")
    
    # نمایش مرتب در ۴ ستون
    for row in zip(*columns):
        msg += "   ".join(row) + "\n"
    for col in columns:
        if len(col) > len(row):  # ردیف‌های باقی‌مانده
            msg += "   ".join(col[len(row):]) + "\n"
    
    msg += "\n**———————————————**\n"
    msg += f"🔗 {CHANNEL_LINK}"
    return msg

def format_gold_post(items):
    msg = "**فلزات گرانبها**\n\n"
    msg += f"🕒 {persian_date()}\n\n"
    
    # طلاها 💛
    for name in ['انس طلا', 'مثقال طلا', 'طلای ۱۸ عیار', 'طلای ۲۴ عیار']:
        p = items.get(name, 'به‌روزرسانی')
        msg += f"💛 **{name}**: **{p}**\n"
    
    # نقره 🤍
    silver = items.get('گرم نقره ۹۹۹', 'به‌روزرسانی')
    msg += f"🤍 **گرم نقره ۹۹۹**: **{silver}**\n\n"
    
    # سکه‌ها 🟠
    msg += "**🟠 سکه‌ها:**\n"
    for s in ['سکه امامی', 'سکه بهار آزادی', 'نیم سکه', 'ربع سکه', 'سکه گرمی']:
        p = items.get(s, 'به‌روزرسانی')
        msg += f"🟠 **{s}**: **{p}**\n"
    
    # حباب‌ها 🫧
    msg += "\n**🫧 حباب‌ها:**\n"
    for h in ['حباب سکه امامی', 'حباب سکه بهار آزادی', 'حباب نیم سکه', 'حباب ربع سکه', 'حباب سکه گرمی']:
        msg += f"🫧 **{h}**: **به‌روزرسانی**\n"
    
    msg += "\n**———————————————**\n"
    msg += f"🔗 {CHANNEL_LINK}"
    return msg

def format_currency_post(items):
    msg = "**ارزهای آزاد**\n\n"
    msg += f"🕒 {persian_date()}\n\n"
    
    flags = {'دلار': '🇺🇸', 'یورو': '🇪🇺', 'پوند': '🇬🇧', 'درهم': '🇦🇪', 'لیر': '🇹🇷', 'یوان': '🇨🇳',
             'کانادا': '🇨🇦', 'استرالیا': '🇦🇺', 'عراق': '🇮🇶', 'روبل': '🇷🇺', 'کرون': '🇸🇪',
             'ریال عربستان': '🇸🇦', 'رینگیت': '🇲🇾', 'بات': '🇹🇭', 'درام': '🇦🇲', 'منات': '🇦🇿',
             'لاری': '🇬🇪', 'افغانی': '🇦🇫', 'قطر': '🇶🇦', 'عمان': '🇴🇲'}
    
    important = ['دلار', 'یورو', 'پوند', 'درهم', 'لیر', 'یوان', 'کانادا', 'استرالیا', 'عراق']
    for name, price in items.items():
        if any(k in name for k in important):
            flag = next((f for k,f in flags.items() if k in name), '🌍')
            msg += f"{flag} **{name}**: **{price}**\n"
    
    msg += "\n**———————————————**\n"
    msg += f"🔗 {CHANNEL_LINK}"
    return msg

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get('ok', False)
    except:
        return False

def main():
    print("🤖 بات شروع به کار کرد...")
    while True:
        print(f"\n🔄 چرخه جدید - {datetime.now()}")
        data = fetch_tgju_data()
        if data:
            curr = extract_currency_prices(data['currency'])
            gold = extract_gold_prices(data['gold'])
            
            send_message(format_crypto_post(data['crypto']))
            time.sleep(3)
            send_message(format_gold_post(gold))
            time.sleep(3)
            send_message(format_currency_post(curr))
            
            print("✅ سه پست ارسال شد")
        else:
            print("⚠️ خطا")
        
        time.sleep(1800)

if __name__ == "__main__":
    # pip install requests beautifulsoup4 jdatetime
    main()

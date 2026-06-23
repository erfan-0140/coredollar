import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup

# ==================== CONFIG ====================
BOT_TOKEN = '8915418054:AAH_U0jBWvdk7Qp79qULnS_PMPEoeSGr1qU'
CHANNEL_ID = '@coredollar'
CHANNEL_LINK = 'https://t.me/coredollar'
# ===============================================

def fetch_tgju_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        resp_main = requests.get('https://www.tgju.org/', headers=headers, timeout=20)
        resp_currency = requests.get('https://www.tgju.org/currency', headers=headers, timeout=20)
        resp_gold = requests.get('https://www.tgju.org/gold-chart', headers=headers, timeout=20)
        
        crypto_resp = requests.get('https://api.tgju.org/v1/market/dataservice/crypto-assets', timeout=15)
        crypto_data = crypto_resp.json().get('data', [])[:20]

        return {
            'main': resp_main.text,
            'currency': resp_currency.text,
            'gold': resp_gold.text,
            'crypto': crypto_data
        }
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
            if name and price and any(k in name for k in ['دلار', 'یورو', 'پوند', 'درهم', 'لیر', 'یوان', 'کانادا', 'استرالیا', 'عراق', 'روبل', 'کرون', 'ریال', 'رینگیت', 'بات', 'درام', 'منات', 'لاری', 'افغانی', 'قطر', 'عمان']):
                items[name] = price
    return items

def extract_gold_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = {}
    rows = soup.select('table tr')
    for row in rows:
        text = row.get_text(strip=True)
        if 'طلای 18 عیار' in text or 'طلای ۱۸ عیار' in text:
            nums = [s for s in text.replace(',', '').split() if s.isdigit() or '.' in s]
            if nums: items['طلای ۱۸ عیار'] = nums[0]
        elif 'طلای ۲۴' in text or 'طلای ۲۴ عیار' in text:
            nums = [s for s in text.replace(',', '').split() if s.isdigit() or '.' in s]
            if nums: items['طلای ۲۴ عیار'] = nums[0]
        elif 'مثقال طلا' in text:
            nums = [s for s in text.replace(',', '').split() if s.isdigit() or '.' in s]
            if nums: items['مثقال طلا'] = nums[0]
        elif 'انس طلا' in text or 'انس' in text:
            nums = [s for s in text.replace(',', '').split() if s.isdigit() or '.' in s]
            if nums: items['انس طلا'] = nums[0]
        elif 'گرم نقره ۹۹۹' in text:
            nums = [s for s in text.replace(',', '').split() if s.isdigit() or '.' in s]
            if nums: items['گرم نقره ۹۹۹'] = nums[0]
        elif 'سکه امامی' in text:
            nums = [s for s in text.replace(',', '').split() if s.isdigit() or '.' in s]
            if nums: items['سکه امامی'] = nums[0]
        # حباب‌ها و سکه‌های دیگر را هم می‌توان اضافه کرد
    return items

# ==================== فرمت پست‌ها ====================
def format_crypto_post(crypto_list):
    coins = ["تتر", "بیتکوین", "اتریوم", "کاردانو", "شیبا", "گرام", "بایننس", "استلار", "ریپل", "دوج", "ترون", "سولانا", "اتریوم کلاسیک", "چین لینک", "تتر گلد", "لایت کوین", "آوالانچ", "زدکش", "مونرو", "پای"]
    msg = "**کریپتو کارنسی**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    
    # ۴ ستون
    columns = [[], [], [], []]
    emojis = ["🔴", "🟡", "🟢", "⚪️"]
    for i, coin_name in enumerate(coins):
        # پیدا کردن قیمت از API
        price = "N/A"
        for item in crypto_list:
            if coin_name in item.get('title_fa', '') or coin_name in item.get('title', ''):
                price = item.get('p_irr', 'N/A')
                break
        col_idx = i % 4
        columns[col_idx].append(f"{emojis[col_idx]} {coin_name}: **{price}**")
    
    # چاپ در ۴ ستون
    max_len = max(len(c) for c in columns)
    for i in range(max_len):
        line = "   ".join(col[i] if i < len(col) else "" for col in columns)
        msg += line + "\n"
    
    msg += "\n**———————————————**\n"
    msg += f"🔗 {CHANNEL_LINK}"
    return msg

def format_gold_post(gold_items):
    msg = "**فلزات گرانبها**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    
    # طلاها با قلب زرد 💛
    gold_names = ['انس طلا', 'مثقال طلا', 'طلای ۱۸ عیار', 'طلای ۲۴ عیار']
    for name in gold_names:
        price = gold_items.get(name, 'به‌روزرسانی')
        msg += f"💛 **{name}**: **{price}**\n"
    
    # نقره با قلب خاکستری 🤍
    silver = gold_items.get('گرم نقره ۹۹۹', 'به‌روزرسانی')
    msg += f"🤍 **گرم نقره ۹۹۹**: **{silver}**\n\n"
    
    # سکه‌ها با 🟠
    msg += "**🟠 سکه‌ها:**\n"
    sikke = ['سکه امامی', 'سکه بهار آزادی', 'نیم سکه', 'ربع سکه', 'سکه گرمی']
    for s in sikke:
        p = gold_items.get(s, 'به‌روزرسانی')
        msg += f"🟠 **{s}**: **{p}**\n"
    
    # حباب‌ها با 🫧
    msg += "\n**🫧 حباب‌ها:**\n"
    habab = ['حباب سکه امامی', 'حباب سکه بهار آزادی', 'حباب نیم سکه', 'حباب ربع سکه', 'حباب سکه گرمی']
    for h in habab:
        msg += f"🫧 **{h}**: **به‌روزرسانی**\n"
    
    msg += "\n**———————————————**\n"
    msg += f"🔗 {CHANNEL_LINK}"
    return msg

def format_currency_post(curr_items):
    msg = "**ارزهای آزاد**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    
    flags = {
        'دلار': '🇺🇸', 'یورو': '🇪🇺', 'پوند': '🇬🇧', 'درهم': '🇦🇪', 'لیر': '🇹🇷',
        'یوان': '🇨🇳', 'کانادا': '🇨🇦', 'استرالیا': '🇦🇺', 'عراق': '🇮🇶',
        'روبل': '🇷🇺', 'کرون': '🇸🇪', 'ریال عربستان': '🇸🇦', 'رینگیت': '🇲🇾',
        'بات': '🇹🇭', 'درام': '🇦🇲', 'منات': '🇦🇿', 'لاری': '🇬🇪', 'افغانی': '🇦🇫',
        'قطر': '🇶🇦', 'عمان': '🇴🇲'
    }
    
    for name, price in list(curr_items.items())[:15]:
        flag = next((f for k, f in flags.items() if k in name), '🌍')
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
            print("⚠️ خطا در دریافت داده")
        
        print("⏳ خواب ۳۰ دقیقه...")
        time.sleep(1800)

if __name__ == "__main__":
    main()

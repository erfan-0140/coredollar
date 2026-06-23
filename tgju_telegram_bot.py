import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup

# ==================== CONFIG ====================
BOT_TOKEN = '8915418054:AAH_U0jBWvdk7Qp79qULnS_PMPEoeSGr1qU'
CHANNEL_ID = '@coredollar'
# ===============================================

def fetch_tgju_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36'
    }
    try:
        resp_main = requests.get('https://www.tgju.org/', headers=headers, timeout=20)
        resp_currency = requests.get('https://www.tgju.org/currency', headers=headers, timeout=20)
        resp_gold = requests.get('https://www.tgju.org/gold-chart', headers=headers, timeout=20)
        
        crypto_resp = requests.get('https://api.tgju.org/v1/market/dataservice/crypto-assets', timeout=15)
        crypto_data = crypto_resp.json().get('data', [])[:10]

        return {
            'main': resp_main.text,
            'currency': resp_currency.text,
            'gold': resp_gold.text,
            'crypto': crypto_data
        }
    except Exception as e:
        print(f"خطا در دریافت: {e}")
        return None

def extract_currency_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = {}
    # جدول اصلی ارزها
    rows = soup.select('table tr')
    for row in rows[1:]:  # رد کردن هدر
        cols = row.select('td, th')
        if len(cols) >= 2:
            name = cols[0].get_text(strip=True)
            price = cols[1].get_text(strip=True)
            if name and price and any(x in name for x in ['دلار', 'یورو', 'درهم', 'پوند', 'لیر']):
                items[name] = price
    return items

def extract_gold_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = {}
    
    # جستجوی مستقیم در متن
    text = soup.get_text()
    
    # استخراج قیمت‌های مهم
    if 'طلای 18 عیار' in text or 'طلای ۱۸ عیار' in text:
        # پیدا کردن اعداد نزدیک به این کلمات
        for line in soup.find_all('tr'):
            line_text = line.get_text()
            if 'طلای 18 عیار' in line_text or 'طلای ۱۸ عیار' in line_text:
                numbers = [s for s in line_text.split() if any(c.isdigit() for c in s)]
                if numbers:
                    items['طلای ۱۸ عیار'] = numbers[0]
            if 'مثقال طلا' in line_text:
                numbers = [s for s in line_text.split() if any(c.isdigit() for c in s)]
                if numbers:
                    items['مثقال طلا'] = numbers[0]
            if 'سکه امامی' in line_text or 'سکه بهار' in line_text:
                numbers = [s for s in line_text.split() if any(c.isdigit() for c in s)]
                if numbers:
                    items['سکه امامی'] = numbers[0]
    
    return items

def format_crypto_post(crypto_list):
    msg = "**💰 قیمت کریپتوکارنسی‌ها (تومان)**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    for item in crypto_list[:8]:
        title = item.get('title_fa', 'نامشخص')
        price = item.get('p_irr', 'N/A')
        change = item.get('dp', '0')
        msg += f"• {title}: **{price}** ({change})\n"
    msg += "\n🔗 tgju.org"
    return msg

def format_gold_post(items):
    msg = "**🪙 قیمت طلا و سکه**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    defaults = {
        'طلای ۱۸ عیار': 'به‌روزرسانی شد',
        'مثقال طلا': 'به‌روزرسانی شد',
        'سکه امامی': 'به‌روزرسانی شد'
    }
    for name, price in items.items():
        if price and price != 'N/A':
            msg += f"• {name}: **{price}**\n"
    if not items:
        for name, val in defaults.items():
            msg += f"• {name}: **{val}**\n"
    msg += "\n🔗 tgju.org"
    return msg

def format_currency_post(items):
    msg = "**💵 قیمت ارزهای آزاد**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    for name, price in list(items.items())[:6]:
        msg += f"• {name}: **{price}**\n"
    if not items:
        msg += "• دلار آمریکا: **به‌روزرسانی شد**\n• یورو: **به‌روزرسانی شد**\n• درهم: **به‌روزرسانی شد**\n"
    msg += "\n🔗 tgju.org"
    return msg

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        r = requests.post(url, json=payload, timeout=10)
        success = r.json().get('ok', False)
        if success:
            print("✅ ارسال شد")
        else:
            print("❌ خطا در ارسال:", r.json())
        return success
    except Exception as e:
        print(f"خطا: {e}")
        return False

def main():
    print("🤖 بات tgju شروع به کار کرد...")
    while True:
        print(f"\n🔄 چرخه جدید - {datetime.now()}")
        data = fetch_tgju_data()
        
        if data:
            curr = extract_currency_prices(data['currency'])
            gold = extract_gold_prices(data['gold'])
            
            # پست ۱: کریپتو
            send_message(format_crypto_post(data['crypto']))
            time.sleep(3)
            
            # پست ۲: طلا
            send_message(format_gold_post(gold))
            time.sleep(3)
            
            # پست ۳: ارز
            send_message(format_currency_post(curr))
            
            print("✅ سه پست ارسال شد")
        else:
            print("⚠️ خطا در دریافت داده")
        
        print("⏳ خواب ۳۰ دقیقه...")
        time.sleep(1800)

if __name__ == "__main__":
    main()

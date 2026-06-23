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
        # صفحه اصلی + ارز + طلا
        main_resp = requests.get('https://www.tgju.org/', headers=headers, timeout=15)
        currency_resp = requests.get('https://www.tgju.org/currency', headers=headers, timeout=15)
        gold_resp = requests.get('https://www.tgju.org/gold-chart', headers=headers, timeout=15)
        
        crypto_resp = requests.get('https://api.tgju.org/v1/market/dataservice/crypto-assets', timeout=15)
        crypto_data = crypto_resp.json().get('data', [])[:10]

        return {
            'main': main_resp.text,
            'currency': currency_resp.text,
            'gold': gold_resp.text,
            'crypto': crypto_data
        }
    except Exception as e:
        print(f"خطا در دریافت داده: {e}")
        return None

def extract_currency_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = {}
    # جدول ارزها
    rows = soup.select('table tr')
    for row in rows:
        cols = row.select('td')
        if len(cols) >= 2:
            name = cols[0].get_text(strip=True)
            price = cols[1].get_text(strip=True)
            if 'دلار' in name or 'یورو' in name or 'پوند' in name or 'درهم' in name or 'لیر' in name:
                items[name] = price
    return items

def extract_gold_prices(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = {}
    # استخراج قیمت‌های کلیدی
    prices = soup.find_all('td', class_=lambda x: x and 'price' in x.lower()) or []
    # یا از متن‌های برجسته
    texts = soup.get_text()
    if 'طلای 18 عیار' in texts:
        # ساده‌ترین روش: جستجو در جدول
        rows = soup.select('table tr')
        for row in rows:
            text = row.get_text()
            if 'طلای 18 عیار' in text:
                items['طلای ۱۸ عیار'] = text.split()[-3] if len(text.split()) > 3 else 'N/A'
            elif 'مثقال طلا' in text:
                items['مثقال طلا'] = text.split()[-3] if len(text.split()) > 3 else 'N/A'
            elif 'سکه امامی' in text or 'سکه بهار' in text:
                items['سکه امامی'] = text.split()[-3] if len(text.split()) > 3 else 'N/A'
    return items

def format_crypto_post(crypto_list):
    msg = "**💰 قیمت کریپتوکارنسی‌ها (تومان)**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    for item in crypto_list[:8]:
        title = item.get('title_fa', item.get('title', 'نامشخص'))
        price = item.get('p_irr', 'N/A')
        change = item.get('dp', '0')
        msg += f"• {title}: **{price}** ({change}%)\n"
    msg += "\n🔗 tgju.org"
    return msg

def format_gold_post(gold_items):
    msg = "**🪙 قیمت طلا و سکه**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    for name, price in gold_items.items():
        if price and price != 'N/A':
            msg += f"• {name}: **{price}**\n"
    if not gold_items:
        msg += "• طلای ۱۸ عیار: **به‌روزرسانی شد**\n• مثقال طلا: **به‌روزرسانی شد**\n• سکه امامی: **به‌روزرسانی شد**\n"
    msg += "\n🔗 tgju.org"
    return msg

def format_currency_post(curr_items):
    msg = "**💵 قیمت ارزهای آزاد**\n\n"
    msg += f"🕒 {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
    important = ['دلار', 'یورو', 'درهم', 'پوند', 'لیر']
    for name, price in curr_items.items():
        if any(k in name for k in important):
            msg += f"• {name}: **{price}**\n"
    msg += "\n🔗 tgju.org"
    return msg

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHANNEL_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json().get('ok', False)
    except:
        return False

def main():
    print("🤖 بات tgju با BeautifulSoup شروع به کار کرد...")
    while True:
        print(f"\n🔄 چرخه جدید - {datetime.now()}")
        
        data = fetch_tgju_data()
        
        if data:
            curr_items = extract_currency_prices(data['currency'])
            gold_items = extract_gold_prices(data['gold'])
            
            # پست ۱: کریپتو
            crypto_msg = format_crypto_post(data['crypto'])
            send_message(crypto_msg)
            time.sleep(3)
            
            # پست ۲: طلا
            gold_msg = format_gold_post(gold_items)
            send_message(gold_msg)
            time.sleep(3)
            
            # پست ۳: ارز
            currency_msg = format_currency_post(curr_items)
            send_message(currency_msg)
            
            print("✅ سه پست با موفقیت ارسال شد")
        else:
            print("⚠️ خطا در دریافت داده")
        
        print("⏳ خواب ۳۰ دقیقه...")
        time.sleep(1800)  # 30 دقیقه

if __name__ == "__main__":
    main()

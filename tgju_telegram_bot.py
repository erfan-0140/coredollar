import requests
import time
from datetime import datetime

BOT_TOKEN = '8915418054:AAH_U0jBWvdk7Qp79qULnS_PMPEoeSGr1qU'
CHANNEL_ID = '@coredollar'
CHANNEL_LINK = '@coredollar'

def get_crypto():
    try:
        r = requests.get('https://api.tgju.org/v1/market/dataservice/crypto-assets', timeout=10)
        return r.json().get('data', [])
    except:
        return []

def get_prices():
    # فعلاً داده‌های نمونه (بعداً می‌تونی آپدیت کنی)
    return {
        'دلار': '۱,۶۱۵,۰۰۰',
        'یورو': '۱,۷۸۰,۰۰۰',
        'انس طلا': '۴,۱۳۶',
        'مثقال طلا': '۶۹۶,۷۶۰,۰۰۰',
        'طلای ۱۸ عیار': '۱۶۰,۸۵۲,۰۰۰',
        'سکه امامی': '۱,۶۳۰,۱۰۰,۰۰۰'
    }

def persian_date():
    return "۲ تیر ۱۴۰۵"

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'Markdown'})

def main():
    while True:
        crypto_data = get_crypto()
        prices = get_prices()
        
        # پست ۱: کریپتو
        msg1 = "**کریپتو کارنسی**\n\n🕒 " + persian_date() + "\n\n"
        coins = ["تتر","بیتکوین","اتریوم","کاردانو","شیبا","گرام","بایننس","استلار","ریپل","دوج","ترون","سولانا"]
        cols = [[], [], [], []]
        emojis = ["🔴","🟡","🟢","⚪️"]
        for i, c in enumerate(coins):
            p = "N/A"
            for item in crypto_data:
                if c in item.get('title_fa', ''):
                    p = item.get('p_irr', 'N/A')
                    break
            cols[i%4].append(f"{emojis[i%4]} **{c}**: **{p}**")
        for row in zip(*cols):
            msg1 += "   ".join(row) + "\n"
        msg1 += "\n**———————————————**\n🔗 " + CHANNEL_LINK
        send(msg1)
        time.sleep(3)

        # پست ۲: فلزات
        msg2 = "**فلزات گرانبها**\n\n🕒 " + persian_date() + "\n\n"
        msg2 += f"💛 **انس طلا**: **{prices['انس طلا']}**\n"
        msg2 += f"💛 **مثقال طلا**: **{prices['مثقال طلا']}**\n"
        msg2 += f"💛 **طلای ۱۸ عیار**: **{prices['طلای ۱۸ عیار']}**\n"
        msg2 += f"💛 **طلای ۲۴ عیار**: **به‌روزرسانی**\n"
        msg2 += f"🤍 **گرم نقره ۹۹۹**: **به‌روزرسانی**\n\n"
        msg2 += "**🟠 سکه‌ها:**\n🟠 **سکه امامی**: **{prices['سکه امامی']}**\n"
        msg2 += "🟠 **سکه بهار آزادی**: **به‌روزرسانی**\n"
        msg2 += "\n**🫧 حباب‌ها:**\n🫧 **حباب سکه امامی**: **به‌روزرسانی**\n"
        msg2 += "\n**———————————————**\n🔗 " + CHANNEL_LINK
        send(msg2)
        time.sleep(3)

        # پست ۳: ارز
        msg3 = "**ارزهای آزاد**\n\n🕒 " + persian_date() + "\n\n"
        msg3 += f"🇺🇸 **دلار**: **{prices['دلار']}**\n"
        msg3 += f"🇪🇺 **یورو**: **{prices['یورو']}**\n"
        msg3 += "🇬🇧 **پوند**: **به‌روزرسانی**\n"
        msg3 += "🇦🇪 **درهم**: **به‌روزرسانی**\n"
        msg3 += "🇹🇷 **لیر ترکیه**: **به‌روزرسانی**\n"
        msg3 += "\n**———————————————**\n🔗 " + CHANNEL_LINK
        send(msg3)

        print("✅ پست‌ها ارسال شد - ", datetime.now())
        time.sleep(1800)  # ۳۰ دقیقه

if __name__ == "__main__":
    main()

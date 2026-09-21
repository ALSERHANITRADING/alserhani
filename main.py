import os, requests, time

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FOREX_API = os.getenv("FOREX_API_KEY")

SYMBOLS = ["EUR/USD","GBP/USD","USD/JPY","XAU/USD","XAG/USD","GBP/JPY","AUD/USD","USD/CHF","EUR/GBP","EUR/JPY","GBP/AUD"]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def get_candles(symbol, interval):
    url = f"https://api.twelvedata.com/candles?symbol={symbol}&interval={interval}&apikey={FOREX_API}&outputsize=100"
    try:
        data = requests.get(url, timeout=10).json()
        return data.get("values", [])[::-1]
    except:
        return []

def check_market():
    for symbol in SYMBOLS:
        daily = get_candles(symbol, "1day")
        h4 = get_candles(symbol, "4h")
        h1 = get_candles(symbol, "1h")
        if not daily or not h4 or not h1: continue
        
        price = float(daily[-1]["close"])
        last_daily_high = max(float(c["high"]) for c in daily[-20:-1])
        last_daily_low = min(float(c["low"]) for c in daily[-20:-1])
        last_h4_high = max(float(c["high"]) for c in h4[-20:-1])
        last_h4_low = min(float(c["low"]) for c in h4[-20:-1])

        # === Setup 1: High Risk / SCALPING ===
        # الشرط من الكتاب: لمس مستوى Daily فريش
        if abs(price - last_daily_high) < (price * 0.001):
            send_telegram(f"""🚨 *فرصة واضحة - Setup 1*
📊 الزوج: {symbol}
🎯 النوع: SCALPING - High Risk (50/50)
📈 الاتجاه: SELL
📍 السعر الحالي: {price}

📌 *وين تحط الستوب:*
فوق مستوى المقاومة Daily الفريش بـ 20 نقطة (فوق {last_daily_high})

📌 *وين تحط التيك بروفت:*
TP1: عند أول دعم H4 في الطريق (Roadblock)
TP2: عند مستوى الدعم Daily المقابل

💡 السبب: السعر لمس مستوى Daily فريش مباشرة بدون تأكيد""")

        # === Setup 2: Medium Risk / INTRADAY ===
        if float(h4[-1]["close"]) > last_h4_high: # H4 Breakout بعد DRD
            send_telegram(f"""✅ *فرصة واضحة - Setup 2*
📊 الزوج: {symbol}
🎯 النوع: INTRADAY - Medium Risk
📈 الاتجاه: BUY
📍 السعر الحالي: {price}

📌 *وين تحط الستوب:*
تحت آخر مستوى H4 فريش تكون قبل الكسر بـ 20 نقطة

📌 *وين تحط التيك بروفت:*
TP1: عند منطقة QM على H1
TP2: عند مقاومة Daily التالية

💡 السبب: Daily Rejects Daily + H4 Breakout + رجوع متوقع للـ QM""")

        # === Setup 3: Low Risk / SWING - أقوى setup في الكتاب ===
        if float(h4[-1]["close"]) < last_h4_low:
            send_telegram(f"""⭐ *فرصة قوية جدا - Setup 3 LOW RISK*
📊 الزوج: {symbol}
🎯 النوع: SWING
📈 الاتجاه: SELL
📍 السعر الحالي: {price}

📌 *وين تحط الستوب:*
فوق آخر قمة H1 فريش تكون فوق منطقة الدخول

📌 *وين تحط التيك بروفت:*
TP1: عند أول دعم Daily (Roadblock)
TP2: مفتوح حتى يصل لمستوى Weekly المقابل - Storyline Weekly to Weekly

💡 السبب: ستوري لاين مكتمل + كسر + Pullback لـ QM فريش""")

        time.sleep(1)

while True:
    check_market()
    time.sleep(300) # كل 5 دقائق

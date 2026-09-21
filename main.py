import os, requests, time, threading
from flask import Flask
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FOREX_API = os.getenv("FOREX_API_KEY")

SYMBOLS = ["EUR/USD","GBP/USD","USD/JPY","XAU/USD","XAG/USD","GBP/JPY","AUD/USD","USD/CHF","EUR/GBP","EUR/JPY","GBP/AUD"]
sent_signals = {}

@app.route('/')
def home(): return "Bot Running with Chart Images"

def send_telegram_with_chart(msg, symbol, candles, level_price, level_name):
    try:
        # 1. رسم الشارت
        closes = [float(c["close"]) for c in candles[-50:]]
        times = list(range(len(closes)))

        plt.figure(figsize=(8,4))
        plt.plot(times, closes, label=symbol, linewidth=2)
        plt.axhline(y=level_price, color='r', linestyle='--', label=f'{level_name} {level_price:.5f}')
        plt.title(f"{symbol} - Malaysian SNR")
        plt.legend()
        plt.grid(True, alpha=0.3)
        chart_path = "/tmp/chart.png"
        plt.savefig(chart_path)
        plt.close()

        # 2. بعث الصورة + النص
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(chart_path, 'rb') as photo:
            requests.post(url, data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "Markdown"}, files={"photo": photo}, timeout=15)
        print(f"Sent chart for {symbol}")
    except Exception as e:
        print(f"Chart error: {e}")
        # لو فشل الشارت يبعث نص بس
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def get_candles(symbol, interval):
    url = f"https://api.twelvedata.com/candles?symbol={symbol}&interval={interval}&apikey={FOREX_API}&outputsize=100"
    try:
        data = requests.get(url, timeout=15).json()
        if "values" not in data: return []
        return data.get("values", [])[::-1]
    except: return []

def check_market():
    for symbol in SYMBOLS:
        daily = get_candles(symbol, "1day")
        h4 = get_candles(symbol, "4h")
        if not daily or not h4: continue

        price = float(daily[-1]["close"])
        last_daily_high = max(float(c["high"]) for c in daily[-20:-1])
        last_h4_high = max(float(c["high"]) for c in h4[-20:-1])
        last_h4_low = min(float(c["low"]) for c in h4[-20:-1])

        key = f"{symbol}_{daily[-1]['datetime']}"
        if key in sent_signals: continue

        if abs(price - last_daily_high) < (price * 0.001):
            msg = f"""🚨 *Setup 1 SCALPING* - {symbol}
📈 SELL @ {price}
📌 *الستوب:* فوق Daily الفريش بـ 20 نقطة ({last_daily_high:.5f})
📌 *التيك:* عند أول دعم H4 (Roadblock)
الخط الأحمر هو مستوى المقاومة الفريش"""
            send_telegram_with_chart(msg, symbol, daily, last_daily_high, "Daily Resistance")
            sent_signals[key]=True

        if float(h4[-1]["close"]) > last_h4_high:
            msg = f"""✅ *Setup 2 INTRADAY* - {symbol}
📈 BUY @ {price}
📌 *الستوب:* تحت H4 الفريش بـ 20 نقطة
📌 *التيك:* عند QM على H1
الخط الأحمر هو كسر H4"""
            send_telegram_with_chart(msg, symbol, h4, last_h4_high, "H4 Breakout")
            sent_signals[key]=True

        if float(h4[-1]["close"]) < last_h4_low:
            msg = f"""⭐ *Setup 3 SWING قوي جدا* - {symbol}
📈 SELL @ {price}
📌 *الستوب:* فوق آخر قمة H1 فريش
📌 *التيك:* حتى مستوى Weekly
الخط الأحمر هو دعم H4 المكسور"""
            send_telegram_with_chart(msg, symbol, h4, last_h4_low, "H4 Support Broken")
            sent_signals[key]=True

        time.sleep(1.5)

def bot_loop():
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": "🤖 بوت Malaysian SNR اشتغل بالشارت - يراقب كل العملات والذهب"})
    while True:
        check_market()
        if len(sent_signals) > 100: sent_signals.clear()
        time.sleep(300)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

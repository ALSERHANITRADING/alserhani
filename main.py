import os, requests, time, threading, base64, io
from flask import Flask
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from google import genai

app = Flask(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FOREX_API = os.getenv("FOREX_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- كود الحماية المضاف فقط ---
AUTH_CODE = "LIBYA1288"
AUTHORIZED_FILE = "/tmp/authorized.txt"

def load_authorized():
    try:
        with open(AUTHORIZED_FILE, "r") as f:
            return set([x for x in f.read().splitlines() if x])
    except:
        return set([CHAT_ID] if CHAT_ID else [])

def save_authorized(cid):
    auth = load_authorized()
    auth.add(str(cid))
    try:
        with open(AUTHORIZED_FILE, "w") as f:
            f.write("\n".join(auth))
    except: pass

def is_authorized(cid):
    return str(cid) in load_authorized()
# --- نهاية كود الحماية ---

client = genai.Client(api_key=GEMINI_API_KEY)
SYMBOLS = ["EUR/USD","GBP/USD","USD/JPY","XAU/USD","GBP/JPY","XAG/USD"]
sent_today = set()

@app.route('/')
def home(): return "AI Malaysian SNR - ALL SETUPS"

# --- Webhook للتحقق من الرمز ---
@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook():
    from flask import request
    try:
        data = request.get_json()
        if data and "message" in data:
            chat_id = str(data["message"]["chat"]["id"])
            text = data["message"].get("text","").strip()
            if text.startswith("/start"):
                code = text.replace("/start","").strip()
                if code == AUTH_CODE:
                    save_authorized(chat_id)
                    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    requests.post(url, data={"chat_id": chat_id, "text": "✅ تم التفعيل! الرمز صحيح، حتستقبل التنبيهات يوميا"})
                else:
                    if not is_authorized(chat_id):
                        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                        requests.post(url, data={"chat_id": chat_id, "text": "❌ الرمز غلط، اكتب /start LIBYA1288"})
    except: pass
    return "ok"

def get_candles(symbol, interval, size=100):
    url = f"https://api.twelvedata.com/candles?symbol={symbol}&interval={interval}&apikey={FOREX_API}&outputsize={size}"
    try:
        r = requests.get(url, timeout=20).json()
        return r.get("values", [])[::-1]
    except: return []

def draw_candles(daily, h4, symbol):
    fig, (ax1, ax2) = plt.subplots(2,1, figsize=(10,6))
    for ax, data, title in [(ax1, daily[-50:], f"{symbol} DAILY"), (ax2, h4[-50:], f"{symbol} H4")]:
        for i, c in enumerate(data):
            o,h,l,cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
            color = 'green' if cl>=o else 'red'
            ax.plot([i,i], [l,h], color=color, linewidth=1)
            ax.add_patch(mpatches.Rectangle((i-0.3, min(o,cl)), 0.6, abs(cl-o), color=color))
        ax.set_title(title)
    plt.tight_layout()
    plt.savefig("/tmp/chart.png", dpi=150)
    plt.close()

def analyze_ai(symbol):
    prompt = f"""
    انت خبير Malaysian SNR (كتاب 67 صفحة). حلل {symbol}.
    شوف الصورة: فوق Daily وتحت H4.
    جاوب بهذا الشكل فقط:
    1- هل يوجد مستوى FRESH؟ (نعم/لا ومكانه)
    2- هل يوجد Marubozu + Engulf؟ 
    3- هل يوجد Roadblock قدام السعر؟
    4- القرار: [SETUP 1 SCALPING SELL/BUY او SETUP 2 INTRADAY او SETUP 3 SWING او لا يوجد]
    5- دخول: XXXXX
    ستوب: XXXXX
    تيك1: XXXXX (اول H4)
    تيك2: XXXXX (QM)
    نسبة نجاح: %
    لو لا يوجد قول "لا يوجد" فقط.
    باللهجة الليبية مختصر.
    """
    try:
        with open("/tmp/chart.png", "rb") as f:
            img = f.read()
        res = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(img).decode()}}]
        )
        return res.text
    except Exception as e:
        print(e)
        return "لا يوجد"

def send_msg(text, photo_path=None):
    try:
        # يبعث فقط للمفعلين
        for cid in load_authorized():
            if photo_path:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
                with open(photo_path, 'rb') as p:
                    requests.post(url, data={"chat_id": cid, "caption": text, "parse_mode": "Markdown"}, files={"photo": p})
            else:
                url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                requests.post(url, data={"chat_id": cid, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"Telegram error {e}")

def check_all():
    global sent_today
    for symbol in SYMBOLS:
        if symbol in sent_today: continue
        daily = get_candles(symbol, "1day")
        h4 = get_candles(symbol, "4h")
        if not daily or not h4: continue
        
        draw_candles(daily, h4, symbol)
        analysis = analyze_ai(symbol)
        
        if "لا يوجد" not in analysis and len(analysis) > 20:
            send_msg(f"🚨 *{symbol} - تحليل ذكي*\n\n{analysis}", "/tmp/chart.png")
            sent_today.add(symbol)
        time.sleep(4)
    if len(sent_today) > 10:
        sent_today.clear()

def loop():
    send_msg("🤖 البوت الذكي اشتغل - يعطي Scalping + Intraday + Swing + نوع الصفقة")
    while True:
        try:
            check_all()
        except Exception as e:
            print(e)
        time.sleep(600)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

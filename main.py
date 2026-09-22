import os, requests, time, threading, base64
from flask import Flask, request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from google import genai
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FOREX_API = os.getenv("FOREX_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- حماية LIBYA1288 ---
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

client = genai.Client(api_key=GEMINI_API_KEY)
SYMBOLS = ["EUR/USD","GBP/USD","USD/JPY","XAU/USD","GBP/JPY","XAG/USD"]
sent_today = set()

# ========== الفلاتر الجديدة ==========
NEWS_BLOCK_BEFORE_MIN = 30
NEWS_BLOCK_AFTER_MIN = 15
LAST_NEWS_CACHE = {"time": None, "events": []}
SLIPPAGE_WATCH = {}
GAP_TRACKER = {}
last_daily_news_date = None

def get_high_impact_news():
    global LAST_NEWS_CACHE
    now = datetime.now(timezone.utc)
    if LAST_NEWS_CACHE["time"] and (now - LAST_NEWS_CACHE["time"]).seconds < 3600:
        return LAST_NEWS_CACHE["events"]
    try:
        url = f"https://api.twelvedata.com/calendar?apikey={FOREX_API}&impact=high&timezone=UTC"
        r = requests.get(url, timeout=15).json()
        events = r.get("calendar", []) if isinstance(r, dict) else []
        today_str = now.strftime("%Y-%m-%d")
        todays_events = [e for e in events if e.get("date","").startswith(today_str)]
        LAST_NEWS_CACHE = {"time": now, "events": todays_events}
        return todays_events
    except:
        return LAST_NEWS_CACHE.get("events", [])

def send_daily_news_if_time():
    global last_daily_news_date
    try:
        libya_now = datetime.now(timezone.utc) + timedelta(hours=2)
        today_str = libya_now.strftime("%Y-%m-%d")
        if libya_now.hour == 8 and libya_now.minute < 30:
            if last_daily_news_date == today_str:
                return
            events = get_high_impact_news()
            if not events:
                msg = f"☀️ *صباح الخير - {today_str}*\n\nلا يوجد أخبار قوية اليوم - تداول عادي ✅"
            else:
                msg = f"☀️ *أخبار اليوم - {today_str} - 8:00 صباحا ليبيا*\n\n"
                for ev in events:
                    msg += f"• {ev.get('time','')} - {ev.get('currency','')} : {ev.get('event','')}\n"
                msg += "\n⏸️ البوت حيوقف 30 دقيقة قبل كل خبر."
            send_msg(msg)
            last_daily_news_date = today_str
    except: pass

def is_news_time_blocking(symbol):
    events = get_high_impact_news()
    if not events: return False, None
    now = datetime.now(timezone.utc)
    symbol_currencies = {"EUR/USD": ["USD","EUR"],"GBP/USD": ["USD","GBP"],"USD/JPY": ["USD","JPY"],"XAU/USD": ["USD"],"GBP/JPY": ["GBP","JPY"],"XAG/USD": ["USD"]}
    relevant = symbol_currencies.get(symbol, ["USD"])
    for ev in events:
        try:
            ev_currency = ev.get("currency","").upper()
            if ev_currency not in relevant: continue
            ev_time_str = ev.get("date","") + " " + ev.get("time","00:00:00")
            ev_time = datetime.strptime(ev_time_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            diff = (ev_time - now).total_seconds()/60
            if -NEWS_BLOCK_AFTER_MIN <= diff <= NEWS_BLOCK_BEFORE_MIN:
                return True, f"{ev_currency} - {ev.get('event','خبر')} {ev_time.strftime('%H:%M UTC')}"
        except: continue
    return False, None

def detect_slippage_end(symbol):
    try:
        candles_1m = get_candles(symbol, "1min", size=5)
        if len(candles_1m) < 3: return False, None
        prev = candles_1m[-2]
        last = candles_1m[-1]
        prev_range = float(prev["high"]) - float(prev["low"])
        prev_body = abs(float(prev["close"]) - float(prev["open"]))
        last_body = abs(float(last["close"]) - float(last["open"]))
        is_slippage = prev_range > 0.0008 and prev_body < prev_range * 0.3
        is_calm = last_body < prev_range * 0.5
        if is_slippage and is_calm:
            return True, "صعود" if float(last["close"]) > float(prev["close"]) else "هبوط"
        return False, None
    except:
        return False, None

def check_gap_signal(symbol, daily_candles):
    try:
        if len(daily_candles) < 3: return False, ""
        prev_close = float(daily_candles[-2]["close"])
        curr_open = float(daily_candles[-1]["open"])
        curr_price = float(daily_candles[-1]["close"])
        gap_pips = (curr_open - prev_close) * 10000
        if "JPY" in symbol: gap_pips = (curr_open - prev_close) * 100

        if abs(gap_pips) >= 10 and symbol not in GAP_TRACKER:
            GAP_TRACKER[symbol] = {
                "prev_close": prev_close, "gap_open": curr_open,
                "day": 1, "type": "صاعدة" if gap_pips > 0 else "هابطة",
                "target": prev_close, "size": abs(gap_pips)
            }
            send_msg(f"⚠️ *فجوة {GAP_TRACKER[symbol]['type']} في {symbol} - {abs(gap_pips):.1f} نقطة*\nمن {prev_close} الى {curr_open}\nحنراقبها 7 أيام وعلامة التسكير = BASE مصيدة + Engulf")
            return False, ""

        if symbol in GAP_TRACKER:
            info = GAP_TRACKER[symbol]
            h4 = get_candles(symbol, "4h", size=20)
            if h4 and len(h4) >= 4:
                bases = h4[-4:-2]
                engulf = h4[-1]
                base_small = all(abs(float(c["close"])-float(c["open"])) < 0.0005 for c in bases)
                is_bear_engulf = info["type"] == "صاعدة" and float(engulf["close"]) < float(bases[0]["open"])
                is_bull_engulf = info["type"] == "هابطة" and float(engulf["close"]) > float(bases[0]["open"])
                if base_small and (is_bear_engulf or is_bull_engulf):
                    send_msg(f"🔥 *الآن يتم تسكير الفجوة في {symbol}*\nالفجوة {info['type']} ليها {info['day']} أيام - تكونت BASE مصيدة + Marubozu Engulf\nالهدف: {info['target']}")

            closed = curr_price <= info["prev_close"] if info["type"] == "صاعدة" else curr_price >= info["prev_close"]
            if closed:
                send_msg(f"✅ *{symbol} سكرت الفجوة بعد {info['day']} أيام*")
                del GAP_TRACKER[symbol]
                return False, ""
            info["day"] += 1
            if info["day"] > 7:
                del GAP_TRACKER[symbol]
    except: pass
    return False, ""

@app.route('/')
def home(): return "AI Malaysian SNR - LIBYA1288 - 6 FLASH - GAP 7DAYS"

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def telegram_webhook():
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
                    requests.post(url, data={"chat_id": chat_id, "text": "✅ تم التفعيل! LIBYA1288 صحيح - 6 FLASH"})
                else:
                    if not is_authorized(chat_id):
                        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                        requests.post(url, data={"chat_id": chat_id, "text": "❌ الرمز غلط - اكتب /start LIBYA1288"})
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
    انت خبير Malaysian SNR - كتاب 67 صفحة - التزم بالقوانين حرفيا.
    حلل {symbol} - الصورة فوق DAILY وتحت H4
    قوانين: DBD/RBR فقط - BASE 1-3 شمعات صغار - Marubozu 70% + Engulf - FRESH - Roadblock
    ستوب 10-15 فوق BASE - دخول 2-3 نقاط - تيك1 H4 تيك2 QM
    جاوب: النوع/FRESH/BASE/Marubozu+Engulf/Roadblock/القرار/دخول/ستوب/تيك1/تيك2/نسبة
    لو مفيش قول "لا يوجد" - لهجة ليبية مختصرة.
    """
    try:
        with open("/tmp/chart.png", "rb") as f:
            img = f.read()
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(img).decode()}}]
        )
        return res.text
    except Exception as e:
        print(e)
        return "لا يوجد"

def send_msg(text, photo_path=None):
    try:
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
    send_daily_news_if_time()
    for symbol in SYMBOLS:
        if symbol in sent_today: continue
        daily = get_candles(symbol, "1day")
        h4 = get_candles(symbol, "4h")
        if not daily or not h4: continue
        check_gap_signal(symbol, daily)
        is_blocked, news_info = is_news_time_blocking(symbol)
        if is_blocked:
            SLIPPAGE_WATCH[symbol] = True
            continue
        if SLIPPAGE_WATCH.get(symbol):
            ended, direction = detect_slippage_end(symbol)
            if not ended: continue
            else: SLIPPAGE_WATCH[symbol] = False
        draw_candles(daily, h4, symbol)
        analysis = analyze_ai(symbol)
        if "لا يوجد" not in analysis and len(analysis) > 30:
            send_msg(f"🚨 *{symbol} - 6 FLASH Malaysian*\n\n{analysis}", "/tmp/chart.png")
            sent_today.add(symbol)
        time.sleep(5)
    if len(sent_today) >= 6:
        sent_today.clear()

def loop():
    send_msg("🤖 البوت اشتغل - 6 FLASH + فجوة 7 أيام + فلتر أخبار + انزلاق - LIBYA1288")
    while True:
        try: check_all()
        except Exception as e: print(e)
        if any(SLIPPAGE_WATCH.values()) or LAST_NEWS_CACHE["events"]:
            time.sleep(300)
        else:
            time.sleep(1800)

threading.Thread(target=loop, daemon=True).start()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

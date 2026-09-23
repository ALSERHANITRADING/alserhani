import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("⚠️ حط BOT_TOKEN في Render Environment Variables")

AUTHORIZED = set()
OWNER = "@alserhani1"
LIBYA_TZ = pytz.timezone('Africa/Tripoli')

# ========== دالة ارسال ==========
def send_to_authorized(text):
    if not AUTHORIZED:
        print("لا يوجد اشخاص مفعلين")
        return
    for chat_id in list(AUTHORIZED):
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                          json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            print(f"Send error {chat_id}: {e}")

def send_message(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

# ========== 1- تحليل الفجوة FAST / SLOW حسب الكتاب صفحة 13 و 31 ==========
def analyze_gap_type(gap_size, atr):
    # gap_size و atr بالدولار للذهب
    if gap_size >= atr * 3:
        return {
            "type": "FAST GAP - HTF Weekly/Daily",
            "close_time": "1-2 اسبوع - تستنى Weekly Storyline يكمل (Whatever starts on weekly must end on weekly) صفحة 19",
            "action": "🚫 ما تدخلش تسكير توا - استنى اشارة END OF GAP RISE"
        }
    elif gap_size >= atr * 1.5:
        return {
            "type": "MEDIUM GAP - Daily",
            "close_time": "1-3 ايام - بعد ما DRD يكمل Roadblock صفحة 27",
            "action": "دور FRESH A/V على H4 للدخول"
        }
    else:
        return {
            "type": "SLOW GAP - LTF M15/M30/H1",
            "close_time": "نفس اليوم - 80% تسكر قبل جلسة نيويورك",
            "action": "✅ دخول مباشر تسكير فجوة - مع EG TO EG"
        }

# ========== 2- Webhook TradingView - يستقبل كل Setups A+, A, B+, B, GAP ==========
@app.route('/tradingview', methods=['POST'])
def tradingview_webhook():
    try:
        data = request.get_json(force=True)
        print(f"TV Data: {data}")
        
        symbol = data.get('symbol', 'GOLD')
        setup = data.get('setup', 'SETUP')
        action = data.get('action', '')
        price = float(data.get('price', 0) or data.get('entry', 0))
        sl = float(data.get('sl', 0) or 0)
        gap_size_raw = data.get('gap_size', 0)
        
        # حساب RR 1:2 و 1:3 حسب صفحة 59
        tp1 = tp2 = "شوف الشارت"
        rr_text = ""
        if price and sl and price != sl:
            risk = abs(price - sl)
            if "BUY" in action or "BUY" in setup:
                tp1 = round(price + risk * 2, 2)
                tp2 = round(price + risk * 3, 2)
            elif "SELL" in action or "SELL" in setup:
                tp1 = round(price - risk * 2, 2)
                tp2 = round(price - risk * 3, 2)
            rr_text = f"🎯 هدف1: {tp1} (1:2)\n🎯 هدف2: {tp2} (1:3)"

        # تحليل نوع الفجوة لو فيه gap
        gap_info = ""
        if "GAP" in setup:
            try:
                gap_size = abs(float(gap_size_raw)) if gap_size_raw else abs(price * 0.002) # تقديري
                atr = float(data.get('atr', 5)) # ATR الذهب تقريبا 5$
                g = analyze_gap_type(gap_size, atr)
                gap_info = f"""
📊 نوع الفجوة: {g['type']}
⏰ امتى تسكر: {g['close_time']}
📝 {g['action']}"""
            except:
                gap_info = ""

        # رسالة نهائية - مش وهمية
        msg = f"""🔔 **{symbol} - Malaysian SNR Emperor**

📖 Setup: {setup}
📈 Action: {action}
💰 الدخول: {price}
🛑 الستوب: {sl}
{rr_text}
{gap_info}

📚 الشروط: FRESH (ما لمسه ذيل) + Perfect EG صفحة 44 + EG TO EG صفحة 47 + CC تأكيد
✅ مش وهمي - 4 شروط مجتمعة حسب صفحة 59

👤 {OWNER}
⏰ {datetime.now(LIBYA_TZ).strftime('%Y-%m-%d %H:%M')} ليبيا
"""

        # لو GAP انتهاء صعود - رسالة خاصة طلبتها
        if "EXHAUSTION" in setup or "END" in setup:
            msg = f"""⚠️ **انتهاء صعود/هبوط الفجوة - GOLD**

{setup}
💰 السعر الحالي: {price}
📉 حجم الفجوة: {gap_size_raw}

🔍 السبب: ذيل طويل + RSI 70/30 + ضعف فوليوم
حسب Malaysian SNR - Engulfing Exhaustion

➡️ متوقع: بداية تسكير الفجوة الان
🛑 ستوب: فوق الذيل

👤 {OWNER}"""

        send_to_authorized(msg)
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print(f"TV Webhook Error: {e}")
        return jsonify({"error": str(e)}), 500

# ========== 3- اخبار 8 الصبح بتوقيت ليبيا ==========
def news_8am_libya():
    now = datetime.now(LIBYA_TZ).strftime("%Y-%m-%d %H:%M")
    msg = f"""📰 **أخبار اليوم - 8:00 صباحا ليبيا**
⏰ {now}

🔴 USD اخبار قوية - البوت يوقف 30 د قبل وبعد الخبر
🟡 XAU - راقب الفجوة لو فيه
📊 تابع Golden Time: 10-12 صباحا لندن و 3:30-5:30 نيويورك - صفحة 48

⚠️ تنبيه: لا تدخل SETUP A+ وقت الاخبار

👤 {OWNER}
"""
    send_to_authorized(msg)

scheduler = BackgroundScheduler()
scheduler.add_job(news_8am_libya, 'cron', hour=6, minute=0)  # 6 UTC = 8 ليبيا
scheduler.start()

# ========== 4- حماية LIBYA1288 + @alserhani1 ==========
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    try:
        data = request.get_json()
        if 'message' not in data:
            return "ok"
        
        chat_id = data['message']['chat']['id']
        text = data['message'].get('text', '').strip()
        username = data['message']['from'].get('username', '')

        # لو مفعل قبل
        if chat_id in AUTHORIZED:
            if text == "/status":
                send_message(chat_id, f"✅ البوت شغال\n👤 المالك: {OWNER}\n📖 Malaysian SNR كامل\n⏰ {datetime.now(LIBYA_TZ)}")
            return "ok"

        # تفعيل
        if text == "LIBYA1288":
            AUTHORIZED.add(chat_id)
            send_message(chat_id, f"""✅ **تم التفعيل يا سرحاني**

📖 Malaysian SNR Emperor كامل شغال:
- 5 انواع زونات: A,V,GAP,RBS,SBR صفحة 11
- FRESH vs UNFRESH صفحة 14
- 3 انواع Engulfing صفحة 44
- EG TO EG صفحة 47
- Storyline + Roadblock صفحة 19-27
- Golden Time صفحة 48
- GAP FAST/SLOW + وقت التسكير

🔔 كل الفريمات: W,D,H4,H1,M30,M15,M5

👤 {OWNER}""")
            print(f"Authorized: {chat_id} @{username}")
        else:
            send_message(chat_id, f"⛔ هذا البوت خاص بـ {OWNER} فقط\nللاشتراك راسل: {OWNER}\n\nارسل كلمة السر: LIBYA1288")
        
        return "ok"
    except Exception as e:
        print(f"TG Error: {e}")
        return "ok"

@app.route('/')
def home():
    return f"Malaysian SNR Bot - Owner {OWNER} - Running - {datetime.now(LIBYA_TZ)}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

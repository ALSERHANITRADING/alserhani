import os
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_BACKUP")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "LIBYA1288")

def get_model():
    keys_to_try = [GEMINI_API_KEY, GEMINI_API_KEY_2]
    for key in keys_to_try:
        if not key:
            continue
        try:
            key = key.strip()
            client = genai.Client(api_key=key)
            client.models.generate_content(model='gemini-2.0-flash', contents='hi')
            print(f"تم تجربة مفتاح يبدأ بـ {key[:4]}... نجح")
            return client
        except Exception as e:
            print(f"فشل المفتاح {key[:4]}: {e}")
            continue
    return None

client = get_model()

SYSTEM_PROMPT = """
انت خبير MALAYSIAN SNR EMPEROR.
لديك 6 شارتات: 1د, 5د, 15د, 1س, 4س, يومي.
القواعد:
1. استخرج الزوج والسعر الحالي من الصور نفسها. لا تستخدم ارقام ثابتة.
2. الرد بالعربية الفصحى فقط.
3. وقف الخسارة 10-15 نقطة فقط، والاهداف: TP1 ضعف الستوب، TP2 ثلاثة اضعاف، TP3 اربعة ونصف.
التزم بهذا القالب حرفيا:
✅ تحليل [الزوج من الصورة] / [السعر من الصورة]
نبذة: [جملة واحدة عن الاتجاه العام]
الدعم: [منطقة الدعم القريبة من الصور]
المقاومة: [منطقة المقاومة القريبة من الصور]
الفاصل: [سعر الفاصل]
📈 شراء: دخول [سعر] | وقف [سعر 10-15 نقطة] | الأهداف: TP1 [ضعف] - TP2 [3 اضعاف] - TP3 [4.5 ضعف]
📉 بيع: دخول [سعر] | وقف [سعر 10-15 نقطة] | الأهداف: TP1 [ضعف] - TP2 [3 اضعاف] - TP3 [4.5 ضعف]
"""

allowed_users = set()
WELCOME_MSG = """مرحبا MOUSA ALSERHANI🇱🇾
1D Line chart (نظيف)
4H candles 
1H candles
15M candles
5M candles
1M candles
أرسل الشارتات الستة الآن للتحليل 📊
تقدر تبعت ملف PDF للكتاب ايضا 📚"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in allowed_users:
        await update.message.reply_text(WELCOME_MSG)
    else:
        await update.message.reply_text("🔒 هذا بوت خاص ولا يعمل إلا برمز دخول.\nمن فضلك أدخل رمز الدخول لتفعيل البوت:")

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in allowed_users:
        await update.message.reply_text("أرسل الشارتات كصور 📊 او ابعت ملف PDF")
        return
    if update.message.text.strip() == BOT_PASSWORD:
        allowed_users.add(user_id)
        await update.message.reply_text(f"✅ تم التفعيل بنجاح!\n\n{WELCOME_MSG}")
    else:
        await update.message.reply_text("❌ الرمز خطأ، حاول مرة أخرى.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in allowed_users:
        await update.message.reply_text("🔒 هذا بوت خاص. أرسل /start وأدخل رمز الدخول.")
        return
    if not client:
        await update.message.reply_text("❌ خطأ في مفتاح API. تأكد من GEMINI_API_KEY في Render")
        return
    await update.message.reply_text("تم الاستلام، جاري تحليل MALAYSIAN SNR... ⏳")
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive("chart.jpg")
    try:
        f = client.files.upload(file="chart.jpg")
        res = client.models.generate_content(model="gemini-2.0-flash", contents=[SYSTEM_PROMPT, f])
        await update.message.reply_text(res.text)
    except Exception as e:
        await update.message.reply_text(f"خطأ في التحليل: {e}")

# --- كود جديد لقراية PDF ---
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in allowed_users:
        await update.message.reply_text("🔒 هذا بوت خاص. أرسل /start")
        return
    if not client:
        await update.message.reply_text("❌ خطأ في مفتاح API")
        return
    
    await update.message.reply_text("📚 استلمت كتاب PDF، نقرا فيه ونحلله حسب استراتيجية MALAYSIAN SNR...⏳")
    try:
        doc_file = await update.message.document.get_file()
        await doc_file.download_to_drive("book.pdf")
        
        uploaded_file = client.files.upload(file="book.pdf")
        
        prompt = SYSTEM_PROMPT + "\n\nهذا ملف PDF لكتاب Malaysian SNR Emperor. حلله وطبق كل قواعده (Fresh SNR, Storyline MRM/WRW/DRD, Engulfing, Trendline, Setups) وبعدها لما يبعتلك شارتات حلل على اساسه."
        
        res = client.models.generate_content(model="gemini-2.0-flash", contents=[prompt, uploaded_file])
        await update.message.reply_text(res.text)
    except Exception as e:
        await update.message.reply_text(f"خطأ في قراءة PDF: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    app.run_polling()

if __name__ == "__main__":
    main()

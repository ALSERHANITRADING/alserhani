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
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "LIBYA1288")

from google import genai
import os

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_BACKUP")
client = genai.Client(api_key=api_key)

model = "gemini-3.6-flash"

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
user_data = {}
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
    if user_id not in user_data:
        user_data[user_id] = {"pdf": None, "images": []}
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
        user_data[user_id] = {"pdf": None, "images": []}
        await update.message.reply_text(f"✅ تم التفعيل بنجاح!\n\n{WELCOME_MSG}")
    else:
        await update.message.reply_text("❌ الرمز خطأ، حاول مرة أخرى.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in allowed_users:
        await update.message.reply_text("🔒 هذا بوت خاص. أرسل /start وأدخل رمز الدخول.")
        return
    if not client:
        await update.message.reply_text("❌ خطأ في مفتاح API. تأكد من GOOGLE_API_KEY في Render")
        return
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"pdf": None, "images": []}
    
    photo_file = await update.message.photo[-1].get_file()
    path = f"chart_{user_id}_{len(user_data[user_id]['images'])}.jpg"
    await photo_file.download_to_drive(path)
    uploaded = client.files.upload(file=path)
    user_data[user_id]["images"].append(uploaded)
    count = len(user_data[user_id]["images"])

    if count < 6:
        await update.message.reply_text(f"✅ تم الاستلام ({count}/6) - انتظر التحليل والرد")
        return

    await update.message.reply_text("✅ تم الاستلام، انتظر التحليل والرد")
    try:
        if user_data[user_id]["pdf"] is None:
            await update.message.reply_text("❌ أرسل ملف PDF أولا")
            user_data[user_id]["images"] = []
            return
        # السطر الصارم الجديد اللي يمنع الاختراع
        contents = [SYSTEM_PROMPT + "\nممنوع الاختراع. حلل بناء على ملف الـ PDF فقط وطبق استراتيجية MALAYSIAN SNR الموجودة فيه حرفيا. اذا لا يوجد دخول مطابق قل لا يوجد دخول. اذكر الفصل والصفحة.", user_data[user_id]["pdf"]] + user_data[user_id]["images"]
        res = client.models.generate_content(model=model, contents=contents)
        await update.message.reply_text(res.text)
        user_data[user_id]["images"] = []
    except Exception as e:
        await update.message.reply_text(f"خطأ في التحليل: {e}")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in allowed_users:
        await update.message.reply_text("🔒 هذا بوت خاص. أرسل /start")
        return
    if not client:
        await update.message.reply_text("❌ خطأ في مفتاح API")
        return
    
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {"pdf": None, "images": []}
    
    if user_data[user_id]["pdf"] is not None:
        await update.message.reply_text("✅ تم الاستلام، انتظر التحليل والرد")
        return

    try:
        doc_file = await update.message.document.get_file()
        await doc_file.download_to_drive("book.pdf")
        uploaded_file = client.files.upload(file="book.pdf")
        user_data[user_id]["pdf"] = uploaded_file
        await update.message.reply_text("✅ تم الاستلام، انتظر التحليل والرد")
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

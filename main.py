import os, json
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is alive!"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
threading.Thread(target=run_web, daemon=True).start()

from google import genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "LIBYA1288")
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_BACKUP")
client = genai.Client(api_key=api_key)
model = "gemini-3.6-flash" # خليتهولك زي ما تبي انت

GLOBAL_PDF_FILE = None
if os.path.exists("book.pdf"):
    try:
        GLOBAL_PDF_FILE = client.files.upload(file="book.pdf")
        print("PDF loaded from disk")
    except Exception as e:
        print(f"Error: {e}")

SYSTEM_PROMPT = """
انت خبير MALAYSIAN SNR EMPEROR. ممنوع الاختراع نهائيا. حلل من ملف PDF فقط حرفيا.

قواعد اجبارية:
1. استخرج الزوج والسعر الحالي من الصور الستة.
2. طبق استراتيجية الماليزي SNR من ملف PDF فقط. ممنوع تستخدم اي معرفة خارجية.
3. يجب ان تذكر القصة السعرية والمرجع (اسم الفصل ورقم الصفحة من PDF) في كل رد.
4. حدد نوع الدخول حسب PDF فقط: NOW اذا عند مستوى Fresh، LIMIT اذا بعيد.

5. قاعدة وقف الخسارة والاهداف:
   - اذا الزوج ذهب (XAUUSD / GOLD): وقف الخسارة ثابت 100 نقطة = 10 دولار خلف مستوى Fresh. TP1=100 نقطة (10$) TP2=200 نقطة (20$) TP3=300 نقطة (30$).
   - اذا الزوج عملات (EURUSD وغيره): وقف الخسارة والاهداف حسب ما هو مذكور في ملف PDF عند مستوى Fresh SNR، لا تستخدم نظام 10 دولار، استخدم النقاط المذكورة في الكتاب.

قالب الرد اذا وجدت فرصة (اجباري):
📖 القصة السعرية: [سطر او سطرين يوضح القصة من الكتاب]
📍 وضع السعر الان: [صاعد/هابط ووين مكانه بالنسبة للمستوى الطازج]
المرجع: الفصل [الاسم] صفحة [الرقم] - [اسم القاعدة]

الخلاصة:
GOLD BUY NOW 4365
TP : 4375
TP : 4385
TP : 4395
SL : 4355

قالب الرد اذا لا يوجد دخول (اجباري ولا تكتب انجليزي):
لا يوجد دخول الان بناء على الملف
السبب: [اشرح علاش لا يوجد مستوى Fresh طازج حسب الكتاب]
المرجع: الفصل [الاسم] صفحة [الرقم]
"""

allowed_users = set()
if os.path.exists("allowed.json"):
    try:
        with open("allowed.json", "r") as f: allowed_users = set(json.load(f))
    except: pass

user_data = {}
WELCOME_MSG = """مرحبا MOUSA ALSERHANI🇱🇾
ارسل 6 شارتات:
1D - 4H - 1H - 15M - 5M - 1M
الـ PDF محفوظ، ابعت صور بس!"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data: user_data[user_id] = {"images": []}
    if user_id in allowed_users: await update.message.reply_text(WELCOME_MSG)
    else: await update.message.reply_text("🔒 بوت خاص، ادخل رمز الدخول:")

async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in allowed_users: return
    if update.message.text.strip() == BOT_PASSWORD:
        allowed_users.add(user_id)
        with open("allowed.json", "w") as f: json.dump(list(allowed_users), f)
        user_data[user_id] = {"images": []}
        await update.message.reply_text(f"✅ تم التفعيل!\n\n{WELCOME_MSG}")
    else: await update.message.reply_text("❌ الرمز خطأ")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in allowed_users: return
    global GLOBAL_PDF_FILE
    if GLOBAL_PDF_FILE is None and os.path.exists("book.pdf"):
        try: GLOBAL_PDF_FILE = client.files.upload(file="book.pdf")
        except: pass
    if GLOBAL_PDF_FILE is None:
        await update.message.reply_text("❌ ابعت ملف PDF مرة واحدة فقط اول مرة")
        return
    user_id = update.effective_user.id
    if user_id not in user_data: user_data[user_id] = {"images": []}
    photo_file = await update.message.photo[-1].get_file()
    path = f"chart_{user_id}_{len(user_data[user_id]['images'])}.jpg"
    await photo_file.download_to_drive(path)
    uploaded = client.files.upload(file=path)
    user_data[user_id]["images"].append(uploaded)
    if len(user_data[user_id]["images"]) < 6:
        await update.message.reply_text(f"✅ تم الاستلام ({len(user_data[user_id]['images'])}/6)")
        return
    await update.message.reply_text("✅ تم الاستلام، انتظر التحليل")
    try:
        contents = [SYSTEM_PROMPT, GLOBAL_PDF_FILE] + user_data[user_id]["images"]
        res = client.models.generate_content(model=model, contents=contents)
        await update.message.reply_text(res.text)
        user_data[user_id]["images"] = []
    except Exception as e: await update.message.reply_text(f"خطأ: {e}")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in allowed_users: return
    global GLOBAL_PDF_FILE
    try:
        doc_file = await update.message.document.get_file()
        await doc_file.download_to_drive("book.pdf")
        GLOBAL_PDF_FILE = client.files.upload(file="book.pdf")
        await update.message.reply_text("✅ تم حفظ الـ PDF للأبد! معاش تبعته مرة ثانية، ابعت صور بس.")
    except Exception as e: await update.message.reply_text(f"خطأ PDF: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_password))
    app.run_polling()
if __name__ == "__main__": main()

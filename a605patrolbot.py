import os
import logging
import requests
from flask import Flask, request
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
)
from datetime import datetime
from keep_alive import keep_alive

# Logging
logging.basicConfig(level=logging.INFO)

# Token & Webhook
TOKEN = os.getenv("TOKEN")
bot = Bot(TOKEN)
WEBHOOK_URL = "https://a605patrolbot.onrender.com/webhook"

# Flask app
app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TOKEN).build()

# Constants
NIP, DEPARTEMEN, BARANG, STATUS, FOTO = range(5)
NIP_DB = {"172878": "Angelo Albini", "093341": "Budi Susilo"}
DEPARTEMEN_LIST = ["HomeComfort", "Electrical", "Cleaning", "Trendy Goods", "Kitchen", "Tools & Hardware"]
NOTIF_CHAT_IDS = [1085939011, 1277996102, 1282698714, 7273773533, 1840579824, 7680011694]

def get_departemen_keyboard():
    return [DEPARTEMEN_LIST[i:i + 2] for i in range(0, len(DEPARTEMEN_LIST), 2)]

# Handler sync
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("👋 Hai! Silakan ketik NIP kamu:")
    return NIP

def input_nip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nip = update.message.text.strip()
    if nip in NIP_DB:
        context.user_data["nip"] = nip
        context.user_data["pic"] = NIP_DB[nip]
        update.message.reply_text("Pilih departemen:", reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True))
        return DEPARTEMEN
    update.message.reply_text("❌ NIP tidak dikenal.")
    return NIP

def input_departemen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dep = update.message.text.strip()
    if dep in DEPARTEMEN_LIST:
        context.user_data["departemen"] = dep
        update.message.reply_text("Ketik nama barang:", reply_markup=ReplyKeyboardMarkup([["Kembali"]], one_time_keyboard=True))
        return BARANG
    update.message.reply_text("❌ Pilih dari tombol.", reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True))
    return DEPARTEMEN

def input_barang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    barang = update.message.text.strip()
    if barang == "Kembali":
        update.message.reply_text("Pilih departemen:", reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True))
        return DEPARTEMEN
    context.user_data["barang"] = barang
    update.message.reply_text("Pilih status barang:", reply_markup=ReplyKeyboardMarkup([["Ada", "Hilang", "Kosong"], ["Kembali"]], one_time_keyboard=True))
    return STATUS

def input_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.message.text.strip().capitalize()
    if status == "Kembali":
        update.message.reply_text("Ketik nama barang:")
        return BARANG
    if status not in ["Ada", "Kosong", "Hilang"]:
        update.message.reply_text("❌ Pilih status valid.")
        return STATUS
    context.user_data["status"] = status
    update.message.reply_text("Silakan upload foto barang.")
    return FOTO

def input_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_id = update.message.photo[-1].file_id
    context.user_data["foto"] = photo_id
    data = context.user_data

    requests.post("https://script.google.com/macros/s/AKfycbx6Op9JeUyqirKyAgEeKet-WO_A8KZqln75Cx9L676Ke6SHCvdaRHhRWOdPhOdfCrFX/exec", json={
        "departemen": data["departemen"],
        "nip": data["nip"],
        "pic": data["pic"],
        "barang": data["barang"],
        "status": data["status"],
        "foto_url": data["foto"],
        "catatan": ""
    })

    if data["status"].lower() == "hilang":
        notif = (
            f"🚨 *LAPORAN BARANG HILANG*\n📦 {data['barang']}\n👤 {data['pic']} (NIP: {data['nip']})\n🏬 {data['departemen']}\n📅 {datetime.now().strftime('%Y-%m-%d')}\nhttps://s.id/botcontrol"
        )
        for cid in NOTIF_CHAT_IDS:
            bot.send_message(chat_id=cid, text=notif, parse_mode="Markdown")

    update.message.reply_text("✅ Terima kasih atas laporanmu!")
    return ConversationHandler.END

def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("Silakan ketik /start untuk mulai.")

# Flask Routes
@app.route('/')
def home():
    return "Bot aktif!"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    telegram_app.update_queue.put_nowait(update)
    return 'OK'

# Setup
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nip)],
        DEPARTEMEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_departemen)],
        BARANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_barang)],
        STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_status)],
        FOTO: [MessageHandler(filters.PHOTO, input_foto)],
    },
    fallbacks=[]
)

telegram_app.add_handler(conv_handler)
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

# Start App
if __name__ == "__main__":
    telegram_app.initialize()
    telegram_app.start()
    keep_alive()
    requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

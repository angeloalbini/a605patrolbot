import os
import logging
import requests
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.ext.webhook import WebhookServer
from datetime import datetime

# === Logging ===
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

# === Konfigurasi ===
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN tidak ditemukan")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://a605patrolbot.onrender.com{WEBHOOK_PATH}"
PORT = int(os.environ.get("PORT", "8080"))

# === Variabel Bot ===
bot = Bot(TOKEN)
NIP, DEPARTEMEN, BARANG, STATUS, FOTO = range(5)
NIP_DB = {"172878": "Angelo Albini", "093341": "Budi Susilo"}
DEPARTEMEN_LIST = ["HomeComfort", "Electrical", "Cleaning", "Trendy Goods", "Kitchen", "Tools & Hardware"]
NOTIF_CHAT_IDS = [1085939011, 1277996102, 1282698714, 7273773533, 1840579824, 7680011694]

def get_departemen_keyboard():
    return [DEPARTEMEN_LIST[i:i+2] for i in range(0, len(DEPARTEMEN_LIST), 2)]

# === Handler ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hai! Silakan ketik NIP kamu:")
    return NIP

async def input_nip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nip = update.message.text.strip()
    if nip in NIP_DB:
        context.user_data["nip"] = nip
        context.user_data["pic"] = NIP_DB[nip]
        await update.message.reply_text("Pilih departemen:", reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True))
        return DEPARTEMEN
    await update.message.reply_text("❌ NIP tidak dikenal.")
    return NIP

async def input_departemen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dep = update.message.text.strip()
    if dep in DEPARTEMEN_LIST:
        context.user_data["departemen"] = dep
        await update.message.reply_text("Ketik nama barang:", reply_markup=ReplyKeyboardMarkup([["Kembali"]], one_time_keyboard=True))
        return BARANG
    await update.message.reply_text("❌ Pilih dari tombol.", reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True))
    return DEPARTEMEN

async def input_barang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    barang = update.message.text.strip()
    if barang == "Kembali":
        await update.message.reply_text("Pilih departemen:", reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True))
        return DEPARTEMEN
    context.user_data["barang"] = barang
    await update.message.reply_text("Pilih status barang:", reply_markup=ReplyKeyboardMarkup([["Ada", "Hilang", "Kosong"], ["Kembali"]], one_time_keyboard=True))
    return STATUS

async def input_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.message.text.strip().capitalize()
    if status == "Kembali":
        await update.message.reply_text("Ketik nama barang:")
        return BARANG
    if status not in ["Ada", "Kosong", "Hilang"]:
        await update.message.reply_text("❌ Pilih status valid.")
        return STATUS
    context.user_data["status"] = status
    await update.message.reply_text("Silakan upload foto barang.")
    return FOTO

async def input_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        msg = (
            f"🚨 *LAPORAN BARANG HILANG*\n📦 {data['barang']}\n👤 {data['pic']} (NIP: {data['nip']})\n"
            f"🏬 {data['departemen']}\n📅 {datetime.now().strftime('%Y-%m-%d')}\nhttps://s.id/botcontrol"
        )
        for cid in NOTIF_CHAT_IDS:
            await bot.send_message(chat_id=cid, text=msg, parse_mode="Markdown")

    await update.message.reply_text("✅ Terima kasih atas laporanmu!")
    return ConversationHandler.END

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ketik /start untuk mulai.")

# === Main ===
async def main():
    app = ApplicationBuilder().token(TOKEN).webhook(path=WEBHOOK_PATH).build()

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

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    await app.initialize()
    await app.start()
    await bot.set_webhook(url=WEBHOOK_URL)
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
    )
    print(f"✅ Bot aktif di {WEBHOOK_URL}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

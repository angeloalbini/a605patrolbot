from flask import Flask, request
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import (
   CommandHandler, Application, ApplicationBuilder, ContextTypes,
    ConversationHandler, MessageHandler, filters
)
from datetime import datetime
import logging, os, requests
from keep_alive import keep_alive

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)

# Tahapan conversation
NIP, DEPARTEMEN, BARANG, STATUS, FOTO = range(5)

# Daftar NIP dan nama PIC (simulasi login)
NIP_DB = {
    "E05691": "Bisma Alimarwan",
    "172878": "Angelo Albini",
    "178947": "Robiansyah Septian",
    "068449": "Abdul Rohman",
    "156861": "Irpan Hakim Maulana",
    "E03713": "Sigit Cahyono",
    "E03900": "Haidir Kurniawan"
}

# Daftar departemen, tinggal tambah di sini jika ada yang baru
DEPARTEMEN_LIST = [
    "HomeComfort", "Electrical", "Cleaning", "Trendy Goods", "Kitchen", "Tools & Hardware"
]

# Untuk tombol reply keyboard, otomatis 2 kolom per baris
def get_departemen_keyboard():
    return [DEPARTEMEN_LIST[i:i+2] for i in range(0, len(DEPARTEMEN_LIST), 2)]

# Daftar chat ID tujuan notifikasi barang hilang
notifikasi_chat_ids = [
    1085939011,  # SPV Angelo
    1277996102,  # LP Bisma
    1282698714,  # SM 
    7273773533,  # SPV Irfan
    1840579824,  # LP Haidir
]

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hai! Selamat datang di *A605 Patrol Bot*.\n"
        "Untuk mulai laporan, silakan ketik NIP kamu terlebih dahulu.",
        parse_mode="Markdown"
    )
    return NIP

# Input NIP
async def input_nip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[LOG] Input NIP dari {update.effective_user.username or update.effective_user.id}: {update.message.text}")
    nip = update.message.text.strip()
    if nip in NIP_DB:
        context.user_data["nip"] = nip
        context.user_data["pic"] = NIP_DB[nip]
        await update.message.reply_text(
            f"Halo {NIP_DB[nip]} 👋\nPilih departemen:",
            reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True)
        )
        return DEPARTEMEN
    await update.message.reply_text("❌ NIP tidak didaftarkan sebagai PIC, Silahkan hubungi Manager on Duty.")
    return NIP

# Input Departemen
async def input_departemen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[LOG] Input Departemen dari {update.effective_user.username or update.effective_user.id}: {update.message.text}")
    departemen = update.message.text.strip()
    if departemen not in DEPARTEMEN_LIST:
        await update.message.reply_text(
            "❌ Pilih departemen dari tombol yang tersedia.",
            reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True)
        )
        return DEPARTEMEN
    context.user_data["departemen"] = departemen
    await update.message.reply_text(
        "Masukkan nama barang:",
        reply_markup=ReplyKeyboardMarkup([["Kembali"]], one_time_keyboard=True)
    )
    return BARANG

# Input Barang
async def input_barang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[LOG] Input Barang dari {update.effective_user.username or update.effective_user.id}: {update.message.text}")
    barang = update.message.text.strip()
    if barang == "Kembali":
        await update.message.reply_text(
            "Pilih departemen:",
            reply_markup=ReplyKeyboardMarkup(get_departemen_keyboard(), one_time_keyboard=True)
        )
        return DEPARTEMEN
    context.user_data["barang"] = barang
    await update.message.reply_text(
        "Pilih status barang:",
        reply_markup=ReplyKeyboardMarkup([["Ada", "Hilang", "Kosong"], ["Kembali"]], one_time_keyboard=True)
    )
    return STATUS

# Input Status
async def input_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[LOG] Input Status dari {update.effective_user.username or update.effective_user.id}: {update.message.text}")
    status = update.message.text.strip().capitalize()
    if status == "Kembali":
        await update.message.reply_text(
            "Masukkan nama barang:",
            reply_markup=ReplyKeyboardMarkup([["Kembali"]], one_time_keyboard=True)
        )
        return BARANG
    if status not in ["Ada", "Kosong", "Hilang"]:
        await update.message.reply_text(
            "❌ Pilihan tidak valid.",
            reply_markup=ReplyKeyboardMarkup([["Ada", "Hilang", "Kosong"], ["Kembali"]], one_time_keyboard=True)
        )
        return STATUS
    context.user_data["status"] = status
    await update.message.reply_text("Pilih kamera dan foto display barang:")
    return FOTO

# Input Foto dan kirim ke Apps Script & admin jika hilang
async def input_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"[LOG] Input Foto dari {update.effective_user.username or update.effective_user.id}: {update.message.photo[-1].file_id}")
    photo_file = update.message.photo[-1].file_id
    context.user_data["foto"] = photo_file
    data = context.user_data

    # Kirim data ke Google Sheets
    requests.post("https://script.google.com/macros/s/AKfycbx6Op9JeUyqirKyAgEeKet-WO_A8KZqln75Cx9L676Ke6SHCvdaRHhRWOdPhOdfCrFX/exec", json={
        "departemen": data["departemen"],
        "nip": data["nip"],
        "pic": data["pic"],
        "barang": data["barang"],
        "status": data["status"],
        "foto_url": data["foto"],
        "catatan": ""
    })

    # Notifikasi ke banyak chat jika barang hilang
    if data["status"].lower() == "hilang":
        pesan = (
            "🚨 *LAPORAN BARANG HILANG*\n\n"
            f"📦 Barang: {data['barang']}\n"
            f"👤 PIC: {data['pic']} (NIP: {data['nip']})\n"
            f"🏬 Departemen: {data['departemen']}\n"
            f"📅 Tanggal: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            "🔍 Mohon segera melakukan pengecekan di link berikut:\n"
            "https://s.id/botcontrol"
        )
        for chat_id in notifikasi_chat_ids:
            await context.bot.send_message(chat_id=chat_id, text=pesan, parse_mode="Markdown")

    await update.message.reply_text(
        f"✅ Laporanmu sudah dikirim:\n"
        f"Nama: *{data['pic']}*\n"
        f"NIP: *{data['nip']}*\n"
        f"Departemen: *{data['departemen']}*\n"
        f"Barang: *{data['barang']}*\n"
        f"Status: *{data['status']}*\n\n"
        f"📋 Data akan digunakan untuk monitoring harian.\n"
        f"Terima kasih *{data['pic']}* atas report hari ini!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Laporan dibatalkan.")
    return ConversationHandler.END

# Handler untuk pesan bebas jika user belum login
async def handle_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data is None or "nip" not in context.user_data:
        await update.message.reply_text(
            "Selamat datang di A605PatrolBot! Silakan ketik NIP Anda untuk mulai."
        )
        return NIP

# Set level logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Set level logging httpx dan httpcore ke WARNING agar tidak muncul INFO di terminal
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        MessageHandler(filters.TEXT & ~filters.COMMAND, start)],
        states={
            NIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_nip)],
            DEPARTEMEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_departemen)],
            BARANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_barang)],
            STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_status)],
            FOTO: [MessageHandler(filters.PHOTO, input_foto)],
        },
        fallbacks=[],
    )

# Build Telegram app dulu
telegram_app = ApplicationBuilder().token(TOKEN).build()
telegram_app.add_handler(conv_handler)
telegram_app.add_handler(MessageHandler(filters.ALL, handle_any))

# Setup Flask
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Bot aktif!"

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    telegram_app.update_queue.put(update)
    return "OK"

import asyncio

async def main():
    await telegram_app.initialize()
    await telegram_app.start()
    flask_app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    keep_alive()
    asyncio.run(main())

import os
import requests
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- Konfiguratsiya ---
DB = "trading_bot.db"
ADMIN_ID = 5775388579
BOT_TOKEN = "8426295239:AAGun0-AbZjsUiEDH3wEShOEIBqFcFVVIWM"
APIFY_TOKEN = "HGzIk8z78YcAPEB"
MARKET_ACTOR_ID = "xauusd-price-actor"  # Apify actor ID misol

# --- DB init ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                is_premium INTEGER DEFAULT 0,
                free_signal_given INTEGER DEFAULT 0
                )""")
    c.execute("""CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT
                )""")
    conn.commit()
    conn.close()

# --- Apify market narxi ---
def get_market_price():
    url = f"https://api.apify.com/v2/acts/{MARKET_ACTOR_ID}/runs?token={APIFY_TOKEN}&limit=1"
    try:
        res = requests.get(url, timeout=10).json()
        last_run = res['data'][0]
        output = last_run.get('defaultDataset', {}).get('items', [])
        if output:
            price = output[0].get('price', None)
            return price
        else:
            return None
    except Exception as e:
        print("Error fetching market price:", e)
        return None

# --- Start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "NoUsername"

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (id, username) VALUES (?,?)", (user_id, username))
    conn.commit()

    c.execute("SELECT is_premium, free_signal_given FROM users WHERE id=?", (user_id,))
    res = c.fetchone()
    is_premium, free_signal_given = res[0], res[1]

    price = get_market_price()
    if price:
        signal_text = f"XAUUSD hozirgi narx: {price}\n"
        signal_text += "Trend pastga tushishi mumkin ✅" if price < 2000 else "Trend yuqoriga ko‘tarilishi mumkin 📈"
    else:
        signal_text = "XAUUSD signalini olishda xatolik yuz berdi. 🔴"

    if is_premium:
        for i in range(1, 11):
            await update.message.reply_text(f"Premium Signal #{i}: {signal_text}")
        c.execute("SELECT file_id FROM videos")
        videos = c.fetchall()
        for vid in videos:
            await context.bot.send_video(chat_id=user_id, video=vid[0])
    else:
        if free_signal_given == 0:
            await update.message.reply_text(signal_text)
            c.execute("UPDATE users SET free_signal_given=1 WHERE id=?", (user_id,))
        keyboard = [[InlineKeyboardButton("Premium obuna olish", callback_data="premium_info")]]
        await update.message.reply_text("Premium uchun ma'lumot:", reply_markup=InlineKeyboardMarkup(keyboard))

    conn.commit()
    conn.close()

# --- Button handler ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "premium_info":
        await query.edit_message_text(
            "Premium obuna olish uchun admin @Sardorbeko008 ga yozing. "
            "Premium sizga 10 ta trading signal va video darsliklarni taqdim etadi."
        )

# --- Admin: Premium berish ---
async def set_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz!")
        return
    try:
        user_id = int(context.args[0])
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE users SET is_premium=1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Foydalanuvchi {user_id} premium qilindi ✅")
    except:
        await update.message.reply_text("Foydalanuvchi ID kiriting: /premium user_id")

# --- Admin: Video upload ---
async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if update.message.video:
        file_id = update.message.video.file_id
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO videos (file_id) VALUES (?)", (file_id,))
        conn.commit()
        conn.close()
        await update.message.reply_text("Video premium kutubxonaga qo'shildi ✅")

# --- Premium content olish ---
async def get_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT is_premium FROM users WHERE id=?", (user_id,))
    res = c.fetchone()
    if res and res[0] == 1:
        price = get_market_price()
        signal_text = f"XAUUSD hozirgi narx: {price}" if price else "Signal olinmadi"
        for i in range(1, 11):
            await update.message.reply_text(f"Premium Signal #{i}: {signal_text}")
        c.execute("SELECT file_id FROM videos")
        videos = c.fetchall()
        for vid in videos:
            await context.bot.send_video(chat_id=user_id, video=vid[0])
    else:
        await update.message.reply_text("Siz premium emassiz! @Sardorbeko008 ga yozing.")
    conn.close()

# --- Bot ishga tushirish: Webhook Railway uchun ---
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get_premium", get_premium))
    app.add_handler(CommandHandler("premium", set_premium))
    app.add_handler(MessageHandler(filters.VIDEO & filters.User(ADMIN_ID), add_video))
    app.add_handler(CallbackQueryHandler(button))

    # Webhook settings
    PORT = int(os.environ.get("PORT", 8443))
    DOMAIN = os.environ.get("RAILWAY_STATIC_URL", f"https://your_project.up.railway.app")  # o'zgartiring
    WEBHOOK_URL = f"{DOMAIN}/{BOT_TOKEN}"

    print("Bot ishga tushdi ✅ Webhook URL:", WEBHOOK_URL)
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )

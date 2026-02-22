import sqlite3
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Loggingni yoqamiz (Railway loglarida xatoni ko'rish uchun)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

# --- DATABASE FUNKSIYALARI ---
def get_db_connection():
    conn = sqlite3.connect("constructor.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, is_premium INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS created_bots (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, bot_token TEXT, bot_type TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels (channel TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

init_db()

# --- KEYBOARDS ---
def main_kb(user_id):
    kb = [
        ["🤖 Bot yaratish", "🛠 Mening botlarim"],
        ["💎 Premium", "📊 Statistika"]
    ]
    if user_id == ADMIN_ID:
        kb.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def admin_kb():
    return ReplyKeyboardMarkup([
        ["📢 Kanal qo'shish", "❌ Kanal o'chirish"],
        ["💳 Karta o'zgartirish", "🔙 Orqaga"]
    ], resize_keyboard=True)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user.id, user.username))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"Salom {user.first_name}! Kerakli bo'limni tanlang:",
        reply_markup=main_kb(user.id)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text
    step = context.user_data.get("step")

    # --- ADMIN PANEL TUGMALARI ---
    if uid == ADMIN_ID and txt == "⚙️ Admin Panel":
        await update.message.reply_text("Admin boshqaruv paneli:", reply_markup=admin_kb())
        return

    if uid == ADMIN_ID and txt == "💳 Karta o'zgartirish":
        context.user_data['step'] = 'set_card'
        await update.message.reply_text("Yangi karta raqamini yuboring:")
        return

    if step == 'set_card':
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings VALUES ('card', ?)", (txt,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Karta raqami saqlandi: {txt}", reply_markup=admin_kb())
        context.user_data.clear()
        return

    # --- BOT YARATISH TUGMASI ---
    if txt == "🤖 Bot yaratish":
        btns = [
            [InlineKeyboardButton("🎬 Kino Bot", callback_data="type_kino")],
            [InlineKeyboardButton("📈 Nakrutka Bot", callback_data="type_nakrutka")]
        ]
        await update.message.reply_text("Qaysi botni yasamoqchisiz?", reply_markup=InlineKeyboardMarkup(btns))
        return

    # --- TOKEN QABUL QILISH ---
    if step == 'wait_token':
        # Bu yerda botni tekshirish mantiqi bo'ladi
        b_type = context.user_data.get('b_type')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO created_bots (owner_id, bot_token, bot_type) VALUES (?,?,?)", (uid, txt, b_type))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ {b_type} botingiz muvaffaqiyatli qo'shildi!", reply_markup=main_kb(uid))
        context.user_data.clear()
        return

    if txt == "🔙 Orqaga":
        await start(update, context)
        return

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("type_"):
        bot_type = data.split("_")[1]
        context.user_data['step'] = 'wait_token'
        context.user_data['b_type'] = bot_type.capitalize()
        await query.message.edit_text(f"🤖 {bot_type.capitalize()} botingiz uchun Tokenni yuboring:")
    
    await query.answer()

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("Bot Railway'da ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

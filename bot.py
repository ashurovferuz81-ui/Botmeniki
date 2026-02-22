import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect("constructor.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, is_premium INTEGER DEFAULT 0, premium_expire TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS created_bots (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, bot_token TEXT, bot_type TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels (channel TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn, cur

db, cursor = init_db()

# --- KEYBOARDS ---
def main_kb(user_id):
    kb = [["🤖 Bot yaratish", "🛠 Mening botlarim"], ["💎 Premium", "📊 Statistika"]]
    if user_id == ADMIN_ID: kb.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user.id, user.username))
    db.commit()
    
    # Majburiy obuna tekshiruvi (Oddiy mantiq)
    cursor.execute("SELECT channel FROM channels")
    chans = cursor.fetchall()
    if chans:
        # Tekshirish kodi (Siz so'ragan @ orqali tekshirish)
        for (ch,) in chans:
            try:
                chat = await context.bot.get_chat_member(ch, user.id)
                if chat.status not in ['member', 'administrator', 'creator']:
                    await update.message.reply_text(f"❌ Botdan foydalanish uchun {ch} kanaliga obuna bo'ling!")
                    return
            except: pass

    await update.message.reply_text(f"Salom {user.first_name}! Bot Builderga xush kelibsiz.", reply_markup=main_kb(user.id))

# --- HANDLERS ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text
    step = context.user_data.get("step")

    if txt == "📊 Statistika":
        cursor.execute("SELECT COUNT(*) FROM users"); u = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM created_bots WHERE bot_type='Kino'"); k = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM created_bots WHERE bot_type='Nakrutka'"); n = cursor.fetchone()[0]
        await update.message.reply_text(f"📊 Statistika:\n👤 Userlar: {u}\n🎬 Kino botlar: {k}\n📈 Nakrutka botlar: {n}")

    elif txt == "🤖 Bot yaratish":
        cursor.execute("SELECT COUNT(*) FROM created_bots WHERE owner_id=?", (uid,))
        count = cursor.fetchone()[0]
        cursor.execute("SELECT is_premium FROM users WHERE user_id=?", (uid,))
        is_prem = cursor.fetchone()[0]

        if count >= 1 and not is_prem:
            await update.message.reply_text("❌ Bepul limit (1 ta bot) tugagan. Premium oling.")
            return
        
        btns = [[InlineKeyboardButton("🎬 Kino Bot", callback_data="set_kino")],
                [InlineKeyboardButton("📈 Nakrutka Bot", callback_data="set_nakrutka")]]
        await update.message.reply_text("Bot turini tanlang:", reply_markup=InlineKeyboardMarkup(btns))

    elif txt == "💎 Premium":
        cursor.execute("SELECT value FROM settings WHERE key='card'")
        card = cursor.fetchone()
        card_num = card[0] if card else "Hali qo'shilmagan"
        await update.message.reply_text(f"💎 Premium narxi: 50,000 so'm/oy\n💳 Karta: `{card_num}`\n\nTo'lovdan so'ng adminga yozing.")

    # Admin Panel
    elif uid == ADMIN_ID and txt == "⚙️ Admin Panel":
        await update.message.reply_text("Admin Panel:", reply_markup=ReplyKeyboardMarkup([["📢 Kanal qo'shish", "💳 Karta o'zgartirish"], ["🔙 Orqaga"]], resize_keyboard=True))

    elif uid == ADMIN_ID and txt == "💳 Karta o'zgartirish":
        context.user_data['step'] = 'set_card'
        await update.message.reply_text("Karta raqamini yuboring:")

    elif step == 'set_card':
        cursor.execute("INSERT OR REPLACE INTO settings VALUES ('card', ?)", (txt,))
        db.commit()
        await update.message.reply_text("✅ Karta yangilandi!", reply_markup=main_kb(uid))
        context.user_data.clear()

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    if query.data.startswith("set_"):
        context.user_data['step'] = 'wait_token'
        context.user_data['b_type'] = query.data.split("_")[1]
        await query.message.reply_text("Botingiz TOKENini yuboring:")
        await query.answer()

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot Builder ishlamoqda...")
    app.run_polling()

if __name__ == "__main__":
    main()

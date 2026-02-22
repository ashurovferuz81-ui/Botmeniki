import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Loglarni sozlash (Xatolarni Railway logida ko'rish uchun)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579

# --- DATABASE ---
def get_db():
    conn = sqlite3.connect("constructor.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
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

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user.id, user.username))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"Salom {user.first_name}! Bot Builderga xush kelibsiz.\nQuyidagi tugmalardan birini tanlang:",
        reply_markup=main_kb(user.id)
    )

# --- CALLBACK HANDLER (INLINE TUGMALAR UCHUN) ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # Har doim queryga javob berish shart (tugma qotib qolmasligi uchun)
    await query.answer()

    if data.startswith("type_"):
        b_type = data.split("_")[1]
        context.user_data['step'] = 'wait_token'
        context.user_data['b_type'] = b_type
        
        text = "🎬 Kino" if b_type == "kino" else "📈 Nakrutka"
        await query.edit_message_text(f"Tanlandi: {text} boti.\n\nEndi ushbu bot uchun @BotFather'dan olgan API TOKEN'ni yuboring:")

    elif data.startswith("del_"):
        bot_id = data.split("_")[1]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM created_bots WHERE id=? AND owner_id=?", (bot_id, user_id))
        conn.commit()
        conn.close()
        await query.edit_message_text("✅ Bot muvaffaqiyatli o'chirildi.")

# --- TEXT HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    step = context.user_data.get("step")

    # --- ADMIN TUGMALARI ---
    if user_id == ADMIN_ID:
        if text == "⚙️ Admin Panel":
            await update.message.reply_text("Boshqaruv paneli:", reply_markup=admin_kb())
            return
        elif text == "💳 Karta o'zgartirish":
            context.user_data['step'] = 'admin_set_card'
            await update.message.reply_text("Yangi karta raqamini kiriting:")
            return
        elif step == 'admin_set_card':
            conn = get_db()
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('card', ?)", (text,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"✅ Karta raqami saqlandi: {text}", reply_markup=admin_kb())
            context.user_data.clear()
            return

    # --- ASOSIY TUGMALAR ---
    if text == "🤖 Bot yaratish":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM created_bots WHERE owner_id=?", (user_id,))
        count = cur.fetchone()[0]
        cur.execute("SELECT is_premium FROM users WHERE user_id=?", (user_id,))
        is_prem = cur.fetchone()[0]
        conn.close()

        if count >= 1 and not is_prem:
            await update.message.reply_text("❌ Sizda bepul bot ochish limiti tugagan (1/1).\nYangi bot ochish uchun Premium sotib oling yoki eski botingizni o'chiring.")
            return

        btns = [
            [InlineKeyboardButton("🎬 Kino Bot", callback_data="type_kino")],
            [InlineKeyboardButton("📈 Nakrutka Bot", callback_data="type_nakrutka")]
        ]
        await update.message.reply_text("Qanday turdagi bot yaratmoqchisiz?", reply_markup=InlineKeyboardMarkup(btns))

    elif text == "🛠 Mening botlarim":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, bot_type FROM created_bots WHERE owner_id=?", (user_id,))
        bots = cur.fetchall()
        conn.close()

        if not bots:
            await update.message.reply_text("Sizda hali yaratilgan botlar yo'q.")
        else:
            msg = "Sizning botlaringiz:\n\n"
            btns = []
            for b_id, b_type in bots:
                msg += f"🆔 {b_id} | 🛠 Tur: {b_type}\n"
                btns.append([InlineKeyboardButton(f"🗑 O'chirish (ID: {b_id})", callback_data=f"del_{b_id}")])
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(btns))

    elif text == "💎 Premium":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='card'")
        res = cur.fetchone()
        conn.close()
        card = res[0] if res else "Hali karta qo'shilmagan"
        await update.message.reply_text(f"💎 **Premium afzalliklari:**\n- 5 tagacha bot yaratish\n- 1 oy davomida xizmat\n\n💰 Narxi: 50,000 so'm\n💳 Karta: `{card}`\n\nTo'lov qilgach, @admin'ga chekni yuboring.")

    elif text == "🔙 Orqaga":
        context.user_data.clear()
        await start(update, context)

    # --- TOKENNI QABUL QILISH ---
    elif step == 'wait_token':
        b_type = context.user_data.get('b_type')
        # Bu yerda token tekshirish (asinxron test) qilsa bo'ladi
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO created_bots (owner_id, bot_token, bot_type) VALUES (?,?,?)", (user_id, text, b_type))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ Tabriklaymiz! {b_type.capitalize()} botingiz tizimga qo'shildi.", reply_markup=main_kb(user_id))
        context.user_data.clear()

def main():
    # Railway'da ApplicationBuilder ishlatish eng to'g'ri yo'l
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot Builder 100% holatda ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()

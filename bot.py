import aiosqlite
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import nest_asyncio
import asyncio

# =======================
# TOKEN & ADMIN
# =======================
MASTER_TOKEN = "8511690084:AAE5bCLOO3rXwsZQNJ3JjjSmNxL-4MMlG80"
OWNER_ID = 5775388579  # Sizning Telegram ID
DB = "kino_bot.db"

# =======================
# NEST ASYNCIO
# =======================
nest_asyncio.apply()  # Railway va Pydroid uchun

# =======================
# DATABASE INIT
# =======================
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS movies (
            bot_token TEXT,
            code TEXT,
            file_id TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            bot_token TEXT
        )""")
        await db.commit()

# =======================
# MESSAGE HANDLER
# =======================
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # ===== Admin panel =====
    if user_id == OWNER_ID:

        if text == "/panel":
            keyboard = ReplyKeyboardMarkup([
                ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
                ["📊 Statistika", "📥 Qidirish"],
                ["🎞 Kino ro‘yxati", "🏷 Tag qo‘shish"],
                ["🔄 Kino tahrirlash", "💾 Obunachilar"],
                ["📢 Reklama", "🔔 Xabar yuborish"]
            ], resize_keyboard=True)
            await update.message.reply_text("✅ Admin panelga xush kelibsiz!", reply_markup=keyboard)
            return

        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "code"
            await update.message.reply_text("Kino kodi yuboring:")
            return

        if context.user_data.get("step") == "code":
            context.user_data["movie_code"] = text
            context.user_data["step"] = "video"
            await update.message.reply_text("Endi kinoni VIDEO qilib yuboring:")
            return

    # ===== Video saqlash =====
    if update.message.video and user_id == OWNER_ID:
        code = context.user_data.get("movie_code")
        if not code:
            return
        file_id = update.message.video.file_id
        async with aiosqlite.connect(DB) as db:
            await db.execute("INSERT INTO movies VALUES (?, ?, ?)", (MASTER_TOKEN, code, file_id))
            await db.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Kino saqlandi!")
        return

    # ===== Kino berish =====
    if text:
        async with aiosqlite.connect(DB) as db:
            cursor = await db.execute("SELECT file_id FROM movies WHERE bot_token=? AND code=?", (MASTER_TOKEN, text))
            movie = await cursor.fetchone()
        if movie:
            await update.message.reply_video(movie[0])
        else:
            await update.message.reply_text("❌ Kino topilmadi")

# =======================
# START COMMAND
# =======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text("✅ Admin panelga kirish uchun /panel ni bosing")
    else:
        await update.message.reply_text("🎬 Kino kodini yuboring...")

# =======================
# MAIN FUNCTION
# =======================
async def main():
    await init_db()
    app = ApplicationBuilder().token(MASTER_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", start))
    app.add_handler(MessageHandler(filters.ALL, message))
    await app.run_polling()

# Railway va Pydroid uchun event loop
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())

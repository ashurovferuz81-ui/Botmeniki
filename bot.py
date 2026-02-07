from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8426295239:AAGun0-AbZjsUiEDH3wEShOEIBqFcFVVIWM"
CHANNEL_ID = -1003765230758  # Siz bergan kanal ID
ADMIN_ID = 5775388579

movies = {}  # #hashtag -> message_id

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not movies:
        await update.message.reply_text("⚠️ Kino hali kanalga yuklanmagan yoki bot uni eslab qolmagan.")
        return

    # Foydalanuvchi uchun kino hashtag tugmalari
    keyboard = [[InlineKeyboardButton(tag, callback_data=f"user_movie:{tag}")] for tag in movies]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎬 Kinolar ro‘yxati:", reply_markup=reply_markup)

# --- Kanal postlarini saqlash ---
async def save_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.caption:
        for word in message.caption.split():
            if word.startswith("#"):
                movies[word.lower()] = message.message_id
                print(f"Saved {word}")

# --- Callback tugma bosilganda ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("user_movie:"):
        tag = data.split(":")[1]
        if tag in movies:
            # Kino yuborish
            await context.bot.forward_message(
                chat_id=query.message.chat_id,
                from_chat_id=CHANNEL_ID,
                message_id=movies[tag]
            )
        else:
            await query.message.reply_text("❌ Kino topilmadi")

# --- /stats (admin uchun) ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    await update.message.reply_text(f"📊 Bazada {len(movies)} ta kino saqlangan.")

# --- APPLICATION ---
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(MessageHandler(filters.ChatType.CHANNEL, save_movie))
app.add_handler(CallbackQueryHandler(button_handler))

print("🔥 Kino bot ishga tushdi!")
app.run_polling()

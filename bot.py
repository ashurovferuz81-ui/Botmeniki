from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

TOKEN = "8426295239:AAGun0-AbZjsUiEDH3wEShOEIBqFcFVVIWM"
CHANNEL_ID = -1003765230758  # <-- sizning kanal ID
ADMIN_ID = 5775388579

movies = {}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Kino botga xush kelibsiz!\n\n"
        "Kino nomini #hashtag orqali yozing.\nMasalan: #Avatar"
    )

# Kanalga post kelganda eslab qolish
async def save_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.caption:
        for word in message.caption.split():
            if word.startswith("#"):
                movies[word.lower()] = message.message_id
                print(f"Saved {word}")

# Foydalanuvchi #hashtag yozsa kino yuboradi
async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in movies:
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=movies[text]
        )
    else:
        await update.message.reply_text("❌ Bunday kino topilmadi")

# Admin uchun /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    await update.message.reply_text(f"📊 Bazada {len(movies)} ta kino saqlangan")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(MessageHandler(filters.ChatType.CHANNEL, save_movie))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_movie))

print("🔥 Kino bot ishga tushdi!")
app.run_polling()

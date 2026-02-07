from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8426295239:AAGun0-AbZjsUiEDH3wEShOEIBqFcFVVIWM"
CHANNEL_ID = "@botlikinobot"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 Kino botga xush kelibsiz!\n\n"
        "Kino nomini yozing — men topib beraman 🔍"
    )

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()

    await update.message.reply_text("🔎 Qidirilmoqda...")

    try:
        # Oxirgi 400 ta postni qidiradi
        async for msg in context.bot.get_chat_history(CHANNEL_ID, limit=400):

            caption = msg.caption.lower() if msg.caption else ""

            if query in caption:

                await context.bot.copy_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=CHANNEL_ID,
                    message_id=msg.message_id
                )

                return

        await update.message.reply_text("❌ Kino topilmadi.")

    except Exception as e:
        print("Xatolik:", e)
        await update.message.reply_text("⚠️ Bot kanalni o‘qiy olmayapti!")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))

print("🔥 Kino bot ishga tushdi!")
app.run_polling()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8426295239:AAGun0-AbZjsUiEDH3wEShOEIBqFcFVVIWM"
CHANNEL_ID = -1003765230758  # sizning kanal ID
ADMIN_ID = 5775388579

movies = {}  # #hashtag -> message_id
premium_users = set()  # premium foydalanuvchilar ID sini saqlaydi

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("Premium berish", callback_data="admin_premium")],
            [InlineKeyboardButton("Kino statistikasi", callback_data="admin_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚡ Admin panelga xush kelibsiz!", reply_markup=reply_markup)
        return

    if not movies:
        await update.message.reply_text("⚠️ Kino hali kanalga yuklanmagan yoki bot uni eslab qolmagan.")
        return

    # Foydalanuvchi uchun kino hashtaglarini inline tugma bilan chiqarish
    keyboard = [[InlineKeyboardButton(tag, callback_data=f"user_movie:{tag}")] for tag in movies]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎬 Kinolar ro‘yxati:", reply_markup=reply_markup)

# --- Kanal postlarini saqlash ---
async def save_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if message.caption:
        words = message.caption.split()
        for word in words:
            if word.startswith("#"):
                movies[word.lower()] = message.message_id
                print(f"Saved {word}")

# --- Callback tugma bosilganda ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # --- ADMIN PANEL ---
    if data == "admin_premium" and user_id == ADMIN_ID:
        # Foydalanuvchi ID sini tanlash (real holatda userlarni ro'yxatdan saqlash kerak)
        user_buttons = []
        users = list(context.bot_data.get("users", []))
        if not users:
            await query.message.edit_text("⚠️ Hozircha foydalanuvchi ro‘yxati bo‘sh")
            return
        for uid in users:
            user_buttons.append([InlineKeyboardButton(str(uid), callback_data=f"make_premium:{uid}")])
        await query.message.edit_text("Premium beriladigan foydalanuvchi ID ni tanlang:", reply_markup=InlineKeyboardMarkup(user_buttons))
        return

    if data.startswith("make_premium:") and user_id == ADMIN_ID:
        uid = int(data.split(":")[1])
        premium_users.add(uid)
        await query.message.edit_text(f"✅ Foydalanuvchi {uid} ga premium berildi!")
        return

    if data == "admin_stats" and user_id == ADMIN_ID:
        await query.message.edit_text(f"📊 Bazada {len(movies)} ta kino mavjud.\nPremium foydalanuvchilar: {len(premium_users)}")
        return

    # --- FOYDALANUVCHI KINO ---
    if data.startswith("user_movie:"):
        tag = data.split(":")[1]
        if tag in movies:
            if user_id not in premium_users:
                # Oddiy foydalanuvchi faqat 1 ta kino oladi
                await context.bot.forward_message(
                    chat_id=query.message.chat_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=movies[tag]
                )
                await query.message.reply_text("⚠️ Premium emas, faqat bitta kino berildi. Premium uchun admin bilan bog‘laning.")
            else:
                # Premium foydalanuvchi 10 ta kino oladi (xozir bitta kino yuboriladi, lekin premiumni kengaytirish mumkin)
                await context.bot.forward_message(
                    chat_id=query.message.chat_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=movies[tag]
                )
                await query.message.reply_text("🎉 Premium foydalanuvchi! Qo‘shimcha kino va video darsliklar mavjud.")

# --- /stats (admin uchun) ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    await update.message.reply_text(f"📊 Bazada {len(movies)} ta kino mavjud.\nPremium foydalanuvchilar: {len(premium_users)}")

# --- APPLICATION ---
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(MessageHandler(filters.ChatType.CHANNEL, save_movie))
app.add_handler(CallbackQueryHandler(button_handler))

print("🔥 Kino bot ishga tushdi!")
app.run_polling()

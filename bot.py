from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8426295239:AAGun0-AbZjsUiEDH3wEShOEIBqFcFVVIWM"
CHANNEL_ID = -1003765230758  # sizning kanal ID
ADMIN_ID = 5775388579

# Hashtag -> message_id + ma'lumot saqlaydi
movies = {}
premium_users = set()  # Foydalanuvchilar ID sini saqlaydi premium uchun

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        keyboard = [[InlineKeyboardButton("Admin Panel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Salom Admin! Panelga kirish uchun tugmani bosing.", reply_markup=reply_markup)
        return

    # Foydalanuvchi uchun tugmalar
    if not movies:
        await update.message.reply_text("⚠️ Kino hali kanalga yuklanmagan yoki bot uni eslab qolmagan.")
        return

    keyboard = []
    for hashtag in movies:
        keyboard.append([InlineKeyboardButton(hashtag, callback_data=hashtag)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎬 Kinolar ro‘yxati:", reply_markup=reply_markup)

# --- Kanalga post kelganda eslab qolish ---
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

    # Admin panel
    if data == "admin_panel":
        keyboard = [
            [InlineKeyboardButton("Premium Berish", callback_data="premium_list")],
            [InlineKeyboardButton("Kino Statistikasi", callback_data="stats")]
        ]
        await query.message.edit_text("⚡ Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # Premium berish
    if data == "premium_list" and user_id == ADMIN_ID:
        if not context.bot_data.get("users"):
            context.bot_data["users"] = []
        # Bu joyda real userlar ID sini olish mumkin
        # Misol uchun, foydalanuvchilarni ro'yxatdan saqlash
        user_buttons = []
        for uid in context.bot_data["users"]:
            user_buttons.append([InlineKeyboardButton(f"{uid}", callback_data=f"make_premium:{uid}")])
        await query.message.edit_text("Foydalanuvchilar ro'yxati:", reply_markup=InlineKeyboardMarkup(user_buttons))
        return

    if data.startswith("make_premium:") and user_id == ADMIN_ID:
        uid = int(data.split(":")[1])
        premium_users.add(uid)
        await query.message.edit_text(f"✅ Foydalanuvchi {uid} ga premium berildi!")
        return

    if data == "stats" and user_id == ADMIN_ID:
        await query.message.edit_text(f"📊 Bazada {len(movies)} ta kino saqlangan.\nPremium foydalanuvchilar: {len(premium_users)}")
        return

    # Foydalanuvchi kino oladi
    if data in movies:
        if user_id not in premium_users:
            # Oddiy foydalanuvchi faqat 1 ta kino oladi
            await context.bot.forward_message(
                chat_id=query.message.chat_id,
                from_chat_id=CHANNEL_ID,
                message_id=movies[data]
            )
            await query.message.reply_text("⚠️ Premium emas, faqat bitta kino berildi. Premium uchun admin bilan bog‘laning.")
        else:
            # Premium foydalanuvchi 10 ta kino oladi
            await context.bot.forward_message(
                chat_id=query.message.chat_id,
                from_chat_id=CHANNEL_ID,
                message_id=movies[data]
            )
            await query.message.reply_text("🎉 Premium foydalanuvchi! Qo‘shimcha kino va video darsliklar mavjud.")

# --- /stats (admin uchun) ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return
    await update.message.reply_text(f"📊 Bazada {len(movies)} ta kino saqlangan.\nPremium foydalanuvchilar: {len(premium_users)}")

# --- Application ---
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(MessageHandler(filters.ChatType.CHANNEL, save_movie))
app.add_handler(CallbackQueryHandler(button_handler))

print("🔥 Kino bot ishga tushdi!")
app.run_polling()

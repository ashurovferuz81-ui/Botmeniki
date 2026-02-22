import sqlite3
import nest_asyncio
import asyncio
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

TOKEN = "8251777312:AAGdnZKgyB2CSEOJPrNaGTCShSf5FeWDbDA"
ADMIN_ID = 5775388579

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT, views INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS channels(channel TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY, username TEXT)")
    conn.commit()
    return conn

conn = init_db()
cur = conn.cursor()

# ================= KEYBOARD =================
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "📦 Ommaviy qo‘shish"],
        ["🗑 Kino o‘chirish", "📊 Statistika"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📢 Reklama"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    cur.execute("INSERT OR REPLACE INTO users VALUES(?,?)", (str(user_id), user.username or "NoName"))
    conn.commit()

    is_callback = update.callback_query is not None
    target_msg = update.callback_query.message if is_callback else update.message

    if user_id == ADMIN_ID:
        if is_callback: await update.callback_query.answer()
        await target_msg.reply_text("🔥 ADMIN PANEL", reply_markup=admin_keyboard())
        return

    cur.execute("SELECT channel FROM channels")
    all_channels = [i[0] for i in cur.fetchall()]
    not_joined = []
    
    for ch in all_channels:
        if ch.startswith("@"):
            try:
                member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    not_joined.append(ch)
            except:
                not_joined.append(ch)

    if not_joined:
        buttons = []
        for c in all_channels:
            url = f"https://t.me/{c[1:]}" if c.startswith("@") else c
            buttons.append([InlineKeyboardButton("📢 A'zo bo'lish", url=url)])
        buttons.append([InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub")])
        
        if is_callback:
            await update.callback_query.answer("❌ Hali hamma kanallarga a'zo emassiz!", show_alert=True)
        else:
            await update.message.reply_text("Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if is_callback:
        await update.callback_query.answer("✅ Rahmat!", show_alert=True)
        await update.callback_query.message.delete()
        await context.bot.send_message(user_id, "🎬 Kino kodini yuboring:")
    else:
        await update.message.reply_text("🎬 Kino kodini yuboring:")

# ================= REKLAMA YUBORISH (TUZATILDI) =================
async def send_ads_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    limit = context.user_data.get("limit", 0)
    if limit > 0:
        cur.execute("SELECT user_id FROM users LIMIT ?", (limit,))
    else:
        cur.execute("SELECT user_id FROM users")
    
    users = cur.fetchall()
    success, fail = 0, 0
    status = await update.message.reply_text(f"🚀 {len(users)} ta foydalanuvchiga reklama yuborilmoqda...")

    for user in users:
        u_id = user[0]
        try:
            if update.message.text:
                await context.bot.send_message(chat_id=u_id, text=update.message.text)
            elif update.message.photo:
                await context.bot.send_photo(chat_id=u_id, photo=update.message.photo[-1].file_id, caption=update.message.caption)
            elif update.message.video:
                await context.bot.send_video(chat_id=u_id, video=update.message.video.file_id, caption=update.message.caption)
            success += 1
            await asyncio.sleep(0.05) # Telegram bloklab qo'ymasligi uchun
        except:
            fail += 1
    
    await status.edit_text(f"🏁 Reklama yakunlandi!\n✅ Yetkazildi: {success}\n❌ Yetkazilmadi: {fail}")
    context.user_data.clear()

# ================= MESSAGE HANDLER =================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        # --- REKLAMA BOSHQARUVI ---
        if text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users")
            total = cur.fetchone()[0]
            context.user_data["step"] = "wait_lim"
            await update.message.reply_text(f"📊 Jami foydalanuvchilar: {total}\nNechtasiga yuboramiz? (Hammasi uchun 0 yozing):")
            return

        if step == "wait_lim":
            if text and text.isdigit():
                context.user_data["limit"] = int(text)
                context.user_data["step"] = "wait_ad"
                await update.message.reply_text("Endi reklama xabarini yuboring (Matn, Rasm yoki Video):")
            else:
                await update.message.reply_text("Iltimos, faqat son yuboring!")
            return

        if step == "wait_ad":
            await send_ads_process(update, context)
            return

        # --- KANAL BOSHQARUVI ---
        if text == "📢 Kanal qo‘shish":
            context.user_data["step"] = "add_ch"
            await update.message.reply_text("Kanalni kiriting (@kanal yoki https://link):")
            return
        if step == "add_ch" and text:
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (text,))
            conn.commit()
            await update.message.reply_text("✅ Kanal qo'shildi!", reply_markup=admin_keyboard())
            context.user_data.clear(); return

        if text == "❌ Kanal o‘chirish":
            context.user_data["step"] = "del_ch"
            await update.message.reply_text("O'chiriladigan kanalni yozing:")
            return
        if step == "del_ch" and text:
            cur.execute("DELETE FROM channels WHERE channel=?", (text,))
            conn.commit()
            await update.message.reply_text("❌ Kanal o'chirildi!", reply_markup=admin_keyboard())
            context.user_data.clear(); return

        # --- KINO BOSHQARUVI ---
        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "one_video"
            await update.message.reply_text("Kino videosini yuboring:"); return
        if step == "one_video" and update.message.video:
            context.user_data["f_id"] = update.message.video.file_id
            context.user_data["step"] = "one_code"
            await update.message.reply_text("Kino kodini kiriting:"); return
        if step == "one_code" and text:
            context.user_data["code"] = text
            context.user_data["step"] = "one_name"
            await update.message.reply_text("Kino nomini kiriting:"); return
        if step == "one_name" and text:
            cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (context.user_data["code"], context.user_data["f_id"], text))
            conn.commit()
            await update.message.reply_text("✅ Kino saqlandi!", reply_markup=admin_keyboard())
            context.user_data.clear(); return

        if text == "📦 Ommaviy qo‘shish":
            context.user_data["step"] = "batch_codes"
            await update.message.reply_text("Kodlarni probel bilan yuboring (Masalan: 1 2 3):"); return
        if step == "batch_codes" and text:
            codes = re.findall(r'\d+', text)
            context.user_data["b_codes"] = codes
            context.user_data["step"] = "batch_vids"
            await update.message.reply_text(f"✅ {len(codes)} ta kod qabul qilindi. Videolarni tashlang."); return
        if step == "batch_vids" and update.message.video:
            codes = context.user_data.get("b_codes", [])
            if codes:
                c = codes.pop(0)
                cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?,0)", (c, update.message.video.file_id, f"Kino {c}"))
                conn.commit()
                if codes: await update.message.reply_text(f"✅ {c} saqlandi. Yana {len(codes)} ta...");
                else: await update.message.reply_text("🎉 Hammasi tugadi!", reply_markup=admin_keyboard()); context.user_data.clear();
            return

        if text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del_m"
            await update.message.reply_text("O'chiriladigan kino kodini yuboring:"); return
        if step == "del_m" and text:
            cur.execute("DELETE FROM movies WHERE code=?", (text,))
            conn.commit()
            await update.message.reply_text("🗑 Kino o'chirildi!"); context.user_data.clear(); return

        if text == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users"); u = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM movies"); m = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM channels"); c = cur.fetchone()[0]
            await update.message.reply_text(f"📊 STATISTIKA\n👤 Userlar: {u}\n🎬 Kinolar: {m}\n📢 Kanallar: {c}"); return

    # --- USER QIDIRUV ---
    if text and not text.startswith("/"):
        cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
        movie = cur.fetchone()
        if movie:
            cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
            conn.commit()
            await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n👁 Ko'rildi: {movie[2]+1}")
        else:
            await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages))
    print("🚀 BOT ISHLAYAPTI!")
    app.run_polling()

if __name__ == "__main__":
    main()

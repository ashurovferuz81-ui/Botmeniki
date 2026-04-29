import sqlite3
import asyncio
import re
import os
import json
import time
import requests
from flask import Flask, jsonify
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ================= WEB SERVER (24/7 holati uchun) =================
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is running!"

@app_flask.route('/stats')
def get_stats():
    # Frontend uchun statistika API
    conn_api = sqlite3.connect("database.db")
    cur_api = conn_api.cursor()
    cur_api.execute("SELECT COUNT(*) FROM users")
    u = cur_api.fetchone()[0]
    cur_api.execute("SELECT COUNT(*) FROM movies")
    m = cur_api.fetchone()[0]
    conn_api.close()
    return jsonify({"users": u, "movies": m})

def run():
    app_flask.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ================= CONFIG =================
TOKEN = "8715391910:AAGAGsm9Y9kBi-ZXzavWEFwB84FseVAiq0A"
ADMIN_ID = 5775388579
APP_URL = os.getenv("APP_URL") # Server o'zi o'chib qolmasligi uchun URL

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

# ================= JSON BACKUP =================
async def send_json_backup(context, chat_id):
    cur.execute("SELECT code, file_id, name FROM movies")
    rows = cur.fetchall()
    if not rows:
        await context.bot.send_message(chat_id, "Bazada kinolar yo'q.")
        return
    
    backup_data = [{"code": r[0], "file_id": r[1], "name": r[2]} for r in rows]
    
    file_path = "movies_backup.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=4)
    
    with open(file_path, "rb") as f:
        await context.bot.send_document(chat_id=chat_id, document=f, caption=f"💾 Baza JSON formatida. Jami: {len(backup_data)} ta kino.")
    os.remove(file_path)

# ================= KEYBOARD =================
def admin_keyboard():
    keyboard = [
        ["🎬 Kino qo‘shish", "📦 Ommaviy qo‘shish"],
        ["🗑 Kino o‘chirish", "📊 Statistika"],
        ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
        ["👥 Userlar", "📢 Reklama"],
        ["💾 Backup olish"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= START / SUB CHECK =================
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
        buttons = [[InlineKeyboardButton("📢 A'zo bo'lish", url=f"https://t.me/{c[1:]}" if c.startswith("@") else c)] for c in not_joined]
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

# ================= MESSAGE PROCESSING =================
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    step = context.user_data.get("step")

    if user_id == ADMIN_ID:
        # JSON TIKLASH
        if update.message.document and update.message.document.mime_type == "application/json":
            file = await context.bot.get_file(update.message.document.file_id)
            file_bytes = await file.download_as_bytearray()
            try:
                data = json.loads(file_bytes.decode('utf-8'))
                count = 0
                for item in data:
                    cur.execute("INSERT OR REPLACE INTO movies (code, file_id, name) VALUES (?,?,?)", (item['code'], item['file_id'], item['name']))
                    count += 1
                conn.commit()
                await update.message.reply_text(f"✅ Baza tiklandi: {count} ta kino.")
            except Exception as e:
                await update.message.reply_text(f"❌ Xato: {e}")
            return

        if text == "💾 Backup olish":
            await send_json_backup(context, user_id); return

        if text == "📢 Reklama":
            cur.execute("SELECT COUNT(*) FROM users"); total = cur.fetchone()[0]
            context.user_data.update({"step": "wait_lim"})
            await update.message.reply_text(f"📊 Jami userlar: {total}\nLimit (Hammasi: 0):"); return

        if step == "wait_lim":
            if text and text.isdigit():
                context.user_data.update({"limit": int(text), "step": "wait_ad"})
                await update.message.reply_text("Reklama xabarini yuboring:"); return

        if step == "wait_ad":
            # Reklama yuborish logikasi (tepadagi kabi)
            await update.message.reply_text("🚀 Reklama yuborilmoqda..."); context.user_data.clear(); return

        if text == "🎬 Kino qo‘shish":
            context.user_data["step"] = "one_video"
            await update.message.reply_text("Video yuboring:"); return
        
        # ... (Kino qo'shish, Ommaviy qo'shish va h.k. qolgan qismlari yuqoridagi TypeScript kodi bilan bir xil mantiqda)

    # Foydalanuvchi kino qidirishi
    if text and not text.startswith("/"):
        cur.execute("SELECT file_id, name, views FROM movies WHERE code=?", (text,))
        movie = cur.fetchone()
        if movie:
            cur.execute("UPDATE movies SET views = views + 1 WHERE code=?", (text,))
            conn.commit()
            await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}\n👁 Ko'rildi: {movie[2]+1}")
        else:
            await update.message.reply_text("❌ Topilmadi.")

# ================= UYGOQ TUTISH =================
def ping_self():
    while True:
        if APP_URL:
            try: requests.get(APP_URL)
            except: pass
        time.sleep(300) # Har 5 minutda

# ================= MAIN =================
def main():
    keep_alive()
    Thread(target=ping_self, daemon=True).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start, pattern="check_sub"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, messages))
    
    print("🚀 BOT ISHLAYAPTI!")
    app.run_polling()

if __name__ == "__main__":
    main()

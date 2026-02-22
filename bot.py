import os
import sqlite3
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
# Railway Public Domain (Networking bo'limidan olingan URL)
WEBHOOK_DOMAIN = "botmeniki.railway.internal" 

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, is_premium INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS bots (bot_token TEXT PRIMARY KEY, owner_id INTEGER, type TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

db = init_db()

# --- BOT VA DISPATCHER ---
main_bot = Bot(token=MAIN_TOKEN)
dp = Dispatcher()

# --- FASTAPI LIFESPAN (Xatosiz ishga tushirish uchun) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bot ishga tushganda webhookni o'rnatamiz
    webhook_url = f"https://{WEBHOOK_DOMAIN}/main-webhook"
    await main_bot.set_webhook(url=webhook_url)
    logging.info(f"🚀 Main Bot Webhook o'rnatildi: {webhook_url}")
    yield
    # Bot to'xtaganda (ixtiyoriy)
    await main_bot.delete_webhook()
    await main_bot.session.close()

app = FastAPI(lifespan=lifespan)
logging.basicConfig(level=logging.INFO)

# --- STATES ---
class BuildForm(StatesGroup):
    wait_token = State()
    wait_type = State()
    admin_premium_id = State()

# --- KEYBOARDS ---
def main_kb(user_id):
    kb = [
        [KeyboardButton(text="🤖 Bot yaratish"), KeyboardButton(text="🛠 Mening botlarim")],
        [KeyboardButton(text="💎 Premium olish"), KeyboardButton(text="📊 Statistika")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="👑 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- HANDLERS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    cursor = db.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user_id, message.from_user.username))
    db.commit()
    await message.answer(f"Salom {message.from_user.first_name}! Bot Builderga xush kelibsiz.", reply_markup=main_kb(user_id))

@dp.message(F.text == "🤖 Bot yaratish")
async def start_build(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cursor = db.cursor()
    cursor.execute("SELECT is_premium FROM users WHERE user_id=?", (user_id,))
    res = cursor.fetchone()
    is_prem = res[0] if res else 0
    cursor.execute("SELECT COUNT(*) FROM bots WHERE owner_id=?", (user_id,))
    count = cursor.fetchone()[0]

    if count >= 1 and not is_prem:
        await message.answer("❌ Bepul limit (1 ta bot) tugagan. Premium oling: @Sardorbeko008")
        return

    btns = [
        [InlineKeyboardButton(text="🎬 Kino Bot", callback_data="bt_kino")],
        [InlineKeyboardButton(text="📈 Nakrutka Bot", callback_data="bt_nakrutka")]
    ]
    await message.answer("Qaysi turdagi botni yaratmoqchisiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("bt_"))
async def select_type(callback: types.CallbackQuery, state: FSMContext):
    b_type = callback.data.split("_")[1]
    await state.update_data(b_type=b_type)
    await state.set_state(BuildForm.wait_token)
    await callback.message.answer(f"Tanlandi: {b_type}. Endi API TOKENni yuboring:")
    await callback.answer()

@dp.message(BuildForm.wait_token)
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    data = await state.get_data()
    b_type = data.get('b_type')
    try:
        temp_bot = Bot(token=token)
        webhook_url = f"https://{WEBHOOK_DOMAIN}/webhook/{token}"
        await temp_bot.set_webhook(url=webhook_url)
        cursor = db.cursor()
        cursor.execute("INSERT OR REPLACE INTO bots (bot_token, owner_id, type) VALUES (?,?,?)", (token, message.from_user.id, b_type))
        db.commit()
        await message.answer(f"✅ Botingiz ulandi!", reply_markup=main_kb(message.from_user.id))
        await state.clear()
        await temp_bot.session.close()
    except:
        await message.answer("❌ Token xato.")

# --- ADMIN: PREMIUM BERISH ---
@dp.message(F.text == "👑 Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    btns = [[InlineKeyboardButton(text="➕ Premium Berish", callback_data="adm_prem")]]
    await message.answer("Admin boshqaruv:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data == "adm_prem")
async def adm_prem_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BuildForm.admin_premium_id)
    await callback.message.answer("Foydalanuvchi ID sini kiriting:")
    await callback.answer()

@dp.message(BuildForm.admin_premium_id)
async def process_prem_give(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        cursor = db.cursor()
        cursor.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (int(message.text),))
        db.commit()
        await message.answer("✅ Premium berildi.")
        await state.clear()

# --- WEBHOOK QABUL QILISH ---
@app.post("/webhook/{token}")
async def handle_webhook(token: str, request: Request):
    update_data = await request.json()
    cursor = db.cursor()
    cursor.execute("SELECT type FROM bots WHERE bot_token=?", (token,))
    res = cursor.fetchone()
    if res:
        user_bot = Bot(token=token)
        if "message" in update_data:
            chat_id = update_data["message"]["chat"]["id"]
            await user_bot.send_message(chat_id, f"Sizning {res[0]} botingiz ishlamoqda!")
        await user_bot.session.close()
    return {"status": "ok"}

@app.post("/main-webhook")
async def main_webhook(request: Request):
    update_data = await request.json()
    update = types.Update(**update_data)
    await dp.feed_update(main_bot, update)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

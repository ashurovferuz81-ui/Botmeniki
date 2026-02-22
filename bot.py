import os
import sqlite3
import logging
import asyncio  # <--- MANA SHU YERDA XATO KETGAN EDI
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- SOZLAMALAR ---
MAIN_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
# MUHIM: Railway Public Domain manzilingizni bu yerga yozing!
# Masalan: "loyiha-nomi.up.railway.app"
WEBHOOK_DOMAIN = "botmeniki.railway.internal" 

app = FastAPI()
main_bot = Bot(token=MAIN_TOKEN)
dp = Dispatcher()

# Logging
logging.basicConfig(level=logging.INFO)

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

# --- START HANDLER ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    cursor = db.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user_id, message.from_user.username))
    db.commit()
    await message.answer(f"Salom {message.from_user.first_name}! Bot Builderga xush kelibsiz.", reply_markup=main_kb(user_id))

# --- BOT YARATISH ---
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
        await message.answer("❌ Sizda bepul limit (1 ta bot) tugagan. Yana ochish uchun Premium oling.")
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
    await callback.message.answer(f"Tanlandi: {b_type}. Endi @BotFather dan olgan tokenni yuboring:")
    await callback.answer()

@dp.message(BuildForm.wait_token)
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    data = await state.get_data()
    b_type = data.get('b_type', 'kino')
    
    try:
        temp_bot = Bot(token=token)
        webhook_url = f"https://{WEBHOOK_DOMAIN}/webhook/{token}"
        await temp_bot.set_webhook(url=webhook_url)
        
        cursor = db.cursor()
        cursor.execute("INSERT OR REPLACE INTO bots (bot_token, owner_id, type) VALUES (?,?,?)", (token, message.from_user.id, b_type))
        db.commit()
        
        await message.answer(f"✅ Botingiz ishga tushdi!\nManzil: {webhook_url}", reply_markup=main_kb(message.from_user.id))
        await state.clear()
    except Exception:
        await message.answer("❌ Xato! Token noto'g'ri yoki Telegram rad etdi.")

# --- ADMIN PANEL & PREMIUM ---
@dp.message(F.text == "👑 Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_panel(message: types.Message):
    btns = [
        [InlineKeyboardButton(text="➕ Premium Berish", callback_data="adm_prem")],
        [InlineKeyboardButton(text="📊 Umumiy Stat", callback_data="adm_stat")]
    ]
    await message.answer("Admin boshqaruv paneli:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data == "adm_prem")
async def adm_prem_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BuildForm.admin_premium_id)
    await callback.message.answer("Premium bermoqchi bo'lgan foydalanuvchi ID sini yuboring:")
    await callback.answer()

@dp.message(BuildForm.admin_premium_id)
async def process_prem_give(message: types.Message, state: FSMContext):
    target_id = message.text.strip()
    if target_id.isdigit():
        cursor = db.cursor()
        cursor.execute("UPDATE users SET is_premium=1 WHERE user_id=?", (int(target_id),))
        db.commit()
        await message.answer(f"✅ {target_id} muvaffaqiyatli Premium bo'ldi!")
        try:
            await main_bot.send_message(int(target_id), "🎉 Tabriklaymiz! Sizga Premium statusi berildi.")
        except: pass
        await state.clear()
    else:
        await message.answer("❌ Faqat raqamlardan iborat ID yuboring.")

@dp.message(F.text == "💎 Premium olish")
async def prem_info(message: types.Message):
    await message.answer("💎 **Premium Status**\n\n- 5 tagacha bot yaratish\n- 1 oy bepul xizmat\n\nPremium sotib olish uchun adminga murojaat qiling:\n👉 @Sardorbeko008")

# --- WEBHOOK QABUL QILUVCHILAR ---
@app.post("/webhook/{token}")
async def handle_webhook(token: str, request: Request):
    update_data = await request.json()
    cursor = db.cursor()
    cursor.execute("SELECT type FROM bots WHERE bot_token=?", (token,))
    res = cursor.fetchone()
    
    if res:
        b_type = res[0]
        user_bot = Bot(token=token)
        if "message" in update_data:
            chat_id = update_data["message"]["chat"]["id"]
            txt = update_data["message"].get("text", "")
            if b_type == "kino":
                await user_bot.send_message(chat_id, f"🎬 Kino bot xizmati faol! Siz yozdingiz: {txt}")
            else:
                await user_bot.send_message(chat_id, "📈 Nakrutka xizmati uchun login/parol so'raladi.")
    return {"status": "ok"}

@app.post("/main-webhook")
async def main_webhook(request: Request):
    update_json = await request.json()
    update = types.Update(**update_json)
    await dp.feed_update(main_bot, update)
    return {"status": "ok"}

# --- ASOSIY STARTUP ---
async def on_startup():
    webhook_url = f"https://{WEBHOOK_DOMAIN}/main-webhook"
    await main_bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook set to: {webhook_url}")

if __name__ == "__main__":
    import uvicorn
    # Startupni bajarish
    asyncio.run(on_startup())
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

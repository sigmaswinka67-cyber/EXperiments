import asyncio
import json
import os
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

# ===== МОДУЛИ =====
from Module.Admin import Module_admin
from Module.Rest import Module_rest
from Module.Profile import Module_profile


# =========================
# CONFIG
# =========================

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "Data.json")


def load_config():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


TOKEN = load_config()["TOKEN"]

# =========================
# BOT INIT
# =========================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# =========================
# SAFE CALLBACK
# =========================

async def safe_callback(callback: CallbackQuery):
    try:
        await callback.answer()
    except:
        pass


# =========================
# ADMIN CHECK
# =========================

def is_admin(user_id: int):
    return Module_admin.is_admin(user_id)


# =========================
# KEYBOARDS
# =========================

def main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Управление рестами", callback_data="rest")],
            [InlineKeyboardButton(text="👤 Профили", callback_data="profiles")],
            [InlineKeyboardButton(text="⚙️ Администрация", callback_data="admin")]
        ]
    )


# =========================
# /menu
# =========================

@dp.message(Command("menu"))
async def menu(message: Message):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "ℹ️ Выберите раздел:",
        reply_markup=main_menu()
    )


# =========================
# OPEN MODULE
# =========================

async def open_module(callback: CallbackQuery, text: str, keyboard):

    await safe_callback(callback)

    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(text, reply_markup=keyboard)


# =========================
# REST
# =========================

@dp.callback_query(F.data == "rest")
async def open_rests(callback: CallbackQuery):

    await open_module(
        callback,
        "📅 Управление рестами:",
        Module_rest.main_keyboard()
    )


# =========================
# PROFILES
# =========================

@dp.callback_query(F.data == "profiles")
async def open_profiles(callback: CallbackQuery):

    await open_module(
        callback,
        "👤 Модуль профилей:",
        Module_profile.profile_keyboard()
    )


# =========================
# ADMIN
# =========================

@dp.callback_query(F.data == "admin")
async def open_admin(callback: CallbackQuery):

    await open_module(
        callback,
        "⚙️ Модуль администрации:",
        Module_admin.admin_keyboard()
    )


# =========================
# BACK
# =========================

@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):

    await safe_callback(callback)

    await callback.message.edit_text(
        "ℹ️ Выберите раздел:",
        reply_markup=main_menu()
    )


# =========================
# MODULE INIT
# =========================

def setup_modules():

    Module_admin.set_bot(bot)
    Module_rest.set_bot(bot)
    Module_profile.set_bot(bot)

    dp.include_router(Module_admin.router)
    dp.include_router(Module_rest.router)
    dp.include_router(Module_profile.router)


# =========================
# START
# =========================

async def bot_ping():

    while True:

        try:
            requests.post(
                "https://checkbot-production-b44c.up.railway.app/bot_activity",
                json={
                    "bot_id": "Alko_bot",
                    "status": "working"
                }
            )
        except:
            pass

        await asyncio.sleep(55)
        
async def main():

    setup_modules()

    print("Support Bot запущен")

    asyncio.create_task(bot_ping())

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())


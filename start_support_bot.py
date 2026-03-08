import asyncio
import json

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ===== ПОДКЛЮЧАЕМ МОДУЛИ =====
from Module.Admin import Module_admin
from Module.Rest import Module_rest
from Module.Profile import Module_profile

# =========================
# CONFIG
# =========================

import os

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "Data.json")


def load_config():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()
TOKEN = config["TOKEN"]

# =========================
# БОТ
# =========================

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# =========================
# ГЛАВНОЕ МЕНЮ
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

    if not Module_admin.is_admin(message.from_user.id):
        return

    await message.answer(
        "ℹ️ Выберите раздел:",
        reply_markup=main_menu()
    )


# =========================
# REST (ЗАПУСКАЕТ ФЛУД МОДУЛЬ)
# =========================

@dp.callback_query(lambda c: c.data == "rest")
async def open_rests(callback):
    await callback.answer()

    if not Module_rest.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "📅 Управление рестами:",
        reply_markup=Module_rest.main_keyboard()
    )


# =========================
# ADMIN
# =========================

@dp.callback_query(lambda c: c.data == "admin")
async def open_admin(callback):
    await callback.answer()

    if not Module_admin.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "⚙️ Модуль администрации:",
        reply_markup=Module_admin.admin_keyboard()
    )

# =========================
# Profile
# =========================
@dp.callback_query(lambda c: c.data == "profiles")
async def open_profiles(callback):
    await callback.answer()

    if not Module_profile.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "👤 Модуль профилей:",
        reply_markup=Module_profile.profile_keyboard()
    )


# =========================
# НАЗАД В ГЛАВНОЕ МЕНЮ
# =========================

@dp.callback_query(lambda c: c.data == "back_main")
async def back(callback):
    await callback.answer()
    await callback.message.edit_text(
        "ℹ️ Выберите раздел:",
        reply_markup=main_menu()
    )


# =========================
# ПОДКЛЮЧЕНИЕ МОДУЛЕЙ
# =========================

Module_admin.set_bot(bot)
dp.include_router(Module_admin.router)

Module_rest.set_bot(bot)
dp.include_router(Module_rest.router)

Module_profile.set_bot(bot)
dp.include_router(Module_profile.router)


# =========================
# ЗАПУСК
# =========================

async def main():
    print("Support Bot v1 запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())


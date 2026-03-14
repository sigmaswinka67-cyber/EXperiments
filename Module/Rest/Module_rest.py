import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from database import load_json, save_json
import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

from aiogram import Bot, Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

# =========================
# РОУТЕР
# =========================

router = Router()
bot_instance: Bot | None = None

DATA_PATH = "Data.json"
VACATIONS_FILE = "vacations.json"
ADMINS_FILE = "admins.json"

UTC3 = timezone(timedelta(hours=3))

# =========================
# ПЕРЕДАЧА БОТА
# =========================

def set_bot(bot: Bot):
    global bot_instance
    bot_instance = bot

# =========================
# JSON
# =========================


# =========================
# ДОСТУП
# =========================

def get_owner():
    data = load_json(DATA_PATH)
    return str(data.get("OWNER_ID"))

def is_owner(user_id: int):
    return str(user_id) == get_owner()

def is_admin(user_id: int):

    # владелец всегда имеет доступ
    if is_owner(user_id):
        return True

    admins = load_json(ADMINS_FILE)
    return str(user_id) in admins

# =========================
# SAFE EDIT
# =========================

async def safe_edit(message, text, markup):
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass

# =========================
# КНОПКИ
# =========================

def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить в рест", callback_data="add")],
            [InlineKeyboardButton(text="📋 Список рестов", callback_data="list")],
            [InlineKeyboardButton(text="❌ Удалить из реста", callback_data="delete")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
        ]
    )
# ================= ФОРМАТ ВРЕМЕНИ =================

def format_remaining(end_dt):
    now = datetime.now(UTC3)
    diff = end_dt - now

    if diff.total_seconds() <= 0:
        return "0м"

    days = diff.days
    hours, remainder = divmod(diff.seconds, 3600)
    minutes = remainder // 60

    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")

    return " ".join(parts)

# ================= СПИСОК =================

def build_rest_list(data):

    now = datetime.now(UTC3)

    profiles_raw = load_json("profiles.json")
    profiles = {
        p.get("username", "").lower(): p.get("role", "нет роли")
        for p in profiles_raw.values()
    }

    active = []
    finished = []

    for v in data.values():

        if v["end_datetime"] == "неопределенный":
            active.append((v, None))
            continue

        end_dt = datetime.strptime(
            v["end_datetime"], "%Y-%m-%d %H:%M"
        ).replace(tzinfo=UTC3)

        if now <= end_dt:
            active.append((v, end_dt))

        elif now <= end_dt + timedelta(days=7):
            finished.append((v, end_dt))

    text = "📋 <b>Список рестов</b>\n\n"

    # ================= АКТИВНЫЕ =================

    text += "🟢 <b>Активные:</b>\n\n"

    if not active:
        text += "Нет активных рестов.\n\n"

    else:
        for i, (v, end_dt) in enumerate(active, 1):

            username = v["username"]
            role = profiles.get(username.lower(), "нет роли")

            user_link = f'<a href="tg://resolve?domain={username}">{username}</a>'

            if v["end_datetime"] == "неопределенный":

                text += f"{i}. {user_link} | {role}\nнеопределенный\n\n"

            else:

                remaining = format_remaining(end_dt)

                text += (
                    f"{i}. {user_link} | {role}\n"
                    f"{v['start_datetime']} → {v['end_datetime']}\n"
                    f"(осталось: {remaining})\n\n"
                )

    # ================= ЗАВЕРШЁННЫЕ =================

    text += "🔴 <b>Завершённые:</b>\n\n"

    if not finished:
        text += "Нет завершённых рестов."

    else:
        for i, (v, end_dt) in enumerate(finished, 1):

            username = v["username"]
            role = profiles.get(username.lower(), "нет роли")

            user_link = f'<a href="tg://resolve?domain={username}">{username}</a>'

            text += (
                f"{i}. {user_link} | {role}\n"
                f"Рест закончился: {v['end_datetime']}\n\n"
            )

    return text


# ================= ОЧИСТКА =================

def clean_old(data):
    now = datetime.now(UTC3)
    updated = {}

    for key, v in data.items():

        if v["end_datetime"] == "неопределенный":
            updated[key] = v
            continue

        end_dt = datetime.strptime(
            v["end_datetime"], "%Y-%m-%d %H:%M"
        ).replace(tzinfo=UTC3)

        if now <= end_dt + timedelta(days=7):
            updated[key] = v

    save_json(VACATIONS_FILE, updated)
    return updated

# ================= МЕНЮ =================


# ================= CALLBACK =================

@router.callback_query(F.data == "add")
async def add_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    text = (
        "<b>Для добавления:</b>\n"
        "!!добавить рест @username YYYY-MM-DD YYYY-MM-DD,\n"
        "!!добавить рест @username 1-4 недель,\n"
        "!!добавить рест @username 1-4 месяцев,\n"
        "!!добавить рест @username ?"
    )

    await safe_edit(callback.message, text, main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "delete")
async def delete_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    text = "<b>Для удаления:</b>\n!!удалить рест @username"
    await safe_edit(callback.message, text, main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "list")
async def list_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    data = clean_old(load_json(VACATIONS_FILE))
    text = build_rest_list(data)

    await safe_edit(callback.message, text, main_keyboard())
    await callback.answer()

# =========================
# ДОБАВИТЬ РЕСТ
# =========================

@router.message(F.text.startswith("!!добавить рест"))
async def add_user_vacation(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) < 4:
        await message.reply(
            "❌ Использование:\n"
            "!!добавить рест @username YYYY-MM-DD YYYY-MM-DD\n"
            "!!добавить рест @username 2 недели\n"
            "!!добавить рест @username 1 месяц\n"
            "!!добавить рест @username ?"
        )
        return

    username_raw = parts[2]

    if not username_raw.startswith("@"):
        await message.reply("❌ Нужно указать @username")
        return

    clean_username = username_raw.replace("@", "").lower()

    data = load_json(VACATIONS_FILE)

    now = datetime.now(UTC3)
    start_dt = now
    end_dt = None

    # ================= НЕОПРЕДЕЛЕННЫЙ РЕСТ =================
    if parts[3] == "?":

        data[clean_username] = {
            "username": clean_username,
            "start_datetime": start_dt.strftime("%Y-%m-%d %H:%M"),
            "end_datetime": "неопределенный",
            "group_id": message.chat.id,
            "notified": False
        }

        save_json(VACATIONS_FILE, data)

        await message.reply("✅ Добавлен неопределённый рест.")
        return

    # ================= РЕСТ ПО ДАТАМ =================
    # !!добавить рест @user 2026-03-10 2026-03-20
    if len(parts) >= 5 and "-" in parts[3]:

        try:
            start_dt = datetime.strptime(parts[3], "%Y-%m-%d").replace(tzinfo=UTC3)

            end_dt = datetime.strptime(parts[4], "%Y-%m-%d").replace(
                hour=18,
                minute=0,
                tzinfo=UTC3
            )

        except:
            await message.reply("❌ Неверный формат даты.\nПример: 2026-03-10")
            return

    # ================= НЕДЕЛИ / МЕСЯЦЫ =================
    # !!добавить рест @user 2 недели
    # !!добавить рест @user 1 месяц
    elif len(parts) >= 5:

        try:
            amount = int(parts[3])
            unit = parts[4].lower()

            if "нед" in unit:
                end_dt = now + timedelta(weeks=amount)

            elif "мес" in unit:
                end_dt = now + timedelta(days=30 * amount)

            else:
                await message.reply("❌ Нужно указать недели или месяцы.")
                return

            end_dt = end_dt.replace(hour=18, minute=0, tzinfo=UTC3)

        except:
            await message.reply("❌ Неверный формат команды.")
            return

    else:
        await message.reply("❌ Неверный формат команды.")
        return

    # ================= СОХРАНЕНИЕ =================

    data[clean_username] = {
        "username": clean_username,
        "start_datetime": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end_datetime": end_dt.strftime("%Y-%m-%d %H:%M"),
        "group_id": message.chat.id,
        "notified": False
    }

    save_json(VACATIONS_FILE, data)

    await message.reply("✅ Рест выдан.")

# =========================
# УДАЛИТЬ РЕСТ
# =========================

@router.message(F.text.startswith("!!удалить рест"))
async def delete_rest_user(message: Message):

    if not is_admin(message.from_user.id):
        return

    data = load_json(VACATIONS_FILE)
    username = None

    # ================= УДАЛЕНИЕ ЧЕРЕЗ REPLY =================
    if message.reply_to_message:

        user = message.reply_to_message.from_user

        if not user.username:
            await message.reply("❌ У пользователя нет username.")
            return

        username = user.username.lower()

    # ================= УДАЛЕНИЕ ЧЕРЕЗ @username =================
    else:

        parts = message.text.split()

        if len(parts) < 3:
            await message.reply(
                "❌ Использование:\n"
                "!!удалить рест @username\n"
                "или ответьте на сообщение пользователя."
            )
            return

        username = parts[2]

        if not username.startswith("@"):
            await message.reply("❌ Нужно указать @username")
            return

        username = username.replace("@", "").lower()

    # ================= УДАЛЕНИЕ =================

    if username in data:
        del data[username]
        save_json(VACATIONS_FILE, data)
        await message.reply("✅ Пользователь удалён из реста.")
    else:
        await message.reply("❌ Этот пользователь не находится в ресте.")
# =========================
# /restlist с КД (красивый таймер)
# =========================

from datetime import datetime

chat_cooldown = {}
COOLDOWN_SECONDS = 120


def format_cooldown(seconds: int) -> str:
    minutes = seconds // 60
    sec = seconds % 60

    parts = []
    if minutes > 0:
        parts.append(f"{minutes} мин")
    if sec > 0:
        parts.append(f"{sec} сек")

    return " ".join(parts)


def has_full_access(user_id: int):
    return is_admin(user_id)


@router.message(F.text == "!!рестлист")
async def restlist(message: Message):

    user_id = message.from_user.id
    chat_id = message.chat.id

    # ================= КД ДЛЯ ОБЫЧНЫХ =================
    if not has_full_access(user_id):

        now = datetime.now()

        if chat_id in chat_cooldown:

            diff = (now - chat_cooldown[chat_id]).total_seconds()

            if diff < COOLDOWN_SECONDS:
                remaining = int(COOLDOWN_SECONDS - diff)

                await message.reply(
                    "⏳ <b>Список недавно уже запрашивали.</b>\n\n"
                    f"Попробуйте снова через: <b>{format_cooldown(remaining)}</b>"
                )
                return

        chat_cooldown[chat_id] = now

    # ================= ВЫВОД СПИСКА =================

    data = load_json(VACATIONS_FILE)
    text = build_rest_list(data)

    await message.answer(text)





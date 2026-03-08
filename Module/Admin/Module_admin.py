import os

from aiogram import Bot, Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.exceptions import TelegramBadRequest

from database import load_json, save_json

router = Router()
bot_instance: Bot | None = None

DATA_PATH = "Data.json"
ADMINS_FILE = "admins.json"


# ================= БОТ =================

def set_bot(bot: Bot):
    global bot_instance
    bot_instance = bot


# ================= ДОСТУП =================

def get_owner():
    data = load_json(DATA_PATH)
    return str(data.get("OWNER_ID"))


def is_owner(user_id: int):
    return str(user_id) == get_owner()


def is_admin(user_id: int):

    if is_owner(user_id):
        return True

    admins = load_json(ADMINS_FILE)

    return str(user_id) in admins


# ================= SAFE EDIT =================

async def safe_edit(message, text, markup):

    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass


# ================= КНОПКИ =================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить админа", callback_data="a_add")],
            [InlineKeyboardButton(text="🔰 Передать Создателя", callback_data="a_owner")],
            [InlineKeyboardButton(text="📋 Лист Администрации", callback_data="a_list")],
            [InlineKeyboardButton(text="❌ Снять админа", callback_data="a_del")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
        ]
    )


# ================= ПОИСК ПОЛЬЗОВАТЕЛЯ =================

async def find_user(message: Message):

    # ===== REPLY =====
    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()

    if len(parts) < 2:
        return None

    # берем последний аргумент команды
    target = parts[-1]

    # ===== ID =====
    if target.isdigit():
        try:
            return await bot_instance.get_chat(int(target))
        except:
            return None

    # ===== USERNAME =====
    if target.startswith("@"):

        username = target.replace("@", "").lower()

        # поиск через profiles.json
        try:
            from Module.Profile.Module_profile import load_profiles

            profiles = load_profiles()

            for uid, p in profiles.items():

                if p.get("username") and p["username"].lower() == username:
                    return await bot_instance.get_chat(int(uid))

        except:
            pass

        # прямой запрос Telegram
        try:
            return await bot_instance.get_chat(target)
        except:
            return None

    return None


# ================= CALLBACK =================

@router.callback_query(F.data.startswith("a_"))
async def admin_callbacks(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if callback.data == "a_add":

        text = (
            "➕ <b>Добавить админа</b>\n\n"
            "Команда:\n"
            "!!выдать админа @username"
        )

    elif callback.data == "a_owner":

        text = (
            "🔰 <b>Передать Создателя</b>\n\n"
            "Команда:\n"
            "!!передать владельца @username"
        )

    elif callback.data == "a_del":

        text = (
            "❌ <b>Снять админа</b>\n\n"
            "Команда:\n"
            "!!снять админа @username"
        )

    elif callback.data == "a_list":

        text = await build_admin_list()

    await safe_edit(callback.message, text, admin_keyboard())

    await callback.answer()


# ================= СПИСОК АДМИНОВ =================

async def build_admin_list():

    owner = get_owner()
    admins = load_json(ADMINS_FILE)
    profiles = load_json("profiles.json")

    text = "📋 <b>Лист администрации</b>\n\n"

    # ===== СОЗДАТЕЛЬ =====

    text += "🔰 <b>Создатель</b>\n\n"

    try:

        chat = await bot_instance.get_chat(int(owner))
        name = chat.full_name

        role = profiles.get(owner, {}).get("role", "нет роли")

        text += f"1. <a href='tg://user?id={chat.id}'>{name}</a> | {role}\n\n"

    except:

        text += f"1. <code>{owner}</code>\n\n"

    # ===== АДМИНЫ =====

    text += "❇️ <b>Админы</b>\n\n"

    if not admins:
        text += "Нет админов."
        return text

    for i, admin_id in enumerate(admins, 1):

        role = profiles.get(admin_id, {}).get("role", "нет роли")

        try:

            chat = await bot_instance.get_chat(int(admin_id))
            name = chat.full_name

            display = f"<a href='tg://user?id={chat.id}'>{name}</a> | {role}"

        except:

            display = f"<code>{admin_id}</code> | {role}"

        text += f"{i}. {display}\n"

    return text


# ================= ВЫДАТЬ АДМИНА =================

@router.message(F.text.startswith("!!выдать админа"))
async def add_admin(message: Message):

    if not is_owner(message.from_user.id):
        return

    user = await find_user(message)

    if not user:
        await message.reply("❌ Пользователь не найден.")
        return

    if user.id == message.from_user.id:
        await message.reply("❌ Нельзя выдать админку самому себе.")
        return

    admins = load_json(ADMINS_FILE)

    if str(user.id) in admins:
        await message.reply("⚠️ Уже админ.")
        return

    admins[str(user.id)] = {
        "username": user.username or ""
    }

    save_json(ADMINS_FILE, admins)

    await message.reply(f"✅ @{user.username or user.id} добавлен в админы.")


# ================= СНЯТЬ АДМИНА =================

@router.message(F.text.startswith("!!снять админа"))
async def remove_admin(message: Message):

    if not is_owner(message.from_user.id):
        return

    user = await find_user(message)

    if not user:
        await message.reply("❌ Пользователь не найден.")
        return

    if str(user.id) == get_owner():
        await message.reply("❌ Нельзя снять владельца.")
        return

    admins = load_json(ADMINS_FILE)

    if str(user.id) not in admins:
        await message.reply("❌ Этот пользователь не админ.")
        return

    del admins[str(user.id)]

    save_json(ADMINS_FILE, admins)

    await message.reply("✅ Админ снят.")


# ================= ПЕРЕДАТЬ ВЛАДЕЛЬЦА =================

@router.message(F.text.startswith("!!передать владельца"))
async def give_owner(message: Message):

    if not is_owner(message.from_user.id):
        return

    user = await find_user(message)

    if not user:
        await message.reply("❌ Пользователь не найден.")
        return

    data = load_json(DATA_PATH)

    data["OWNER_ID"] = user.id

    save_json(DATA_PATH, data)

    await message.reply("🔰 Создатель передан.")





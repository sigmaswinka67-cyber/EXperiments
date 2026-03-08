import json
import os
from aiogram import Bot
from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

router = Router()
bot_instance: Bot | None = None
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATA_PATH = "Data.json"
ADMINS_FILE = "admins.json"

# ================= ПОИСК ПОЛЬЗОВАТЕЛЯ =================

async def find_user(message: Message):

    # если ответ на сообщение
    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()

    if len(parts) < 2:
        return None

    target = parts[1]

    # ================= ID =================
    if target.isdigit():
        try:
            return await bot_instance.get_chat(int(target))
        except:
            pass

    # ================= USERNAME =================
    if target.startswith("@"):

        username = target.replace("@", "").lower()

        # поиск в profiles.json
        try:
            from Module.Profile.Module_profile import load_profiles
            profiles = load_profiles()

            for uid, p in profiles.items():
                if p.get("username") and p["username"].lower() == username:
                    return await bot_instance.get_chat(int(uid))
        except:
            pass

        # попытка через telegram
        try:
            return await bot_instance.get_chat(target)
        except:
            pass

    return None

# ================= JSON =================


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ================= ДОСТУП =================

def get_owner():
    data = load_json(DATA_PATH)
    return data.get("OWNER_ID")
def is_owner(user_id: int):
    return str(user_id) == str(get_owner())

def is_admin(user_id: int):
    if str(user_id) == str(get_owner()):
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

# ================= Овнер имя =================

def set_bot(bot: Bot):
    global bot_instance
    bot_instance = bot
# ================= CALLBACK =================

@router.callback_query(F.data.startswith("a_"))
async def admin_callbacks(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    if callback.data == "a_add":
        text = (
            "➕ <b>Добавить админа</b>\n"
            "Добавить админа:\n"
            "!!выдать админа @username\n\n"
        )

    elif callback.data == "a_owner":
        text = (
            "🔰 <b>Передать Создателя</b>\n"
            "Передать владельца:\n"
            "!!передать владельца @username\n\n"
        )


    elif callback.data == "a_list":

        text = await build_admin_list()

    elif callback.data == "a_del":
        text = (
            "❌ <b>Снять админа</b>\n"
            "Для удаления админа:\n"
            "!!снять админа @username\n\n"
        )

    await safe_edit(callback.message, text, admin_keyboard())
    await callback.answer()

# ================= ЛИСТ =================

async def build_admin_list():

    owner = get_owner()
    admins = load_json(ADMINS_FILE)
    profiles = load_json("profiles.json")

    text = "📋 <b>Лист администрации</b>\n\n"

    # ================= СОЗДАТЕЛЬ =================
    text += "🔰 <b>Создатель:</b>\n\n"

    owner_display = "Не назначен"

    if owner:

        role = ""
        if str(owner) in profiles:
            role = profiles[str(owner)].get("role") or "нет роли"

        # если хранится ID
        if str(owner).isdigit() and bot_instance:
            try:
                chat = await bot_instance.get_chat(int(owner))
                name = chat.full_name
                owner_display = f'<a href="tg://user?id={chat.id}">{name}</a> | {role}'

            except:
                owner_display = f"<code>{owner}</code> | {role}"

        elif str(owner).startswith("@"):
            owner_display = f"{owner} | {role}"

        else:
            owner_display = f"<code>{owner}</code> | {role}"

    text += f"1. {owner_display}\n\n"

    # ================= АДМИНЫ =================
    text += "❇️ <b>Админы:</b>\n\n"

    if not admins:
        text += "Нет админов."
    else:
        for i, (admin_id, data) in enumerate(admins.items(), 1):

            username = data.get("username")

            role = "нет роли"
            if admin_id in profiles:
                role = profiles[admin_id].get("role") or "нет роли"

            try:
                chat = await bot_instance.get_chat(int(admin_id))
                name = chat.full_name
                admin_display = f'<a href="tg://user?id={chat.id}">{name}</a> | {role}'
            except:
                    admin_display = f"<code>{admin_id}</code> | {role}"

            text += f"{i}. {admin_display}\n"

    return text
# ================= КОМАНДЫ =================

@router.message(F.text.startswith("!!выдать админа"))
async def add_admin(message: Message):

    # доступ только owner
    if not is_owner(message.from_user.id):
        return

    user = await find_user(message)

    if not user:
        await message.reply("❌ Пользователь не найден.")
        return

    # нельзя выдать самому себе
    if user.id == message.from_user.id:
        await message.reply("❌ Нельзя выдать админку самому себе.")
        return

    # нельзя выдать owner
    if str(user.id) == str(get_owner()):
        await message.reply("❌ Этот пользователь уже владелец.")
        return

    admins = load_json(ADMINS_FILE)

    if str(user.id) in admins:
        await message.reply("⚠️ Этот пользователь уже админ.")
        return

    admins[str(user.id)] = {
        "username": user.username or ""
    }

    save_json(ADMINS_FILE, admins)

    await message.reply(f"✅ @{user.username or user.id} добавлен в админы.")
@router.message(F.text.startswith("!!снять админа"))
async def remove_admin(message: Message):

    if not is_owner(message.from_user.id):
        return

    user = await find_user(message)

    if not user:
        await message.reply("❌ Пользователь не найден.")
        return

    # нельзя снять owner
    if str(user.id) == str(get_owner()):
        await message.reply("❌ Нельзя снять владельца.")
        return

    admins = load_json(ADMINS_FILE)

    if str(user.id) not in admins:
        await message.reply("❌ Этот пользователь не админ.")
        return

    del admins[str(user.id)]

    save_json(ADMINS_FILE, admins)

    await message.reply("✅ Админ снят.")
@router.message(F.text.startswith("!!передать владельца"))
async def give_owner(message: Message):

    if message.from_user.id != get_owner():
        return

    user = await find_user(message)

    if not user:
        await message.reply("❌ Пользователь не найден.")
        return

    new_owner = user.id

    data = load_json(DATA_PATH)
    data["OWNER_ID"] = new_owner
    save_json(DATA_PATH, data)


    await message.reply("🔰 Создатель передан.")




import os
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import load_json, save_json

router = Router()

bot_instance = None

def set_bot(bot):
    global bot_instance
    bot_instance = bot


DATA_PATH = "data.json"
ADMINS_FILE = "admins.json"
PROFILES_FILE = "profiles.json"
VACATIONS_FILE = "vacations.json"

UTC3 = timezone(timedelta(hours=3))


# ================= ДОСТУП =================

def get_owner():
    data = load_json(DATA_PATH)
    return str(data.get("OWNER_ID"))

def is_admin(user_id: int):

    if str(user_id) == get_owner():
        return True

    admins = load_json(ADMINS_FILE)
    return str(user_id) in admins


def get_position(user_id):

    if str(user_id) == get_owner():
        return "создатель"

    if is_admin(user_id):
        return "админ"

    return "участник"


# ================= ПРОФИЛИ =================

def load_profiles():
    return load_json(PROFILES_FILE)

def save_profiles(data):
    save_json(PROFILES_FILE, data)


# ================= УТИЛИТЫ =================

def shorten(text, limit=25):
    return text[:limit] + "..." if len(text) > limit else text


def days_until_birthday(date_str):

    try:

        month, day = map(int, date_str.split("-"))

        today = datetime.now()
        next_bday = datetime(today.year, month, day)

        if next_bday < today:
            next_bday = datetime(today.year + 1, month, day)

        return (next_bday - today).days

    except:
        return None


# ================= РЕСТ =================

def get_rest_status(username):

    data = load_json(VACATIONS_FILE)

    if not username:
        return "нету"

    username = username.lower()

    # ищем ключ и с @ и без
    v = data.get(username) or data.get("@" + username)

    if not v:
        return "нету"

    if v["end_datetime"] == "неопределенный":
        return "неопределенный"

    try:
        end_dt = datetime.strptime(
            v["end_datetime"], "%Y-%m-%d %H:%M"
        ).replace(tzinfo=UTC3)
    except:
        return "нету"

    now = datetime.now(UTC3)

    end_formatted = end_dt.strftime("%m-%d")

    if now <= end_dt:
        return f"до {end_formatted}"

    if now <= end_dt + timedelta(days=7):
        return f"до {end_formatted}"

    return "нету"


# ================= ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ =================

async def get_target_user(message: Message):

    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()

    if len(parts) >= 2 and parts[-1].startswith("@"):

        username = parts[-1].replace("@", "").lower()

        profiles = load_profiles()

        for uid, p in profiles.items():

            if p.get("username") and p["username"].lower() == username:
                return await bot_instance.get_chat(int(uid))

        await message.reply("❌ Пользователь не найден.")
        return None

    return message.from_user


# ================= КЛАВИАТУРА =================

def profile_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать профиль", callback_data="profile_create")],
            [InlineKeyboardButton(text="👤 Профиль", callback_data="profile_view")],
            [InlineKeyboardButton(text="⚙ Редактировать профиль", callback_data="profile_edit")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
        ]
    )

# =========================
# ОПИСАНИЕ КОМАНД
# =========================


@router.callback_query(lambda c: c.data == "profile_create")
async def profile_create_info(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_text(
        "➕ <b>Создать профиль</b>\n"
        "Используйте:\n"
        "!!создать профиль",
        reply_markup=profile_keyboard()
    )


@router.callback_query(lambda c: c.data == "profile_view")
async def profile_view_info(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_text(
        "👤 <b>Профиль</b>\n"
        "Для просмотра используйте:\n"
        "!!профиль @username или в ответ на сообщение",
        reply_markup=profile_keyboard()
    )


@router.callback_query(lambda c: c.data == "profile_edit")
async def profile_edit_info(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_text(
        "⚙ <b>Редактировать профиль</b>\n"
        "Используйте:\n"
        "!!редактировать профиль @username или в ответ",
        reply_markup=profile_keyboard()
    )

# ================= СОЗДАТЬ ПРОФИЛЬ =================

@router.message(F.text.startswith("!!создать профиль"))
async def create_profile(message: Message):

    if not is_admin(message.from_user.id):
        return

    target = await get_target_user(message)

    if not target:
        return

    profiles = load_profiles()

    user_id = str(target.id)

    if user_id in profiles:
        await message.reply("⚠️ Профиль уже существует.")
        return

    profiles[user_id] = {
        "name": target.full_name,
        "username": target.username,
        "role": "",
        "pronoun": None,
        "birthday": None
    }

    save_profiles(profiles)

    await message.reply(f"✅ Профиль создан для @{target.username or target.full_name}")


# ================= ПРОФИЛЬ =================

@router.message(F.text.startswith("!!профиль"))
async def show_profile(message: Message):

    target = await get_target_user(message)

    if not target:
        return

    profiles = load_profiles()

    p = profiles.get(str(target.id))

    if not p:
        await message.reply("❌ Профиль не найден.")
        return

    name = shorten(target.full_name)

    user_link = f'<a href="tg://user?id={target.id}">{name}</a>'

    username = p.get("username") or target.username

    rest_text = get_rest_status(username) if username else "нету"

    role = p.get("role") or "нет роли"
    pronoun = p.get("pronoun") or "не указано"

    birthday = p.get("birthday")

    if birthday:
        days = days_until_birthday(birthday)
        birthday_text = f"{birthday} ({days} дн.)"
    else:
        birthday_text = "не указано"

    position = get_position(target.id)

    text = (
        f"👤 {user_link} | {role}\n"
        f"🧬 Местоимение: {pronoun}\n"
        f"🔰 Должность: {position}\n"
        f"📅 Рест: {rest_text}\n"
        f"🎂 День рождения: {birthday_text}"
    )

    await message.reply(text, parse_mode="HTML")


# ================= РЕДАКТИРОВАТЬ =================

@router.message(F.text.startswith("!!редактировать профиль"))
async def edit_profile(message: Message):

    target = await get_target_user(message)

    if not target:
        return

    if target.id != message.from_user.id and not is_admin(message.from_user.id):
        await message.reply("❌ Можно редактировать только свой профиль.")
        return

    profiles = load_profiles()

    if str(target.id) not in profiles:
        await message.reply("❌ Профиль не найден.")
        return

    kb = InlineKeyboardBuilder()

    caller = message.from_user.id
    user_id = target.id

    if is_admin(caller):
        kb.button(text="Роль", callback_data=f"role_{user_id}_{caller}")

    if caller == user_id:

        kb.button(text="Местоимение", callback_data=f"pronoun_{user_id}_{caller}")
        kb.button(text="День рождения", callback_data=f"birthday_{user_id}_{caller}")

    kb.adjust(1)

    await message.reply("⚙️ Редактирование профиля", reply_markup=kb.as_markup())


# ================= МЕСТОИМЕНИЯ =================

@router.callback_query(F.data.startswith("pronoun_"))
async def pronoun_menu(callback: CallbackQuery):

    _, user_id, caller = callback.data.split("_")

    if callback.from_user.id != int(caller):
        return await callback.answer()

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Он", callback_data=f"setpron_{user_id}_{caller}_он")],
            [InlineKeyboardButton(text="Она", callback_data=f"setpron_{user_id}_{caller}_она")],
            [InlineKeyboardButton(text="Они", callback_data=f"setpron_{user_id}_{caller}_они")]
        ]
    )

    await callback.message.edit_text("Выберите местоимение", reply_markup=kb)


@router.callback_query(F.data.startswith("setpron_"))
async def set_pronoun(callback: CallbackQuery):

    _, user_id, caller, pronoun = callback.data.split("_")

    if callback.from_user.id != int(caller):
        return await callback.answer()

    profiles = load_profiles()

    profiles[user_id]["pronoun"] = pronoun

    save_profiles(profiles)

    await callback.message.edit_text("✅ Местоимение обновлено")


# ================= РОЛЬ =================

waiting_role = {}

@router.callback_query(F.data.startswith("role_"))
async def ask_role(callback: CallbackQuery):

    _, user_id, caller = callback.data.split("_")

    if callback.from_user.id != int(caller):
        return await callback.answer()

    if not is_admin(callback.from_user.id):
        return await callback.answer()

    waiting_role[callback.from_user.id] = user_id

    await callback.message.answer("Введите роль")


@router.message(lambda m: m.from_user.id in waiting_role)
async def set_role(message: Message):

    role = message.text.strip()

    if len(role) > 25:
        await message.reply("❌ Роль до 25 символов.")
        return

    user_id = waiting_role.pop(message.from_user.id)

    profiles = load_profiles()

    profiles[user_id]["role"] = role

    save_profiles(profiles)

    await message.reply("✅ Роль сохранена.")


# ================= ДЕНЬ РОЖДЕНИЯ =================

waiting_birthday = {}

@router.callback_query(F.data.startswith("birthday_"))
async def ask_birthday(callback: CallbackQuery):

    _, user_id, caller = callback.data.split("_")

    if callback.from_user.id != int(caller):
        return await callback.answer()

    waiting_birthday[callback.from_user.id] = user_id

    await callback.message.answer("Введите дату ММ-ДД")


@router.message(lambda m: m.from_user.id in waiting_birthday)
async def set_birthday(message: Message):

    text = message.text.strip()

    try:

        month, day = map(int, text.split("-"))

        if not 1 <= month <= 12 or not 1 <= day <= 31:
            raise ValueError

    except:
        await message.reply("❌ Формат ММ-ДД\nПример: 05-21")
        return

    user_id = waiting_birthday.pop(message.from_user.id)

    profiles = load_profiles()

    profiles[user_id]["birthday"] = text

    save_profiles(profiles)

    await message.reply("🎂 День рождения сохранён.")


# ================= СПИСОК ДР =================

@router.message(F.text == "!!дрлист")
async def birthday_list(message: Message):

    profiles = load_profiles()

    users = []

    for uid, p in profiles.items():

        birthday = p.get("birthday")

        if not birthday:
            continue

        days = days_until_birthday(birthday)

        role = p.get("role") or "нет роли"

        users.append((days, role, birthday))

    if not users:
        return await message.reply("🎂 Нет дней рождения.")

    users.sort(key=lambda x: x[0])

    text = "🎂 <b>Список дней рождения</b>\n\n"

    for days, role, birthday in users:
        text += f"• {role} — {birthday} ({days} дн.)\n"

    await message.reply(text, parse_mode="HTML")
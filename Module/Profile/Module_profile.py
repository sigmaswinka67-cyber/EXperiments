import json
import os
from datetime import datetime, timedelta, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from Module.Rest import Module_rest

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

# =========================
# МЕНЮ ПРОФИЛЕЙ
# =========================




def profile_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Создать профиль",
                    callback_data="profile_create"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👤 Профиль",
                    callback_data="profile_view"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙ Редактировать профиль",
                    callback_data="profile_edit"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="back_main"
                )
            ]
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
# ================= JSON =================

def load_json(path):
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ================= ДОСТУП =================

def get_owner():
    data = load_json(DATA_PATH)
    return data.get("OWNER_ID")


def is_admin(user_id: int):
    if str(user_id) == str(get_owner()):
        return True

    admins = load_json(ADMINS_FILE)
    return str(user_id) in admins


# ================= получение звнаний =================

def get_position(user_id):

    if user_id == get_owner():
        return "создатель"

    admins = load_json(ADMINS_FILE)

    if str(user_id) in admins:
        return "админ"

    return "участник"

# ================= Ресты =================
def get_rest_status(username):

    data = load_json(VACATIONS_FILE)

    username = username.lower()

    if username not in data:
        return "нету"

    v = data[username]

    # неопределённый рест
    if v["end_datetime"] == "неопределенный":
        return "неопределенный"

    end_dt = datetime.strptime(
        v["end_datetime"], "%Y-%m-%d %H:%M"
    ).replace(tzinfo=UTC3)

    now = datetime.now(UTC3)

    # формат MM-DD
    end_formatted = end_dt.strftime("%m-%d")

    # активный
    if now <= end_dt:
        return f"до {end_formatted}"

    # завершённый (до 7 дней)
    elif now <= end_dt + timedelta(days=7):
        return f"до {end_formatted}"

    return "нету"
# ============== ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЯ ==============

async def get_target_user(message: Message):

    # если ответ на сообщение
    if message.reply_to_message:
        return message.reply_to_message.from_user

    parts = message.text.split()

    # поиск по username
    if len(parts) >= 2 and parts[-1].startswith("@"):

        username = parts[-1].replace("@", "").lower()

        profiles = load_profiles()

        for user_id, p in profiles.items():

            if p.get("username") and p["username"].lower() == username:
                try:
                    return await bot_instance.get_chat(int(user_id))
                except:
                    return None

        await message.reply("❌ Пользователь не найден.")
        return None

    return message.from_user
# ================= ПРОФИЛИ =================

def load_profiles():
    return load_json(PROFILES_FILE)


def save_profiles(data):
    save_json(PROFILES_FILE, data)


# ================= УТИЛИТЫ =================

def shorten(text, limit=25):
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def days_until_birthday(date_str):
    try:
        month, day = map(int, date_str.split("-"))

        today = datetime.now()
        next_bday = datetime(today.year, month, day)

        if next_bday < today:
            next_bday = datetime(today.year + 1, month, day)

        diff = (next_bday - today).days

        return diff
    except:
        return None


# ================= СОЗДАТЬ ПРОФИЛЬ =================

@router.message(lambda m: m.text and m.text.startswith("!!создать профиль"))
async def create_profile(message: Message):

    if not is_admin(message.from_user.id):
        return

    target = await get_target_user(message)

    if not target:
        await message.reply("❌ Пользователь не найден.")
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


# ================= ПОКАЗАТЬ ПРОФИЛЬ =================

@router.message(lambda m: m.text and m.text.startswith("!!профиль"))
async def show_profile(message: Message):

    target = await get_target_user(message)

    if not target:
        await message.reply("❌ Пользователь не найден.")
        return

    profiles = load_profiles()

    user_id = str(target.id)

    p = profiles.get(user_id)

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
        birthday_text = f"{birthday} ({days} дней)"
    else:
        birthday_text = "не указано"

    position = "участник"

    if is_admin(target.id):
        position = "админ"

    if str(target.id) == str(get_owner()):
        position = "создатель"

    text = (
        f"👤 {user_link} | {role}\n"
        f"🧬 Местоимение: {pronoun}\n"
        f"🔰 Должность: {position}\n"
        f"📅 Рест: {rest_text}\n"
        f"🎂 День рождения: {birthday_text}"
    )

    await message.reply(text, parse_mode="HTML")


# ================= РЕДАКТИРОВАТЬ =================

@router.message(lambda m: m.text and m.text.startswith("!!редактировать профиль"))
async def edit_profile(message: Message):

    profiles = load_profiles()

    target = await get_target_user(message)

    if not target:
        await message.reply("❌ Пользователь не найден.")
        return

    # если пытаются редактировать чужой профиль
    if target.id != message.from_user.id and not is_admin(message.from_user.id):
        await message.reply("❌ Вы можете редактировать только свой профиль.")
        return

    user_id = str(target.id)

    if user_id not in profiles:
        await message.reply("❌ Профиль не найден.")
        return

    kb = InlineKeyboardBuilder()

    caller_id = message.from_user.id

    if is_admin(caller_id):
        kb.button(
            text="Роль",
            callback_data=f"profile_role_{user_id}_{caller_id}"
        )

    if caller_id == target.id:
        kb.button(
            text="Местоимение",
            callback_data=f"profile_pronoun_{user_id}_{caller_id}"
        )

        kb.button(
            text="День рождения",
            callback_data=f"profile_birthday_{user_id}_{caller_id}"
        )

    kb.adjust(1)

    await message.reply(
        "⚙️ Редактирование профиля",
        reply_markup=kb.as_markup()
    )

# ================= МЕСТОИМЕНИЯ =================

async def pronoun_menu(callback: CallbackQuery):

    _, _, user_id, caller_id = callback.data.split("_")

    if callback.from_user.id != int(caller_id):
        await callback.answer()
        return

    kb = InlineKeyboardBuilder()

    kb.button(text="Он", callback_data=f"set_pronoun_{user_id}_{caller_id}_он")
    kb.button(text="Она", callback_data=f"set_pronoun_{user_id}_{caller_id}_она")
    kb.button(text="Они", callback_data=f"set_pronoun_{user_id}_{caller_id}_они")

    kb.adjust(1)

    await callback.message.edit_text(
        "Выберите местоимение",
        reply_markup=kb.as_markup()
    )


@router.callback_query(lambda c: c.data.startswith("set_pronoun"))
async def set_pronoun(callback: CallbackQuery):
    _, _, user_id, caller_id, pronoun = callback.data.split("_")

    if callback.from_user.id != int(caller_id):
        await callback.answer()
        return

    profiles = load_profiles()

    profiles[user_id]["pronoun"] = pronoun

    save_profiles(profiles)

    await callback.message.edit_text("✅ Местоимение обновлено")


# ================= УСТАНОВКА РОЛИ =================

waiting_role = {}

@router.callback_query(lambda c: c.data.startswith("profile_role"))
async def ask_role(callback: CallbackQuery):

    _, _, user_id, caller_id = callback.data.split("_")

    if callback.from_user.id != int(caller_id):
        await callback.answer()
        return

    if not is_admin(callback.from_user.id):
        await callback.answer()
        return

    user_id = callback.data.split("_")[2]

    # записываем кто нажал кнопку
    waiting_role[callback.from_user.id] = user_id

    await callback.message.answer(
        "Введите роль"
    )

    await callback.answer()


@router.message(lambda m: m.from_user.id in waiting_role)
async def set_role(message: Message):

    admin_id = message.from_user.id

    # проверяем что именно этот человек нажал кнопку
    if admin_id not in waiting_role:
        return

    if not is_admin(admin_id):
        waiting_role.pop(admin_id, None)
        return

    role = message.text.strip()

    if len(role) > 25:
        await message.reply("❌ Роль должна быть до 25 символов.")
        return

    target_id = waiting_role.pop(admin_id)

    profiles = load_profiles()

    if target_id not in profiles:
        await message.reply("❌ Профиль не найден.")
        return

    profiles[target_id]["role"] = role

    save_profiles(profiles)

    await message.reply("✅ Роль сохранена.")

# ================= ДЕНЬ РОЖДЕНИЯ =================
waiting_birthday = {}
@router.callback_query(lambda c: c.data.startswith("profile_birthday"))
async def ask_birthday(callback: CallbackQuery):

    _, _, user_id, caller_id = callback.data.split("_")

    if callback.from_user.id != int(caller_id):
        await callback.answer()
        return

    waiting_birthday[callback.from_user.id] = user_id

    await callback.message.answer(
        "Введите дату дня рождения в формате ММ-ДД"
    )

    await callback.answer()


@router.message(lambda m: m.from_user.id in waiting_birthday)
async def set_birthday(message: Message):

    text = message.text.strip()

    try:
        month, day = map(int, text.split("-"))

        if month < 1 or month > 12 or day < 1 or day > 31:
            raise ValueError

    except:
        await message.reply("❌ Неверный формат. Используйте ММ-ДД\nПример: 05-21")
        return

    user_id = waiting_birthday.pop(message.from_user.id)

    profiles = load_profiles()

    if user_id not in profiles:
        await message.reply("❌ Профиль не найден.")
        return

    profiles[user_id]["birthday"] = text

    save_profiles(profiles)

    await message.reply("🎂 День рождения сохранён.")
# ================= СПИСОК ДНЕЙ РОЖДЕНИЯ =================

@router.message(lambda m: m.text and m.text.startswith("!!дрлист"))
async def birthday_list(message: Message):

    profiles = load_profiles()

    if not profiles:
        await message.reply("❌ Профили не найдены.")
        return

    birthday_users = []

    for user_id, p in profiles.items():

        birthday = p.get("birthday")

        if not birthday:
            continue

        days = days_until_birthday(birthday)

        role = p.get("role") or "нет роли"

        birthday_users.append((days, role, birthday))

    if not birthday_users:
        await message.reply("🎂 В списке нет дней рождения.")
        return

    # сортировка по ближайшему ДР
    birthday_users.sort(key=lambda x: x[0])

    text = "🎂 <b>Список дней рождения</b>\n\n"

    for days, role, birthday in birthday_users:
        text += f"• {role} — {birthday} ({days} дн.)\n"

    await message.reply(text, parse_mode="HTML")


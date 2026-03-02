# app/keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Добавить тему"), KeyboardButton(text="🧠 Пройти повтор")],
            [KeyboardButton(text="🏆 Профиль"), KeyboardButton(text="⏰ Напоминания")],
            [KeyboardButton(text="📚 Предметы"), KeyboardButton(text="🤖 AI")],
            [KeyboardButton(text="🖼 Галерея")],
            [KeyboardButton(text="🤝 Помощь друга")],
        ],
        resize_keyboard=True
    )


# ---------- SUBJECTS ----------
def subjects_kb(subjects: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for name in subjects:
        kb.button(text=name, callback_data=f"sub:{name}")
    kb.adjust(2)
    kb.button(text="⬅️ Назад", callback_data="sub:back")
    return kb.as_markup()


def subject_menu_kb(subject_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать папку", callback_data=f"sf:new:{subject_id}")
    kb.button(text="📁 Мои папки", callback_data=f"sf:list:{subject_id}")
    kb.button(text="⬅️ К предметам", callback_data="sf:back")
    kb.adjust(1)
    return kb.as_markup()


def folders_kb(subject_id: int, folders: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in folders:
        kb.button(
            text=f"📁 {f['title']} ({f['created_at']})",
            callback_data=f"fold:open:{f['id']}"
        )
    kb.adjust(1)
    kb.button(text="⬅️ Назад", callback_data=f"sf:listback:{subject_id}")
    return kb.as_markup()


def folder_menu_kb(folder_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить тему", callback_data=f"fm:topic:{folder_id}")
    kb.button(text="📸 Загрузить фото", callback_data=f"fm:photo:{folder_id}")
    kb.button(text="📄 Показать содержимое", callback_data=f"fm:view:{folder_id}")
    kb.button(text="⬅️ К папкам", callback_data=f"fm:back:{folder_id}")
    kb.adjust(1)
    return kb.as_markup()


def help_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать запрос", callback_data="help:new")
    kb.button(text="📋 Список запросов", callback_data="help:list")
    kb.button(text="⬅️ Назад", callback_data="help:back")
    kb.adjust(1)
    return kb.as_markup()


def assistant_levels_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="1️⃣ Как ребёнку", callback_data="assist:level:1")
    kb.button(text="2️⃣ Обычное", callback_data="assist:level:2")
    kb.button(text="3️⃣ Академ.", callback_data="assist:level:3")
    kb.button(text="⬅️ Назад", callback_data="assist:back")
    kb.adjust(1)
    return kb.as_markup()
# ---------- GALLERY ----------
def gallery_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить фото", callback_data="gallery:add")
    kb.button(text="📁 Моя галерея", callback_data="gallery:my")
    kb.button(text="👥 Галерея друга", callback_data="gallery:friend")
    kb.button(text="⬅️ Назад", callback_data="gallery:back")
    kb.adjust(1)
    return kb.as_markup()


def gallery_list_kb(items: list[dict], owner_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for idx, it in enumerate(items, start=1):
        title = it['title'] if len(it['title']) <= 32 else it['title'][:29] + "…"
        kb.button(
            text=f"{idx}. {title}",
            callback_data=f"gallery:view:{it['id']}:{owner_id}"
        )
    kb.adjust(1)
    kb.button(text="⬅️ Назад", callback_data=f"gallery:back")
    return kb.as_markup()

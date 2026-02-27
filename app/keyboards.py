from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .config import SUBJECTS

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Добавить тему"), KeyboardButton(text="🧠 Пройти повтор")],
        [KeyboardButton(text="📚 Предметы"), KeyboardButton(text="🤝 Помощь друга")],
        [KeyboardButton(text="🤖 Ассистент"), KeyboardButton(text="🏆 Профиль")],
        [KeyboardButton(text="⏰ Напоминания")],
    ],
    resize_keyboard=True
)

def subjects_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in SUBJECTS:
        b.button(text=s, callback_data=f"sub:{s}")
    b.adjust(2)
    return b.as_markup()

def subject_menu_kb(subject: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Добавить материал", callback_data=f"subadd:{subject}")
    b.button(text="📂 Материалы", callback_data=f"sublist:{subject}")
    b.button(text="🔎 Поиск", callback_data=f"subsearch:{subject}")
    b.button(text="⬅️ Назад к предметам", callback_data="subback")
    b.adjust(1)
    return b.as_markup()

def help_menu_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="➕ Создать запрос", callback_data="help:new")
    b.button(text="📌 Открытые запросы", callback_data="help:list")
    b.adjust(1)
    return b.as_markup()

def assistant_levels_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="1️⃣ Как ребёнку", callback_data="ai:l1")
    b.button(text="2️⃣ Обычное", callback_data="ai:l2")
    b.button(text="3️⃣ Академично", callback_data="ai:l3")
    b.adjust(1)
    return b.as_markup()
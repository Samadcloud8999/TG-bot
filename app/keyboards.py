# app/keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Добавить тему"), KeyboardButton(text="🧠 Пройти повтор")],
            [KeyboardButton(text="🏆 Профиль"), KeyboardButton(text="⏰ Напоминания")],
            [KeyboardButton(text="📚 Предметы"), KeyboardButton(text="🤖 Ассистент")],
            [KeyboardButton(text="🤝 Помощь друга")],
        ],
        resize_keyboard=True
    )

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
        # пример: "📁 Алгебра ДЗ (2026-02-27 22:10)"
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
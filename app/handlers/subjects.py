from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from ..keyboards import subjects_kb, subject_menu_kb
from .. import db

router = Router()

# текущее выбранное пользователем "куда добавлять"
CURRENT_SUBJECT = {}

@router.message(F.text == "📚 Предметы")
async def subjects(msg: Message):
    await msg.answer("Выбери предмет 👇", reply_markup=subjects_kb())

@router.callback_query(F.data == "subback")
async def sub_back(cb: CallbackQuery):
    await cb.message.edit_text("Выбери предмет 👇", reply_markup=subjects_kb())
    await cb.answer()

@router.callback_query(F.data.startswith("sub:"))
async def sub_choose(cb: CallbackQuery):
    subject = cb.data.split("sub:", 1)[1]
    tg_id = cb.from_user.id
    CURRENT_SUBJECT[tg_id] = subject

    # гарантируем наличие пользователя и предмета
    await db.db.execute("INSERT OR IGNORE INTO users(tg_id) VALUES(?)", (tg_id,))
    await db.db.execute("INSERT OR IGNORE INTO user_subjects(tg_id, subject) VALUES(?,?)", (tg_id, subject))
    await db.db.commit()

    await cb.message.edit_text(
        f"📚 Предмет: **{subject}**\nВыбери действие:",
        reply_markup=subject_menu_kb(subject),
        parse_mode="Markdown"
    )
    await cb.answer()
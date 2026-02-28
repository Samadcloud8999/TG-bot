# app/handlers/subjects.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from ..db import db
from ..keyboards import subjects_kb, subject_menu_kb, folders_kb, main_kb

router = Router()

SUBJECTS = [
    "Алгебра", "Геометрия", "Биология", "Химия", "Физика",
    "География", "История", "ЧиО", "ПО/Информатика",
    "Русский язык", "Литература", "Английский", "Кыргызский",
    "Адабият", "ДПМ", "БЯП"
]

class FolderStates(StatesGroup):
    waiting_folder_title = State()

@router.message(F.text == "📚 Предметы")
async def subjects_start(msg: Message):
    await msg.answer("Выбери предмет:", reply_markup=subjects_kb(SUBJECTS))

@router.callback_query(F.data == "sub:back")
async def subjects_back(call: CallbackQuery):
    await call.message.answer("Главное меню ✅", reply_markup=main_kb())
    await call.answer()

@router.callback_query(F.data == "sf:back")
async def subject_back(call: CallbackQuery):
    await call.message.answer("Выбери предмет:", reply_markup=subjects_kb(SUBJECTS))
    await call.answer()

@router.callback_query(F.data.startswith("sub:"))
async def choose_subject(call: CallbackQuery):
    tg_id = call.from_user.id
    name = call.data.split("sub:")[1]

    # создать предмет, если нет
    cur = await db.execute("SELECT id FROM subjects WHERE tg_id=? AND name=?", (tg_id, name))
    row = await cur.fetchone()
    if row:
        subject_id = row["id"]
    else:
        await db.execute("INSERT INTO subjects(tg_id, name) VALUES(?,?)", (tg_id, name))
        await db.commit()
        cur2 = await db.execute("SELECT id FROM subjects WHERE tg_id=? AND name=?", (tg_id, name))
        subject_id = (await cur2.fetchone())["id"]

    await call.message.edit_text(
        f"📌 Предмет: {name}\nЧто делаем?",
        reply_markup=subject_menu_kb(subject_id)
    )
    await call.answer()

@router.callback_query(F.data.startswith("sf:new:"))
async def folder_new(call: CallbackQuery, state: FSMContext):
    subject_id = int(call.data.split(":")[-1])
    await state.update_data(subject_id=subject_id)
    await state.set_state(FolderStates.waiting_folder_title)
    await call.message.answer("Напиши название папки (например: 'Домашка 3' или 'Подготовка к КР'):")
    await call.answer()

@router.message(FolderStates.waiting_folder_title)
async def folder_new_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    subject_id = int(data["subject_id"])
    title = msg.text.strip()

    await db.execute(
        "INSERT INTO folders(tg_id, subject_id, title) VALUES(?,?,?)",
        (msg.from_user.id, subject_id, title)
    )
    await db.commit()

    await state.clear()
    await msg.answer(f"✅ Папка создана: {title}\nТеперь открой её через «📁 Мои папки».")

@router.callback_query(F.data.startswith("sf:list:"))
async def folder_list(call: CallbackQuery):
    tg_id = call.from_user.id
    subject_id = int(call.data.split(":")[-1])

    cur = await db.execute(
        "SELECT id, title, created_at FROM folders WHERE tg_id=? AND subject_id=? ORDER BY id DESC",
        (tg_id, subject_id)
    )
    rows = await cur.fetchall()
    folders = [{"id": r["id"], "title": r["title"], "created_at": r["created_at"]} for r in rows]

    if not folders:
        await call.message.answer("Папок пока нет. Нажми «➕ Создать папку».")
        await call.answer()
        return

    await call.message.answer("📁 Твои папки:", reply_markup=folders_kb(subject_id, folders))
    await call.answer()

@router.callback_query(F.data.startswith("sf:listback:"))
async def back_to_subject_menu(call: CallbackQuery):
    subject_id = int(call.data.split(":")[-1])
    # получим название предмета из БД
    cur = await db.execute("SELECT name FROM subjects WHERE id=?", (subject_id,))
    row = await cur.fetchone()
    if row:
        name = row["name"]
        await call.message.answer(
            f"📌 Предмет: {name}\nЧто делаем?",
            reply_markup=subject_menu_kb(subject_id)
        )
    else:
        await call.message.answer("Предмет не найден.")
    await call.answer()
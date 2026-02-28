# app/handlers/materials.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from ..db import db
from ..keyboards import folder_menu_kb

router = Router()

class MaterialStates(StatesGroup):
    waiting_topic_title = State()
    waiting_photo = State()

@router.callback_query(F.data.startswith("fold:open:"))
async def open_folder(call: CallbackQuery):
    folder_id = int(call.data.split(":")[-1])

    cur = await db.execute("SELECT title, created_at FROM folders WHERE id=?", (folder_id,))
    folder = await cur.fetchone()
    if not folder:
        await call.message.answer("Папка не найдена 😕")
        await call.answer()
        return

    await call.message.answer(
        f"📁 Папка: {folder['title']}\n🕒 Создана: {folder['created_at']}",
        reply_markup=folder_menu_kb(folder_id)
    )
    await call.answer()

@router.callback_query(F.data.startswith("fm:topic:"))
async def add_topic_start(call: CallbackQuery, state: FSMContext):
    folder_id = int(call.data.split(":")[-1])
    await state.update_data(folder_id=folder_id)
    await state.set_state(MaterialStates.waiting_topic_title)
    await call.message.answer("Напиши название темы (например: 'Законы Ньютона'):")
    await call.answer()

@router.message(MaterialStates.waiting_topic_title)
async def add_topic_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    folder_id = int(data["folder_id"])
    title = msg.text.strip()

    await db.execute(
        "INSERT INTO folder_materials(tg_id, folder_id, kind, title) VALUES(?,?,?,?)",
        (msg.from_user.id, folder_id, "topic", title)
    )
    await db.commit()

    # получаем инфо о папке
    cur = await db.execute("SELECT title FROM folders WHERE id=?", (folder_id,))
    folder = await cur.fetchone()
    
    await state.clear()
    await msg.answer(
        f"✅ Тема сохранена: {title}\n\n📁 Папка: {folder['title'] if folder else 'Неизв.'}\nЧто дальше?",
        reply_markup=folder_menu_kb(folder_id)
    )

@router.callback_query(F.data.startswith("fm:photo:"))
async def add_photo_start(call: CallbackQuery, state: FSMContext):
    folder_id = int(call.data.split(":")[-1])
    await state.update_data(folder_id=folder_id)
    await state.set_state(MaterialStates.waiting_photo)
    await call.message.answer("Отправь фото (я сохраню в эту папку).")
    await call.answer()

@router.message(MaterialStates.waiting_photo, F.photo)
async def add_photo_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    folder_id = int(data["folder_id"])

    # берём самое большое фото
    file_id = msg.photo[-1].file_id

    await db.execute(
        "INSERT INTO folder_materials(tg_id, folder_id, kind, file_id) VALUES(?,?,?,?)",
        (msg.from_user.id, folder_id, "photo", file_id)
    )
    await db.commit()

    # получаем инфо о папке
    cur = await db.execute("SELECT title FROM folders WHERE id=?", (folder_id,))
    folder = await cur.fetchone()

    await state.clear()
    await msg.answer(
        f"✅ Фото сохранено в папку!\n\n📁 Папка: {folder['title'] if folder else 'Неизв.'}\nЧто дальше?",
        reply_markup=folder_menu_kb(folder_id)
    )

@router.message(MaterialStates.waiting_photo)
async def add_photo_wrong(msg: Message):
    await msg.answer("Нужно отправить именно ФОТО 📸")

@router.callback_query(F.data.startswith("fm:back:"))
async def back_to_folder_menu(call: CallbackQuery):
    folder_id = int(call.data.split(":")[-1])
    
    cur = await db.execute("SELECT title, created_at FROM folders WHERE id=?", (folder_id,))
    folder = await cur.fetchone()
    if not folder:
        await call.message.answer("Папка не найдена 😕")
        await call.answer()
        return

    await call.message.answer(
        f"📁 Папка: {folder['title']}\n🕒 Создана: {folder['created_at']}\n\nЧто делаем?",
        reply_markup=folder_menu_kb(folder_id)
    )
    await call.answer()

@router.callback_query(F.data.startswith("fm:view:"))
async def view_folder(call: CallbackQuery):
    folder_id = int(call.data.split(":")[-1])
    tg_id = call.from_user.id

    cur = await db.execute(
        "SELECT kind, title, file_id, created_at FROM folder_materials WHERE tg_id=? AND folder_id=? ORDER BY id DESC",
        (tg_id, folder_id)
    )
    rows = await cur.fetchall()

    if not rows:
        await call.message.answer("В папке пока пусто.")
        await call.answer()
        return

    await call.message.answer("📄 Содержимое папки:")
    for r in rows[:20]:
        if r["kind"] == "topic":
            await call.message.answer(f"📝 Тема: {r['title']}\n🕒 {r['created_at']}")
        else:
            await call.message.answer_photo(r["file_id"], caption=f"📸 Фото\n🕒 {r['created_at']}")

    await call.answer()
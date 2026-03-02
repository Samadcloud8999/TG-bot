from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime

from .. import db
from ..keyboards import gallery_kb, gallery_list_kb

router = Router()


class GalleryFlow(StatesGroup):
    waiting_photo = State()
    waiting_title = State()
    waiting_password = State()
    # we keep authorization info in state data


def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="gallery:cancel")]
    ])


@router.message(F.text == "🖼 Галерея")
async def gallery_menu(msg: Message):
    await msg.answer("🖼 Галерея\nВыбери:", reply_markup=gallery_kb())


@router.callback_query(F.data == "gallery:back")
async def gallery_back(cb: CallbackQuery, state: FSMContext):
    from ..keyboards import main_kb
    await state.clear()
    await cb.message.answer("Главное меню ✅", reply_markup=main_kb())
    await cb.answer()


@router.callback_query(F.data == "gallery:cancel")
async def gallery_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("Ок, отменил ✅", reply_markup=gallery_kb())
    await cb.answer()


@router.callback_query(F.data == "gallery:add")
async def gallery_add_start(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(GalleryFlow.waiting_photo)
    await cb.message.answer("📸 Отправь photo, которое хочешь сохранить в галерее.", reply_markup=cancel_kb())
    await cb.answer()


@router.message(GalleryFlow.waiting_photo, F.photo)
async def gallery_received_photo(msg: Message, state: FSMContext):
    file_id = msg.photo[-1].file_id
    await state.update_data(file_id=file_id)
    await state.set_state(GalleryFlow.waiting_title)
    await msg.answer("✏️ Введи название для этого фото.", reply_markup=cancel_kb())


@router.message(GalleryFlow.waiting_photo)
async def gallery_no_photo(msg: Message):
    await msg.answer("Пожалуйста, отправь фото.", reply_markup=cancel_kb())


@router.message(GalleryFlow.waiting_title)
async def gallery_received_title(msg: Message, state: FSMContext):
    title = (msg.text or "").strip()
    if not title:
        await msg.answer("Название не может быть пустым. Попробуй ещё.", reply_markup=cancel_kb())
        return
    data = await state.get_data()
    file_id = data.get("file_id")
    if not file_id:
        await msg.answer("Что-то пошло не так (нет файла). Попробуй отправить фото заново.")
        await state.clear()
        return
    await db.db.execute("INSERT INTO gallery(tg_id, title, file_id, created_at) VALUES(?,?,?,?)",
                        (msg.from_user.id, title, file_id, datetime.utcnow().isoformat()))
    await db.db.commit()
    await state.clear()
    await msg.answer("✅ Фото сохранено в галерее.", reply_markup=gallery_kb())


async def show_gallery(message, owner_id: int):
    cur = await db.db.execute("SELECT id, title FROM gallery WHERE tg_id=? ORDER BY created_at DESC", (owner_id,))
    rows = await cur.fetchall()
    if not rows:
        await message.answer("Галерея пуста.")
        return
    items = [{'id': r[0], 'title': r[1]} for r in rows]
    kb = gallery_list_kb(items, owner_id)
    header = "📁 Моя галерея" if owner_id == message.from_user.id else "📁 Галерея друга"
    await message.answer(header, reply_markup=kb)


@router.callback_query(F.data == "gallery:my")
async def gallery_list_my(cb: CallbackQuery):
    await show_gallery(cb.message, cb.from_user.id)
    await cb.answer()


@router.callback_query(F.data == "gallery:friend")
async def gallery_friend(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(GalleryFlow.waiting_password)
    await cb.message.answer("🔐 Введи пароль друга.", reply_markup=cancel_kb())
    await cb.answer()


@router.message(GalleryFlow.waiting_password)
async def gallery_password_entered(msg: Message, state: FSMContext):
    pwd = (msg.text or "").strip()
    cur = await db.db.execute("SELECT tg_id FROM users WHERE password=?", (pwd,))
    row = await cur.fetchone()
    if not row:
        await msg.answer("Пароль не найден. Попробуй снова.", reply_markup=cancel_kb())
        return
    friend_id = row[0]
    await state.update_data(authorized_friend=friend_id)
    # show friend's gallery
    await show_gallery(msg, friend_id)
    # keep state so that callbacks can validate
    await state.set_state(GalleryFlow.waiting_password)  # state doesn't matter much


@router.callback_query(F.data.startswith("gallery:view:"))
async def gallery_view_item(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")
    if len(parts) < 3:
        await cb.answer()
        return
    item_id = int(parts[2])
    cur = await db.db.execute("SELECT tg_id, file_id, title FROM gallery WHERE id=?", (item_id,))
    row = await cur.fetchone()
    if not row:
        await cb.message.answer("Фото не найдено.")
        await cb.answer()
        return
    owner_id, file_id, title = row
    user_id = cb.from_user.id
    allowed = False
    if owner_id == user_id:
        allowed = True
    else:
        data = await state.get_data()
        allowed = data.get("authorized_friend") == owner_id
    if not allowed:
        await cb.message.answer("Ты не можешь просматривать это фото. Введи пароль друга.")
        await cb.answer()
        return
    await cb.message.answer_photo(photo=file_id, caption=title)
    await cb.answer()



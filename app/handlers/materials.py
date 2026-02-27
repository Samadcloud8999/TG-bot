from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from datetime import datetime
from .. import db
from ..keyboards import subject_menu_kb

router = Router()

WAIT_MATERIAL = {}      # tg_id -> subject
WAIT_SEARCH = {}        # tg_id -> subject

@router.callback_query(F.data.startswith("subadd:"))
async def sub_add(cb: CallbackQuery):
    subject = cb.data.split("subadd:", 1)[1]
    WAIT_MATERIAL[cb.from_user.id] = subject
    await cb.message.answer(
        f"➕ Добавление материала в предмет **{subject}**\n"
        "Отправь:\n"
        "• текст (сообщение)\n"
        "• фото\n"
        "• PDF (файл)\n\n"
        "Если это текст — просто напиши его.",
        parse_mode="Markdown"
    )
    await cb.answer()

@router.message(lambda m: WAIT_MATERIAL.get(m.from_user.id) is not None)
async def material_receive(msg: Message):
    subject = WAIT_MATERIAL.pop(msg.from_user.id, None)
    if not subject:
        return

    kind = "text"
    file_id = None
    text = ""

    if msg.photo:
        kind = "photo"
        file_id = msg.photo[-1].file_id
        text = msg.caption or ""
    elif msg.document:
        # pdf или любой документ (для MVP принимаем, но можно ограничить mime_type)
        kind = "pdf"
        file_id = msg.document.file_id
        text = msg.caption or ""
    else:
        kind = "text"
        text = msg.text or ""

    await db.db.execute("""
        INSERT INTO materials(tg_id, subject, kind, file_id, text, tags, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
    """, (msg.from_user.id, subject, kind, file_id, text, "", datetime.utcnow().isoformat()))
    await db.db.commit()

    await msg.answer(f"✅ Материал сохранён в **{subject}**", parse_mode="Markdown")

@router.callback_query(F.data.startswith("sublist:"))
async def sub_list(cb: CallbackQuery):
    subject = cb.data.split("sublist:", 1)[1]

    cur = await db.db.execute("""
        SELECT id, kind, text, created_at
        FROM materials
        WHERE tg_id=? AND subject=?
        ORDER BY created_at DESC
        LIMIT 10
    """, (cb.from_user.id, subject))
    rows = await cur.fetchall()

    if not rows:
        await cb.message.answer("Пока материалов нет. Нажми ➕ Добавить материал.")
        await cb.answer()
        return

    msg_text = f"📂 Материалы по предмету **{subject}** (последние 10)\n\n"
    for mid, kind, text, created_at in rows:
        preview = (text or "").strip()
        if len(preview) > 30:
            preview = preview[:30] + "..."
        msg_text += f"ID {mid} • {kind} • {preview}\n"

    msg_text += "\nЧтобы открыть материал:\n/open ID"
    await cb.message.answer(msg_text, parse_mode="Markdown")
    await cb.answer()

@router.message(F.text.startswith("/open"))
async def open_material(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Формат: /open ID")
        return
    try:
        mid = int(parts[1])
    except ValueError:
        await msg.answer("ID должен быть числом.")
        return

    cur = await db.db.execute("""
        SELECT subject, kind, file_id, text, created_at
        FROM materials
        WHERE id=? AND tg_id=?
    """, (mid, msg.from_user.id))
    row = await cur.fetchone()
    if not row:
        await msg.answer("Материал не найден.")
        return

    subject, kind, file_id, text, created_at = row
    header = f"📌 **{subject}**\nТип: {kind}\nДата: {created_at}\n\n"
    caption = (header + (text or "")).strip()

    if kind == "photo" and file_id:
        await msg.answer_photo(file_id, caption=caption[:1024], parse_mode="Markdown")
    elif kind == "pdf" and file_id:
        await msg.answer_document(file_id, caption=caption[:1024], parse_mode="Markdown")
    else:
        await msg.answer(caption, parse_mode="Markdown")

@router.callback_query(F.data.startswith("subsearch:"))
async def sub_search(cb: CallbackQuery):
    subject = cb.data.split("subsearch:", 1)[1]
    WAIT_SEARCH[cb.from_user.id] = subject
    await cb.message.answer(f"🔎 Поиск по **{subject}**: напиши ключевое слово или дату (например 2026-02-27)", parse_mode="Markdown")
    await cb.answer()

@router.message(lambda m: WAIT_SEARCH.get(m.from_user.id) is not None)
async def do_search(msg: Message):
    subject = WAIT_SEARCH.pop(msg.from_user.id, None)
    q = (msg.text or "").strip()
    if not q:
        return

    like = f"%{q}%"
    cur = await db.db.execute("""
        SELECT id, kind, text, created_at
        FROM materials
        WHERE tg_id=? AND subject=? AND (text LIKE ? OR created_at LIKE ?)
        ORDER BY created_at DESC
        LIMIT 10
    """, (msg.from_user.id, subject, like, like))
    rows = await cur.fetchall()

    if not rows:
        await msg.answer("Ничего не найдено.")
        return

    out = f"🔎 Результаты по **{subject}**:\n\n"
    for mid, kind, text, created_at in rows:
        preview = (text or "").strip()
        if len(preview) > 30:
            preview = preview[:30] + "..."
        out += f"ID {mid} • {kind} • {preview}\n"
    out += "\nОткрыть: /open ID"
    await msg.answer(out, parse_mode="Markdown")
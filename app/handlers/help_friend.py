from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime

from ..keyboards import help_menu_kb
from .. import db
from ..rewards import calc_level

router = Router()

XP_HELP_REPLY = 25


class HelpFlow(StatesGroup):
    topic = State()
    desc = State()
    respond_text = State()


def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="help:cancel")]
    ])

def open_requests_kb(rows):
    # rows: [(id, topic, created_at), ...]
    buttons = []
    for rid, topic, _ in rows:
        title = topic if len(topic) <= 35 else topic[:32] + "…"
        buttons.append([InlineKeyboardButton(text=f"ID {rid} • {title}", callback_data=f"help:req:{rid}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="help:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def request_actions_kb(req_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Ответить", callback_data=f"help:reply:{req_id}")],
        [InlineKeyboardButton(text="⬅️ К списку", callback_data="help:list")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="help:back")],
    ])


# ---------- Menu ----------
@router.message(F.text == "🤝 Помощь друга")
async def help_menu(msg: Message):
    await msg.answer("🤝 Помощь друга\nВыбери:", reply_markup=help_menu_kb())


@router.callback_query(F.data == "help:back")
async def help_back(cb: CallbackQuery, state: FSMContext):
    from ..keyboards import main_kb
    await state.clear()
    await cb.message.answer("Главное меню ✅", reply_markup=main_kb())
    await cb.answer()


@router.callback_query(F.data == "help:cancel")
async def help_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("Ок, отменил ✅", reply_markup=help_menu_kb())
    await cb.answer()


# ---------- Create new request ----------
@router.callback_query(F.data == "help:new")
async def help_new(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(HelpFlow.topic)
    await cb.message.answer(
        "📝 Напиши тему запроса\n"
        "Пример: <i>Алгебра — производные</i>\n\n"
        "Можно нажать «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )
    await cb.answer()


@router.message(HelpFlow.topic)
async def help_got_topic(msg: Message, state: FSMContext):
    topic = (msg.text or "").strip()
    if len(topic) < 3:
        await msg.answer("Тема слишком короткая. Напиши чуть подробнее 🙂", reply_markup=cancel_kb())
        return

    await state.update_data(topic=topic)
    await state.set_state(HelpFlow.desc)
    await msg.answer(
        "🧩 Опиши проблему (можно коротко)\n"
        "Если не хочешь — напиши <b>-</b>\n\n"
        "Можно нажать «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )


@router.message(HelpFlow.desc)
async def help_got_desc(msg: Message, state: FSMContext):
    data = await state.get_data()
    topic = data["topic"]

    desc = (msg.text or "").strip()
    if desc == "-":
        desc = ""

    await db.db.execute("INSERT OR IGNORE INTO users(tg_id) VALUES(?)", (msg.from_user.id,))
    await db.db.execute("""
        INSERT INTO help_requests(tg_id, topic, description, status, ai_sent, created_at)
        VALUES(?, ?, ?, 'open', 0, ?)
    """, (msg.from_user.id, topic, desc, datetime.utcnow().isoformat()))
    await db.db.commit()

    await state.clear()

    await msg.answer(
        "✅ Запрос создан!\n\n"
        "Теперь зайди в «Открытые запросы», чтобы увидеть его в списке.\n"
        "Если за 1 час никто не ответит — поможет AI 🤖",
        reply_markup=help_menu_kb()
    )


# ---------- List open requests ----------
@router.callback_query(F.data == "help:list")
async def help_list(cb: CallbackQuery):
    cur = await db.db.execute("""
        SELECT id, topic, created_at
        FROM help_requests
        WHERE status='open'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    rows = await cur.fetchall()

    if not rows:
        await cb.message.answer("Пока нет открытых запросов.")
        await cb.answer()
        return

    await cb.message.answer(
        "📌 Открытые запросы\nНажми на нужный, чтобы посмотреть детали:",
        reply_markup=open_requests_kb(rows)
    )
    await cb.answer()


# ---------- View request ----------
@router.callback_query(F.data.startswith("help:req:"))
async def help_view_request(cb: CallbackQuery):
    req_id = int(cb.data.split(":")[-1])

    cur = await db.db.execute("""
        SELECT id, tg_id, topic, description, created_at, status
        FROM help_requests
        WHERE id=?
    """, (req_id,))
    row = await cur.fetchone()

    if not row:
        await cb.message.answer("Запрос не найден.")
        await cb.answer()
        return

    rid, owner_id, topic, desc, created_at, status = row

    # немного красоты
    desc_block = desc if desc else "—"
    created_short = created_at.replace("T", " ")[:16] if created_at else "—"

    text = (
        f"🆘 <b>Запрос #{rid}</b>\n"
        f"📌 <b>Тема:</b> {topic}\n"
        f"📝 <b>Описание:</b> {desc_block}\n"
        f"🕒 <b>Создан:</b> {created_short} (UTC)\n"
        f"📍 <b>Статус:</b> {status}"
    )

    await cb.message.answer(text, parse_mode="HTML", reply_markup=request_actions_kb(rid))
    await cb.answer()


# ---------- Start reply ----------
@router.callback_query(F.data.startswith("help:reply:"))
async def help_start_reply(cb: CallbackQuery, state: FSMContext):
    req_id = int(cb.data.split(":")[-1])

    # проверка статуса + владелец
    cur = await db.db.execute("SELECT tg_id, status, topic FROM help_requests WHERE id=?", (req_id,))
    row = await cur.fetchone()
    if not row:
        await cb.message.answer("Такого запроса нет.")
        await cb.answer()
        return

    owner_id, status, topic = row
    if status != "open":
        await cb.message.answer("Запрос уже закрыт.")
        await cb.answer()
        return
    if owner_id == cb.from_user.id:
        await cb.message.answer("Нельзя отвечать на свой запрос 😄")
        await cb.answer()
        return

    await state.clear()
    await state.update_data(req_id=req_id, owner_id=owner_id, topic=topic)
    await state.set_state(HelpFlow.respond_text)

    await cb.message.answer(
        f"✍️ Напиши свой ответ для запроса #{req_id}\n"
        f"Тема: <b>{topic}</b>\n\n"
        f"Можно нажать «Отмена».",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )
    await cb.answer()


# ---------- Save reply + reward ----------
@router.message(HelpFlow.respond_text)
async def help_save_reply(msg: Message, state: FSMContext):
    data = await state.get_data()
    req_id = data["req_id"]
    owner_id = data["owner_id"]
    topic = data["topic"]

    answer_text = (msg.text or "").strip()
    if len(answer_text) < 5:
        await msg.answer("Ответ слишком короткий. Напиши чуть подробнее 🙂", reply_markup=cancel_kb())
        return

    # проверим ещё раз что запрос открыт
    cur = await db.db.execute("SELECT status FROM help_requests WHERE id=?", (req_id,))
    row = await cur.fetchone()
    if not row or row[0] != "open":
        await state.clear()
        await msg.answer("Запрос уже закрыт/не найден.", reply_markup=help_menu_kb())
        return

    await db.db.execute("INSERT OR IGNORE INTO users(tg_id) VALUES(?)", (msg.from_user.id,))
    await db.db.execute("""
        INSERT INTO help_responses(request_id, responder_id, text)
        VALUES(?, ?, ?)
    """, (req_id, msg.from_user.id, answer_text))
    await db.db.commit()

    # награда
    cur2 = await db.db.execute("SELECT xp, level, help_given_count FROM users WHERE tg_id=?", (msg.from_user.id,))
    u = await cur2.fetchone() or (0, 1, 0)
    xp, level, help_count = u

    xp = int(xp or 0)
    help_count = int(help_count or 0)

    new_xp = xp + XP_HELP_REPLY
    new_level = calc_level(new_xp)
    help_count += 1

    await db.db.execute("""
        UPDATE users SET xp=?, level=?, help_given_count=?
        WHERE tg_id=?
    """, (new_xp, new_level, help_count, msg.from_user.id))

    # ачивки
    if help_count == 1:
        await db.db.execute(
            "INSERT OR IGNORE INTO achievements(tg_id, code, title) VALUES(?,?,?)",
            (msg.from_user.id, "help_1", "🤝 Первый раз помог другу")
        )
    if help_count == 5:
        await db.db.execute(
            "INSERT OR IGNORE INTO achievements(tg_id, code, title) VALUES(?,?,?)",
            (msg.from_user.id, "help_5", "🏅 Помощник лицея (5 ответов)")
        )

    await db.db.commit()
    await state.clear()

    # уведомим автора
    try:
        await msg.bot.send_message(
            owner_id,
            f"🤝 На твой запрос #{req_id} ответили!\n"
            f"Тема: {topic}\n\n"
            f"Ответ:\n{answer_text}"
        )
    except Exception:
        pass

    # сообщение отвечающему
    lvl_up = " 🎉 <b>Новый уровень!</b>" if new_level > int(level or 1) else ""
    await msg.answer(
        f"✅ Ответ отправлен!\n"
        f"+{XP_HELP_REPLY} XP{lvl_up}\n"
        f"Твой XP: {new_xp} | Уровень: {new_level}",
        parse_mode="HTML",
        reply_markup=help_menu_kb()
    )
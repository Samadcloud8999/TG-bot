from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import datetime
from ..keyboards import help_menu_kb
from .. import db
from ..rewards import calc_level

router = Router()

WAIT_HELP_TOPIC = {}
WAIT_HELP_DESC = {}
WAIT_HELP_RESP = {}  # responder -> request_id

@router.message(F.text == "🤝 Помощь друга")
async def help_menu(msg: Message):
    await msg.answer("🤝 Помощь друга\nВыбери:", reply_markup=help_menu_kb())

@router.callback_query(F.data == "help:back")
async def help_back(cb: CallbackQuery):
    from ..keyboards import main_kb
    await cb.message.answer("Главное меню ✅", reply_markup=main_kb())
    await cb.answer()

@router.callback_query(F.data == "help:new")
async def help_new(cb: CallbackQuery):
    WAIT_HELP_TOPIC[cb.from_user.id] = True
    await cb.message.answer("Напиши тему запроса (например: 'Алгебра: производные'):")
    await cb.answer()

@router.message(lambda m: WAIT_HELP_TOPIC.get(m.from_user.id, False))
async def help_got_topic(msg: Message):
    WAIT_HELP_TOPIC.pop(msg.from_user.id, None)
    WAIT_HELP_DESC[msg.from_user.id] = msg.text.strip()
    await msg.answer("Опиши проблему (можно коротко). Если не хочешь — напиши '-' :")

@router.message(lambda m: WAIT_HELP_DESC.get(m.from_user.id) is not None)
async def help_got_desc(msg: Message):
    topic = WAIT_HELP_DESC.pop(msg.from_user.id, None)
    desc = msg.text.strip()
    if desc == "-":
        desc = ""

    # создать запрос
    await db.db.execute("INSERT OR IGNORE INTO users(tg_id) VALUES(?)", (msg.from_user.id,))
    await db.db.execute("""
        INSERT INTO help_requests(tg_id, topic, description, status, ai_sent, created_at)
        VALUES(?, ?, ?, 'open', 0, ?)
    """, (msg.from_user.id, topic, desc, datetime.utcnow().isoformat()))
    await db.db.commit()

    await msg.answer("✅ Запрос создан! Другие смогут откликнуться в разделе 'Открытые запросы'.\n"
                     "Если за 1 час никто не ответит — поможет ассистент 🤖")

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

    text = "📌 Открытые запросы (ответь командой: /respond ID твой_ответ)\n\n"
    for rid, topic, created_at in rows:
        text += f"ID {rid}: {topic}\n"
    await cb.message.answer(text)
    await cb.answer()

@router.message(F.text.startswith("/respond"))
async def respond_cmd(msg: Message):
    # формат: /respond 12 текст...
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Формат: /respond ID твой_ответ\nПример: /respond 12 Это решается так...")
        return
    try:
        req_id = int(parts[1])
    except ValueError:
        await msg.answer("ID должен быть числом.")
        return

    answer_text = parts[2].strip()
    if not answer_text:
        await msg.answer("Напиши текст ответа.")
        return

    # проверим что запрос открыт
    cur = await db.db.execute("SELECT tg_id, status, topic FROM help_requests WHERE id=?", (req_id,))
    row = await cur.fetchone()
    if not row:
        await msg.answer("Такого запроса нет.")
        return

    owner_id, status, topic = row
    if status != "open":
        await msg.answer("Запрос уже закрыт.")
        return
    if owner_id == msg.from_user.id:
        await msg.answer("Нельзя отвечать на свой запрос 😄")
        return

    # записываем ответ
    await db.db.execute("INSERT OR IGNORE INTO users(tg_id) VALUES(?)", (msg.from_user.id,))
    await db.db.execute("""
        INSERT INTO help_responses(request_id, responder_id, text)
        VALUES(?, ?, ?)
    """, (req_id, msg.from_user.id, answer_text))
    await db.db.commit()

    # награда отвечающему: XP + help_count
    cur2 = await db.db.execute("SELECT xp, level, help_given_count FROM users WHERE tg_id=?", (msg.from_user.id,))
    u = await cur2.fetchone()
    xp, level, help_count = u

    xp_add = 25
    new_xp = xp + xp_add
    new_level = calc_level(new_xp)
    help_count += 1

    await db.db.execute("""
        UPDATE users SET xp=?, level=?, help_given_count=?
        WHERE tg_id=?
    """, (new_xp, new_level, help_count, msg.from_user.id))

    # ачивки минимально
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

    # уведомим автора запроса
    try:
        await msg.bot.send_message(owner_id, f"🤝 На твой запрос (ID {req_id}) ответили!\nТема: {topic}\n\nОтвет:\n{answer_text}")
    except Exception:
        pass

    await msg.answer(f"✅ Ответ отправлен! +{xp_add} XP")
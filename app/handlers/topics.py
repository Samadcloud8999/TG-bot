from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, timedelta
from .. import db

router = Router()

WAITING_TOPIC = {}

# value may be True (waiting), or tuple('confirm', title) when duplicate check pending

@router.message(F.text == "📚 Добавить тему")
async def ask_topic(msg: Message):
    WAITING_TOPIC[msg.from_user.id] = True
    await msg.answer("Напиши название темы (например: 'JS замыкания')\n(можно ввести /cancel чтобы выйти)")

@router.message(lambda m: WAITING_TOPIC.get(m.from_user.id, False))
async def add_topic(msg: Message):
    state = WAITING_TOPIC.get(msg.from_user.id)
    if isinstance(state, tuple) and state[0] == "confirm":
        resp = msg.text.strip().lower()
        title = state[1]
        WAITING_TOPIC.pop(msg.from_user.id, None)
        if resp in ("да", "yes", "ok", "конечно"):
            await _insert_topic(msg.from_user.id, title, msg)
        else:
            await msg.answer("Ок, тема не добавлена.")
        return

    title = msg.text.strip()
    WAITING_TOPIC.pop(msg.from_user.id, None)

    # check duplicate
    cur = await db.db.execute("SELECT id FROM topics WHERE tg_id=? AND title=?", (msg.from_user.id, title))
    if await cur.fetchone():
        WAITING_TOPIC[msg.from_user.id] = ("confirm", title)
        await msg.answer(f"Тема \"{title}\" уже есть. Добавить повторно? (да/нет)")
        return

    await _insert_topic(msg.from_user.id, title, msg)


async def _insert_topic(user_id: int, title: str, msg: Message):
    cur = await db.db.execute(
        "INSERT INTO topics(tg_id, title) VALUES(?, ?)",
        (user_id, title)
    )
    await db.db.commit()
    topic_id = cur.lastrowid
    next_review = (datetime.utcnow() + timedelta(days=1)).isoformat()
    await db.db.execute(
        "INSERT INTO reviews(topic_id, next_review, step) VALUES(?, ?, ?)",
        (topic_id, next_review, 0)
    )
    await db.db.commit()
    await msg.answer(f"✅ Тема добавлена: {title}\nПервый повтор — завтра.")

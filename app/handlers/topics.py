from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, timedelta
from .. import db

router = Router()

WAITING_TOPIC = {}

@router.message(F.text == "📚 Добавить тему")
async def ask_topic(msg: Message):
    WAITING_TOPIC[msg.from_user.id] = True
    await msg.answer("Напиши название темы (например: 'JS замыкания')")

@router.message(lambda m: WAITING_TOPIC.get(m.from_user.id, False))
async def add_topic(msg: Message):
    title = msg.text.strip()
    WAITING_TOPIC.pop(msg.from_user.id, None)

    cur = await db.db.execute(
        "INSERT INTO topics(tg_id, title) VALUES(?, ?)",
        (msg.from_user.id, title)
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
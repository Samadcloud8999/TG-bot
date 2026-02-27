import asyncio
from datetime import datetime, timedelta
from . import db

CHECK_EVERY_SECONDS = 60
REMIND_COOLDOWN_MIN = 180  # не чаще чем раз в 3 часа по одной теме

def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()

async def _send_due_review_reminders(bot):
    now = _utcnow_iso()

    # Выбираем все повторы, которые уже пора, и у пользователей включены напоминания
    cur = await db.db.execute("""
        SELECT r.id as review_id, u.tg_id, t.title
        FROM reviews r
        JOIN topics t ON t.id = r.topic_id
        JOIN users u ON u.tg_id = t.tg_id
        WHERE r.next_review <= ?
          AND u.reminders_enabled = 1
        ORDER BY r.next_review ASC
        LIMIT 50
    """, (now,))
    rows = await cur.fetchall()

    for review_id, tg_id, title in rows:
        # проверяем, не отправляли ли недавно
        c2 = await db.db.execute("SELECT last_sent FROM review_notifications WHERE review_id=?", (review_id,))
        row2 = await c2.fetchone()

        if row2 and row2[0]:
            try:
                last_sent = datetime.fromisoformat(row2[0])
                if datetime.utcnow() - last_sent < timedelta(minutes=REMIND_COOLDOWN_MIN):
                    continue
            except Exception:
                pass

        try:
            await bot.send_message(tg_id, f"⏰ Пора повторить тему: **{title}**\nЖми: 🧠 Пройти повтор", parse_mode="Markdown")
            await db.db.execute(
                "INSERT OR REPLACE INTO review_notifications(review_id, last_sent) VALUES(?, ?)",
                (review_id, _utcnow_iso())
            )
            await db.db.commit()
        except Exception:
            # не валим бота из-за одной ошибки отправки
            continue

async def _auto_ai_help_after_1h(bot):
    # если запрос открыт > 1 часа и никто не ответил, отправляем авто-помощь
    threshold = (datetime.utcnow() - timedelta(hours=1)).isoformat()

    cur = await db.db.execute("""
        SELECT hr.id, hr.tg_id, hr.subject, hr.topic, hr.description
        FROM help_requests hr
        WHERE hr.status='open'
          AND hr.ai_sent=0
          AND hr.created_at <= ?
          AND NOT EXISTS (SELECT 1 FROM help_responses r WHERE r.request_id = hr.id)
        LIMIT 20
    """, (threshold,))
    rows = await cur.fetchall()

    for req_id, tg_id, subject, topic, description in rows:
        # Заглушка-ассистент (работает без внешнего API)
        text = (
            "🤖 Никто не успел ответить за 1 час, поэтому помогу я.\n\n"
            f"📌 Тема: {topic}\n"
            f"📚 Предмет: {subject or '—'}\n\n"
            "✅ Коротко (обычно):\n"
            f"- Определи ключевые понятия темы.\n"
            f"- Сделай 3 примера и реши их.\n"
            f"- Сформулируй тему своими словами.\n\n"
            "📝 Вопросы для самопроверки:\n"
            "1) Что это такое простыми словами?\n"
            "2) Где применяется?\n"
            "3) Приведи 1 пример.\n"
        )
        try:
            await bot.send_message(tg_id, text)
            await db.db.execute("UPDATE help_requests SET ai_sent=1 WHERE id=?", (req_id,))
            await db.db.commit()
        except Exception:
            continue

async def start(bot):
    # основной цикл планировщика
    while True:
        try:
            await _send_due_review_reminders(bot)
            await _auto_ai_help_after_1h(bot)
        except Exception:
            # не падаем
            pass
        await asyncio.sleep(CHECK_EVERY_SECONDS)
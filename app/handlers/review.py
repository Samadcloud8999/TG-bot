from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime, timedelta, date
from .. import db
from ..rewards import calc_level, update_streak

router = Router()

INTERVALS = [1, 3, 7, 14, 30]
ACTIVE_REVIEW = {}

@router.message(F.text == "🧠 Пройти повтор")
async def start_review(msg: Message):
    tg_id = msg.from_user.id
    now_iso = datetime.utcnow().isoformat()

    cur = await db.db.execute("""
        SELECT r.id as review_id, t.title, r.step
        FROM reviews r
        JOIN topics t ON t.id = r.topic_id
        WHERE t.tg_id=? AND r.next_review <= ?
        ORDER BY r.next_review ASC
        LIMIT 1
    """, (tg_id, now_iso))
    row = await cur.fetchone()

    if not row:
        await msg.answer("Пока нет тем для повтора ✅\nЗайди позже или добавь новую тему.")
        return

    review_id, title, step = row
    ACTIVE_REVIEW[tg_id] = review_id

    await msg.answer(
        f"📌 Тема: {title}\n"
        "Ответь честно:\n"
        "1) ✅ Я знаю\n"
        "2) 🤔 Сомневаюсь\n"
        "3) ❌ Не знаю\n\n"
        "Напиши цифру 1/2/3"
    )

@router.message(F.text.in_(["1", "2", "3"]))
async def review_answer(msg: Message):
    tg_id = msg.from_user.id
    review_id = ACTIVE_REVIEW.get(tg_id)
    if not review_id:
        return

    ans = msg.text.strip()
    now = datetime.utcnow()

    cur = await db.db.execute("SELECT step FROM reviews WHERE id=?", (review_id,))
    r = await cur.fetchone()
    step = r[0]

    if ans == "1":
        step = min(step + 1, len(INTERVALS) - 1)
        xp_add = 20
    elif ans == "2":
        step = max(step, 0)
        xp_add = 10
    else:
        step = 0
        xp_add = 5

    next_review = (now + timedelta(days=INTERVALS[step])).isoformat()

    await db.db.execute(
        "UPDATE reviews SET step=?, next_review=? WHERE id=?",
        (step, next_review, review_id)
    )

    cur = await db.db.execute(
        "SELECT xp, level, streak, last_streak_date FROM users WHERE tg_id=?",
        (tg_id,)
    )
    u = await cur.fetchone()
    xp, level, streak, last_date = u

    new_xp = xp + xp_add
    new_level = calc_level(new_xp)

    last_date_obj = date.fromisoformat(last_date) if last_date else None
    new_streak, new_streak_date = update_streak(last_date_obj, date.today(), streak)

    await db.db.execute("""
        UPDATE users
        SET xp=?, level=?, streak=?, last_streak_date=?
        WHERE tg_id=?
    """, (new_xp, new_level, new_streak, new_streak_date.isoformat(), tg_id))

    await db.db.commit()

    ACTIVE_REVIEW.pop(tg_id, None)
    await msg.answer(f"✅ Записал! +{xp_add} XP\nСледующий повтор: через {INTERVALS[step]} дн.")
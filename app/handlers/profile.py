from aiogram import Router, F
from aiogram.types import Message
from .. import db

router = Router()

@router.message(F.text == "🏆 Профиль")
async def profile(msg: Message):
    tg_id = msg.from_user.id

    cur = await db.db.execute(
        "SELECT xp, level, streak, help_given_count FROM users WHERE tg_id=?",
        (tg_id,)
    )
    u = await cur.fetchone()

    if not u:
        await msg.answer("Нажми /start")
        return

    xp, level, streak, help_given = u

    await msg.answer(
        f"🏆 Твой профиль\n"
        f"Уровень: {level}\n"
        f"XP: {xp}\n"
        f"🔥 Серия (streak): {streak} дней\n"
        f"🤝 Помог другим: {help_given} раз"
    )
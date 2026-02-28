from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from .. import db

router = Router()


def xp_for_next_level(level: int) -> int:
    """
    Примерная формула. Если у тебя другая логика уровней — скажи, подстрою.
    """
    # чем выше уровень — тем больше XP нужно
    return 100 + (level - 1) * 50


def safe_int(x, default=0) -> int:
    try:
        return int(x) if x is not None else default
    except (TypeError, ValueError):
        return default


@router.message(F.text == "🏆 Профиль")
async def profile(msg: Message):
    tg_id = msg.from_user.id

    cur = await db.db.execute(
        "SELECT xp, level, streak, help_given_count FROM users WHERE tg_id=?",
        (tg_id,)
    )
    row = await cur.fetchone()

    if not row:
        await msg.answer("Нажми /start, чтобы создать профиль 🙂")
        return

    xp = safe_int(row[0], 0)
    level = max(1, safe_int(row[1], 1))
    streak = safe_int(row[2], 0)
    help_given = safe_int(row[3], 0)

    next_need = xp_for_next_level(level)
    # прогресс в процентах (не больше 100)
    pct = min(100, int((xp / next_need) * 100)) if next_need > 0 else 0

    # простой прогресс-бар
    blocks = 10
    filled = int((pct / 100) * blocks)
    bar = "█" * filled + "░" * (blocks - filled)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="profile_refresh")]
        ]
    )

    name = msg.from_user.full_name or "Пользователь"

    text = (
        f"🏆 <b>Профиль</b>\n"
        f"👤 <b>{name}</b>\n\n"
        f"🎖 <b>Уровень:</b> {level}\n"
        f"✨ <b>XP:</b> {xp} / {next_need}\n"
        f"📈 <b>Прогресс:</b> {bar} <b>{pct}%</b>\n\n"
        f"🔥 <b>Серия:</b> {streak} дн.\n"
        f"🤝 <b>Помог другим:</b> {help_given} раз"
    )

    await msg.answer(text, parse_mode="HTML", reply_markup=kb)
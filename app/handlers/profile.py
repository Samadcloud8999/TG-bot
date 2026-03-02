from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from .. import db

router = Router()

class ProfileFlow(StatesGroup):
    set_password = State()


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
        "SELECT xp, level, streak, help_given_count, password FROM users WHERE tg_id=?",
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
    password = row[4] or ''

    next_need = xp_for_next_level(level)
    pct = min(100, int((xp / next_need) * 100)) if next_need > 0 else 0

    blocks = 10
    filled = int((pct / 100) * blocks)
    bar = "█" * filled + "░" * (blocks - filled)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="profile_refresh")],
        [InlineKeyboardButton(text="🔑 Установить пароль", callback_data="profile_set_password")]
    ])

    name = msg.from_user.full_name or "Пользователь"
    pass_text = password if password else "<i>(не задан)</i>"

    text = (
        f"🏆 <b>Профиль</b>\n"
        f"👤 <b>{name}</b>\n\n"
        f"🎖 <b>Уровень:</b> {level}\n"
        f"✨ <b>XP:</b> {xp} / {next_need}\n"
        f"📈 <b>Прогресс:</b> {bar} <b>{pct}%</b>\n\n"
        f"🔥 <b>Серия:</b> {streak} дн.\n"
        f"🤝 <b>Помог другим:</b> {help_given} раз\n"
        f"🔐 <b>Пароль:</b> {pass_text}"
    )

    await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "profile_set_password")
async def profile_set_password(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileFlow.set_password)
    await cb.message.answer(
        "🔑 Введи новый пароль. Другие люди смогут просмотреть твою галерею, если введут его.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="profile_cancel")]
        ])
    )
    await cb.answer()


@router.callback_query(F.data == "profile_cancel")
async def profile_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.answer("Ок, отменил ✅")
    await cb.answer()


@router.message(ProfileFlow.set_password)
async def profile_save_password(msg: Message, state: FSMContext):
    pwd = (msg.text or "").strip()
    if len(pwd) < 3:
        await msg.answer("Пароль слишком короткий, минимум 3 символа.")
        return
    await db.db.execute("UPDATE users SET password=? WHERE tg_id=?", (pwd, msg.from_user.id))
    await db.db.commit()
    await state.clear()
    await msg.answer("✅ Пароль сохранён.")

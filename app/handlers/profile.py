from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from .. import db

router = Router()

class ProfileFlow(StatesGroup):
    set_password = State()


def xp_for_next_level(level: int) -> int:
    return 100 + (level - 1) * 50


def safe_int(x, default=0) -> int:
    try:
        return int(x) if x is not None else default
    except (TypeError, ValueError):
        return default


def progress_bar(pct: int, blocks: int = 12) -> str:
    pct = max(0, min(100, pct))
    filled = round((pct / 100) * blocks)
    return "▰" * filled + "▱" * (blocks - filled)


def make_profile_kb(has_password: bool) -> InlineKeyboardMarkup:
    pwd_text = "🔒 Изменить пароль" if has_password else "🔑 Установить пароль"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="profile_refresh"),
            InlineKeyboardButton(text=pwd_text, callback_data="profile_set_password"),
        ]
    ])


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
    password = (row[4] or "").strip()

    next_need = max(1, xp_for_next_level(level))
    pct = min(100, int((xp / next_need) * 100))
    bar = progress_bar(pct, blocks=12)

    left = max(0, next_need - xp)
    has_password = bool(password)

    name = (msg.from_user.full_name or "Пользователь").strip()

    # Чтобы не палить пароль в чате — показываем статус (так безопаснее и выглядит лучше)
    pass_status = "✅ задан" if has_password else "❌ не задан"

    # небольшой “ранг” по уровню — чисто визуал (можешь убрать)
    if level >= 20:
        rank = "👑 Легенда"
    elif level >= 10:
        rank = "🦾 Профи"
    elif level >= 5:
        rank = "🚀 Опытный"
    else:
        rank = "🌱 Новичок"

    text = (
        "╔══════════════╗\n"
        "🏆 <b>ТВОЙ ПРОФИЛЬ</b>\n"
        "╚══════════════╝\n\n"
        f"👤 <b>{name}</b>\n"
        f"🏷 <b>Ранг:</b> {rank}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🎖 <b>Уровень:</b> <b>{level}</b>\n"
        f"✨ <b>XP:</b> <code>{xp}</code> / <code>{next_need}</code>\n"
        f"📊 <b>Прогресс:</b> {bar}  <b>{pct}%</b>\n"
        f"➕ <b>До апа:</b> <code>{left}</code> XP\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔥 <b>Серия:</b> <b>{streak}</b> дн.\n"
        f"🤝 <b>Помощь другим:</b> <b>{help_given}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔐 <b>Пароль к галерее:</b> {pass_status}\n"
        "\n"
        "<i>Совет: жми «Обновить», чтобы увидеть свежие цифры.</i>"
    )

    await msg.answer(text, parse_mode="HTML", reply_markup=make_profile_kb(has_password))


@router.callback_query(F.data == "profile_set_password")
async def profile_set_password(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(ProfileFlow.set_password)
    await cb.message.answer(
        "🔑 Введи новый пароль.\n"
        "<i>Его будут вводить другие люди, чтобы открыть твою галерею.</i>\n\n"
        "⚠️ Не ставь пароль от почты/банка — придумай отдельный.",
        parse_mode="HTML",
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
        await msg.answer("Пароль слишком короткий — минимум 3 символа.")
        return

    # чуть-чуть гигиены: ограничим длину, чтобы не ломать UI/БД
    if len(pwd) > 64:
        await msg.answer("Пароль слишком длинный — максимум 64 символа.")
        return

    await db.db.execute("UPDATE users SET password=? WHERE tg_id=?", (pwd, msg.from_user.id))
    await db.db.commit()
    await state.clear()

    await msg.answer("✅ Пароль сохранён. Теперь доступ к галерее можно открыть по нему.")
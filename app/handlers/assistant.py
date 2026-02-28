from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from ..keyboards import assistant_levels_kb  # твоя клавиатура уровней

router = Router()


# ---------- FSM ----------
class AssistantFlow(StatesGroup):
    topic = State()
    level = State()


# ---------- Keyboards ----------
def assistant_nav_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Новый вопрос", callback_data="ai:new")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="ai:back")],
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="ai:cancel")],
    ])

def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="ai:cancel")]
    ])

def after_answer_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Сменить уровень", callback_data="ai:change_level")],
        [InlineKeyboardButton(text="🆕 Новый вопрос", callback_data="ai:new")],
    ])


# ---------- Text builder ----------
def explain_template(topic: str, level: str) -> str:
    topic = topic.strip()

    if level == "l1":
        return (
            f"🧠 <b>Объяснение “как ребёнку”</b>\n"
            f"📌 <b>Тема:</b> {topic}\n\n"
            f"✅ <b>Что это?</b>\n"
            f"Представь, что <b>{topic}</b> — это простое правило.\n\n"
            f"🔎 <b>Зачем нужно?</b>\n"
            f"Чтобы быстро понимать и решать похожие задачи.\n\n"
            f"🧩 <b>Пример:</b>\n"
            f"Придумай 1 простой пример и объясни его в 1–2 предложениях.\n\n"
            f"🧪 <b>Проверка:</b>\n"
            f"1) Скажи определение одним предложением\n"
            f"2) Приведи пример\n"
            f"3) Объясни своими словами"
        )

    if level == "l3":
        return (
            f"🎓 <b>Академическое объяснение</b>\n"
            f"📌 <b>Тема:</b> {topic}\n\n"
            f"1) <b>Определение</b> (строго)\n"
            f"2) <b>Свойства</b> и следствия\n"
            f"3) <b>Условия применимости</b>\n"
            f"4) <b>Типовые ошибки</b>\n\n"
            f"🧪 <b>Самопроверка:</b>\n"
            f"• Сформулируй определение\n"
            f"• Приведи контрпример/ограничение\n"
            f"• Реши задачу и объясни ход"
        )

    # l2 по умолчанию
    return (
        f"✨ <b>Обычное объяснение</b>\n"
        f"📌 <b>Тема:</b> {topic}\n\n"
        f"✅ <b>Быстро понять:</b>\n"
        f"1) Что это (1–2 предложения)\n"
        f"2) Где применяется\n"
        f"3) 2 примера: лёгкий + средний\n\n"
        f"⚠️ <b>Частые ошибки:</b>\n"
        f"• Путают определение/условия\n"
        f"• Неправильно подставляют значения\n\n"
        f"🧪 <b>Мини-тест:</b>\n"
        f"1) Как объяснишь это в 1 фразе?\n"
        f"2) Где это используется?\n"
        f"3) Что будет, если поменять условие?"
    )


# ---------- Handlers ----------
@router.message(F.text == "🤖 Ассистент")
async def assistant_start(msg: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AssistantFlow.topic)
    await msg.answer(
        "🤖 <b>Ассистент</b>\n\n"
        "Напиши тему/вопрос, который нужно объяснить.\n"
        "Пример: <i>“Что такое производная?”</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )


@router.message(AssistantFlow.topic)
async def assistant_got_topic(msg: Message, state: FSMContext):
    topic = (msg.text or "").strip()
    if len(topic) < 3:
        await msg.answer("Тема слишком короткая. Напиши чуть подробнее 🙂", reply_markup=cancel_kb())
        return

    await state.update_data(topic=topic)
    await state.set_state(AssistantFlow.level)
    await msg.answer(
        "Выбери уровень объяснения:",
        reply_markup=assistant_levels_kb()
    )


@router.callback_query(F.data.startswith("ai:"))
async def assistant_level(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topic = (data.get("topic") or "").strip()

    action = cb.data.split("ai:", 1)[1]

    # навигация
    if action == "cancel":
        await state.clear()
        await cb.message.answer("Ок, отменил ✅")
        await cb.answer()
        return

    if action == "new":
        await state.clear()
        await state.set_state(AssistantFlow.topic)
        await cb.message.answer("Напиши новую тему/вопрос:", reply_markup=cancel_kb())
        await cb.answer()
        return

    if action == "back":
        await state.clear()
        await cb.message.answer("Вернулся назад ✅")
        await cb.answer()
        return

    if action == "change_level":
        if not topic:
            await state.set_state(AssistantFlow.topic)
            await cb.message.answer("Сначала напиши тему:", reply_markup=cancel_kb())
        else:
            await state.set_state(AssistantFlow.level)
            await cb.message.answer("Ок, выбери новый уровень:", reply_markup=assistant_levels_kb())
        await cb.answer()
        return

    # это уровень l1/l2/l3
    if action not in ("l1", "l2", "l3"):
        await cb.answer()
        return

    if not topic:
        await state.clear()
        await cb.message.answer("Сначала нажми 🤖 Ассистент и напиши тему.")
        await cb.answer()
        return

    text = explain_template(topic, action)

    await cb.message.answer(text, parse_mode="HTML", reply_markup=after_answer_kb())
    await cb.answer()
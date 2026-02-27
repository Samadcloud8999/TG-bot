from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from ..keyboards import assistant_levels_kb
from ..config import OPENAI_API_KEY

router = Router()

WAIT_AI_TOPIC = {}
AI_TOPIC_TEXT = {}

def fallback_explain(topic: str, level: str) -> str:
    # level: l1/l2/l3
    if level == "l1":
        return (
            f"1️⃣ Объяснение как ребёнку:\n"
            f"Представь, что **{topic}** — это простое правило.\n"
            f"Смысл: понять *что это*, *зачем нужно*, и *увидеть пример*.\n\n"
            "✅ План:\n"
            "1) Дай определение 1 предложением\n"
            "2) Приведи 1 простой пример\n"
            "3) Повтори своими словами\n"
        )
    if level == "l3":
        return (
            f"3️⃣ Академическое объяснение:\n"
            f"Тема: **{topic}**\n\n"
            "📌 Структура:\n"
            "• определения и формальные свойства\n"
            "• условия применимости\n"
            "• типовые задачи и ошибки\n\n"
            "🧪 Самопроверка:\n"
            "1) Сформулируй ключевое определение\n"
            "2) Приведи контрпример/ограничение\n"
            "3) Реши задачу и объясни ход\n"
        )
    return (
        f"2️⃣ Обычное объяснение:\n"
        f"Тема: **{topic}**\n\n"
        "✅ Быстро понять:\n"
        "1) Что это (1–2 предложения)\n"
        "2) Где применяется\n"
        "3) 2 примера (лёгкий и средний)\n\n"
        "📝 Вопросы:\n"
        "• Что будет если изменить условие?\n"
        "• Какая самая частая ошибка?\n"
    )

@router.message(F.text == "🤖 Ассистент")
async def assistant_start(msg: Message):
    WAIT_AI_TOPIC[msg.from_user.id] = True
    await msg.answer("Напиши тему/вопрос, который нужно объяснить:")

@router.message(lambda m: WAIT_AI_TOPIC.get(m.from_user.id, False))
async def assistant_got_topic(msg: Message):
    WAIT_AI_TOPIC.pop(msg.from_user.id, None)
    AI_TOPIC_TEXT[msg.from_user.id] = msg.text.strip()
    await msg.answer("Выбери уровень объяснения:", reply_markup=assistant_levels_kb())

@router.callback_query(F.data.startswith("ai:"))
async def assistant_level(cb: CallbackQuery):
    tg_id = cb.from_user.id
    level = cb.data.split("ai:", 1)[1]  # l1/l2/l3
    topic = AI_TOPIC_TEXT.pop(tg_id, "").strip()

    if not topic:
        await cb.message.answer("Сначала нажми 🤖 Ассистент и напиши тему.")
        await cb.answer()
        return

    # место под внешний API (опционально). Сейчас fallback.
    # Чтобы не ломать MVP — всегда работаем без API.
    text = fallback_explain(topic, level)

    await cb.message.answer(text, parse_mode="Markdown")
    await cb.answer()
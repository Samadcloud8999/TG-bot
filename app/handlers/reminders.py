from aiogram import Router, F
from aiogram.types import Message
from .. import db

router = Router()

@router.message(F.text == "⏰ Напоминания")
async def reminders(msg: Message):
    tg_id = msg.from_user.id

    cur = await db.db.execute(
        "SELECT reminders_enabled FROM users WHERE tg_id=?",
        (tg_id,)
    )
    row = await cur.fetchone()

    if not row:
        await msg.answer("Нажми /start")
        return

    enabled = int(row[0])
    new_val = 0 if enabled == 1 else 1

    await db.db.execute(
        "UPDATE users SET reminders_enabled=? WHERE tg_id=?",
        (new_val, tg_id)
    )
    await db.db.commit()

    await msg.answer("✅ Напоминания включены" if new_val == 1 else "⛔ Напоминания выключены")
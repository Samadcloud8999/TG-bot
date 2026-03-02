from aiogram import Router, F
from aiogram.types import Message
from datetime import datetime
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

    # ---------- дополнительные сведения ----------
    now = datetime.utcnow().isoformat()
    cur2 = await db.db.execute(
        "SELECT COUNT(*) FROM reviews r JOIN topics t ON t.id=r.topic_id "
        "WHERE t.tg_id=? AND r.next_review <= ?",
        (tg_id, now)
    )
    pending = (await cur2.fetchone())[0] or 0
    cur3 = await db.db.execute(
        "SELECT MIN(r.next_review) FROM reviews r JOIN topics t ON t.id=r.topic_id "
        "WHERE t.tg_id=? AND r.next_review > ?",
        (tg_id, now)
    )
    nxt = await cur3.fetchone()
    next_text = nxt[0] if nxt and nxt[0] else "—"

    status = "включены" if new_val == 1 else "выключены"
    msg_text = f"✅ Напоминания {status}." if new_val == 1 else f"⛔ Напоминания {status}."
    if new_val == 1:
        msg_text += f"\n📌 Отложенных: {pending}. Следующее: {next_text}."

    await msg.answer(msg_text)
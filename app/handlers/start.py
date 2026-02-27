from aiogram import Router, F
from aiogram.types import Message
from .. import db
from ..keyboards import main_kb

router = Router()

@router.message(F.text == "/start")
async def start_cmd(msg: Message):
    await db.db.execute(
        "INSERT OR IGNORE INTO users(tg_id) VALUES(?)",
        (msg.from_user.id,)
    )
    await db.db.commit()

    await msg.answer(
        "Привет! Я SmartStudy 🤖\n"
        "Я помогаю: повторять по интервалам, хранить материалы по предметам и получать помощь от одноклассников.\n\n"
        "Выбирай кнопки ниже 👇",
        reply_markup=main_kb()
    )
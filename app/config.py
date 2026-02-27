import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SUBJECTS = [
    "Алгебра", "Геометрия", "Биология", "Химия", "Физика", "География",
    "История", "ЧиО", "ПО/Информатика", "Русский язык", "Литература",
    "Английский", "Кыргызский", "Адабият", "ДПМ", "БЯП"
]
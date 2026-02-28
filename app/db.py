import aiosqlite

DB_FILE = "smartstudy.db"
db = None

async def init_db():
    global db
    db = await aiosqlite.connect(DB_FILE)
    await db.execute("PRAGMA foreign_keys = ON;")
    await db.commit()

async def create_tables():
    # Базовые таблицы
    await db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        streak INTEGER DEFAULT 0,
        last_streak_date TEXT,
        reminders_enabled INTEGER DEFAULT 1,
        help_given_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tg_id) REFERENCES users(tg_id)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        next_review TEXT NOT NULL,
        step INTEGER DEFAULT 0,
        FOREIGN KEY (topic_id) REFERENCES topics(id)
    );
    """)
    await db.commit()

    # --- Обновления схемы (на случай старой БД) ---
    # users.reminders_enabled
    try:
        await db.execute("ALTER TABLE users ADD COLUMN reminders_enabled INTEGER DEFAULT 1")
        await db.commit()
    except Exception:
        pass

    # users.help_given_count
    try:
        await db.execute("ALTER TABLE users ADD COLUMN help_given_count INTEGER DEFAULT 0")
        await db.commit()
    except Exception:
        pass

    # --- Новые фичи: предметы/материалы ---
    await db.executescript("""
    CREATE TABLE IF NOT EXISTS user_subjects (
        tg_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (tg_id, subject),
        FOREIGN KEY (tg_id) REFERENCES users(tg_id)
    );

    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        kind TEXT NOT NULL,              -- text/photo/pdf
        file_id TEXT,                    -- для photo/pdf
        text TEXT,                       -- для text или подписи
        tags TEXT,                       -- ключевые слова (опционально)
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tg_id) REFERENCES users(tg_id)
    );

    CREATE TABLE IF NOT EXISTS help_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER NOT NULL,
        subject TEXT,
        topic TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'open',      -- open/closed
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        ai_sent INTEGER DEFAULT 0,
        FOREIGN KEY (tg_id) REFERENCES users(tg_id)
    );

    CREATE TABLE IF NOT EXISTS help_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        responder_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES help_requests(id),
        FOREIGN KEY (responder_id) REFERENCES users(tg_id)
    );

    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (tg_id, code),
        FOREIGN KEY (tg_id) REFERENCES users(tg_id)
    );
    -- Чтобы не спамить напоминаниями каждую минуту
    CREATE TABLE IF NOT EXISTS review_notifications (
        review_id INTEGER PRIMARY KEY,
        last_sent TEXT
    );
    """)
    await db.commit()

    # --- Таблица предметов ---
    await db.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(tg_id, name),
        FOREIGN KEY(tg_id) REFERENCES users(tg_id)
    )
    """)
    await db.commit()

    # --- Доп. таблицы: folders и материалы внутри папки ---
    await db.execute("""
    CREATE TABLE IF NOT EXISTS folders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER NOT NULL,
        subject_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(subject_id) REFERENCES subjects(id)
    )
    """)
    await db.commit()

    await db.execute("""
    CREATE TABLE IF NOT EXISTS folder_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER NOT NULL,
        folder_id INTEGER NOT NULL,
        kind TEXT NOT NULL,
        title TEXT,
        file_id TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(folder_id) REFERENCES folders(id)
    )
    """)
    await db.commit()
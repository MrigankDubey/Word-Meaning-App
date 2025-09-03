import os
import sqlite3
from contextlib import contextmanager

APP_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "app.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash BLOB NOT NULL,
            is_admin INTEGER DEFAULT 0,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            definition TEXT NOT NULL,
            part_of_speech TEXT,
            language TEXT DEFAULT 'en',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date_local TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS session_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            word_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            user_answer TEXT,
            correct INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES sessions(id),
            FOREIGN KEY(word_id) REFERENCES words(id)
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_day_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date_local TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            UNIQUE(user_id, date_local, word_id)
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word_id INTEGER NOT NULL,
            date_local TEXT NOT NULL,
            correct INTEGER NOT NULL,
            response_time_ms INTEGER,
            box INTEGER DEFAULT 1, -- Leitner box (1-5)
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(word_id) REFERENCES words(id)
        )
        """)
        con.commit()

@contextmanager
def get_conn():
    con = sqlite3.connect(DB_PATH)
    try:
        yield con
    finally:
        con.close()

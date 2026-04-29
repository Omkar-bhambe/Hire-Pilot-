import sqlite3

DB_NAME = "interview.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # USERS (Admin)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT,
        role TEXT
    )
    """)

    # INTERVIEWS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interviews (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        job_description TEXT,
        resume TEXT,
        schedule_time TEXT,
        status TEXT
    )
    """)

    # ANSWERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id TEXT,
        question TEXT,
        answer TEXT,
        score INTEGER,
        feedback TEXT
    )
    """)

    conn.commit()
    conn.close()
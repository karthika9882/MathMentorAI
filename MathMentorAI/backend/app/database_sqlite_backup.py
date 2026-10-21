import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "mathmentor.db"

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS student_profiles (
            student_id TEXT PRIMARY KEY, grade INTEGER NOT NULL DEFAULT 9,
            language TEXT NOT NULL DEFAULT 'en', support_level TEXT NOT NULL DEFAULT 'guided',
            correct_streak INTEGER NOT NULL DEFAULT 0, wrong_streak INTEGER NOT NULL DEFAULT 0,
            total_answered INTEGER NOT NULL DEFAULT 0, total_correct INTEGER NOT NULL DEFAULT 0)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS answer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL, topic TEXT NOT NULL,
            question TEXT NOT NULL, submitted_answer TEXT NOT NULL, is_correct INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")

def get_or_create_student(student_id: str, grade: int = 9, language: str = "en"):
    with connect() as conn:
        row = conn.execute("SELECT * FROM student_profiles WHERE student_id=?", (student_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO student_profiles (student_id,grade,language) VALUES (?,?,?)",
                         (student_id, grade, language))
            row = conn.execute("SELECT * FROM student_profiles WHERE student_id=?", (student_id,)).fetchone()
        return dict(row)

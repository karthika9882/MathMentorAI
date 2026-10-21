
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Add it to the backend/.env file."
    )


def connect():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS student_profiles (
                student_id TEXT PRIMARY KEY,
                grade INTEGER NOT NULL DEFAULT 9,
                language TEXT NOT NULL DEFAULT 'en',
                support_level TEXT NOT NULL DEFAULT 'guided',
                correct_streak INTEGER NOT NULL DEFAULT 0,
                wrong_streak INTEGER NOT NULL DEFAULT 0,
                total_answered INTEGER NOT NULL DEFAULT 0,
                total_correct INTEGER NOT NULL DEFAULT 0
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS answer_history (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                student_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                question TEXT NOT NULL,
                submitted_answer TEXT NOT NULL,
                is_correct BOOLEAN NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_accounts (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                grade INTEGER NOT NULL DEFAULT 9,
                language TEXT NOT NULL DEFAULT 'en',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_or_create_student(
    student_id: str,
    grade: int = 9,
    language: str = "en",
):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO student_profiles (
                student_id, grade, language
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (student_id) DO NOTHING
            """,
            (student_id, grade, language),
        )

        row = conn.execute(
            """
            SELECT *
            FROM student_profiles
            WHERE student_id = %s
            """,
            (student_id,),
        ).fetchone()

        return dict(row)

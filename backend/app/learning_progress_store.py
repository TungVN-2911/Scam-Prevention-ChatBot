import json
from contextlib import contextmanager
from typing import Optional

import pyodbc

from app.config import settings

ANONYMOUS_USER_KEY = "anonymous_user"


@contextmanager
def _connection():
    conn = pyodbc.connect(settings.sql_server_connection_string)
    try:
        yield conn
    finally:
        conn.close()


def get_or_create_learning_progress(user_key: str = ANONYMOUS_USER_KEY) -> dict:
    with _connection() as conn:
        row = conn.execute(
            "SELECT xp FROM learning_progress WHERE user_key = ?", user_key
        ).fetchone()
        if row is not None:
            return {"xp": row[0]}

        conn.execute(
            "INSERT INTO learning_progress (user_key, xp) VALUES (?, 0)", user_key
        )
        conn.commit()
    return {"xp": 0}


def record_quiz_attempt(
    topic: str,
    correct_count: int,
    total_questions: int,
    xp_earned: int,
    answers: Optional[dict[str, int]] = None,
    user_key: str = ANONYMOUS_USER_KEY,
) -> None:
    with _connection() as conn:
        conn.execute(
            "INSERT INTO quiz_attempts "
            "(user_key, topic, correct_count, total_questions, xp_earned, answers_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            user_key, topic, correct_count, total_questions, xp_earned,
            json.dumps(answers or {}, ensure_ascii=False),
        )
        conn.commit()


def list_quiz_attempts(user_key: str = ANONYMOUS_USER_KEY, limit: int = 10) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            "SELECT TOP (?) id, topic, correct_count, total_questions, xp_earned, created_at, answers_json "
            "FROM quiz_attempts WHERE user_key = ? ORDER BY id DESC",
            limit, user_key,
        ).fetchall()
    return [
        {
            "id": r[0],
            "topic": r[1],
            "correct_count": r[2],
            "total_questions": r[3],
            "xp_earned": r[4],
            "created_at": r[5].isoformat(),
            "answers": json.loads(r[6]) if r[6] else {},
        }
        for r in rows
    ]


def record_detective_attempt(
    case_id: str,
    correct_count: int,
    total_expected: int,
    xp_earned: int,
    result: Optional[dict] = None,
    user_key: str = ANONYMOUS_USER_KEY,
) -> None:
    # Luu san ca dap an vi GET /detective/cases/{id} khong tra ve dap an (chong spoil).
    with _connection() as conn:
        conn.execute(
            "INSERT INTO detective_attempts "
            "(user_key, case_id, correct_count, total_expected, xp_earned, result_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            user_key, case_id, correct_count, total_expected, xp_earned,
            json.dumps(result or {}, ensure_ascii=False),
        )
        conn.commit()


def list_detective_attempts(user_key: str = ANONYMOUS_USER_KEY, limit: int = 10) -> list[dict]:
    with _connection() as conn:
        rows = conn.execute(
            "SELECT TOP (?) id, case_id, correct_count, total_expected, xp_earned, created_at, result_json "
            "FROM detective_attempts WHERE user_key = ? ORDER BY id DESC",
            limit, user_key,
        ).fetchall()
    return [
        {
            "id": r[0],
            "case_id": r[1],
            "correct_count": r[2],
            "total_expected": r[3],
            "xp_earned": r[4],
            "created_at": r[5].isoformat(),
            "result": json.loads(r[6]) if r[6] else {},
        }
        for r in rows
    ]


def add_xp(amount: int, user_key: str = ANONYMOUS_USER_KEY) -> int:
    # UPDATE nguyen tu (khong doc-tinh-ghi rieng le) de tranh race condition.
    with _connection() as conn:
        cursor = conn.execute(
            "UPDATE learning_progress SET xp = xp + ?, updated_at = SYSUTCDATETIME() "
            "WHERE user_key = ?",
            amount, user_key,
        )
        if cursor.rowcount == 0:
            conn.execute(
                "INSERT INTO learning_progress (user_key, xp) VALUES (?, ?)",
                user_key, amount,
            )
        conn.commit()
        row = conn.execute(
            "SELECT xp FROM learning_progress WHERE user_key = ?", user_key
        ).fetchone()
    return row[0]

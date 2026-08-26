from contextlib import contextmanager

import pyodbc

from app.config import settings

# Chua co authentication, chi co 1 nguoi dung duy nhat -> dung 1 hang so co
# dinh lam khoa, khong can he thong user/login phuc tap.
ANONYMOUS_USER_KEY = "anonymous_user"


@contextmanager
def _connection():
    conn = pyodbc.connect(settings.sql_server_connection_string)
    try:
        yield conn
    finally:
        conn.close()


def get_or_create_learning_progress(user_key: str = ANONYMOUS_USER_KEY) -> dict:
    """Tra ve tien do hoc tap (hien tai chi gom XP); tao ban ghi mac dinh
    neu chua ton tai. Doc lap hoan toan voi conversation session."""
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


def add_xp(amount: int, user_key: str = ANONYMOUS_USER_KEY) -> int:
    """Cong don XP bang 1 UPDATE nguyen tu (khong doc-tinh-ghi rieng le de
    tranh race condition). Neu ban ghi chua ton tai (hiem, vi app start da
    goi get_or_create_learning_progress truoc), tu tao voi gia tri ban dau."""
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

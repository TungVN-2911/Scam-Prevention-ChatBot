from contextlib import contextmanager

import bcrypt
import pyodbc

from app.config import settings


@contextmanager
def _connection():
    conn = pyodbc.connect(settings.sql_server_connection_string)
    try:
        yield conn
    finally:
        conn.close()


def create_user(username: str, password: str, role: str = "user") -> None:
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with _connection() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            username, password_hash, role,
        )
        conn.commit()


def verify_user(username: str, password: str) -> str | None:
    with _connection() as conn:
        row = conn.execute(
            "SELECT password_hash, role FROM users WHERE username = ?", username
        ).fetchone()
    if row is None:
        return None
    if bcrypt.checkpw(password.encode(), row.password_hash.encode()):
        return row.role
    return None
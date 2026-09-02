import json
import uuid
from contextlib import contextmanager
from typing import Optional

import pyodbc

from app.config import settings


@contextmanager
def _connection():
    conn = pyodbc.connect(settings.sql_server_connection_string)
    try:
        yield conn
    finally:
        conn.close()


def create_session(username: Optional[str] = None) -> str:
    session_id = str(uuid.uuid4())
    with _connection() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (session_id, username) VALUES (?, ?)",
            session_id, username,
        )
        conn.commit()
    return session_id


def create_session_with_message(
    role: str, content: str, sources: Optional[list[str]] = None, username: Optional[str] = None
) -> str:
    # pyodbc autocommit=False mac dinh nen 1 commit() cuoi la du de atomic ca 2 INSERT.
    session_id = str(uuid.uuid4())
    with _connection() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (session_id, username) VALUES (?, ?)",
            session_id, username,
        )
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, sources_json) VALUES (?, ?, ?, ?)",
            session_id, role, content, json.dumps(sources or [], ensure_ascii=False),
        )
        conn.commit()
    return session_id


def get_session(session_id: str, username: Optional[str] = None) -> Optional[dict]:
    # Neu truyen username, session cua nguoi khac coi nhu khong ton tai.
    with _connection() as conn:
        row = conn.execute(
            "SELECT session_id, username FROM chat_sessions WHERE session_id = ?", session_id
        ).fetchone()
        if row is None:
            return None
        if username is not None and row.username != username:
            return None

        rows = conn.execute(
            "SELECT role, content, sources_json FROM chat_messages "
            "WHERE session_id = ? ORDER BY id ASC",
            session_id,
        ).fetchall()

    messages = [
        {
            "role": r[0],
            "content": r[1],
            "sources": json.loads(r[2]) if r[2] else [],
        }
        for r in rows
    ]
    return {"messages": messages}


def append_message(session_id: str, role: str, content: str, sources: Optional[list[str]] = None) -> None:
    with _connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, sources_json) VALUES (?, ?, ?, ?)",
            session_id, role, content, json.dumps(sources or [], ensure_ascii=False),
        )
        conn.execute(
            "UPDATE chat_sessions SET updated_at = SYSUTCDATETIME() WHERE session_id = ?",
            session_id,
        )
        conn.commit()


def list_sessions(limit: int = 20, username: Optional[str] = None) -> list[dict]:
    # Chi liet ke phien DA CO tin nhan - phien moi tao chua chat se khong hien.
    with _connection() as conn:
        rows = conn.execute(
            "SELECT TOP (?) s.session_id, s.updated_at, "
            "(SELECT TOP 1 content FROM chat_messages m "
            " WHERE m.session_id = s.session_id AND m.role = 'user' "
            " ORDER BY m.id ASC) AS first_message, "
            "(SELECT MAX(m.id) FROM chat_messages m WHERE m.session_id = s.session_id) AS last_message_id "
            "FROM chat_sessions s "
            "WHERE EXISTS (SELECT 1 FROM chat_messages m WHERE m.session_id = s.session_id) "
            "AND (? IS NULL OR s.username = ?) "
            # last_message_id, khong phai updated_at: phien tao lien tiep co the trung timestamp.
            "ORDER BY last_message_id DESC",
            limit, username, username,
        ).fetchall()

    sessions = []
    for session_id, updated_at, first_message, _last_message_id in rows:
        title = (first_message or "").replace("\n", " ").strip()
        if len(title) > 40:
            title = title[:40] + "…"
        if not title:
            title = "Cuộc trò chuyện"
        sessions.append({"session_id": session_id, "title": title, "updated_at": updated_at.isoformat()})
    return sessions


def delete_session_if_empty(session_id: str, username: Optional[str] = None) -> None:
    with _connection() as conn:
        conn.execute(
            "DELETE FROM chat_sessions WHERE session_id = ? "
            "AND NOT EXISTS (SELECT 1 FROM chat_messages WHERE session_id = ?) "
            "AND (? IS NULL OR username = ?)",
            session_id, session_id, username, username,
        )
        conn.commit()

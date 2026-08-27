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


def create_session() -> str:
    session_id = str(uuid.uuid4())
    with _connection() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (session_id) VALUES (?)",
            session_id,
        )
        conn.commit()
    return session_id


def create_session_with_message(role: str, content: str, sources: Optional[list[str]] = None) -> str:
    """Tao session moi VA luu tin nhan dau tien trong cung 1 transaction.
    pyodbc mac dinh autocommit=False nen chi commit() 1 lan o cuoi la du de
    dat tinh atomic (khong can them transaction framework moi): neu co loi
    truoc dong commit, dong ket noi se tu rollback ca 2 INSERT."""
    session_id = str(uuid.uuid4())
    with _connection() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (session_id) VALUES (?)",
            session_id,
        )
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, sources_json) VALUES (?, ?, ?, ?)",
            session_id, role, content, json.dumps(sources or [], ensure_ascii=False),
        )
        conn.commit()
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    with _connection() as conn:
        row = conn.execute(
            "SELECT session_id FROM chat_sessions WHERE session_id = ?", session_id
        ).fetchone()
        if row is None:
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


def list_sessions(limit: int = 20) -> list[dict]:
    """Chi liet ke cac phien DA CO tin nhan - phien moi tao nhung chua chat
    se khong hien trong danh sach, tranh nham voi nut "Cuoc tro chuyen moi".
    Gioi han so luong tra ve (moi nhat truoc) de sidebar khong phinh to vo han
    theo thoi gian su dung."""
    with _connection() as conn:
        rows = conn.execute(
            "SELECT TOP (?) s.session_id, s.updated_at, "
            "(SELECT TOP 1 content FROM chat_messages m "
            " WHERE m.session_id = s.session_id AND m.role = 'user' "
            " ORDER BY m.id ASC) AS first_message, "
            "(SELECT MAX(m.id) FROM chat_messages m WHERE m.session_id = s.session_id) AS last_message_id "
            "FROM chat_sessions s "
            "WHERE EXISTS (SELECT 1 FROM chat_messages m WHERE m.session_id = s.session_id) "
            # Sap xep theo id tu tang cua chat_messages (don dieu tuyet doi) thay vi
            # updated_at, vi cac phien tao lien tiep co the bi trung timestamp do
            # do phan giai dong ho SQL Server.
            "ORDER BY last_message_id DESC",
            limit,
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


def delete_session_if_empty(session_id: str) -> None:
    """Xoa han phien khoi DB neu chua co tin nhan nao - dung khi nguoi dung
    roi khoi 1 phien moi tao ma chua chat, tranh tich luy phien rac."""
    with _connection() as conn:
        conn.execute(
            "DELETE FROM chat_sessions WHERE session_id = ? "
            "AND NOT EXISTS (SELECT 1 FROM chat_messages WHERE session_id = ?)",
            session_id, session_id,
        )
        conn.commit()

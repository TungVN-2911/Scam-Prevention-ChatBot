import uuid

import pytest

from app import session_store
from app.config import settings

pytestmark = pytest.mark.skipif(
    not settings.sql_server_connection_string,
    reason="Cần SQL_SERVER_CONNECTION_STRING trong .env để chạy test kết nối SQL Server thật",
)


def test_create_and_get_session_round_trip():
    session_id = session_store.create_session()
    state = session_store.get_session(session_id)
    assert state == {"messages": []}


def test_get_session_not_found_returns_none():
    assert session_store.get_session(str(uuid.uuid4())) is None


def test_append_message_and_get_session():
    session_id = session_store.create_session()
    session_store.append_message(session_id, "user", "Xin chào", [])
    session_store.append_message(session_id, "assistant", "Chào bạn", ["data/hotlines.json"])

    state = session_store.get_session(session_id)

    assert state["messages"] == [
        {"role": "user", "content": "Xin chào", "sources": []},
        {"role": "assistant", "content": "Chào bạn", "sources": ["data/hotlines.json"]},
    ]


def test_list_sessions_excludes_session_without_messages():
    session_id = session_store.create_session()

    sessions = session_store.list_sessions()

    assert all(s["session_id"] != session_id for s in sessions)


def test_list_sessions_title_uses_first_user_message():
    session_id = session_store.create_session()
    session_store.append_message(session_id, "user", "Tôi vừa bị lừa chuyển tiền", [])
    session_store.append_message(session_id, "assistant", "Bạn cần bình tĩnh...", [])

    sessions = session_store.list_sessions()

    matching = next(s for s in sessions if s["session_id"] == session_id)
    assert matching["title"] == "Tôi vừa bị lừa chuyển tiền"


def test_list_sessions_most_recently_updated_first():
    older_id = session_store.create_session()
    session_store.append_message(older_id, "user", "tin nhắn cũ hơn", [])
    newer_id = session_store.create_session()
    session_store.append_message(newer_id, "user", "tin nhắn mới nhất", [])

    sessions = session_store.list_sessions()
    ids_in_order = [s["session_id"] for s in sessions]

    assert ids_in_order.index(newer_id) < ids_in_order.index(older_id)


def test_list_sessions_respects_limit():
    for i in range(3):
        session_id = session_store.create_session()
        session_store.append_message(session_id, "user", f"limit test {i}", [])

    sessions = session_store.list_sessions(limit=2)

    assert len(sessions) == 2


def test_delete_session_if_empty_removes_session_without_messages():
    session_id = session_store.create_session()

    session_store.delete_session_if_empty(session_id)

    assert session_store.get_session(session_id) is None


def test_delete_session_if_empty_keeps_session_with_messages():
    session_id = session_store.create_session()
    session_store.append_message(session_id, "user", "Xin chào", [])

    session_store.delete_session_if_empty(session_id)

    assert session_store.get_session(session_id) is not None


def test_delete_session_if_empty_on_unknown_id_does_not_crash():
    session_store.delete_session_if_empty(str(uuid.uuid4()))


def test_create_session_with_message_creates_session_with_one_message():
    session_id = session_store.create_session_with_message("user", "Xin chào", [])

    state = session_store.get_session(session_id)

    assert state == {
        "messages": [{"role": "user", "content": "Xin chào", "sources": []}],
    }


def test_create_session_with_message_two_calls_produce_different_sessions():
    first_id = session_store.create_session_with_message("user", "Tin nhắn A", [])
    second_id = session_store.create_session_with_message("user", "Tin nhắn B", [])

    assert first_id != second_id
    assert session_store.get_session(first_id)["messages"][0]["content"] == "Tin nhắn A"
    assert session_store.get_session(second_id)["messages"][0]["content"] == "Tin nhắn B"


def test_create_session_with_message_then_append_assistant_message():
    session_id = session_store.create_session_with_message("user", "Xin chào", [])
    session_store.append_message(session_id, "assistant", "Chào bạn", ["data/hotlines.json"])

    state = session_store.get_session(session_id)

    assert state["messages"] == [
        {"role": "user", "content": "Xin chào", "sources": []},
        {"role": "assistant", "content": "Chào bạn", "sources": ["data/hotlines.json"]},
    ]

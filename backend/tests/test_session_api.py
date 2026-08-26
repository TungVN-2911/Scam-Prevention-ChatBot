import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not settings.sql_server_connection_string,
    reason="Cần SQL_SERVER_CONNECTION_STRING trong .env để chạy test kết nối SQL Server thật",
)

client = TestClient(app)


def test_create_then_get_session():
    session_id = client.post("/api/session").json()["session_id"]

    response = client.get(f"/api/session/{session_id}")

    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_get_unknown_session_returns_404():
    response = client.get(f"/api/session/{uuid.uuid4()}")
    assert response.status_code == 404


def test_add_message_then_visible_in_get():
    session_id = client.post("/api/session").json()["session_id"]

    response = client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
    )
    assert response.status_code == 204

    state = client.get(f"/api/session/{session_id}").json()
    assert state["messages"] == [{"role": "user", "content": "Xin chào", "sources": []}]


def test_add_message_to_unknown_session_returns_404():
    response = client.post(
        f"/api/session/{uuid.uuid4()}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
    )
    assert response.status_code == 404


def test_list_sessions_excludes_session_without_messages():
    session_id = client.post("/api/session").json()["session_id"]

    response = client.get("/api/sessions")

    assert response.status_code == 200
    ids = [s["session_id"] for s in response.json()]
    assert session_id not in ids


def test_list_sessions_includes_session_after_first_message():
    session_id = client.post("/api/session").json()["session_id"]
    client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
    )

    response = client.get("/api/sessions")

    ids = [s["session_id"] for s in response.json()]
    assert session_id in ids


def test_delete_empty_session_via_api():
    session_id = client.post("/api/session").json()["session_id"]

    response = client.delete(f"/api/session/{session_id}")

    assert response.status_code == 204
    assert client.get(f"/api/session/{session_id}").status_code == 404


def test_delete_session_with_messages_keeps_it_via_api():
    session_id = client.post("/api/session").json()["session_id"]
    client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
    )

    client.delete(f"/api/session/{session_id}")

    assert client.get(f"/api/session/{session_id}").status_code == 200


def test_start_session_creates_session_with_first_message():
    response = client.post("/api/session/start", json={"content": "Xin chào", "sources": []})

    assert response.status_code == 200
    session_id = response.json()["session_id"]

    state = client.get(f"/api/session/{session_id}").json()
    assert state == {
        "messages": [{"role": "user", "content": "Xin chào", "sources": []}],
    }


def test_start_session_rejects_empty_content():
    response = client.post("/api/session/start", json={"content": "   ", "sources": []})
    assert response.status_code == 400


def test_start_session_appears_in_sessions_list():
    session_id = client.post("/api/session/start", json={"content": "Tôi vừa bị lừa", "sources": []}).json()[
        "session_id"
    ]

    ids = [s["session_id"] for s in client.get("/api/sessions").json()]

    assert session_id in ids


def test_two_start_session_calls_produce_different_sessions():
    first_id = client.post("/api/session/start", json={"content": "Tin nhắn A", "sources": []}).json()["session_id"]
    second_id = client.post("/api/session/start", json={"content": "Tin nhắn B", "sources": []}).json()["session_id"]

    assert first_id != second_id

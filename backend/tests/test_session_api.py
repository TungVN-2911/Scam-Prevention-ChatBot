import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.config import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not settings.sql_server_connection_string or not settings.jwt_secret_key,
    reason="Cần SQL_SERVER_CONNECTION_STRING và JWT_SECRET_KEY trong .env để chạy test kết nối SQL Server thật",
)

client = TestClient(app)


def _headers_for(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(username, 'user')}"}


def test_create_session_requires_auth():
    response = client.post("/api/session")
    assert response.status_code == 401


def test_create_then_get_session():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=headers).json()["session_id"]

    response = client.get(f"/api/session/{session_id}", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_get_unknown_session_returns_404():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    response = client.get(f"/api/session/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


def test_get_session_of_another_user_returns_404():
    owner = _headers_for(f"test-{uuid.uuid4()}")
    other = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=owner).json()["session_id"]

    response = client.get(f"/api/session/{session_id}", headers=other)

    assert response.status_code == 404


def test_add_message_then_visible_in_get():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=headers).json()["session_id"]

    response = client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
        headers=headers,
    )
    assert response.status_code == 204

    state = client.get(f"/api/session/{session_id}", headers=headers).json()
    assert state["messages"] == [{"role": "user", "content": "Xin chào", "sources": []}]


def test_add_message_to_unknown_session_returns_404():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    response = client.post(
        f"/api/session/{uuid.uuid4()}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
        headers=headers,
    )
    assert response.status_code == 404


def test_add_message_to_another_users_session_returns_404():
    owner = _headers_for(f"test-{uuid.uuid4()}")
    other = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=owner).json()["session_id"]

    response = client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
        headers=other,
    )

    assert response.status_code == 404


def test_list_sessions_excludes_session_without_messages():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=headers).json()["session_id"]

    response = client.get("/api/sessions", headers=headers)

    assert response.status_code == 200
    ids = [s["session_id"] for s in response.json()]
    assert session_id not in ids


def test_list_sessions_includes_session_after_first_message():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=headers).json()["session_id"]
    client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
        headers=headers,
    )

    response = client.get("/api/sessions", headers=headers)

    ids = [s["session_id"] for s in response.json()]
    assert session_id in ids


def test_list_sessions_does_not_include_another_users_sessions():
    owner = _headers_for(f"test-{uuid.uuid4()}")
    other = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=owner).json()["session_id"]
    client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
        headers=owner,
    )

    ids = [s["session_id"] for s in client.get("/api/sessions", headers=other).json()]

    assert session_id not in ids


def test_delete_empty_session_via_api():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=headers).json()["session_id"]

    response = client.delete(f"/api/session/{session_id}", headers=headers)

    assert response.status_code == 204
    assert client.get(f"/api/session/{session_id}", headers=headers).status_code == 404


def test_delete_session_with_messages_keeps_it_via_api():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=headers).json()["session_id"]
    client.post(
        f"/api/session/{session_id}/messages",
        json={"role": "user", "content": "Xin chào", "sources": []},
        headers=headers,
    )

    client.delete(f"/api/session/{session_id}", headers=headers)

    assert client.get(f"/api/session/{session_id}", headers=headers).status_code == 200


def test_delete_another_users_session_does_not_remove_it():
    owner = _headers_for(f"test-{uuid.uuid4()}")
    other = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post("/api/session", headers=owner).json()["session_id"]

    client.delete(f"/api/session/{session_id}", headers=other)

    assert client.get(f"/api/session/{session_id}", headers=owner).status_code == 200


def test_start_session_creates_session_with_first_message():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    response = client.post("/api/session/start", json={"content": "Xin chào", "sources": []}, headers=headers)

    assert response.status_code == 200
    session_id = response.json()["session_id"]

    state = client.get(f"/api/session/{session_id}", headers=headers).json()
    assert state == {
        "messages": [{"role": "user", "content": "Xin chào", "sources": []}],
    }


def test_start_session_rejects_empty_content():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    response = client.post("/api/session/start", json={"content": "   ", "sources": []}, headers=headers)
    assert response.status_code == 400


def test_start_session_appears_in_sessions_list():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    session_id = client.post(
        "/api/session/start", json={"content": "Tôi vừa bị lừa", "sources": []}, headers=headers
    ).json()["session_id"]

    ids = [s["session_id"] for s in client.get("/api/sessions", headers=headers).json()]

    assert session_id in ids


def test_two_start_session_calls_produce_different_sessions():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    first_id = client.post(
        "/api/session/start", json={"content": "Tin nhắn A", "sources": []}, headers=headers
    ).json()["session_id"]
    second_id = client.post(
        "/api/session/start", json={"content": "Tin nhắn B", "sources": []}, headers=headers
    ).json()["session_id"]

    assert first_id != second_id

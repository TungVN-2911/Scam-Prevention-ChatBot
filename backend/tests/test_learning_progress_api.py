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


def test_get_learning_progress_requires_auth():
    response = client.get("/api/learning-progress")
    assert response.status_code == 401


def test_get_learning_progress_returns_int_xp():
    headers = _headers_for(f"test-{uuid.uuid4()}")

    response = client.get("/api/learning-progress", headers=headers)

    assert response.status_code == 200
    assert isinstance(response.json()["xp"], int)


def test_add_xp_via_api_increases_total_by_delta():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    before = client.get("/api/learning-progress", headers=headers).json()["xp"]

    response = client.post("/api/learning-progress/xp", json={"delta": 10}, headers=headers)

    assert response.status_code == 200
    assert response.json()["xp"] == before + 10


def test_xp_is_isolated_between_users():
    user_a = _headers_for(f"test-{uuid.uuid4()}")
    user_b = _headers_for(f"test-{uuid.uuid4()}")

    client.post("/api/learning-progress/xp", json={"delta": 50}, headers=user_a)

    assert client.get("/api/learning-progress", headers=user_b).json()["xp"] == 0


def test_record_quiz_attempt_appears_in_list():
    headers = _headers_for(f"test-{uuid.uuid4()}")

    response = client.post(
        "/api/learning-progress/quiz-attempts",
        json={
            "topic": "scams",
            "correct_count": 7,
            "total_questions": 10,
            "xp_earned": 75,
            "answers": {"QUIZ-scams-01": 2},
        },
        headers=headers,
    )
    assert response.status_code == 204

    attempts = client.get("/api/learning-progress/quiz-attempts", headers=headers).json()

    assert attempts[0]["topic"] == "scams"
    assert attempts[0]["correct_count"] == 7
    assert attempts[0]["total_questions"] == 10
    assert attempts[0]["xp_earned"] == 75
    assert attempts[0]["answers"] == {"QUIZ-scams-01": 2}
    assert isinstance(attempts[0]["id"], int)


def test_quiz_attempts_are_isolated_between_users():
    user_a = _headers_for(f"test-{uuid.uuid4()}")
    user_b = _headers_for(f"test-{uuid.uuid4()}")

    client.post(
        "/api/learning-progress/quiz-attempts",
        json={"topic": "scams", "correct_count": 5, "total_questions": 10, "xp_earned": 50, "answers": {}},
        headers=user_a,
    )

    assert client.get("/api/learning-progress/quiz-attempts", headers=user_b).json() == []


def test_record_detective_attempt_appears_in_list():
    headers = _headers_for(f"test-{uuid.uuid4()}")
    result = {
        "selected_signal_ids": ["urgency"],
        "expected_signals": ["urgency", "impersonation"],
        "explanations": {"urgency": "vi du giai thich"},
    }
    response = client.post(
        "/api/learning-progress/detective-attempts",
        json={"case_id": "CASE-001", "correct_count": 1, "total_expected": 2, "xp_earned": 50, "result": result},
        headers=headers,
    )
    assert response.status_code == 204

    attempts = client.get("/api/learning-progress/detective-attempts", headers=headers).json()

    assert attempts[0]["case_id"] == "CASE-001"
    assert attempts[0]["correct_count"] == 1
    assert attempts[0]["total_expected"] == 2
    assert attempts[0]["xp_earned"] == 50
    assert attempts[0]["result"] == result
    assert isinstance(attempts[0]["id"], int)

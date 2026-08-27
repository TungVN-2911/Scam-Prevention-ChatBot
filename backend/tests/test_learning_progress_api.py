import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not settings.sql_server_connection_string,
    reason="Cần SQL_SERVER_CONNECTION_STRING trong .env để chạy test kết nối SQL Server thật",
)

client = TestClient(app)


def test_get_learning_progress_returns_int_xp():
    response = client.get("/api/learning-progress")
    assert response.status_code == 200
    assert isinstance(response.json()["xp"], int)


def test_add_xp_via_api_increases_total_by_delta():
    # Endpoint chi phuc vu 1 anonymous user duy nhat (khong nhan user_key tu
    # client) nen test kiem tra tuong doi, khong gia dinh gia tri XP ban dau.
    before = client.get("/api/learning-progress").json()["xp"]

    response = client.post("/api/learning-progress/xp", json={"delta": 10})

    assert response.status_code == 200
    assert response.json()["xp"] == before + 10


def test_record_quiz_attempt_appears_in_list():
    response = client.post(
        "/api/learning-progress/quiz-attempts",
        json={
            "topic": "scams",
            "correct_count": 7,
            "total_questions": 10,
            "xp_earned": 75,
            "answers": {"QUIZ-scams-01": 2},
        },
    )
    assert response.status_code == 204

    attempts = client.get("/api/learning-progress/quiz-attempts").json()

    assert attempts[0]["topic"] == "scams"
    assert attempts[0]["correct_count"] == 7
    assert attempts[0]["total_questions"] == 10
    assert attempts[0]["xp_earned"] == 75
    assert attempts[0]["answers"] == {"QUIZ-scams-01": 2}
    assert isinstance(attempts[0]["id"], int)


def test_record_detective_attempt_appears_in_list():
    result = {
        "selected_signal_ids": ["urgency"],
        "expected_signals": ["urgency", "impersonation"],
        "explanations": {"urgency": "vi du giai thich"},
    }
    response = client.post(
        "/api/learning-progress/detective-attempts",
        json={"case_id": "CASE-001", "correct_count": 1, "total_expected": 2, "xp_earned": 50, "result": result},
    )
    assert response.status_code == 204

    attempts = client.get("/api/learning-progress/detective-attempts").json()

    assert attempts[0]["case_id"] == "CASE-001"
    assert attempts[0]["correct_count"] == 1
    assert attempts[0]["total_expected"] == 2
    assert attempts[0]["xp_earned"] == 50
    assert attempts[0]["result"] == result
    assert isinstance(attempts[0]["id"], int)

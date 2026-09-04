import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.config import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not settings.jwt_secret_key, reason="Cần JWT_SECRET_KEY trong .env để tạo token test"
)

client = TestClient(app)


def _headers_for(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(username, 'user')}"}


def test_list_topics_requires_auth():
    response = client.get("/api/quiz/topics")
    assert response.status_code == 401


def test_get_quiz_requires_auth():
    response = client.get("/api/quiz", params={"topic": "scams"})
    assert response.status_code == 401


def test_list_topics_returns_four_topics():
    response = client.get("/api/quiz/topics", headers=_headers_for(f"test-{uuid.uuid4()}"))
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_get_quiz_returns_ten_questions_for_valid_topic():
    topics = client.get("/api/quiz/topics", headers=_headers_for(f"test-{uuid.uuid4()}")).json()
    response = client.get("/api/quiz", params={"topic": topics[0]}, headers=_headers_for(f"test-{uuid.uuid4()}"))
    assert response.status_code == 200
    assert len(response.json()) == 10


def test_get_quiz_unknown_topic_returns_404():
    response = client.get(
        "/api/quiz", params={"topic": "khong-ton-tai"}, headers=_headers_for(f"test-{uuid.uuid4()}")
    )
    assert response.status_code == 404

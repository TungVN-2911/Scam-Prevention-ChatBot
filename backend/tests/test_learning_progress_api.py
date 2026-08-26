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

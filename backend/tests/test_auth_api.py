import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not settings.sql_server_connection_string or not settings.jwt_secret_key,
    reason="Cần SQL_SERVER_CONNECTION_STRING và JWT_SECRET_KEY trong .env để chạy test đăng nhập/đăng ký",
)

client = TestClient(app)


def test_register_then_login_succeeds():
    username = f"test-{uuid.uuid4()}"

    register_response = client.post("/api/register", json={"username": username, "password": "mat-khau-123"})
    assert register_response.status_code == 204

    login_response = client.post("/api/login", json={"username": username, "password": "mat-khau-123"})
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["role"] == "user"
    assert body["access_token"]


def test_register_duplicate_username_returns_409():
    username = f"test-{uuid.uuid4()}"
    client.post("/api/register", json={"username": username, "password": "mat-khau-123"})

    response = client.post("/api/register", json={"username": username, "password": "mat-khau-khac"})

    assert response.status_code == 409


def test_register_cannot_self_assign_admin_role():
    # RegisterRequest khong khai bao 'role' nen field nay bi Pydantic am tham bo qua.
    username = f"test-{uuid.uuid4()}"

    client.post("/api/register", json={"username": username, "password": "mat-khau-123", "role": "admin"})
    login_response = client.post("/api/login", json={"username": username, "password": "mat-khau-123"})

    assert login_response.json()["role"] == "user"


def test_login_wrong_password_returns_401():
    username = f"test-{uuid.uuid4()}"
    client.post("/api/register", json={"username": username, "password": "mat-khau-dung"})

    response = client.post("/api/login", json={"username": username, "password": "mat-khau-sai"})

    assert response.status_code == 401


def test_login_unknown_username_returns_401():
    response = client.post("/api/login", json={"username": f"khong-ton-tai-{uuid.uuid4()}", "password": "x"})
    assert response.status_code == 401

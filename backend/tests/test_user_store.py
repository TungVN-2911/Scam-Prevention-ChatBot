import uuid

import pytest

from app import user_store
from app.config import settings

pytestmark = pytest.mark.skipif(
    not settings.sql_server_connection_string,
    reason="Cần SQL_SERVER_CONNECTION_STRING trong .env để chạy test kết nối SQL Server thật",
)


def test_create_user_then_verify_correct_password():
    username = f"test-{uuid.uuid4()}"

    user_store.create_user(username, "mat-khau-dung", role="admin")

    assert user_store.verify_user(username, "mat-khau-dung") == "admin"


def test_verify_user_wrong_password_returns_none():
    username = f"test-{uuid.uuid4()}"
    user_store.create_user(username, "mat-khau-dung")

    assert user_store.verify_user(username, "mat-khau-sai") is None


def test_verify_user_unknown_username_returns_none():
    assert user_store.verify_user(f"khong-ton-tai-{uuid.uuid4()}", "bat-ky") is None


def test_create_user_default_role_is_user():
    username = f"test-{uuid.uuid4()}"
    user_store.create_user(username, "mat-khau")

    assert user_store.verify_user(username, "mat-khau") == "user"


def test_password_is_hashed_not_stored_in_plaintext():
    username = f"test-{uuid.uuid4()}"
    password = "mat-khau-can-hash"
    user_store.create_user(username, password)

    with user_store._connection() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE username = ?", username).fetchone()

    assert row.password_hash != password

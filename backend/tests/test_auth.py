import time
import uuid

import jwt
import pytest
from fastapi import HTTPException

from app.auth import ALGORITHM, create_access_token, get_current_user
from app.config import settings

pytestmark = pytest.mark.skipif(
    not settings.jwt_secret_key,
    reason="Cần JWT_SECRET_KEY trong .env để chạy test tạo/kiểm tra token",
)


def test_create_access_token_round_trip():
    username = f"test-{uuid.uuid4()}"
    token = create_access_token(username, "admin")

    user = get_current_user(f"Bearer {token}")

    assert user == {"username": username, "role": "admin"}


def test_get_current_user_rejects_missing_bearer_prefix():
    token = create_access_token("someone", "user")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token)

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_tampered_token():
    token = create_access_token("someone", "user")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(f"Bearer {token}x")

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_expired_token():
    expired_payload = {"sub": "someone", "role": "user", "exp": int(time.time()) - 10}
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(f"Bearer {expired_token}")

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_token_signed_with_wrong_secret():
    forged_token = jwt.encode({"sub": "someone", "role": "admin"}, "sai-secret-key", algorithm=ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(f"Bearer {forged_token}")

    assert exc_info.value.status_code == 401

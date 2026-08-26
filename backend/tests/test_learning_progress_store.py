import uuid

import pytest

from app import learning_progress_store
from app.config import settings

pytestmark = pytest.mark.skipif(
    not settings.sql_server_connection_string,
    reason="Cần SQL_SERVER_CONNECTION_STRING trong .env để chạy test kết nối SQL Server thật",
)


def test_get_or_create_returns_default_zero_for_new_user():
    user_key = f"test-{uuid.uuid4()}"

    progress = learning_progress_store.get_or_create_learning_progress(user_key)

    assert progress == {"xp": 0}


def test_get_or_create_returns_existing_xp_on_second_call():
    user_key = f"test-{uuid.uuid4()}"
    learning_progress_store.get_or_create_learning_progress(user_key)
    learning_progress_store.add_xp(100, user_key)

    progress = learning_progress_store.get_or_create_learning_progress(user_key)

    assert progress == {"xp": 100}


def test_add_xp_accumulates_correctly():
    user_key = f"test-{uuid.uuid4()}"
    learning_progress_store.get_or_create_learning_progress(user_key)

    learning_progress_store.add_xp(100, user_key)
    total = learning_progress_store.add_xp(50, user_key)

    assert total == 150


def test_add_xp_creates_record_if_missing():
    user_key = f"test-{uuid.uuid4()}"

    total = learning_progress_store.add_xp(100, user_key)

    assert total == 100
    assert learning_progress_store.get_or_create_learning_progress(user_key) == {"xp": 100}


def test_default_user_key_is_anonymous_user():
    assert learning_progress_store.ANONYMOUS_USER_KEY == "anonymous_user"

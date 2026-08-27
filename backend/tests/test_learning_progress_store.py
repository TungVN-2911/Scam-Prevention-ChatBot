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


def test_list_quiz_attempts_empty_for_new_user():
    user_key = f"test-{uuid.uuid4()}"
    assert learning_progress_store.list_quiz_attempts(user_key) == []


def test_record_quiz_attempt_then_list():
    user_key = f"test-{uuid.uuid4()}"

    learning_progress_store.record_quiz_attempt("scams", 8, 10, 75, user_key=user_key)

    attempts = learning_progress_store.list_quiz_attempts(user_key)
    assert len(attempts) == 1
    assert attempts[0]["topic"] == "scams"
    assert attempts[0]["correct_count"] == 8
    assert attempts[0]["total_questions"] == 10
    assert attempts[0]["xp_earned"] == 75
    assert attempts[0]["answers"] == {}
    assert isinstance(attempts[0]["id"], int)


def test_record_quiz_attempt_stores_answers():
    user_key = f"test-{uuid.uuid4()}"
    answers = {"QUIZ-scams-01": 2, "QUIZ-scams-02": 0}

    learning_progress_store.record_quiz_attempt("scams", 8, 10, 75, answers, user_key=user_key)

    attempts = learning_progress_store.list_quiz_attempts(user_key)
    assert attempts[0]["answers"] == answers


def test_list_quiz_attempts_most_recent_first():
    user_key = f"test-{uuid.uuid4()}"
    learning_progress_store.record_quiz_attempt("scams", 5, 10, 50, user_key=user_key)
    learning_progress_store.record_quiz_attempt("prevention", 10, 10, 100, user_key=user_key)

    attempts = learning_progress_store.list_quiz_attempts(user_key)

    assert [a["topic"] for a in attempts] == ["prevention", "scams"]


def test_list_quiz_attempts_respects_limit():
    user_key = f"test-{uuid.uuid4()}"
    for _ in range(3):
        learning_progress_store.record_quiz_attempt("scams", 5, 10, 50, user_key=user_key)

    attempts = learning_progress_store.list_quiz_attempts(user_key, limit=2)

    assert len(attempts) == 2


def test_list_detective_attempts_empty_for_new_user():
    user_key = f"test-{uuid.uuid4()}"
    assert learning_progress_store.list_detective_attempts(user_key) == []


def test_record_detective_attempt_then_list():
    user_key = f"test-{uuid.uuid4()}"
    result = {
        "selected_signal_ids": ["urgency", "impersonation"],
        "expected_signals": ["urgency", "impersonation", "money_request"],
        "explanations": {"urgency": "vi du giai thich"},
    }

    learning_progress_store.record_detective_attempt("CASE-001", 2, 3, 50, result, user_key=user_key)

    attempts = learning_progress_store.list_detective_attempts(user_key)
    assert len(attempts) == 1
    assert attempts[0]["case_id"] == "CASE-001"
    assert attempts[0]["correct_count"] == 2
    assert attempts[0]["total_expected"] == 3
    assert attempts[0]["xp_earned"] == 50
    assert attempts[0]["result"] == result
    assert isinstance(attempts[0]["id"], int)


def test_list_detective_attempts_most_recent_first():
    user_key = f"test-{uuid.uuid4()}"
    learning_progress_store.record_detective_attempt("CASE-001", 1, 3, 20, {}, user_key=user_key)
    learning_progress_store.record_detective_attempt("CASE-002", 3, 3, 100, {}, user_key=user_key)

    attempts = learning_progress_store.list_detective_attempts(user_key)

    assert [a["case_id"] for a in attempts] == ["CASE-002", "CASE-001"]


def test_list_detective_attempts_respects_limit():
    user_key = f"test-{uuid.uuid4()}"
    for _ in range(3):
        learning_progress_store.record_detective_attempt("CASE-001", 1, 3, 20, {}, user_key=user_key)

    attempts = learning_progress_store.list_detective_attempts(user_key, limit=2)

    assert len(attempts) == 2

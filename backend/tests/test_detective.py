import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.routes.detective import score_signals
from app.auth import create_access_token
from app.config import settings
from app.main import app

client = TestClient(app)


def _headers_for(username: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(username, 'user')}"}


_auth = pytest.mark.skipif(
    not settings.jwt_secret_key, reason="Cần JWT_SECRET_KEY trong .env để tạo token test"
)


def test_score_signals_all_correct():
    result = score_signals(["a", "b"], ["a", "b"])
    assert result == {"correct_count": 2, "total_expected": 2, "percentage": 100, "xp": 100}


def test_score_signals_partial_correct():
    result = score_signals(["a", "b"], ["a"])
    assert result == {"correct_count": 1, "total_expected": 2, "percentage": 50, "xp": 50}


def test_score_signals_all_wrong():
    result = score_signals(["a", "b"], ["x", "y"])
    assert result == {"correct_count": 0, "total_expected": 2, "percentage": 0, "xp": 20}


def test_score_signals_ignores_extra_wrong_selection():
    result = score_signals(["a", "b"], ["a", "b", "x"])
    assert result["correct_count"] == 2
    assert result["percentage"] == 100


def test_score_signals_is_deterministic():
    first = score_signals(["a", "b", "c"], ["a", "c"])
    second = score_signals(["a", "b", "c"], ["a", "c"])
    assert first == second


def test_score_signals_empty_expected_does_not_crash():
    result = score_signals([], [])
    assert result == {"correct_count": 0, "total_expected": 0, "percentage": 0, "xp": 20}


def test_list_cases_requires_auth():
    response = client.get("/api/detective/cases")
    assert response.status_code == 401


def test_get_case_requires_auth():
    response = client.get("/api/detective/cases/CASE-001")
    assert response.status_code == 401


def test_submit_case_requires_auth():
    response = client.post("/api/detective/cases/CASE-001/submit", json={"selected_signal_ids": []})
    assert response.status_code == 401


@_auth
def test_list_cases_returns_sixteen_cases():
    response = client.get("/api/detective/cases", headers=_headers_for(f"test-{uuid.uuid4()}"))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 16
    assert all("expected_signals" not in c for c in data)


@_auth
def test_get_case_does_not_leak_expected_signals():
    response = client.get("/api/detective/cases/CASE-001", headers=_headers_for(f"test-{uuid.uuid4()}"))
    assert response.status_code == 200
    assert "expected_signals" not in response.json()


@_auth
def test_get_case_not_found_returns_404():
    response = client.get("/api/detective/cases/CASE-999", headers=_headers_for(f"test-{uuid.uuid4()}"))
    assert response.status_code == 404


@_auth
def test_submit_case_not_found_returns_404():
    response = client.post(
        "/api/detective/cases/CASE-999/submit",
        json={"selected_signal_ids": []},
        headers=_headers_for(f"test-{uuid.uuid4()}"),
    )
    assert response.status_code == 404


@_auth
def test_submit_case_full_correct():
    response = client.post(
        "/api/detective/cases/CASE-003/submit",
        json={"selected_signal_ids": ["unsolicited_prize", "upfront_payment"]},
        headers=_headers_for(f"test-{uuid.uuid4()}"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["percentage"] == 100
    assert data["xp"] == 100
    assert set(data["expected_signals"]) == {"unsolicited_prize", "upfront_payment"}


@_auth
def test_submit_case_partial_correct():
    response = client.post(
        "/api/detective/cases/CASE-003/submit",
        json={"selected_signal_ids": ["unsolicited_prize"]},
        headers=_headers_for(f"test-{uuid.uuid4()}"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["correct_count"] == 1
    assert data["percentage"] == 50


@_auth
def test_submit_case_no_selection():
    response = client.post(
        "/api/detective/cases/CASE-003/submit",
        json={"selected_signal_ids": []},
        headers=_headers_for(f"test-{uuid.uuid4()}"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["correct_count"] == 0
    assert data["percentage"] == 0

import pytest
from fastapi.testclient import TestClient

from app.api.routes.detective import score_signals
from app.main import app

client = TestClient(app)


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


def test_list_cases_returns_sixteen_cases():
    response = client.get("/api/detective/cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 16
    assert all("expected_signals" not in c for c in data)


def test_get_case_does_not_leak_expected_signals():
    response = client.get("/api/detective/cases/CASE-001")
    assert response.status_code == 200
    assert "expected_signals" not in response.json()


def test_get_case_not_found_returns_404():
    response = client.get("/api/detective/cases/CASE-999")
    assert response.status_code == 404


def test_submit_case_not_found_returns_404():
    response = client.post("/api/detective/cases/CASE-999/submit", json={"selected_signal_ids": []})
    assert response.status_code == 404


def test_submit_case_full_correct():
    response = client.post(
        "/api/detective/cases/CASE-003/submit",
        json={"selected_signal_ids": ["unsolicited_prize", "upfront_payment"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["percentage"] == 100
    assert data["xp"] == 100
    assert set(data["expected_signals"]) == {"unsolicited_prize", "upfront_payment"}


def test_submit_case_partial_correct():
    response = client.post(
        "/api/detective/cases/CASE-003/submit",
        json={"selected_signal_ids": ["unsolicited_prize"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["correct_count"] == 1
    assert data["percentage"] == 50


def test_submit_case_no_selection():
    response = client.post("/api/detective/cases/CASE-003/submit", json={"selected_signal_ids": []})
    assert response.status_code == 200
    data = response.json()
    assert data["correct_count"] == 0
    assert data["percentage"] == 0

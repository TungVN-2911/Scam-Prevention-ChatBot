from datetime import date

from fastapi.testclient import TestClient

from app.api.routes.scam_of_day import pick_pattern_for_date
from app.main import app
from app.scam_connector.mock_connector import MockScamConnector
from app.scam_connector.models import ScamPattern

client = TestClient(app)


def test_get_scam_of_day_requires_auth():
    response = client.get("/api/scam-of-day")
    assert response.status_code == 401


def _make_pattern(id_, **overrides) -> ScamPattern:
    base = dict(
        id=id_,
        slug=id_.lower(),
        name=f"Pattern {id_}",
        description="Mô tả",
        warning_signs=["dấu hiệu 1"],
        prevention=["nên làm 1"],
        source={"organization": "Nguồn test"},
    )
    base.update(overrides)
    return ScamPattern(**base)


def test_same_date_returns_same_pattern():
    connector = MockScamConnector()
    patterns = connector.search_patterns()
    target_date = date(2026, 8, 26)

    first = pick_pattern_for_date(patterns, target_date)
    second = pick_pattern_for_date(patterns, target_date)

    assert first is not None
    assert first.id == second.id


def test_different_dates_can_return_different_patterns():
    connector = MockScamConnector()
    patterns = connector.search_patterns()

    picked_ids = {pick_pattern_for_date(patterns, date(2026, 1, day)).id for day in range(1, 8)}

    assert len(picked_ids) > 1


def test_incomplete_pattern_falls_back_to_next_pattern():
    incomplete = _make_pattern("A", warning_signs=[], prevention=[])
    complete = _make_pattern("B")
    patterns = [incomplete, complete]

    result = pick_pattern_for_date(patterns, date(2026, 1, 1))

    assert result is not None
    assert result.id == "B"

    result_next_day = pick_pattern_for_date(patterns, date(2026, 1, 2))
    assert result_next_day is not None
    assert result_next_day.id == "B"


def test_empty_pattern_list_does_not_crash():
    assert pick_pattern_for_date([], date(2026, 1, 1)) is None


def test_all_patterns_incomplete_returns_none_without_crashing():
    patterns = [_make_pattern("A", warning_signs=[]), _make_pattern("B", prevention=[])]
    assert pick_pattern_for_date(patterns, date(2026, 1, 1)) is None

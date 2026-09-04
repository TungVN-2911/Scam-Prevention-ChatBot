import pytest

import app.pending_reports_store as pending_reports_store


@pytest.fixture(autouse=True)
def isolated_pending_file(tmp_path, monkeypatch):
    monkeypatch.setattr(pending_reports_store, "_PATH", tmp_path / "pending_reports.json")


def test_add_same_text_twice_merges_into_one_report_with_count_2():
    pending_reports_store.add("cách phòng chống lừa đảo đầu tư tiền ảo", 0.1)
    pending_reports_store.add("cách phòng chống lừa đảo đầu tư tiền ảo", 0.2)

    reports = pending_reports_store.list_all()
    assert len(reports) == 1
    assert reports[0]["count"] == 2


def test_add_same_text_different_case_and_diacritics_still_merges():
    pending_reports_store.add("Cách Phòng Chống Lừa Đảo", 0.1)
    pending_reports_store.add("cach phong chong lua dao", 0.2)

    reports = pending_reports_store.list_all()
    assert len(reports) == 1
    assert reports[0]["count"] == 2


def test_add_different_text_creates_separate_reports():
    pending_reports_store.add("tình huống A", 0.1)
    pending_reports_store.add("tình huống B", 0.2)

    reports = pending_reports_store.list_all()
    assert len(reports) == 2
    assert {r["count"] for r in reports} == {1}


def test_top_score_becomes_max_across_merged_reports():
    pending_reports_store.add("tình huống lặp lại", 0.1)
    pending_reports_store.add("tình huống lặp lại", 0.35)
    pending_reports_store.add("tình huống lặp lại", 0.2)

    reports = pending_reports_store.list_all()
    assert len(reports) == 1
    assert reports[0]["top_score"] == 0.35


def test_duplicate_of_already_reviewed_report_creates_new_pending_entry():
    pending_reports_store.add("tình huống đã xử lý", 0.1)
    first_id = pending_reports_store.list_all()[0]["id"]
    pending_reports_store.update_status(first_id, status="approved")

    pending_reports_store.add("tình huống đã xử lý", 0.2)

    reports = pending_reports_store.list_all()
    assert len(reports) == 2
    new_report = next(r for r in reports if r["id"] != first_id)
    assert new_report["status"] == "pending_review"
    assert new_report["count"] == 1


def test_new_report_defaults_count_to_1():
    pending_reports_store.add("tình huống mới", 0.1)
    reports = pending_reports_store.list_all()
    assert reports[0]["count"] == 1

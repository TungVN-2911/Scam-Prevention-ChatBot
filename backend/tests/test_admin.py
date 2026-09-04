import json
import uuid

import pytest
from fastapi.testclient import TestClient

import app.api.routes.admin as admin_route
import app.pending_reports_store as pending_reports_store
from app.auth import create_access_token
from app.config import settings
from app.main import app

pytestmark = pytest.mark.skipif(
    not settings.jwt_secret_key, reason="Cần JWT_SECRET_KEY trong .env để tạo token test"
)

client = TestClient(app)


def _headers_for(username: str, role: str = "user") -> dict:
    return {"Authorization": f"Bearer {create_access_token(username, role)}"}


@pytest.fixture
def isolated_files(tmp_path, monkeypatch):
    # Khong dung file that (pending_reports.json / scams.json / Pinecone that).
    pending_path = tmp_path / "pending_reports.json"
    monkeypatch.setattr(pending_reports_store, "_PATH", pending_path)

    scams_path = tmp_path / "scams.json"
    scams_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(admin_route, "_SCAMS_PATH", scams_path)

    upserted = []
    monkeypatch.setattr(admin_route._retriever, "upsert", lambda ids, texts, metadata: upserted.append((ids, texts, metadata)))

    pending_reports_store.add("Tình huống nghi ngờ để test", 0.31)
    report_id = pending_reports_store.list_all()[0]["id"]

    return {"pending_path": pending_path, "scams_path": scams_path, "upserted": upserted, "report_id": report_id}


def test_list_pending_reports_requires_auth():
    response = client.get("/api/admin/pending-reports")
    assert response.status_code == 401


def test_list_pending_reports_rejects_non_admin(isolated_files):
    response = client.get("/api/admin/pending-reports", headers=_headers_for(f"u-{uuid.uuid4()}", "user"))
    assert response.status_code == 403


def test_list_pending_reports_allows_admin(isolated_files):
    response = client.get("/api/admin/pending-reports", headers=_headers_for(f"a-{uuid.uuid4()}", "admin"))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending_review"


def test_reject_unknown_report_returns_404(isolated_files):
    response = client.post(
        "/api/admin/pending-reports/PENDING-9999/reject",
        json={"reason": ""},
        headers=_headers_for(f"a-{uuid.uuid4()}", "admin"),
    )
    assert response.status_code == 404


def test_reject_report_updates_status(isolated_files):
    report_id = isolated_files["report_id"]
    response = client.post(
        f"/api/admin/pending-reports/{report_id}/reject",
        json={"reason": "Không đủ căn cứ"},
        headers=_headers_for(f"a-{uuid.uuid4()}", "admin"),
    )
    assert response.status_code == 204
    updated = pending_reports_store.get(report_id)
    assert updated["status"] == "rejected"
    assert updated["reject_reason"] == "Không đủ căn cứ"


def test_approve_report_requires_admin(isolated_files):
    report_id = isolated_files["report_id"]
    response = client.post(
        f"/api/admin/pending-reports/{report_id}/approve",
        json={"slug": "test-pattern", "name": "Test Pattern"},
        headers=_headers_for(f"u-{uuid.uuid4()}", "user"),
    )
    assert response.status_code == 403


def test_approve_report_writes_pattern_and_upserts(isolated_files):
    report_id = isolated_files["report_id"]
    response = client.post(
        f"/api/admin/pending-reports/{report_id}/approve",
        json={
            "slug": "test-pattern",
            "name": "Test Pattern",
            "category": "scams",
            "scenario": "Kịch bản test",
            "warning_signs": ["dấu hiệu A"],
            "prevention": ["phòng tránh A"],
            "source": {"organization": "Test Org"},
        },
        headers=_headers_for(f"a-{uuid.uuid4()}", "admin"),
    )
    assert response.status_code == 204

    scams = json.loads(isolated_files["scams_path"].read_text(encoding="utf-8"))
    assert len(scams) == 1
    assert scams[0]["slug"] == "test-pattern"
    assert scams[0]["id"] == "scam_test-pattern"

    assert len(isolated_files["upserted"]) == 1
    ids, texts, metadata = isolated_files["upserted"][0]
    assert ids == ["scams_test-pattern"]
    assert "Test Pattern" in texts[0]
    assert metadata[0]["category"] == "scams"

    updated_report = pending_reports_store.get(report_id)
    assert updated_report["status"] == "approved"
    assert updated_report["approved_slug"] == "test-pattern"


def test_approve_report_duplicate_slug_returns_409(isolated_files):
    isolated_files["scams_path"].write_text(
        json.dumps([{"id": "scam_existing", "slug": "existing", "name": "Existing"}]), encoding="utf-8"
    )
    report_id = isolated_files["report_id"]
    response = client.post(
        f"/api/admin/pending-reports/{report_id}/approve",
        json={"slug": "existing", "name": "Trùng slug"},
        headers=_headers_for(f"a-{uuid.uuid4()}", "admin"),
    )
    assert response.status_code == 409

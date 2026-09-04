import pytest

import app.pending_reports_store as pending_reports_store
from app.auth import create_access_token
from app.config import settings
from app.mcp.server import ROLE_TOOLS, _authorize, summarize_pending_reports

pytestmark = pytest.mark.skipif(
    not settings.jwt_secret_key,
    reason="Cần JWT_SECRET_KEY trong .env để tạo token test",
)


class _FakeHttpRequest:
    def __init__(self, headers: dict):
        self.headers = headers


class _FakeRequestContext:
    # Header nam trong field .request (Starlette Request that), khong phai .headers truc tiep.
    def __init__(self, headers: dict):
        self.request = _FakeHttpRequest(headers)


class _FakeContext:
    def __init__(self, headers: dict):
        self.request_context = _FakeRequestContext(headers)


def _ctx_with_token(token: str) -> _FakeContext:
    return _FakeContext({"authorization": f"Bearer {token}"})


def test_user_role_can_call_allowed_tools():
    token = create_access_token("someone", "user")
    for tool_name in ("search_scam_patterns", "list_hotlines"):
        payload = _authorize(_ctx_with_token(token), tool_name)
        assert payload["role"] == "user"


def test_user_role_cannot_call_admin_only_tool():
    token = create_access_token("someone", "user")
    with pytest.raises(PermissionError):
        _authorize(_ctx_with_token(token), "summarize_pending_reports")


def test_admin_role_can_call_all_tools():
    token = create_access_token("someone", "admin")
    for tool_name in ROLE_TOOLS["admin"]:
        _authorize(_ctx_with_token(token), tool_name)


def test_missing_authorization_header_is_rejected():
    ctx = _FakeContext({})
    with pytest.raises(PermissionError):
        _authorize(ctx, "list_hotlines")


def test_authorization_header_without_bearer_prefix_is_rejected():
    ctx = _FakeContext({"authorization": "sometoken"})
    with pytest.raises(PermissionError):
        _authorize(ctx, "list_hotlines")


def test_tampered_token_is_rejected():
    token = create_access_token("someone", "admin")
    ctx = _ctx_with_token(token + "x")
    with pytest.raises(PermissionError):
        _authorize(ctx, "search_scam_patterns")


def test_unknown_role_has_no_tools():
    token = create_access_token("someone", "vai-tro-la")
    with pytest.raises(PermissionError):
        _authorize(_ctx_with_token(token), "list_hotlines")


def test_summarize_pending_reports_only_returns_pending_review(tmp_path, monkeypatch):
    monkeypatch.setattr(pending_reports_store, "_PATH", tmp_path / "pending_reports.json")
    pending_reports_store.add("báo cáo A đang chờ", 0.1)
    pending_reports_store.add("báo cáo B đang chờ", 0.2)
    reports = pending_reports_store.list_all()
    pending_reports_store.update_status(reports[1]["id"], status="approved")

    token = create_access_token("someone", "admin")
    result = summarize_pending_reports(_ctx_with_token(token))

    assert len(result) == 1
    assert result[0]["text"] == "báo cáo A đang chờ"
    assert set(result[0].keys()) == {"id", "text", "top_score", "reported_at", "count"}

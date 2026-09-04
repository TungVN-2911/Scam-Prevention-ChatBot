import io
import logging
import sys

import jwt
from mcp.server.mcpserver import Context, MCPServer

from app import pending_reports_store
from app.auth import ALGORITHM
from app.config import settings
from app.scam_connector.mock_connector import MockScamConnector

server = MCPServer("scam-prevention-tools")
_connector = MockScamConnector()

# KHONG log JWT/secret o day, chi log ket qua quyet dinh.
_audit_logger = logging.getLogger("mcp_auth")
_audit_logger.setLevel(logging.INFO)
if not _audit_logger.handlers:
    # Ep UTF-8: console Windows mac dinh (cp1252) lam vo chu tieng Viet co dau.
    _stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    _handler = logging.StreamHandler(_stream)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _audit_logger.addHandler(_handler)


def _log_decision(tool_name: str, user_id: str | None, role: str, decision: str, reason: str = "") -> None:
    _audit_logger.info(
        "[MCP AUTH] tool=%s user_id=%s role=%s permission=%s%s",
        tool_name, user_id, role, decision, f" reason={reason}" if reason else "",
    )

ROLE_TOOLS: dict[str, set[str]] = {
    "user": {"search_scam_patterns", "list_hotlines"},
    "admin": {"search_scam_patterns", "list_hotlines", "summarize_pending_reports"},
}

def _authorize(ctx: Context, tool_name: str) -> dict:
    # Header nam o ctx.request_context.request (Starlette Request), KHONG
    # phai ctx.request_context.headers - de nham voi 1 class Context khac
    # trong SDK khong duoc dung thuc te.
    request = ctx.request_context.request
    headers = request.headers if request is not None else {}
    authorization = headers.get("authorization", "")
    
    if not authorization.startswith("Bearer "):
        _log_decision(tool_name, None, "?", "DENIED", "thiếu Authorization header")
        raise PermissionError("Thiếu token xác thực trong request MCP")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        _log_decision(tool_name, None, "?", "DENIED", "token không hợp lệ/hết hạn")
        raise PermissionError("Token xác thực không hợp lệ")

    user_id = payload.get("sub")
    role = payload.get("role", "user")

    if tool_name not in ROLE_TOOLS.get(role, set()):
        _log_decision(tool_name, user_id, role, "DENIED", "role không có trong permission map của tool")
        raise PermissionError(f"Vai trò '{role}' không có quyền truy cập công cụ '{tool_name}'")

    _log_decision(tool_name, user_id, role, "ALLOWED")
    return payload

@server.tool()
def search_scam_patterns(query: str, ctx: Context) -> list[dict]:
    _authorize(ctx, "search_scam_patterns")
    return [p.model_dump() for p in _connector.search_patterns(query)]

@server.tool()
def list_hotlines(ctx: Context) -> list[dict]:
    _authorize(ctx, "list_hotlines")
    return [p.model_dump() for p in _connector.list_hotlines()]

@server.tool()
def summarize_pending_reports(ctx: Context) -> list[dict]:
    """Lay danh sach cac tinh huong lua dao moi nguoi dung bao cao ma he thong
    chua xac dinh khop voi hinh thuc nao da biet, dang cho admin xem xet. Moi
    report co field "count" - so lan tinh huong nay (sau khi chuan hoa) da
    duoc bao cao, dung de danh gia muc do pho bien/uu tien khi tong hop. Dung
    de tong hop/phan loai xu huong khi admin hoi (vd: gom nhom theo chu de,
    danh gia cai nao khan cap/pho bien nen xem truoc). Chi de THAM KHAO - KHONG
    dung de tu dong duyet/tu choi bao cao, viec do phai lam qua trang quan tri rieng."""
    _authorize(ctx, "summarize_pending_reports")
    reports = pending_reports_store.list_all()
    return [
        {
            "id": r["id"],
            "text": r["text"],
            "top_score": r["top_score"],
            "reported_at": r["reported_at"],
            "count": r.get("count", 1),
        }
        for r in reports
        if r["status"] == "pending_review"
    ]

if __name__ == "__main__":
    try:
        server.run(transport="streamable-http", host="127.0.0.1", port=8020)
    except KeyboardInterrupt:
        pass
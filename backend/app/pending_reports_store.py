import json
import logging
import threading
from datetime import datetime, timezone

from app.config import DATA_DIR
from app.core.vietnamese_text import normalized, strip_diacritics

logger = logging.getLogger("pending_reports_store")

_PATH = DATA_DIR / "pending_reports.json"

# 1 khoa duy nhat cho toan bo doc-sua-ghi file nay (chat_orchestrator ghi report
# moi, admin route duyet/tu choi) - tranh mat du lieu khi 2 luong ghi dong thoi
# trong cung 1 process (chi bao ve trong 1 process, khong phai nhieu worker).
_lock = threading.Lock()


def _load() -> list[dict]:
    try:
        return json.loads(_PATH.read_text(encoding="utf-8")) if _PATH.exists() else []
    except Exception:
        logger.exception("Loi khi doc pending_reports.json, bat dau lai tu danh sach rong")
        return []


def _save(reports: list[dict]) -> None:
    try:
        _PATH.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("Loi khi ghi pending_reports.json")


def list_all() -> list[dict]:
    with _lock:
        return _load()


def get(report_id: str) -> dict | None:
    with _lock:
        return next((r for r in _load() if r["id"] == report_id), None)


def _normalize_key(text: str) -> str:
    # Chi khop trung sau chuan hoa (bo dau, lowercase, gon khoang trang) - KHONG
    # dung embedding/similarity: rui ro gop nham 2 tinh huong khac nhau thanh 1,
    # lam an mat 1 hinh thuc lua dao that su moi. Dien dat khac nhau nhung cung
    # y van duoc coi la 2 report rieng - admin tu nhan ra khi doc, chap nhan duoc.
    return strip_diacritics(normalized(text))


def add(text: str, score: float) -> None:
    with _lock:
        reports = _load()
        key = _normalize_key(text)
        existing = next(
            (r for r in reports if r["status"] == "pending_review" and _normalize_key(r["text"]) == key), None
        )
        if existing is not None:
            existing["count"] = existing.get("count", 1) + 1
            existing["reported_at"] = datetime.now(timezone.utc).isoformat()
            existing["top_score"] = max(existing["top_score"], round(score, 3))
        else:
            reports.append({
                "id": f"PENDING-{len(reports) + 1:04d}",
                "text": text,
                "reported_at": datetime.now(timezone.utc).isoformat(),
                "top_score": round(score, 3),
                "status": "pending_review",
                "count": 1,
            })
        _save(reports)


def update_status(report_id: str, **fields) -> dict | None:
    with _lock:
        reports = _load()
        report = next((r for r in reports if r["id"] == report_id), None)
        if report is None:
            return None
        report.update(fields)
        _save(reports)
        return report

import json
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import pending_reports_store
from app.auth import require_admin
from app.config import KNOWLEDGE_BASE_DIR
from app.rag_engine.chunking import chunk_scam_pattern
from app.rag_engine.retrieval import PineconeRetriever
from app.scam_connector.models import ScamPattern

router = APIRouter()
_retriever = PineconeRetriever()

_SCAMS_PATH = KNOWLEDGE_BASE_DIR / "sources" / "scams" / "scams.json"

# Ghi scams.json (knowledge base) rieng voi pending_reports.json (co khoa
# trong pending_reports_store) - chi 1 route admin ghi file nay nen khoa don gian la du.
_scams_lock = threading.Lock()


class PendingReport(BaseModel):
    id: str
    text: str
    reported_at: str
    top_score: float
    status: str
    count: int = 1
    reviewed_at: str | None = None
    reviewed_by: str | None = None


class ApprovePatternRequest(BaseModel):
    slug: str
    name: str
    category: str | None = None
    description: str | None = None
    scenario: str | None = None
    target: list[str] = []
    channels: list[str] = []
    warning_signs: list[str] = []
    tactics: list[str] = []
    prevention: list[str] = []
    if_victim: list[str] = []
    severity: str | None = None
    related_patterns: list[str] = []
    source: dict = {}


class RejectRequest(BaseModel):
    reason: str = ""


@router.get("/admin/pending-reports", response_model=list[PendingReport])
def list_pending_reports(user: dict = Depends(require_admin)):
    return pending_reports_store.list_all()


@router.post("/admin/pending-reports/{report_id}/reject", status_code=204)
def reject_pending_report(report_id: str, request: RejectRequest, user: dict = Depends(require_admin)):
    fields = {
        "status": "rejected",
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": user["username"],
    }
    if request.reason:
        fields["reject_reason"] = request.reason
    report = pending_reports_store.update_status(report_id, **fields)
    if report is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo này")


@router.post("/admin/pending-reports/{report_id}/approve", status_code=204)
def approve_pending_report(report_id: str, request: ApprovePatternRequest, user: dict = Depends(require_admin)):
    if pending_reports_store.get(report_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo này")

    with _scams_lock:
        scams = json.loads(_SCAMS_PATH.read_text(encoding="utf-8")) if _SCAMS_PATH.exists() else []
        if any(p["slug"] == request.slug for p in scams):
            raise HTTPException(status_code=409, detail="Slug này đã tồn tại trong knowledge base")

        pattern_dict = request.model_dump()
        pattern_dict["id"] = f"scam_{request.slug}"
        # Validate dung dung 1 model ma toan he thong dang dung (mock_connector.py
        # doc lai scams.json qua ScamPattern) - sai schema se fail o day truoc,
        # khong de sai lot vao file roi crash luc backend load lai sau nay.
        ScamPattern(**pattern_dict)

        scams.append(pattern_dict)
        _SCAMS_PATH.write_text(json.dumps(scams, ensure_ascii=False, indent=2), encoding="utf-8")

        text = chunk_scam_pattern(pattern_dict)
        _retriever.upsert(
            ids=[f"scams_{request.slug}"],
            texts=[text],
            metadata=[{"category": "scams", "source": "scams/scams.json"}],
        )

    report = pending_reports_store.update_status(
        report_id,
        status="approved",
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        reviewed_by=user["username"],
        approved_slug=request.slug,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo này")

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import DATA_DIR

router = APIRouter()

_CASES_FILE = DATA_DIR / "detective_cases.json"
_CASES: list[dict] = json.loads(_CASES_FILE.read_text(encoding="utf-8"))
_CASES_BY_ID: dict[str, dict] = {c["id"]: c for c in _CASES}


class DetectiveSignal(BaseModel):
    id: str
    text: str


class DetectiveCaseSummary(BaseModel):
    id: str
    difficulty: str
    title: str
    scam_pattern: str


class DetectiveCase(BaseModel):
    id: str
    scam_pattern: str
    difficulty: str
    title: str
    scenario: str
    signals: list[DetectiveSignal]
    source: dict


class SubmitRequest(BaseModel):
    selected_signal_ids: list[str] = []


class SubmitResponse(BaseModel):
    case_id: str
    correct_count: int
    total_expected: int
    percentage: int
    xp: int
    expected_signals: list[str]
    explanations: dict[str, str]


def score_signals(expected_signals: list[str], selected_signal_ids: list[str]) -> dict:
    total = len(expected_signals)
    correct = len(set(expected_signals) & set(selected_signal_ids))
    percentage = round(correct / total * 100) if total else 0
    if percentage >= 100:
        xp = 100
    elif percentage >= 75:
        xp = 75
    elif percentage >= 50:
        xp = 50
    else:
        xp = 20
    return {"correct_count": correct, "total_expected": total, "percentage": percentage, "xp": xp}


@router.get("/detective/cases", response_model=list[DetectiveCaseSummary])
def list_cases():
    return [
        {"id": c["id"], "difficulty": c["difficulty"], "title": c["title"], "scam_pattern": c["scam_pattern"]}
        for c in _CASES
    ]


@router.get("/detective/cases/{case_id}", response_model=DetectiveCase)
def get_case(case_id: str):
    case = _CASES_BY_ID.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy case này")
    return DetectiveCase(
        id=case["id"],
        scam_pattern=case["scam_pattern"],
        difficulty=case["difficulty"],
        title=case["title"],
        scenario=case["scenario"],
        signals=[{"id": s["id"], "text": s["text"]} for s in case["signals"]],
        source=case["source"],
    )


@router.post("/detective/cases/{case_id}/submit", response_model=SubmitResponse)
def submit_case(case_id: str, request: SubmitRequest):
    case = _CASES_BY_ID.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy case này")
    result = score_signals(case["expected_signals"], request.selected_signal_ids)
    explanations = {s["id"]: s["explanation"] for s in case["signals"]}
    return SubmitResponse(
        case_id=case_id,
        expected_signals=case["expected_signals"],
        explanations=explanations,
        **result,
    )

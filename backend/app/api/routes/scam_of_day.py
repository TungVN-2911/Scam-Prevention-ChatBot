from datetime import date as date_cls
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.scam_connector.mock_connector import MockScamConnector
from app.scam_connector.models import ScamPattern

router = APIRouter()
_connector = MockScamConnector()


class ScamOfDayResponse(BaseModel):
    date: str
    pattern: ScamPattern


def _is_displayable(pattern: ScamPattern) -> bool:
    return bool(
        pattern.name
        and (pattern.description or pattern.scenario)
        and pattern.warning_signs
        and pattern.prevention
        and (pattern.source.get("organization") or pattern.source.get("title"))
    )


def pick_pattern_for_date(patterns: list[ScamPattern], target_date: date_cls) -> Optional[ScamPattern]:
    # Deterministic theo ngay; fallback sang pattern ke tiep neu thieu du lieu hien thi.
    if not patterns:
        return None
    start_index = target_date.toordinal() % len(patterns)
    for offset in range(len(patterns)):
        candidate = patterns[(start_index + offset) % len(patterns)]
        if _is_displayable(candidate):
            return candidate
    return None


@router.get("/scam-of-day", response_model=ScamOfDayResponse)
def get_scam_of_day(date: Optional[str] = Query(default=None, description="YYYY-MM-DD, mặc định là hôm nay")):
    target_date = date_cls.fromisoformat(date) if date else date_cls.today()
    pattern = pick_pattern_for_date(_connector.search_patterns(), target_date)
    if pattern is None:
        raise HTTPException(status_code=404, detail="Không có dữ liệu hình thức lừa đảo để hiển thị")
    return ScamOfDayResponse(date=target_date.isoformat(), pattern=pattern)

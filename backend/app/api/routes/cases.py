from fastapi import APIRouter, HTTPException

from app.scam_connector.mock_connector import MockScamConnector
from app.scam_connector.models import Hotline, ScamCase, ScamPattern

router = APIRouter()
_connector = MockScamConnector()

@router.get("/case/{case_id}", response_model=ScamCase)
def get_case(case_id: str):
    case = _connector.get_case(case_id=case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.get("/patterns", response_model=list[ScamPattern])
def search_patterns(query: str = ""):
    return _connector.search_patterns(query)

@router.get("/hotlines", response_model=list[Hotline])
def list_hotlines():
    return _connector.list_hotlines()
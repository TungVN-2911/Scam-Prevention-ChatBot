import json

from pathlib import Path

from app.scam_connector.models import ScamPattern, Hotline

from app.config import DATA_DIR, KNOWLEDGE_BASE_DIR, REPO_ROOT

def _load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

class MockScamConnector:
    def __init__(self):
        self._hotlines = [Hotline(**h) for h in _load_json(DATA_DIR / "hotlines.json")]
        self._patterns = [ScamPattern(**p) for p in _load_json(
            KNOWLEDGE_BASE_DIR / "sources" / "scams" / "scams.json"
        )]

    def search_patterns(self, query: str = "") -> list[ScamPattern]:
        if not query:
            return self._patterns
        q = query.lower()
        return [p for p in self._patterns if q in (p.category or "").lower() or q in p.slug.lower() or q in p.name.lower()]
    
    def list_hotlines(self) -> list[Hotline]:
        return self._hotlines 
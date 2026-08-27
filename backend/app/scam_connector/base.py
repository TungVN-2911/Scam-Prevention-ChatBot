from typing import Protocol

from app.scam_connector.models import Hotline, ScamPattern

class ScamConnector(Protocol):
    def search_patterns(self, query: str = "") -> list[ScamPattern]: ...
    def list_hotlines(self) -> list[Hotline]: ...
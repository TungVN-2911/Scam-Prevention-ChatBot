from typing import Optional
from pathlib import Path
import yaml
from app.core.vietnamese_text import normalized, strip_diacritics
from dataclasses import dataclass

_INTENTS_PATH_ = Path(__file__).resolve().parent / "intents.yaml"

@dataclass
class IntentMatch:
    name: str
    description: str
    patterns: Optional[list[str]] = None
    
class IntentPatterns:
    def __init__(self, path: Path = _INTENTS_PATH_):
        with open(path, encoding="utf-8") as f:
            self._intents : list[dict] = yaml.safe_load(f) or []
            
    def detect(self, message: str) -> IntentMatch:
        normalize = strip_diacritics(normalized(message))
        for intent in self._intents:
            for pattern in intent.get("patterns", []):
                if strip_diacritics(normalized(pattern)) in normalize:
                    return IntentMatch(intent["name"], intent.get("description", ""), pattern)
        fallback = self._intents[-1] if self._intents else {"name": "general_question", "description": ""} 
        return IntentMatch(fallback["name"], fallback.get("description", ""))           
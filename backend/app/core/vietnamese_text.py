import re

from unicodedata import normalize, category

_WHITESPACE_ = re.compile(r"\s+")

def normalized(text: str) -> str:
    text = normalize("NFC", text)
    text = text.lower().strip()
    return _WHITESPACE_.sub(" ", text)

def strip_diacritics(text: str) -> str:
    text = normalize("NFD", text)
    text = "".join(ch for ch in text if category(ch)!="Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return normalize("NFC", text)
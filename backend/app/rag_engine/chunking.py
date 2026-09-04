from dataclasses import dataclass

@dataclass
class Chunk:
    text: str
    source: str
    
def chunk_markdown(text: str, source: str, max_chars: int = 1000) -> list[Chunk]:
    sections = _split_by_heading(text)
    chunks: list[Chunk] = []
    buffer = ""
    for section in sections:
        if buffer and len(buffer) + len(section) > max_chars:
            chunks.append(Chunk(text=buffer.strip(), source=source))
            buffer = section
        else:
            buffer = f"{buffer}\n\n{section}" if buffer else section
    if buffer.strip():
        chunks.append(Chunk(text=buffer.strip(), source=source))
    return chunks                
    
def chunk_scam_pattern(pattern: dict) -> str:
    # Dung chung cho ca ingest.py (batch) va route admin duyet report (tung record le)
    # - mot record = 1 chunk hoan chinh, khong tach nho (xem docs/summary.md muc 5).
    parts = [
        f"# {pattern['name']}",
        f"Loại: {pattern.get('category', '')}",
        f"Kịch bản: {pattern.get('scenario', '')}",
    ]
    if pattern.get("warning_signs"):
        parts.append("Dấu hiệu cảnh báo: " + "; ".join(pattern["warning_signs"]))
    if pattern.get("prevention"):
        parts.append("Cách phòng ngừa: " + "; ".join(pattern["prevention"]))
    if pattern.get("if_victim"):
        parts.append("Nếu đã là nạn nhân: " + "; ".join(pattern["if_victim"]))
    return "\n".join(parts)


def _split_by_heading(text: str) -> list[str]:
    lines = text.splitlines()
    sections: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("#") and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [s for s in sections if s]                
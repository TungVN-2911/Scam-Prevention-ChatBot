import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import KNOWLEDGE_BASE_DIR
from app.rag_engine.chunking import chunk_markdown
from app.rag_engine.retrieval import PineconeRetriever

SOURCES_DIR = KNOWLEDGE_BASE_DIR / "sources"

def load_markdown_chunks() -> tuple[list[str], list[str], list[dict]]:
    ids, texts, metadata = [], [], []
    for category in ("prevention", "recovery", "regulations"):
        for md_file in sorted((SOURCES_DIR / category).glob("*.md")):
            text = md_file.read_text(encoding = "utf-8")
            chunks = chunk_markdown(text, source = f"{category}/{md_file.name}")
            for i, chunk in enumerate(chunks):
                ids.append(f"{category}_{md_file.stem}_{i}")
                texts.append(chunk.text)
                metadata.append({"category": category, "source": chunk.source, "text": chunk.text})
    return ids, texts, metadata

def load_scam_pattern_chunks() -> tuple[list[str], list[str], list[dict]]:
    patterns = json.loads((SOURCES_DIR / "scams" / "scams.json").read_text(encoding="utf-8"))
    ids, texts, metadata = [], [], []
    for pattern in patterns:
        parts = [
            f"# {pattern['name']}",
            f"Loại: {pattern.get('category', '')}",
            f"Kịch bản: {pattern.get('scenario', '')}"
        ]      
        if pattern.get("warning_signs"):
            parts.append("Dấu hiệu cảnh báo: " + "; ".join(pattern["warning_signs"]))
        if pattern.get("prevention"):
            parts.append("Cách phòng ngừa: " + "; ".join(pattern["prevention"]))
        if pattern.get("if_victim"):
            parts.append("Nếu đã là nạn nhân: " + "; ".join(pattern["if_victim"]))
            
        text = "\n".join(parts)
        ids.append(f"scams_{pattern['slug']}")
        texts.append(text)
        metadata.append({"category": "scams", "source": "scams/scams.json", "text": text})
    return ids, texts, metadata    
    
def main():
    retriever = PineconeRetriever()
    
    all_ids, all_texts, all_metadata = [], [], []
    
    for loader in (load_markdown_chunks, load_scam_pattern_chunks):
        ids, texts, metadata = loader()
        all_ids += ids
        all_texts += texts
        all_metadata += metadata
    print(f"Tổng số chunk: {len(all_ids)}")
    
    batch_size = 50
    
    for i in range(0, len(all_ids), batch_size):
        retriever.upsert(
            ids = all_ids[i:i + batch_size],
            texts = all_texts[i:i + batch_size],
            metadata = all_metadata[i:i + batch_size]
        )        
        print(f"Đã upsert {min(i + batch_size, len(all_ids))}/{len(all_ids)}")
    print("Hoàn tất ingest.")
    
if __name__ == "__main__":
    main()        
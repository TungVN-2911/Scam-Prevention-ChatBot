from pinecone import Pinecone
from app.rag_engine.embedding import OllamaEmbedder
from app.config import settings

class PineconeRetriever:
    def __init__(self):
        self._embedder = OllamaEmbedder()
        self._client = Pinecone(api_key=settings.pinecone_api_key) if settings.pinecone_api_key else None
        self._index = self._client.Index(settings.pinecone_index) if self._client else None
        
    def upsert(self, ids: list[str], texts: list[str], metadata: list[dict]) -> None:
        if self._index is None:
            raise RuntimeError("PINECONE_API_KEY chưa được cấu hình")    
        vectors = self._embedder.embed(texts=texts)
        self._index.upsert(
            vectors=[
                {"id": id_, "values": vec, "metadata": {**meta, "text": text}}
                for id_, vec, meta, text in zip(ids, vectors, metadata, texts)
            ]
        )
        
    def query(self, text: str, top_k: int = 5, category: str | None=None) -> list[dict]:
        if self._index is None:
            return []
        vector = self._embedder.embed([text])[0]
        query_kwargs = {"vector": vector, "top_k": top_k, "include_metadata": True}
        if category:
            query_kwargs["filter"] = {"category": {"$eq": category}}
        result = self._index.query(**query_kwargs)    
        return [{"score": match.score, **(match.metadata or {})} for match in result.matches]
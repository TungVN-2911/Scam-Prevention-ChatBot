from app.config import settings
import requests
class OllamaEmbedder:
    def __init__(self):
        self._url = f"{settings.ollama_host}/api/embed"
        self._model = settings.ollama_embed_model
        
    def embed(self, texts: list[str]) -> list[list[float]]:
        response = requests.post(
            self._url,
            json={"model": self._model, "input": texts},
            timeout=60
        )  
        response.raise_for_status()
        return response.json()["embeddings"]
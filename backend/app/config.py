from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
KNOWLEDGE_BASE_DIR = REPO_ROOT / "knowledge_base"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")
    app_env: str = 'local'
    gemini_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index: str = "scam-prevention-knowledge-base"
    ollama_host: str = "http://localhost:11434"
    ollama_embed_model: str = "nomic-embed-text"
    sql_server_connection_string: str = ""
    jwt_secret_key: str = ""
    mcp_server_url: str = "http://127.0.0.1:8020/mcp"

settings = Settings()    
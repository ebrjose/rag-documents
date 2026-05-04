from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "gpt-oss:20b"
    ollama_embed_model: str = "qwen3-embedding:4b"
    ollama_context_length: int = 32768
    ollama_temperature: float = 0.2

    database_url: str = "postgresql://rag:rag@localhost:5435/rag_da"

    qdrant_url: str = "http://localhost:6335"
    qdrant_collection: str = "disposiciones"
    embed_dim: int = 2560

    uploads_dir: str = "./volumes/uploads"

    chunk_target_tokens: int = 500
    chunk_overlap_tokens: int = 75

    top_k: int = 8
    dense_weight: float = 0.7
    sparse_weight: float = 0.3

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"


settings = Settings()

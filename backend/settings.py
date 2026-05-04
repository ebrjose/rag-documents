"""Centralized configuration. No hardcoded values should leak into modules.

Each section is grouped by concern; defaults are documented inline. All values
override-able via `backend/.env` (pydantic-settings). The .env path is resolved
relative to this module so it works regardless of the cwd from which the
backend is launched.
"""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # ── Ollama ────────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "gemma4:31b"
    ollama_embed_model: str = "qwen3-embedding:4b"
    ollama_context_length: int = 16384
    """num_ctx para chat. 16K cubre system prompt + 8 chunks de ~500 tokens
    + pregunta + respuesta con margen. Subir solo si se aumenta top_k o se
    cambia chunk_target_tokens significativamente."""
    ollama_embed_context_length: int = 2048
    """num_ctx para embeddings. Los textos a embeber son chunks (~500 tokens)
    y queries cortas, así que 2K es holgado y libera VRAM del KV cache."""
    ollama_temperature: float = 0.2
    ollama_embed_timeout_seconds: float = 120.0
    ollama_chat_timeout_seconds: float | None = None  # None = sin límite (streaming largo)
    ollama_ping_timeout_seconds: float = 5.0
    ollama_embed_batch_timeout_seconds: float = 600.0

    # ── Postgres ──────────────────────────────────────────────────────────
    database_url: str = "postgresql://rag:rag@localhost:5435/rag_da"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 8

    # ── Qdrant ────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6335"
    qdrant_collection: str = "disposiciones"
    qdrant_dense_vector_name: str = "dense"
    qdrant_sparse_vector_name: str = "bm25"
    embed_dim: int = 2560

    # ── Sparse embedding (BM25 vía FastEmbed) ─────────────────────────────
    sparse_model_name: str = "Qdrant/bm25"

    # ── Storage de PDFs originales ───────────────────────────────────────
    uploads_dir: str = "./volumes/uploads"
    pdf_header: bytes = b"%PDF-"
    pdf_extension: str = ".pdf"
    max_files_per_upload: int = 20

    # ── Chunking ─────────────────────────────────────────────────────────
    chunk_target_tokens: int = 500
    chunk_overlap_tokens: int = 75
    chunk_chars_per_token: int = 4  # heurística ES (sin tokenizer del modelo)

    # ── Retrieval ────────────────────────────────────────────────────────
    top_k: int = 8
    dense_weight: float = 0.7
    sparse_weight: float = 0.3
    retrieval_prefetch_multiplier: int = 4

    # ── Concurrencia ─────────────────────────────────────────────────────
    embed_concurrency: int = 4
    """Máx. requests simultáneas a Ollama /api/embeddings dentro de un doc.
    Ollama serializa internamente si OLLAMA_NUM_PARALLEL=1, pero igual gana
    por overlap de TCP/HTTP."""
    ingest_concurrency: int = 2
    """Máx. documentos procesándose en paralelo. Pipelining: uno hace OCR
    en GPU mientras otro embebe, otro hace upsert. VRAM = chat + embed +
    Surya × ingest_concurrency, calibrar según hardware."""

    # ── OCR ──────────────────────────────────────────────────────────────
    ocr_enabled: bool = True
    ocr_provider: Literal["surya", "none"] = "surya"
    ocr_languages: list[str] = ["es"]
    ocr_dpi: int = 200
    ocr_min_total_chars: int = 50  # umbral total bajo el cual se considera escaneado
    ocr_device: Literal["auto", "cuda", "cpu"] = "auto"

    # ── Servidor ─────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # Si está definido (ej. "/app/static"), el backend sirve los archivos
    # estáticos de la SPA desde esa ruta en `/`. En dev queda vacío y el
    # frontend corre en su propio dev server con HMR.
    static_dir: str = ""

    # ── Límites varios ───────────────────────────────────────────────────
    error_message_max_length: int = 500


settings = Settings()

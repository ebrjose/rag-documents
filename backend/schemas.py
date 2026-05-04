from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

DocumentStatus = Literal[
    "pending", "processing", "ocr_processing", "indexed", "error", "requires_ocr"
]
SourceType = Literal["pdf", "docx"]


class DocumentOut(BaseModel):
    document_id: UUID
    filename: str
    source_type: SourceType
    status: DocumentStatus
    used_ocr: bool
    uploaded_at: datetime
    page_count: int | None = None
    chunk_count: int | None = None
    error_message: str | None = None


class UploadResult(BaseModel):
    document_id: UUID | None
    filename: str
    accepted: bool
    reason: str | None = None


class UploadResponse(BaseModel):
    results: list[UploadResult]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    """Historial completo de la conversación. El último mensaje debe ser del
    usuario y es la pregunta a responder."""
    top_k: int | None = None


class Citation(BaseModel):
    document_id: UUID
    filename: str
    page: int


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    ollama: bool
    qdrant: bool
    postgres: bool
    indexed_documents: int

import asyncio
import hashlib
import logging
from pathlib import Path
from uuid import UUID

from backend.core import catalog, extract, ollama_client, sparse, store
from backend.core.chunk import chunk_pages
from backend.settings import settings

log = logging.getLogger(__name__)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def process_document(document_id: UUID, storage_path: str, filename: str) -> None:
    """Background task: extract → chunk → embed → upsert → mark indexed."""
    path = Path(storage_path)
    try:
        catalog.update_status(document_id, "processing")

        pages = await asyncio.to_thread(extract.extract_pages, path)
        page_count = len(pages)
        total_chars = sum(len(t) for _, t in pages)
        if total_chars < 50:
            catalog.update_status(
                document_id,
                "requires_ocr",
                page_count=page_count,
                error_message="PDF sin texto extraíble (probablemente escaneado).",
            )
            return

        chunks = chunk_pages(
            pages,
            target_tokens=settings.chunk_target_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        )
        if not chunks:
            catalog.update_status(
                document_id,
                "error",
                page_count=page_count,
                error_message="No se generaron chunks.",
            )
            return

        texts = [c["text"] for c in chunks]
        dense = await ollama_client.embed_batch(texts)
        sparse_vecs = await asyncio.to_thread(sparse.encode, texts)

        await asyncio.to_thread(
            store.upsert_chunks,
            document_id=document_id,
            filename=filename,
            chunks=chunks,
            dense_vectors=dense,
            sparse_vectors=sparse_vecs,
        )

        catalog.update_status(
            document_id,
            "indexed",
            page_count=page_count,
            chunk_count=len(chunks),
        )
    except Exception as e:
        log.exception("ingest failed for %s", document_id)
        catalog.update_status(
            document_id,
            "error",
            error_message=f"{type(e).__name__}: {e}"[:500],
        )

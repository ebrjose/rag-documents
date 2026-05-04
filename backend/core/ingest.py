"""Ingest pipeline: validate → extract → (OCR si hace falta) → chunk → embed → upsert.

Pure orchestration; each step lives in its own module. Status transitions are
the single concern of this file.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from uuid import UUID

from backend.core import catalog, extract, ollama_client, sparse, store
from backend.core.chunk import chunk_pages
from backend.core.ocr import OCRProvider, PageText, get_ocr_provider
from backend.settings import settings

log = logging.getLogger(__name__)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def process_document(
    document_id: UUID, storage_path: str, filename: str
) -> None:
    """Background task. Updates status as the document moves through the pipeline."""
    path = Path(storage_path)
    try:
        catalog.update_status(document_id, "processing")

        pages = await asyncio.to_thread(extract.extract_pages, path)
        page_count = len(pages)

        if _is_text_sparse(pages):
            pages = await _try_ocr(document_id, path, page_count)
            if pages is None:
                return  # status already set to requires_ocr

        chunks = chunk_pages(
            pages,
            target_tokens=settings.chunk_target_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
            chars_per_token=settings.chunk_chars_per_token,
        )
        if not chunks:
            catalog.update_status(
                document_id,
                "error",
                page_count=page_count,
                error_message="No se generaron chunks tras la extracción.",
            )
            return

        await _embed_and_store(document_id, filename, chunks)

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
            error_message=_short_error(e),
        )


# ── pasos ────────────────────────────────────────────────────────────────────


async def _try_ocr(
    document_id: UUID, path: Path, page_count: int
) -> list[PageText] | None:
    """Attempts OCR. Returns new pages on success, None if document must be marked
    requires_ocr (status is set inside)."""
    ocr: OCRProvider | None = get_ocr_provider()
    if ocr is None:
        catalog.update_status(
            document_id,
            "requires_ocr",
            page_count=page_count,
            error_message="OCR deshabilitado y el PDF no tiene texto extraíble.",
        )
        return None

    catalog.update_status(document_id, "ocr_processing", page_count=page_count)
    try:
        pages = await asyncio.to_thread(ocr.extract_text, path)
    except Exception as e:
        log.exception("OCR falló para %s", document_id)
        catalog.update_status(
            document_id,
            "requires_ocr",
            page_count=page_count,
            error_message=f"OCR falló: {_short_error(e)}",
        )
        return None

    if _is_text_sparse(pages):
        catalog.update_status(
            document_id,
            "requires_ocr",
            page_count=page_count,
            error_message="Tras OCR el documento sigue sin texto suficiente.",
        )
        return None

    catalog.mark_used_ocr(document_id)
    return pages


async def _embed_and_store(
    document_id: UUID, filename: str, chunks: list[dict]
) -> None:
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


# ── helpers ─────────────────────────────────────────────────────────────────


def _is_text_sparse(pages: list[PageText]) -> bool:
    if not pages:
        return True
    total_chars = sum(len(t) for _, t in pages)
    return total_chars < settings.ocr_min_total_chars


def _short_error(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"[: settings.error_message_max_length]

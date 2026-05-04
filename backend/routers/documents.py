"""Documents router: upload, list, detail, file, delete.

The router is a thin HTTP layer; orchestration lives in `core.ingest` and
persistence in `core.catalog` / `core.store`.
"""
from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.core import catalog, ingest, scheduler, store
from backend.schemas import DocumentOut, UploadResponse, UploadResult
from backend.settings import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)):
    if len(files) > settings.max_files_per_upload:
        raise HTTPException(
            400, f"Máximo {settings.max_files_per_upload} archivos por operación."
        )
    os.makedirs(settings.uploads_dir, exist_ok=True)

    results: list[UploadResult] = []
    for f in files:
        result = await _ingest_one(f)
        results.append(result)
    return UploadResponse(results=results)


async def _ingest_one(f: UploadFile) -> UploadResult:
    name = f.filename or f"documento{settings.pdf_extension}"

    if not name.lower().endswith(settings.pdf_extension):
        return UploadResult(
            document_id=None,
            filename=name,
            accepted=False,
            reason=f"Extensión no {settings.pdf_extension}",
        )

    data = await f.read()
    if not data.startswith(settings.pdf_header):
        return UploadResult(
            document_id=None, filename=name, accepted=False, reason="Cabecera PDF inválida"
        )

    sha = ingest.sha256_bytes(data)
    existing = catalog.find_by_sha256(sha)
    if existing:
        return UploadResult(
            document_id=existing["document_id"],
            filename=name,
            accepted=False,
            reason="Documento ya indexado (mismo contenido).",
        )

    doc_id = uuid4()
    storage_path = _persist_file(doc_id, data)
    catalog.insert_document_with_id(
        document_id=doc_id,
        filename=name,
        sha256=sha,
        storage_path=storage_path,
        source_type=_infer_source_type(name),
    )
    scheduler.schedule_ingest(ingest.process_document, doc_id, storage_path, name)
    return UploadResult(document_id=doc_id, filename=name, accepted=True)


def _infer_source_type(filename: str) -> str:
    """Maps file extension to source_type. Single source of truth for what
    extensions we support — extend here when adding docx/etc."""
    if filename.lower().endswith(".pdf"):
        return "pdf"
    if filename.lower().endswith(".docx"):
        return "docx"
    raise ValueError(f"Tipo de archivo no soportado: {filename}")


def _persist_file(doc_id: UUID, data: bytes) -> str:
    path = Path(settings.uploads_dir) / f"{doc_id}{settings.pdf_extension}"
    path.write_bytes(data)
    return str(path)


@router.get("", response_model=list[DocumentOut])
def list_all() -> list[DocumentOut]:
    return [_to_out(r) for r in catalog.list_documents()]


@router.get("/{document_id}", response_model=DocumentOut)
def get_one(document_id: UUID) -> DocumentOut:
    row = catalog.get_document(document_id)
    if not row:
        raise HTTPException(404, "Documento no encontrado.")
    return _to_out(row)


@router.get("/{document_id}/file")
def get_file(document_id: UUID) -> FileResponse:
    row = catalog.get_document(document_id)
    if not row:
        raise HTTPException(404, "Documento no encontrado.")
    return FileResponse(
        row["storage_path"],
        media_type="application/pdf",
        filename=row["filename"],
        content_disposition_type="inline",
    )


@router.delete("/{document_id}")
def delete_one(document_id: UUID) -> dict:
    row = catalog.get_document(document_id)
    if not row:
        raise HTTPException(404, "Documento no encontrado.")
    _safely_delete_qdrant_points(document_id)
    _safely_delete_file(row["storage_path"])
    catalog.delete_document(document_id)
    return {"ok": True, "document_id": str(document_id)}


def _safely_delete_qdrant_points(document_id: UUID) -> None:
    try:
        store.delete_document_points(document_id)
    except Exception:
        pass


def _safely_delete_file(storage_path: str) -> None:
    try:
        os.remove(storage_path)
    except FileNotFoundError:
        pass


def _to_out(row: dict) -> DocumentOut:
    return DocumentOut(
        document_id=row["document_id"],
        filename=row["filename"],
        source_type=row["source_type"],
        status=row["status"],
        used_ocr=row["used_ocr"],
        uploaded_at=row["uploaded_at"],
        page_count=row.get("page_count"),
        chunk_count=row.get("chunk_count"),
        error_message=row.get("error_message"),
    )

import os
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.core import catalog, ingest, store
from backend.schemas import DocumentOut, UploadResponse, UploadResult
from backend.settings import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _to_out(row: dict) -> DocumentOut:
    return DocumentOut(
        document_id=row["document_id"],
        filename=row["filename"],
        status=row["status"],
        uploaded_at=row["uploaded_at"],
        page_count=row.get("page_count"),
        chunk_count=row.get("chunk_count"),
        error_message=row.get("error_message"),
    )


@router.post("", response_model=UploadResponse)
async def upload_documents(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
):
    if len(files) > 20:
        raise HTTPException(400, "Máximo 20 archivos por operación.")
    os.makedirs(settings.uploads_dir, exist_ok=True)
    results: list[UploadResult] = []

    for f in files:
        name = f.filename or "documento.pdf"
        if not name.lower().endswith(".pdf"):
            results.append(UploadResult(document_id=None, filename=name, accepted=False, reason="Extensión no .pdf"))
            continue
        data = await f.read()
        if not data.startswith(b"%PDF-"):
            results.append(UploadResult(document_id=None, filename=name, accepted=False, reason="Cabecera PDF inválida"))
            continue
        sha = ingest.sha256_bytes(data)
        existing = catalog.find_by_sha256(sha)
        if existing:
            results.append(
                UploadResult(
                    document_id=existing["document_id"],
                    filename=name,
                    accepted=False,
                    reason="Documento ya indexado (mismo contenido).",
                )
            )
            continue

        doc_id = uuid4()
        storage_path = str(Path(settings.uploads_dir) / f"{doc_id}.pdf")
        with open(storage_path, "wb") as out:
            out.write(data)
        # Insert via app-side UUID by overriding default
        from backend.core.catalog import conn
        with conn() as c:
            c.execute(
                "INSERT INTO documents (document_id, filename, sha256, status, storage_path) VALUES (%s,%s,%s,'pending',%s)",
                (doc_id, name, sha, storage_path),
            )
        background.add_task(_run_ingest, doc_id, storage_path, name)
        results.append(UploadResult(document_id=doc_id, filename=name, accepted=True))

    return UploadResponse(results=results)


async def _run_ingest(document_id: UUID, storage_path: str, filename: str):
    await ingest.process_document(document_id, storage_path, filename)


@router.get("", response_model=list[DocumentOut])
def list_all():
    return [_to_out(r) for r in catalog.list_documents()]


@router.get("/{document_id}", response_model=DocumentOut)
def get_one(document_id: UUID):
    row = catalog.get_document(document_id)
    if not row:
        raise HTTPException(404, "Documento no encontrado.")
    return _to_out(row)


@router.get("/{document_id}/file")
def get_file(document_id: UUID):
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
def delete_one(document_id: UUID):
    row = catalog.get_document(document_id)
    if not row:
        raise HTTPException(404, "Documento no encontrado.")
    try:
        store.delete_document_points(document_id)
    except Exception:
        pass
    try:
        os.remove(row["storage_path"])
    except FileNotFoundError:
        pass
    catalog.delete_document(document_id)
    return {"ok": True, "document_id": str(document_id)}

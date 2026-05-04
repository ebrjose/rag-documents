import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.core import catalog, ingest, scheduler, store
from backend.routers import chat, documents, health
from backend.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.ensure_collection()
    _resume_orphan_ingests()
    yield


def _resume_orphan_ingests() -> None:
    """Reencola docs que quedaron en estados intermedios cuando el backend
    cayó (por ejemplo crash, restart, o killing del scheduler in-flight).

    Sin esto, esos docs quedan eternamente en `pending` / `processing` /
    `ocr_processing`. El scheduler sólo se invoca en uploads, así que
    necesitamos disparar manualmente al boot.

    Para `processing`/`ocr_processing`: los volvemos a `pending` antes de
    encolar. Si el doc ya tenía chunks parciales en Qdrant, el upsert por
    id determinístico los sobreescribe — no hay duplicados.
    """
    rows = catalog.list_documents()
    orphans = [
        r for r in rows
        if r["status"] in ("pending", "processing", "ocr_processing")
    ]
    if not orphans:
        return
    log.info("Reencolando %d docs huérfanos al startup", len(orphans))
    for r in orphans:
        if r["status"] != "pending":
            catalog.update_status(r["document_id"], "pending")
        scheduler.schedule_ingest(
            ingest.process_document,
            r["document_id"],
            r["storage_path"],
            r["filename"],
        )


app = FastAPI(title="RAG-DA Backend", version="0.1.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# API routers van primero — la SPA catch-all (registrada en _mount_spa)
# sólo atrapa lo que no matchea ningún router.
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(chat.router)


def _mount_spa() -> None:
    """If STATIC_DIR is set and exists, serve the built SPA from `/`.

    Same-origin: la SPA queda en `/` y la API en `/api/...`. Cero CORS, un
    solo puerto. En dev este mount queda inactivo y el frontend corre en
    su propio dev server con HMR.
    """
    if not settings.static_dir:
        return
    static_path = Path(settings.static_dir)
    if not static_path.is_dir():
        log.warning("STATIC_DIR=%s no existe; no se monta SPA.", static_path)
        return

    index_file = static_path / "index.html"
    if not index_file.is_file():
        log.warning("index.html no encontrado en %s; no se monta SPA.", static_path)
        return

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        candidate = static_path / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)

    log.info("SPA montada desde %s", static_path)


_mount_spa()

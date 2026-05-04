from fastapi import APIRouter

from backend.core import catalog, ollama_client, store
from backend.schemas import HealthResponse

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health():
    ollama_ok = await ollama_client.ping()
    qdrant_ok = store.ping()
    try:
        n = catalog.count_indexed()
        pg_ok = True
    except Exception:
        n = 0
        pg_ok = False
    status = "ok" if (ollama_ok and qdrant_ok and pg_ok) else "degraded"
    return HealthResponse(
        status=status,
        ollama=ollama_ok,
        qdrant=qdrant_ok,
        postgres=pg_ok,
        indexed_documents=n,
    )

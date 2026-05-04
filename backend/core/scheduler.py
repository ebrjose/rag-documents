"""Pipeline-style ingest scheduler.

`asyncio.create_task` + global semaphore lets multiple documents progress
concurrently in the same event loop. While one is on the GPU (OCR or embed),
another can be doing CPU-bound work (extract, chunk) or I/O (Postgres,
Qdrant upsert). The semaphore caps how many documents may hold an OCR slot
at once, since that step contends for VRAM.

Tasks are tracked in a module-level set so the GC doesn't collect them
mid-run; entries are removed on completion.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable
from uuid import UUID

from backend.settings import settings

log = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None
_running: set[asyncio.Task] = set()


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(settings.ingest_concurrency)
    return _semaphore


def schedule_ingest(
    runner: Callable[[UUID, str, str], Awaitable[None]],
    document_id: UUID,
    storage_path: str,
    filename: str,
) -> None:
    """Fire-and-forget. The runner is awaited inside the semaphore so the
    GPU-bound steps respect the configured concurrency cap."""
    sem = _get_semaphore()

    async def _wrapped() -> None:
        async with sem:
            try:
                await runner(document_id, storage_path, filename)
            except Exception:
                log.exception("Ingest task crashed for %s", document_id)

    task = asyncio.create_task(_wrapped(), name=f"ingest:{document_id}")
    _running.add(task)
    task.add_done_callback(_running.discard)

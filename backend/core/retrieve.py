"""Retrieval orchestration: rewrite (si aplica) → embed query → hybrid search."""
from __future__ import annotations

import asyncio

from backend.core import catalog, ollama_client, rewrite, sparse, store
from backend.schemas import ChatMessage
from backend.settings import settings


async def retrieve(
    messages: list[ChatMessage], top_k: int | None = None
) -> tuple[list[dict], str]:
    """Devuelve (chunks, query_efectiva). La query efectiva es lo que se usó
    para el retrieval — útil para tracing y para que el caller la sepa."""
    k = top_k or settings.top_k

    indexed_ids = catalog.list_indexed_ids()
    if not indexed_ids:
        return [], ""

    query = await rewrite.rewrite_if_followup(messages)
    if not query:
        return [], ""

    dense = await ollama_client.embed(query)
    sparse_vec = await asyncio.to_thread(sparse.encode_query, query)

    chunks = await asyncio.to_thread(
        store.hybrid_search,
        query_dense=dense,
        query_sparse=sparse_vec,
        document_ids=indexed_ids,
        top_k=k,
    )
    return chunks, query

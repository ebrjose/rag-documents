import asyncio

from backend.core import catalog, ollama_client, sparse, store
from backend.settings import settings


async def retrieve(query: str, top_k: int | None = None) -> list[dict]:
    k = top_k or settings.top_k
    indexed_ids = catalog.list_indexed_ids()
    if not indexed_ids:
        return []

    dense = await ollama_client.embed(query)
    sparse_vec = await asyncio.to_thread(sparse.encode_query, query)

    return await asyncio.to_thread(
        store.hybrid_search,
        query_dense=dense,
        query_sparse=sparse_vec,
        document_ids=indexed_ids,
        top_k=k,
    )

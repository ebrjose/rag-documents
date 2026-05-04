"""Qdrant store: collection lifecycle, upsert, hybrid search."""
from __future__ import annotations

from typing import Iterable
from uuid import UUID

from qdrant_client import QdrantClient, models

from backend.settings import settings

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, prefer_grpc=False)
    return _client


def ensure_collection() -> None:
    client = get_client()
    name = settings.qdrant_collection
    if client.collection_exists(name):
        return
    client.create_collection(
        collection_name=name,
        vectors_config={
            settings.qdrant_dense_vector_name: models.VectorParams(
                size=settings.embed_dim,
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            settings.qdrant_sparse_vector_name: models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            ),
        },
    )


def ping() -> bool:
    try:
        get_client().get_collections()
        return True
    except Exception:
        return False


def upsert_chunks(
    *,
    document_id: UUID,
    filename: str,
    chunks: list[dict],
    dense_vectors: list[list[float]],
    sparse_vectors: list[models.SparseVector],
) -> None:
    points = [
        models.PointStruct(
            id=_point_id(document_id, ch["chunk_index"]),
            vector={
                settings.qdrant_dense_vector_name: d_vec,
                settings.qdrant_sparse_vector_name: s_vec,
            },
            payload={
                "document_id": str(document_id),
                "filename": filename,
                "page_start": ch["page_start"],
                "page_end": ch["page_end"],
                "chunk_index": ch["chunk_index"],
                "chunk_total": ch["chunk_total"],
                "text": ch["text"],
            },
        )
        for ch, d_vec, s_vec in zip(chunks, dense_vectors, sparse_vectors)
    ]
    get_client().upsert(
        collection_name=settings.qdrant_collection, points=points, wait=True
    )


def delete_document_points(document_id: UUID) -> None:
    get_client().delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=str(document_id)),
                    )
                ]
            )
        ),
        wait=True,
    )


def hybrid_search(
    *,
    query_dense: list[float],
    query_sparse: models.SparseVector,
    document_ids: Iterable[str],
    top_k: int,
) -> list[dict]:
    doc_ids_list = list(document_ids)
    if not doc_ids_list:
        return []

    flt = models.Filter(
        must=[
            models.FieldCondition(
                key="document_id", match=models.MatchAny(any=doc_ids_list)
            )
        ]
    )
    prefetch_limit = top_k * settings.retrieval_prefetch_multiplier
    prefetch = [
        models.Prefetch(
            query=query_dense,
            using=settings.qdrant_dense_vector_name,
            limit=prefetch_limit,
            filter=flt,
        ),
        models.Prefetch(
            query=query_sparse,
            using=settings.qdrant_sparse_vector_name,
            limit=prefetch_limit,
            filter=flt,
        ),
    ]
    res = get_client().query_points(
        collection_name=settings.qdrant_collection,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        with_payload=True,
        limit=top_k,
    )
    return [{"score": p.score, "payload": p.payload} for p in res.points]


def _point_id(document_id: UUID, chunk_index: int) -> int:
    """Deterministic 64-bit id from document UUID + chunk index.

    Uses 6 bytes of the UUID + 2 bytes for the chunk index (≤ 65,535 chunks per
    document, more than suficiente para nuestros tamaños).
    """
    return int.from_bytes(
        document_id.bytes[:6] + chunk_index.to_bytes(2, "big"), "big"
    )

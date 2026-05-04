from typing import Iterable
from uuid import UUID

from qdrant_client import QdrantClient, models
from qdrant_client.http import models as rest

from backend.settings import settings

_client: QdrantClient | None = None
_bm25_model_name = "Qdrant/bm25"


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
            "dense": models.VectorParams(
                size=settings.embed_dim,
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            "bm25": models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            ),
        },
    )


def ping() -> bool:
    try:
        c = get_client()
        c.get_collections()
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
    client = get_client()
    points = []
    for i, (ch, d_vec, s_vec) in enumerate(zip(chunks, dense_vectors, sparse_vectors)):
        points.append(
            models.PointStruct(
                id=int.from_bytes(
                    document_id.bytes[:6] + i.to_bytes(2, "big"), "big"
                ),
                vector={"dense": d_vec, "bm25": s_vec},
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
        )
    client.upsert(collection_name=settings.qdrant_collection, points=points, wait=True)


def delete_document_points(document_id: UUID) -> None:
    client = get_client()
    client.delete(
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
    client = get_client()
    doc_ids_list = list(document_ids)
    if not doc_ids_list:
        return []

    flt = models.Filter(
        must=[
            models.FieldCondition(
                key="document_id",
                match=models.MatchAny(any=doc_ids_list),
            )
        ]
    )

    prefetch = [
        models.Prefetch(
            query=query_dense,
            using="dense",
            limit=top_k * 4,
            filter=flt,
        ),
        models.Prefetch(
            query=query_sparse,
            using="bm25",
            limit=top_k * 4,
            filter=flt,
        ),
    ]
    res = client.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=prefetch,
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        with_payload=True,
        limit=top_k,
    )
    return [
        {"score": p.score, "payload": p.payload} for p in res.points
    ]

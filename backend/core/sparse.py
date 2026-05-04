"""BM25 sparse encoder. Modelo configurable (settings.sparse_model_name)."""
from __future__ import annotations

from threading import Lock

from qdrant_client import models

from backend.settings import settings

_encoder = None
_lock = Lock()


def get_encoder():
    global _encoder
    if _encoder is None:
        with _lock:
            if _encoder is None:
                from fastembed import SparseTextEmbedding

                _encoder = SparseTextEmbedding(model_name=settings.sparse_model_name)
    return _encoder


def encode(texts: list[str]) -> list[models.SparseVector]:
    enc = get_encoder()
    return [
        models.SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())
        for emb in enc.embed(texts)
    ]


def encode_query(text: str) -> models.SparseVector:
    enc = get_encoder()
    for emb in enc.embed([text]):
        return models.SparseVector(
            indices=emb.indices.tolist(), values=emb.values.tolist()
        )
    return models.SparseVector(indices=[], values=[])

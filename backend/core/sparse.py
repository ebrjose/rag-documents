"""Lazy BM25 sparse encoder using FastEmbed."""
from __future__ import annotations

from qdrant_client import models

_encoder = None


def get_encoder():
    global _encoder
    if _encoder is None:
        from fastembed import SparseTextEmbedding

        _encoder = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _encoder


def encode(texts: list[str]) -> list[models.SparseVector]:
    enc = get_encoder()
    out: list[models.SparseVector] = []
    for emb in enc.embed(texts):
        out.append(
            models.SparseVector(
                indices=emb.indices.tolist(),
                values=emb.values.tolist(),
            )
        )
    return out


def encode_query(text: str) -> models.SparseVector:
    enc = get_encoder()
    # passage_embed/query_embed exist in fastembed; embed() works for both
    for emb in enc.embed([text]):
        return models.SparseVector(
            indices=emb.indices.tolist(),
            values=emb.values.tolist(),
        )
    return models.SparseVector(indices=[], values=[])

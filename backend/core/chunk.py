"""Text chunking: paragraph → sentence → character fallback, with overlap.

Stateless module. All sizes are passed explicitly to keep callers honest about
configuration (no hidden module-level constants).
"""
from __future__ import annotations

import re

_PARAGRAPH_BOUNDARY = re.compile(r"\n\s*\n+")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¡¿])")


def chunk_pages(
    pages: list[tuple[int, str]],
    *,
    target_tokens: int,
    overlap_tokens: int,
    chars_per_token: int,
) -> list[dict]:
    """Splits page texts into overlapping chunks, preserving page_start/page_end.

    Args:
        pages: list of (page_number, text), in order.
        target_tokens: desired chunk size in tokens.
        overlap_tokens: overlap between consecutive chunks.
        chars_per_token: heuristic conversion (4 ≈ Spanish text).

    Returns:
        list of dicts with keys: text, page_start, page_end, chunk_index, chunk_total.
    """
    target_chars = target_tokens * chars_per_token
    overlap_chars = overlap_tokens * chars_per_token

    segments = list(_segment_pages(pages, target_chars))
    raw_chunks = list(_pack_segments(segments, target_chars, overlap_chars))

    total = len(raw_chunks)
    for i, ch in enumerate(raw_chunks):
        ch["chunk_index"] = i
        ch["chunk_total"] = total
    return raw_chunks


# ── internos ────────────────────────────────────────────────────────────────


def _segment_pages(pages: list[tuple[int, str]], target_chars: int):
    """Yields (page_number, segment) breaking long paragraphs into smaller pieces."""
    for page_num, text in pages:
        if not text:
            continue
        for paragraph in _split_paragraphs(text):
            if len(paragraph) <= target_chars:
                yield page_num, paragraph
                continue
            for sentence in _split_sentences(paragraph):
                if len(sentence) <= target_chars:
                    yield page_num, sentence
                else:
                    for piece in _split_chars(sentence, target_chars):
                        yield page_num, piece


def _pack_segments(segments, target_chars: int, overlap_chars: int):
    """Greedy packing of segments into ≤ target_chars chunks with char-level overlap."""
    cur_text = ""
    cur_pages: list[int] = []
    for page_num, seg in segments:
        sep = "\n\n" if cur_text else ""
        if len(cur_text) + len(sep) + len(seg) <= target_chars or not cur_text:
            cur_text = cur_text + sep + seg
            cur_pages.append(page_num)
            continue
        yield {
            "text": cur_text,
            "page_start": min(cur_pages),
            "page_end": max(cur_pages),
        }
        tail = cur_text[-overlap_chars:] if overlap_chars > 0 else ""
        cur_text = (tail + "\n\n" + seg).strip()
        cur_pages = [page_num]

    if cur_text.strip():
        yield {
            "text": cur_text,
            "page_start": min(cur_pages) if cur_pages else 1,
            "page_end": max(cur_pages) if cur_pages else 1,
        }


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in _PARAGRAPH_BOUNDARY.split(text) if p.strip()]


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_BOUNDARY.split(text) if s.strip()]


def _split_chars(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]

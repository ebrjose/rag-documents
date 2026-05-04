import re

# Aproximación: 1 token ≈ 4 chars en español. No usamos tokenizer del modelo
# para evitar dependencia adicional; el rango es lo suficientemente tolerante.
CHARS_PER_TOKEN = 4


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _split_sentences(text: str) -> list[str]:
    # Splitter conservador en español. Mantiene puntuación.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ¡¿])", text)
    return [p.strip() for p in parts if p.strip()]


def _split_chars(text: str, target_chars: int) -> list[str]:
    return [text[i : i + target_chars] for i in range(0, len(text), target_chars)]


def chunk_pages(
    pages: list[tuple[int, str]],
    *,
    target_tokens: int,
    overlap_tokens: int,
) -> list[dict]:
    """Splits page texts into overlapping chunks, preserving page_start/page_end."""
    target_chars = target_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN

    # Build flat segments with their page numbers using paragraph → sentence → char fallback.
    segments: list[tuple[int, str]] = []
    for page_num, text in pages:
        if not text:
            continue
        for para in _split_paragraphs(text):
            if len(para) <= target_chars:
                segments.append((page_num, para))
                continue
            for sent in _split_sentences(para):
                if len(sent) <= target_chars:
                    segments.append((page_num, sent))
                else:
                    for piece in _split_chars(sent, target_chars):
                        segments.append((page_num, piece))

    # Greedily pack segments into chunks ≤ target_chars, then add char-overlap.
    raw_chunks: list[dict] = []
    cur_text = ""
    cur_pages: list[int] = []
    for page_num, seg in segments:
        sep = "\n\n" if cur_text else ""
        if len(cur_text) + len(sep) + len(seg) <= target_chars or not cur_text:
            cur_text = cur_text + sep + seg
            cur_pages.append(page_num)
        else:
            raw_chunks.append(
                {
                    "text": cur_text,
                    "page_start": min(cur_pages),
                    "page_end": max(cur_pages),
                }
            )
            # Apply overlap: keep last `overlap_chars` of prior chunk as prefix
            tail = cur_text[-overlap_chars:] if overlap_chars > 0 else ""
            cur_text = (tail + "\n\n" + seg).strip()
            cur_pages = [page_num]
    if cur_text.strip():
        raw_chunks.append(
            {
                "text": cur_text,
                "page_start": min(cur_pages) if cur_pages else 1,
                "page_end": max(cur_pages) if cur_pages else 1,
            }
        )

    total = len(raw_chunks)
    for i, ch in enumerate(raw_chunks):
        ch["chunk_index"] = i
        ch["chunk_total"] = total
    return raw_chunks

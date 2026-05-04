from pathlib import Path

import pymupdf


def is_pdf(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except Exception:
        return False


def extract_pages(path: Path) -> list[tuple[int, str]]:
    """Returns list of (page_number_1_based, text)."""
    pages: list[tuple[int, str]] = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append((i, text.strip()))
    return pages


def page_count(path: Path) -> int:
    with pymupdf.open(path) as doc:
        return doc.page_count

"""OCR abstraction.

Providers implement `OCRProvider` and are wired by `get_ocr_provider()` based
on `settings.ocr_provider`. The ingest pipeline depends only on the protocol,
not on any concrete implementation, so swapping engines (Surya / Tesseract /
Paddle / etc.) requires no changes outside this package.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

PageText = tuple[int, str]
"""Tuple of (page_number_1_based, extracted_text)."""


class OCRProvider(Protocol):
    """Extracts text from each page of a PDF using OCR.

    Implementations must return a list of `(page_number, text)` ordered by
    ascending page number. Empty pages should still be returned with an empty
    text string so the page count is preserved.
    """

    def extract_text(self, pdf_path: Path) -> list[PageText]: ...


def get_ocr_provider() -> OCRProvider | None:
    """Returns the configured OCR provider, or None if OCR is disabled.

    The returned provider is a process-wide singleton; concrete implementations
    may load heavy models lazily on first call.
    """
    from backend.settings import settings

    if not settings.ocr_enabled or settings.ocr_provider == "none":
        return None
    if settings.ocr_provider == "surya":
        from backend.core.ocr.surya_provider import SuryaOCRProvider

        return SuryaOCRProvider.instance()
    raise ValueError(f"OCR provider no soportado: {settings.ocr_provider!r}")

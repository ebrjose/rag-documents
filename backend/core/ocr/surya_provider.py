"""Surya OCR (>= 0.17) implementation. GPU-accelerated cuando hay CUDA disponible.

Lazy-loads detection, foundation and recognition predictors on first use; reuses
them across requests via process-wide singleton.
"""
from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import ClassVar

import pymupdf
from PIL import Image

from backend.core.ocr import PageText
from backend.settings import settings

log = logging.getLogger(__name__)

_PYMUPDF_BASE_DPI = 72  # PyMuPDF Matrix(1,1) renders at 72 dpi


class SuryaOCRProvider:
    _instance: ClassVar["SuryaOCRProvider | None"] = None
    _instance_lock: ClassVar[Lock] = Lock()

    @classmethod
    def instance(cls) -> "SuryaOCRProvider":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._det_predictor = None
        self._rec_predictor = None
        self._load_lock = Lock()
        # Surya predictors comparten estado interno (batches, buffers).
        # Llamarlos concurrentemente desde varios asyncio.to_thread corrompe
        # tensores y dispara CUDA asserts. Serializa cada extract_text en GPU.
        self._inference_lock = Lock()

    # ── API pública ───────────────────────────────────────────────────────

    def extract_text(self, pdf_path: Path) -> list[PageText]:
        self._ensure_loaded()
        images = self._render_pages(pdf_path)
        if not images:
            return []
        log.info(
            "OCR Surya: %d página(s) en %s (dpi=%d, langs=%s)",
            len(images),
            pdf_path.name,
            settings.ocr_dpi,
            settings.ocr_languages,
        )
        with self._inference_lock:
            predictions = self._rec_predictor(
                images, det_predictor=self._det_predictor, sort_lines=True
            )
        return [
            (page_idx, _join_lines(prediction))
            for page_idx, prediction in enumerate(predictions, start=1)
        ]

    # ── Internos ──────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        if self._is_loaded():
            return
        with self._load_lock:
            if self._is_loaded():
                return
            log.info("Cargando predictores Surya (primera vez tarda más)...")
            from surya.detection import DetectionPredictor
            from surya.foundation import FoundationPredictor
            from surya.recognition import RecognitionPredictor

            device = _resolve_device(settings.ocr_device)
            kwargs = {"device": device} if device else {}

            self._det_predictor = DetectionPredictor(**kwargs)
            foundation = FoundationPredictor(**kwargs)
            self._rec_predictor = RecognitionPredictor(foundation)
            log.info("Predictores Surya listos (device=%s).", device or "default")

    def _is_loaded(self) -> bool:
        return self._det_predictor is not None and self._rec_predictor is not None

    def _render_pages(self, pdf_path: Path) -> list[Image.Image]:
        zoom = settings.ocr_dpi / _PYMUPDF_BASE_DPI
        matrix = pymupdf.Matrix(zoom, zoom)
        images: list[Image.Image] = []
        with pymupdf.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                images.append(
                    Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                )
        return images


def _join_lines(prediction) -> str:
    """Concatenates Surya text_lines into a single string preserving order."""
    lines = getattr(prediction, "text_lines", None) or []
    return "\n".join(line.text for line in lines if getattr(line, "text", "")).strip()


def _resolve_device(device: str) -> str | None:
    """`auto` → None (deja que Surya/torch elijan); explícito se pasa tal cual."""
    if device == "auto":
        return None
    return device

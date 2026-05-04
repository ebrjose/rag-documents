#!/usr/bin/env python3
"""Importador masivo de Disposiciones Administrativas.

Lee PDFs desde un directorio, los sube en lotes al endpoint POST /api/documents,
y opcionalmente bloquea hasta que el backend termine de procesarlos.

El backend dedupe por SHA-256, así que correr esto varias veces es seguro: los
duplicados se rechazan con `Documento ya indexado (mismo contenido)`.

Uso típico:
    # Solo subir, sin esperar procesamiento (recomendado para corpus grande)
    uv run python scripts/import_das.py

    # Subir y esperar a que todo termine de indexarse
    uv run python scripts/import_das.py --wait

    # Probar primero con 10 archivos
    uv run python scripts/import_das.py --limit 10 --wait

    # Apuntando a otro host
    uv run python scripts/import_das.py --api http://192.168.100.110:8000

Variables de entorno (opcionales):
    RAG_API_URL: equivalente a --api
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

DEFAULT_API = os.environ.get("RAG_API_URL", "http://localhost:8000")
DEFAULT_DIR = "administrative_regulations"
MAX_BATCH = 20  # tope del backend (settings.max_files_per_upload)
DEFAULT_BATCH = 15  # margen frente al tope

POLL_INTERVAL_SECONDS = 5
UPLOAD_TIMEOUT_SECONDS = 300


def main() -> int:
    args = _parse_args()
    api = args.api.rstrip("/")
    pdf_dir = Path(args.dir)
    if not pdf_dir.is_dir():
        print(f"ERROR: directorio no existe: {pdf_dir}", file=sys.stderr)
        return 2

    pdfs = sorted(p for p in pdf_dir.glob("*.pdf") if p.is_file())
    if args.limit:
        pdfs = pdfs[: args.limit]
    if not pdfs:
        print(f"No hay PDFs en {pdf_dir}")
        return 0

    print(f"Backend:        {api}")
    print(f"Directorio:     {pdf_dir} ({len(pdfs)} PDFs)")
    print(f"Tamaño de lote: {args.batch}")
    print()

    if not _check_backend_alive(api):
        print(f"ERROR: backend no responde en {api}/api/health", file=sys.stderr)
        return 3

    indexed_filenames = _fetch_existing_filenames(api)
    pending = [p for p in pdfs if p.name not in indexed_filenames]
    print(f"  Ya en sistema (por nombre): {len(pdfs) - len(pending)}")
    print(f"  A intentar subir:           {len(pending)}")
    print()

    if not pending:
        print("Nada que subir.")
        return 0

    if not args.yes:
        resp = input(f"¿Subir {len(pending)} archivos en lotes de {args.batch}? [y/N] ")
        if resp.strip().lower() not in ("y", "s", "yes", "si", "sí"):
            print("Cancelado.")
            return 0

    stats = _upload_in_batches(api, pending, args.batch)
    _print_upload_summary(stats)

    if args.wait and stats["accepted"]:
        return _wait_for_processing(api, stats["accepted"])
    return 0


# ── helpers ──────────────────────────────────────────────────────────────────


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bulk import de DAs al backend RAG.")
    p.add_argument("--dir", default=DEFAULT_DIR, help="Directorio con los PDFs")
    p.add_argument("--api", default=DEFAULT_API, help="URL base del backend")
    p.add_argument(
        "--batch",
        type=int,
        default=DEFAULT_BATCH,
        help=f"Archivos por POST (máx {MAX_BATCH})",
    )
    p.add_argument("--limit", type=int, help="Subir solo los primeros N (debug)")
    p.add_argument(
        "--wait", action="store_true", help="Bloquear hasta terminar el procesamiento"
    )
    p.add_argument("--yes", "-y", action="store_true", help="No pedir confirmación")
    args = p.parse_args()
    if args.batch > MAX_BATCH:
        print(f"ERROR: --batch {args.batch} excede el máximo ({MAX_BATCH})", file=sys.stderr)
        sys.exit(2)
    if args.batch < 1:
        print("ERROR: --batch debe ser >= 1", file=sys.stderr)
        sys.exit(2)
    return args


def _check_backend_alive(api: str) -> bool:
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{api}/api/health")
            return r.status_code == 200
    except Exception:
        return False


def _fetch_existing_filenames(api: str) -> set[str]:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{api}/api/documents")
        r.raise_for_status()
        return {d["filename"] for d in r.json()}


def _upload_in_batches(api: str, files: list[Path], batch_size: int) -> dict:
    accepted = 0
    rejected = 0
    failed = 0
    start = time.time()
    total = len(files)

    with httpx.Client(timeout=UPLOAD_TIMEOUT_SECONDS) as client:
        for i in range(0, total, batch_size):
            batch = files[i : i + batch_size]
            multipart = [
                ("files", (p.name, p.read_bytes(), "application/pdf")) for p in batch
            ]
            try:
                r = client.post(f"{api}/api/documents", files=multipart)
                r.raise_for_status()
                results = r.json().get("results", [])
                acc = sum(1 for x in results if x.get("accepted"))
                rej = sum(1 for x in results if not x.get("accepted"))
                accepted += acc
                rejected += rej
            except httpx.HTTPError as e:
                failed += len(batch)
                print(f"  ! lote {i // batch_size + 1}: {e}", file=sys.stderr)
                continue

            done = i + len(batch)
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0
            eta = (total - done) / rate if rate > 0 else 0
            print(
                f"  [{done:>4}/{total}] +{acc} ok, +{rej} rechazados  "
                f"| {rate:5.1f} arch/s  | eta {_fmt_seconds(eta):>7}"
            )

    return {
        "accepted": accepted,
        "rejected": rejected,
        "failed": failed,
        "elapsed": time.time() - start,
    }


def _print_upload_summary(stats: dict) -> None:
    print()
    print("Uploads:")
    print(f"  aceptados:           {stats['accepted']}")
    print(f"  rechazados (dedup):  {stats['rejected']}")
    print(f"  fallidos (HTTP):     {stats['failed']}")
    print(f"  tiempo total:        {_fmt_seconds(stats['elapsed'])}")
    print()


def _wait_for_processing(api: str, recently_uploaded: int) -> int:
    print("Esperando procesamiento (Ctrl-C para abortar el wait)...")
    start = time.time()
    last_indexed = -1
    try:
        with httpx.Client(timeout=30) as client:
            while True:
                r = client.get(f"{api}/api/documents")
                r.raise_for_status()
                docs = r.json()
                counts = _count_by_status(docs)
                in_flight = (
                    counts["pending"] + counts["processing"] + counts["ocr_processing"]
                )
                elapsed = time.time() - start
                if counts["indexed"] != last_indexed:
                    print(
                        f"  T={_fmt_seconds(elapsed):>7}  "
                        f"indexed={counts['indexed']}  "
                        f"pending+procesando={in_flight}  "
                        f"error={counts['error']}  "
                        f"req_ocr={counts['requires_ocr']}"
                    )
                    last_indexed = counts["indexed"]
                if in_flight == 0:
                    print("\nProcesamiento completo.")
                    return 0
                time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nWait interrumpido. La cola del backend sigue procesando.")
        return 1


def _count_by_status(docs: list[dict]) -> dict[str, int]:
    counts = {
        "pending": 0,
        "processing": 0,
        "ocr_processing": 0,
        "indexed": 0,
        "error": 0,
        "requires_ocr": 0,
    }
    for d in docs:
        counts[d["status"]] = counts.get(d["status"], 0) + 1
    return counts


def _fmt_seconds(s: float) -> str:
    if s < 60:
        return f"{s:.0f}s"
    if s < 3600:
        return f"{s / 60:.1f}m"
    return f"{s / 3600:.1f}h"


if __name__ == "__main__":
    sys.exit(main())

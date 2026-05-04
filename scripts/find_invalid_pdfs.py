"""Scan all PDFs and report invalid/corrupt ones."""
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

ROOT = Path("administrative_regulations")
OUT = Path("scripts/invalid_pdfs.txt")

pdfs = sorted(p for p in ROOT.iterdir() if p.suffix.lower() == ".pdf")

invalid = []  # (path, reason, category)

for i, path in enumerate(pdfs, 1):
    if i % 500 == 0:
        print(f"  scanned {i}/{len(pdfs)}...", flush=True)
    try:
        with open(path, "rb") as f:
            header = f.read(5)
        if header != b"%PDF-":
            invalid.append((path.name, f"bad header: {header!r}", "fake/corrupt"))
            continue
        reader = PdfReader(str(path), strict=False)
        n = len(reader.pages)
        if n == 0:
            invalid.append((path.name, "0 pages", "empty"))
    except PdfReadError as e:
        invalid.append((path.name, f"PdfReadError: {str(e)[:100]}", "unreadable"))
    except Exception as e:
        invalid.append((path.name, f"{type(e).__name__}: {str(e)[:100]}", "error"))

by_cat = {}
for name, reason, cat in invalid:
    by_cat.setdefault(cat, []).append((name, reason))

print(f"\nTotal PDFs scanned: {len(pdfs)}")
print(f"Total invalid: {len(invalid)}")
print(f"Valid: {len(pdfs) - len(invalid)}")
print()
for cat, items in sorted(by_cat.items()):
    print(f"  [{cat}]: {len(items)}")

with OUT.open("w") as f:
    f.write(f"Total scanned: {len(pdfs)}\n")
    f.write(f"Total invalid: {len(invalid)}\n\n")
    for cat, items in sorted(by_cat.items()):
        f.write(f"=== {cat} ({len(items)}) ===\n")
        for name, reason in sorted(items):
            f.write(f"{name}\t{reason}\n")
        f.write("\n")

print(f"\nFull list saved to: {OUT}")

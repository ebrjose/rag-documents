"""Sample PDFs to estimate native-vs-scanned ratio."""
import random
import sys
from pathlib import Path

from pypdf import PdfReader

random.seed(42)

ROOT = Path("administrative_regulations")
SAMPLE_SIZE = 50
MIN_CHARS_PER_PAGE = 50

pdfs = [p for p in ROOT.iterdir() if p.suffix.lower() == ".pdf"]
sample = random.sample(pdfs, min(SAMPLE_SIZE, len(pdfs)))

native, scanned, errors, empty = 0, 0, 0, 0
totals = {"pages": 0, "chars": 0}
errors_list = []

for path in sample:
    try:
        reader = PdfReader(str(path))
        n_pages = len(reader.pages)
        if n_pages == 0:
            empty += 1
            continue
        text = ""
        for page in reader.pages[:3]:
            text += page.extract_text() or ""
        totals["pages"] += n_pages
        totals["chars"] += len(text)
        avg_chars = len(text) / min(n_pages, 3)
        if avg_chars >= MIN_CHARS_PER_PAGE:
            native += 1
        else:
            scanned += 1
    except Exception as e:
        errors += 1
        errors_list.append((path.name, str(e)[:80]))

print(f"Sample size: {len(sample)}")
print(f"Native (>{MIN_CHARS_PER_PAGE} chars/page avg): {native}")
print(f"Scanned/empty text: {scanned}")
print(f"Empty PDFs: {empty}")
print(f"Errors: {errors}")
print(f"Total pages in sample: {totals['pages']}")
print(f"Avg pages per doc: {totals['pages'] / max(len(sample) - errors - empty, 1):.1f}")
if errors_list:
    print("\nFirst errors:")
    for name, err in errors_list[:5]:
        print(f"  {name}: {err}")

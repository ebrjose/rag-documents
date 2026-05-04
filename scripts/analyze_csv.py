"""Analyze the documents_administrative_regulation.csv catalog."""
import csv
from collections import Counter
from pathlib import Path

CSV = Path("documents_administrative_regulation.csv")
PDF_DIR = Path("administrative_regulations")

rows = list(csv.DictReader(CSV.open()))
print(f"Total rows: {len(rows)}")
print()

# Concept distribution (this looks like status: NO UBICADO, etc)
concepts = Counter(r["concept"] for r in rows)
print("=== concept (status?) ===")
for c, n in concepts.most_common(15):
    print(f"  {n:>5}  {c[:80]!r}")
print()

# is_reserved
reserved = Counter(r["is_reserved"] for r in rows)
print(f"=== is_reserved ===")
for v, n in reserved.most_common():
    print(f"  {n:>5}  {v}")
print()

# Year distribution
years = Counter(r["year"] for r in rows if r["year"])
print(f"=== year (top 20) ===  total with year: {sum(years.values())}/{len(rows)}")
for y, n in sorted(years.items())[:20]:
    print(f"  {y}: {n}")
print(f"  ... last 5:")
for y, n in sorted(years.items())[-5:]:
    print(f"  {y}: {n}")
print()

# How many have a file path
with_file = [r for r in rows if r["file"].strip()]
without_file = [r for r in rows if not r["file"].strip()]
print(f"=== file column ===")
print(f"  with file: {len(with_file)}")
print(f"  without file: {len(without_file)}")
print()
if with_file:
    print("  sample file paths:")
    for r in with_file[:5]:
        print(f"    {r['nomenclature']}: {r['file']!r}")
print()

# Cross-check: do file paths in CSV match actual files?
actual_pdfs = {p.name for p in PDF_DIR.iterdir() if p.suffix.lower() in (".pdf", ".docx")}
print(f"=== files on disk vs catalog ===")
print(f"  files on disk: {len(actual_pdfs)}")

referenced = set()
missing_on_disk = []
for r in with_file:
    fname = Path(r["file"]).name
    referenced.add(fname)
    if fname not in actual_pdfs:
        missing_on_disk.append((r["nomenclature"], fname))

print(f"  files referenced by CSV: {len(referenced)}")
print(f"  CSV refs missing on disk: {len(missing_on_disk)}")
print(f"  files on disk NOT in CSV: {len(actual_pdfs - referenced)}")
if missing_on_disk[:5]:
    print("  sample missing:")
    for nom, fn in missing_on_disk[:5]:
        print(f"    {nom} -> {fn}")

# Pages and size stats for those with files
pages_vals = [int(r["pages"]) for r in rows if r["pages"].strip().isdigit()]
size_vals = [float(r["size_kb"]) for r in rows if r["size_kb"].strip()]
if pages_vals:
    print(f"\n=== pages ===  count={len(pages_vals)}")
    print(f"  total pages: {sum(pages_vals):,}")
    print(f"  avg: {sum(pages_vals)/len(pages_vals):.1f}")
    print(f"  max: {max(pages_vals)}")
if size_vals:
    print(f"\n=== size_kb ===  count={len(size_vals)}")
    print(f"  total: {sum(size_vals)/1024:.1f} MB")
    print(f"  avg: {sum(size_vals)/len(size_vals):.1f} KB")

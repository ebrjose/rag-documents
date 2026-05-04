from pathlib import Path
from bs4 import BeautifulSoup
from markdownify import markdownify as md

src = Path("Designing a Production-Grade RAG Architecture _ by Matt Bentley _ Level Up Coding.html")
out = Path("Designing a Production-Grade RAG Architecture.md")
OLD_ASSETS = "./Designing a Production-Grade RAG Architecture _ by Matt Bentley _ Level Up Coding_files"
NEW_ASSETS = "./assets"

soup = BeautifulSoup(src.read_text(encoding="utf-8"), "html.parser")
article = soup.find("article")

for tag in article.find_all(["script", "style", "noscript", "svg", "button"]):
    tag.decompose()

# Rewrite local asset paths to a space-free folder so Markdown previewers resolve them.
for el in article.find_all(["img", "a"]):
    attr = "src" if el.name == "img" else "href"
    val = el.get(attr)
    if val and val.startswith(OLD_ASSETS):
        el[attr] = NEW_ASSETS + val[len(OLD_ASSETS):]

# Medium wraps actual images in <picture><source><img>; keep the <img> with the highest-res src.
for pic in article.find_all("picture"):
    img = pic.find("img")
    if img:
        pic.replace_with(img)

title_el = soup.find("h1")
title = title_el.get_text(strip=True) if title_el else "Article"

# Drop the duplicate H1 inside the article (we re-add the title at the top).
for h1 in article.find_all("h1"):
    h1.decompose()

body_md = md(str(article), heading_style="ATX")

NOISE_EXACT = {
    "top highlight",
    "member-only story",
    "press enter or click to view image in full size",
    "press enter or click to view image in full size.",
    "·",
    "share",
    "listen",
    "follow",
}
NOISE_CONTAINS = (
    "this member-only story is on us",
    "upgrade to access all of medium",
)

lines = [ln.rstrip() for ln in body_md.splitlines()]
cleaned: list[str] = []
blank = 0
for ln in lines:
    low = ln.strip().lower()
    if low in NOISE_EXACT or any(p in low for p in NOISE_CONTAINS):
        continue
    if not ln.strip():
        blank += 1
        if blank <= 1:
            cleaned.append("")
    else:
        blank = 0
        cleaned.append(ln)

out.write_text(f"# {title}\n\n" + "\n".join(cleaned).strip() + "\n", encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size} bytes)")

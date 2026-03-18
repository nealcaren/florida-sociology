"""Render cropped PDF evidence images for each documented change."""

import argparse
import io
import json
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image


PROJECT_ROOT = Path(__file__).parent.parent
ORIGINAL_PDF = PROJECT_ROOT / "IntroductiontoSociology3e-WEB_9QTqRGQ.pdf"
FLORIDA_PDF = PROJECT_ROOT / "the-new-introduction-to-sociology-textbook.pdf"
EVIDENCE_DIR = PROJECT_ROOT / "img" / "evidence"
DATA_DIR = PROJECT_ROOT / "data"

# Padding around matched text region, in PDF points (1/72 inch)
PAD_PT = 30
# Render resolution
DPI = 150
# WebP quality
WEBP_QUALITY = 80
# Search prefix length — first N chars of text used for page.search_for()
SEARCH_PREFIX_LEN = 80


def normalize_quotes(text: str) -> str:
    """Normalize curly/smart quotes to straight quotes for PDF search."""
    return (text
        .replace("\u2018", "'").replace("\u2019", "'")   # single curly
        .replace("\u201c", '"').replace("\u201d", '"')    # double curly
        .replace("\u2013", "-").replace("\u2014", "-")    # en/em dash
        .replace("\u2026", "..."))                        # ellipsis


def curlify_quotes(text: str) -> str:
    """Convert straight quotes to curly quotes (PDF-style).

    Uses a simple heuristic: quote after space/start = opening, otherwise closing.
    """
    import re
    # Single quotes: after word char = closing (it's → it's), otherwise opening
    text = re.sub(r"(?<=\w)'", "\u2019", text)
    text = re.sub(r"'", "\u2018", text)
    # Double quotes
    text = re.sub(r'(?<=\w)"', "\u201d", text)
    text = re.sub(r'"', "\u201c", text)
    return text


def make_search_prefix(text: str) -> str:
    """Extract a search prefix from text, truncating at a word boundary.

    Skips editorial brackets and title lines before body text.
    Normalizes quotes for PDF search compatibility.
    """
    # Skip editorial/summary text that won't be in the PDF
    if text.startswith("["):
        return ""

    # If text has Title\nBody format, search for the body part
    if "\n" in text[:100]:
        body = text.split("\n", 1)[1].lstrip()
        # But if body also starts with [, it's editorial
        if body.startswith("["):
            return ""
        text = body

    text = normalize_quotes(text)

    if len(text) <= SEARCH_PREFIX_LEN:
        return text
    prefix = text[:SEARCH_PREFIX_LEN]
    last_space = prefix.rfind(" ")
    if last_space > 40:
        prefix = prefix[:last_space]
    return prefix


def _search_all_pages(doc: fitz.Document, query: str) -> list[dict] | None:
    """Search for query across all pages, return first match."""
    for page_num in range(len(doc)):
        rects = doc[page_num].search_for(query)
        if rects:
            return [{"page": page_num, "rects": rects}]
    return None


def find_text_in_pdf(doc: fitz.Document, text: str) -> list[dict]:
    """Search for text across all pages of a PDF.

    Tries multiple strategies: normalized prefix, curly-quote prefix,
    and progressively shorter prefixes.

    Returns list of {"page": int, "rects": [fitz.Rect, ...]} sorted by page number.
    Only returns matches for the first page where text is found (lowest page number).
    """
    prefix = make_search_prefix(text)
    if not prefix.strip():
        return []

    # Strategy 1: straight-quote normalized prefix (default)
    result = _search_all_pages(doc, prefix)
    if result:
        return result

    # Strategy 2: try curly-quote version of the prefix
    curly_prefix = curlify_quotes(prefix)
    if curly_prefix != prefix:
        result = _search_all_pages(doc, curly_prefix)
        if result:
            return result

    # Strategy 3: shorter prefix (~40 chars) with both quote styles
    body = text.split("\n")[-1] if "\n" in text else text
    for transform in [normalize_quotes, curlify_quotes]:
        short = transform(body)[:50]
        last_space = short.rfind(" ")
        if last_space > 20:
            short = short[:last_space]
        if short.strip():
            result = _search_all_pages(doc, short)
            if result:
                return result

    # Strategy 4: for pipe-separated text (table rows), try each segment
    if "|" in text:
        for segment in text.split("|"):
            segment = segment.strip()
            if len(segment) > 15:
                for transform in [normalize_quotes, curlify_quotes]:
                    q = transform(segment)[:50]
                    result = _search_all_pages(doc, q)
                    if result:
                        return result

    # Strategy 5: for "term: definition" glossary entries, search the term alone
    if ": " in text[:60] and not text.startswith("["):
        term = text.split(": ", 1)[0].strip()
        if len(term) > 5:
            result = _search_all_pages(doc, term)
            if result:
                return result

    return []


def crop_and_render(
    doc: fitz.Document,
    search_results: list[dict],
    output_path: Path,
) -> bool:
    """Render cropped region around matched text as WebP.

    If text spans two pages, stitches both crops vertically.
    Returns True if image was saved, False on failure.
    """
    if not search_results:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    images = []

    for result in search_results:
        page = doc[result["page"]]
        page_rect = page.rect

        # Union all match rects, then add padding
        union = result["rects"][0]
        for r in result["rects"][1:]:
            union = union | r  # fitz.Rect union operator

        # Expand to full page width with vertical padding
        clip = fitz.Rect(
            page_rect.x0,
            max(page_rect.y0, union.y0 - PAD_PT),
            page_rect.x1,
            min(page_rect.y1, union.y1 + PAD_PT),
        )

        # Render clipped region
        mat = fitz.Matrix(DPI / 72, DPI / 72)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)

    if len(images) == 1:
        final = images[0]
    else:
        # Stitch vertically
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        final = Image.new("RGB", (total_width, total_height), (255, 255, 255))
        y_offset = 0
        for img in images:
            final.paste(img, (0, y_offset))
            y_offset += img.height

    final.save(str(output_path), "WEBP", quality=WEBP_QUALITY)
    return True


def process_chapter(
    chapter_path: Path,
    original_doc: fitz.Document,
    florida_doc: fitz.Document,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Process all changes in a chapter JSON file.

    Returns stats dict: {"matched": int, "skipped": int, "failed": int}
    """
    with open(chapter_path) as f:
        chapter_data = json.load(f)

    ch_num = chapter_data["chapter"]
    ch_dir = EVIDENCE_DIR / f"ch{ch_num:02d}"
    stats = {"matched": 0, "skipped": 0, "failed": 0}

    # Skip removed chapters — their original_text is editorial, not verbatim
    if chapter_data.get("florida_title") is None:
        print(f"  ch{ch_num:02d}: skipped (removed chapter)")
        return stats

    changes = chapter_data.get("changes", [])
    modified = False

    for i, change in enumerate(changes):
        change_type = change.get("type", "")

        # Determine which texts to search in which PDFs
        searches = []  # list of (text, doc, field_page, field_evidence, label)

        original_text = change.get("original_text")
        florida_text = change.get("florida_text")

        if change_type == "moved":
            # Show original location in original PDF, relocated text in Florida PDF
            if original_text:
                searches.append((original_text, original_doc, "original_page", "original_evidence", "original"))
                searches.append((original_text, florida_doc, "florida_page", "florida_evidence", "florida"))
        else:
            if original_text:
                searches.append((original_text, original_doc, "original_page", "original_evidence", "original"))
            if florida_text:
                searches.append((florida_text, florida_doc, "florida_page", "florida_evidence", "florida"))

        for text, doc, page_field, evidence_field, label in searches:
            img_path = ch_dir / f"change_{i}_{label}.webp"
            rel_path = f"img/evidence/ch{ch_num:02d}/change_{i}_{label}.webp"

            # Idempotency: skip if image exists and not forcing
            if not force and img_path.exists():
                if page_field not in change or evidence_field not in change:
                    # Image exists but JSON fields missing — re-search for page number only
                    results = find_text_in_pdf(doc, text)
                    if results:
                        change[page_field] = results[0]["page"] + 1
                        change[evidence_field] = rel_path
                        stats["matched"] += 1
                    else:
                        change[page_field] = None
                        change[evidence_field] = None
                        stats["failed"] += 1
                    modified = True
                else:
                    stats["skipped"] += 1
                continue

            results = find_text_in_pdf(doc, text)

            if not results:
                print(f"  ch{ch_num:02d} change {i} ({label}): NO MATCH")
                change[page_field] = None
                change[evidence_field] = None
                stats["failed"] += 1
                modified = True
                continue

            page_1indexed = results[0]["page"] + 1
            change[page_field] = page_1indexed
            change[evidence_field] = rel_path
            modified = True

            if dry_run:
                print(f"  ch{ch_num:02d} change {i} ({label}): p.{page_1indexed}")
                stats["matched"] += 1
                continue

            ok = crop_and_render(doc, results, img_path)
            if ok:
                stats["matched"] += 1
            else:
                stats["failed"] += 1
                change[evidence_field] = None

        # Set null for fields not searched
        for field in ["original_page", "original_evidence", "florida_page", "florida_evidence"]:
            if field not in change:
                change[field] = None
                modified = True

    if modified and not dry_run:
        with open(chapter_path, "w") as f:
            json.dump(chapter_data, f, indent=2)
            f.write("\n")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Render cropped PDF evidence images for documented changes."
    )
    parser.add_argument(
        "--chapter", type=int,
        help="Process only this chapter (original numbering, 1-21)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report matches without rendering images"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-render even if images already exist"
    )
    args = parser.parse_args()

    # Check PDFs exist
    for pdf_path, label in [(ORIGINAL_PDF, "Original"), (FLORIDA_PDF, "Florida")]:
        if not pdf_path.exists():
            print(f"ERROR: {label} PDF not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)

    print("Opening PDFs...")
    original_doc = fitz.open(str(ORIGINAL_PDF))
    florida_doc = fitz.open(str(FLORIDA_PDF))

    # Collect chapter files to process
    if args.chapter:
        paths = sorted(DATA_DIR.glob(f"ch{args.chapter:02d}.json"))
        if not paths:
            print(f"ERROR: No data file found for chapter {args.chapter}", file=sys.stderr)
            sys.exit(1)
    else:
        paths = sorted(DATA_DIR.glob("ch*.json"))
        paths = [p for p in paths if p.name != "chapters.json"]

    totals = {"matched": 0, "skipped": 0, "failed": 0}

    for path in paths:
        print(f"Processing {path.name}...")
        stats = process_chapter(
            path, original_doc, florida_doc,
            force=args.force, dry_run=args.dry_run,
        )
        for k in totals:
            totals[k] += stats[k]

    original_doc.close()
    florida_doc.close()

    print(f"\nDone: {totals['matched']} matched, {totals['skipped']} skipped, {totals['failed']} failed")
    if not args.dry_run:
        print("Run 'uv run python scripts/build_index.py' to regenerate chapters.json")


if __name__ == "__main__":
    main()

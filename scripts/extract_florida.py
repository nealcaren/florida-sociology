"""Extract clean text from the Florida sociology PDF using layout analysis.

Uses PyMuPDF's block-level extraction with bounding box and font info
to separate body text from headers, sidebars, figure captions, and
page furniture.

Usage:
    uv run python scripts/extract_florida.py
    uv run python scripts/extract_florida.py --chapter 2
    uv run python scripts/extract_florida.py --debug-page 26
"""

import argparse
import re
import sys
from pathlib import Path

import fitz

PROJECT_ROOT = Path(__file__).parent.parent
FLORIDA_PDF = PROJECT_ROOT / "the-new-introduction-to-sociology-textbook.pdf"
OUTPUT_DIR = PROJECT_ROOT / "text" / "florida_v2"

# Layout constants (from PDF analysis)
BODY_FONT_SIZE = 10.6  # Main body text
HEADER_FONT_SIZE = 13.9  # Section headers
BODY_X_MIN = 30  # Left margin of body text
BODY_X_MAX = 45  # Body text starts around x=36
BODY_WIDTH_MIN = 400  # Body text blocks are wide
PAGE_NUM_Y_MIN = 730  # Page numbers are near bottom
HEADER_Y_MAX = 55  # Top header area


def extract_block_text(block: dict) -> str:
    """Extract text from a block dict, joining spans."""
    if "lines" not in block:
        return ""
    text = ""
    for line in block["lines"]:
        line_text = ""
        for span in line["spans"]:
            line_text += span["text"]
        if text and line_text.strip():
            text += "\n"
        text += line_text
    return text


def classify_block(block: dict, page_width: float) -> str:
    """Classify a text block as body, header, figure, page_num, or skip.

    Returns: 'body', 'section_header', 'figure', 'page_num', 'skip'
    """
    if "lines" not in block:
        return "skip"

    x0, y0, x1, y1 = block["bbox"]
    width = x1 - x0

    # Get font info from first span
    first_span = block["lines"][0]["spans"][0]
    font_size = first_span["size"]
    text = extract_block_text(block).strip()

    if not text or len(text) < 2:
        return "skip"

    # Page numbers (bottom of page, short text)
    if y0 > PAGE_NUM_Y_MIN and len(text) < 10:
        return "page_num"

    # Top header/footer
    if y0 < HEADER_Y_MAX and len(text) < 5:
        return "skip"

    # Figure captions: start far right (x > 350) or contain "Figure N.N"
    if x0 > 350 and width < 250:
        return "figure"
    if re.match(r"^Figure\s+\d+\.\d+", text):
        return "figure"

    # Section headers: larger font size
    if font_size > BODY_FONT_SIZE + 1:
        return "section_header"

    # Body text: starts near left margin, wide
    if x0 < BODY_X_MAX and width > BODY_WIDTH_MIN:
        return "body"

    # Narrow body text (some pages have wrapped text around figures)
    if x0 < BODY_X_MAX and width > 250:
        return "body"

    # Table cells or other small blocks
    if width < 200:
        return "skip"

    # Default: include as body
    return "body"


def extract_page(page: fitz.Page, debug: bool = False) -> dict:
    """Extract classified text blocks from a page.

    Returns dict with keys: 'body', 'headers', 'figures'
    """
    blocks_dict = page.get_text("dict")["blocks"]
    pw = page.rect.width

    result = {"body": [], "headers": [], "figures": []}

    for block in blocks_dict:
        cls = classify_block(block, pw)
        text = extract_block_text(block).strip()

        if debug and text:
            x0, y0, x1, y1 = block["bbox"]
            print(f"  [{cls:>14}] ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) w={x1-x0:.0f}: {text[:70]}")

        if cls == "body":
            result["body"].append(text)
        elif cls == "section_header":
            result["headers"].append(text)
        elif cls == "figure":
            result["figures"].append(text)

    return result


def find_chapter_pages(doc: fitz.Document) -> dict[int, tuple[int, int]]:
    """Find the page ranges for each chapter.

    Looks for "Chapter N:" text to identify chapter starts.
    """
    chapters = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        match = re.search(r"Chapter\s+(\d+):\s+", text)
        if match:
            ch_num = int(match.group(1))
            if ch_num not in chapters:
                chapters[ch_num] = page_num

    # Convert to ranges
    ch_nums = sorted(chapters.keys())
    ranges = {}
    for i, ch in enumerate(ch_nums):
        start = chapters[ch]
        end = chapters[ch_nums[i + 1]] if i + 1 < len(ch_nums) else len(doc)
        ranges[ch] = (start, end)

    return ranges


def extract_chapter(doc: fitz.Document, start_page: int, end_page: int,
                    debug: bool = False) -> str:
    """Extract body text for a chapter across its page range."""
    all_body = []

    for page_num in range(start_page, end_page):
        page = doc[page_num]
        if debug:
            print(f"\n--- Page {page_num + 1} ---")
        result = extract_page(page, debug=debug)
        all_body.extend(result["body"])

    # Join blocks with double newline (paragraph breaks)
    # Then join lines within blocks with space (PDF line wrapping)
    paragraphs = []
    for block_text in all_body:
        # Join wrapped lines within a block
        lines = block_text.split("\n")
        joined = " ".join(line.strip() for line in lines if line.strip())
        if joined:
            paragraphs.append(joined)

    return "\n\n".join(paragraphs)


def main():
    parser = argparse.ArgumentParser(description="Extract Florida PDF with layout analysis.")
    parser.add_argument("--chapter", type=int, help="Extract single chapter")
    parser.add_argument("--debug-page", type=int, help="Debug classification for one page")
    args = parser.parse_args()

    if not FLORIDA_PDF.exists():
        print(f"ERROR: {FLORIDA_PDF.name} not found", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(FLORIDA_PDF)
    print(f"Opened: {FLORIDA_PDF.name} ({len(doc)} pages)")

    if args.debug_page:
        page = doc[args.debug_page - 1]
        print(f"\nDebug page {args.debug_page}:")
        extract_page(page, debug=True)
        doc.close()
        return

    # Find chapter boundaries
    ch_ranges = find_chapter_pages(doc)
    print(f"Found {len(ch_ranges)} chapters")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    chapters_to_extract = [args.chapter] if args.chapter else sorted(ch_ranges.keys())

    for ch_num in chapters_to_extract:
        if ch_num not in ch_ranges:
            print(f"  Ch {ch_num}: not found", file=sys.stderr)
            continue

        start, end = ch_ranges[ch_num]
        text = extract_chapter(doc, start, end)

        out_path = OUTPUT_DIR / f"ch{ch_num:02d}.txt"
        out_path.write_text(text, encoding="utf-8")

        para_count = len(text.split("\n\n"))
        word_count = len(text.split())
        print(f"  Ch {ch_num:>2}: pages {start+1}-{end}, {para_count} paragraphs, {word_count} words -> {out_path.name}")

    doc.close()
    print(f"\nDone. Output in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

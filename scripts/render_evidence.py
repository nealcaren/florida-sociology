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


def make_search_prefix(text: str) -> str:
    """Extract a search prefix from text, truncating at a word boundary."""
    if len(text) <= SEARCH_PREFIX_LEN:
        return text
    prefix = text[:SEARCH_PREFIX_LEN]
    last_space = prefix.rfind(" ")
    if last_space > 40:
        prefix = prefix[:last_space]
    return prefix


def find_text_in_pdf(doc: fitz.Document, text: str) -> list[dict]:
    """Search for text across all pages of a PDF.

    Returns list of {"page": int, "rects": [fitz.Rect, ...]} sorted by page number.
    Only returns matches for the first page where text is found (lowest page number).
    """
    prefix = make_search_prefix(text)
    if not prefix.strip():
        return []

    for page_num in range(len(doc)):
        page = doc[page_num]
        rects = page.search_for(prefix)
        if rects:
            return [{"page": page_num, "rects": rects}]

    # Fallback: try shorter prefix if no match found
    if len(prefix) > 40:
        short_prefix = make_search_prefix(text[:50])
        for page_num in range(len(doc)):
            page = doc[page_num]
            rects = page.search_for(short_prefix)
            if rects:
                return [{"page": page_num, "rects": rects}]

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

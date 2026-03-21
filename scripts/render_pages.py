"""Render full PDF pages as WebP images for the companion site thumbnails.

Usage:
    uv run python scripts/render_pages.py
    uv run python scripts/render_pages.py --dpi 100  # lower resolution
    uv run python scripts/render_pages.py --dry-run   # report page counts only
"""

import argparse
import io
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

PROJECT_ROOT = Path(__file__).parent.parent
ORIGINAL_PDF = PROJECT_ROOT / "IntroductiontoSociology3e-WEB_9QTqRGQ.pdf"
FLORIDA_PDF = PROJECT_ROOT / "the-new-introduction-to-sociology-textbook.pdf"
PAGES_DIR = PROJECT_ROOT / "img" / "pages"

DEFAULT_DPI = 100
WEBP_QUALITY = 60


def render_pdf_pages(pdf_path: Path, output_dir: Path, dpi: int, dry_run: bool = False) -> int:
    doc = fitz.open(pdf_path)
    page_count = len(doc)

    if dry_run:
        print(f"  {pdf_path.name}: {page_count} pages")
        doc.close()
        return page_count

    output_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(page_count):
        out_path = output_dir / f"page_{page_num + 1:03d}.webp"
        if out_path.exists():
            continue

        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        img.save(out_path, "WEBP", quality=WEBP_QUALITY)

        if (page_num + 1) % 50 == 0:
            print(f"    ... rendered {page_num + 1}/{page_count}")

    doc.close()
    return page_count


def main():
    parser = argparse.ArgumentParser(description="Render PDF pages as WebP images.")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help=f"Render resolution (default: {DEFAULT_DPI})")
    parser.add_argument("--dry-run", action="store_true", help="Report page counts only")
    args = parser.parse_args()

    for label, pdf_path in [("original", ORIGINAL_PDF), ("florida", FLORIDA_PDF)]:
        if not pdf_path.exists():
            print(f"  WARNING: {pdf_path.name} not found, skipping {label}", file=sys.stderr)
            continue

        output_dir = PAGES_DIR / label
        count = render_pdf_pages(pdf_path, output_dir, dpi=args.dpi, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"  {label}: rendered {count} pages to {output_dir}/")

    if not args.dry_run:
        print(f"\nDone. Page images in {PAGES_DIR}/")


if __name__ == "__main__":
    main()

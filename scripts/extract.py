"""Extract text from OpenStax and Florida sociology PDFs, split by chapter."""

import re
import sys
from pathlib import Path

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def clean_text(text: str) -> str:
    """Remove common PDF artifacts: page numbers, headers, footers."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip standalone page numbers
        if re.match(r"^\d+$", stripped):
            continue
        # Skip common OpenStax footer
        if "Access for free at openstax.org" in stripped:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def split_chapters_original(text: str) -> dict[int, str]:
    """Split OpenStax original text using 'CHAPTER OUTLINE' markers.

    Each chapter starts with 'CHAPTER OUTLINE' followed by section numbers
    like '1.1', '2.1', etc. We derive the chapter number from the first
    section number after the marker.
    """
    pattern = r"CHAPTER OUTLINE\n"
    matches = list(re.finditer(pattern, text))

    if not matches:
        print("WARNING: No CHAPTER OUTLINE headings found!", file=sys.stderr)
        return {}

    chapters = {}
    for i, match in enumerate(matches):
        # Look ahead for the first section number to determine chapter
        lookahead = text[match.end():match.end() + 200]
        sec_match = re.search(r"(\d+)\.\d+\s", lookahead)
        if not sec_match:
            continue
        chapter_num = int(sec_match.group(1))

        # Chapter starts a bit before CHAPTER OUTLINE (include the figure caption)
        # Find the FIGURE line that precedes this
        preceding = text[max(0, match.start() - 500):match.start()]
        fig_match = re.search(r"(FIGURE\s+\d+\.\d+)", preceding)
        if fig_match:
            start = max(0, match.start() - 500) + fig_match.start()
        else:
            start = match.start()

        end = matches[i + 1].start() - 500 if i + 1 < len(matches) else len(text)
        # For end, find the start of the next chapter's figure
        if i + 1 < len(matches):
            next_preceding = text[max(0, matches[i + 1].start() - 500):matches[i + 1].start()]
            next_fig = re.search(r"(FIGURE\s+\d+\.\d+)", next_preceding)
            if next_fig:
                end = max(0, matches[i + 1].start() - 500) + next_fig.start()
            else:
                end = matches[i + 1].start()

        chapters[chapter_num] = text[start:end].strip()

    return chapters


def split_chapters_florida(text: str) -> dict[int, str]:
    """Split Florida version text using 'Chapter N: Title' headings.

    The Florida version has 12 chapters with format 'Chapter N: Title'.
    """
    pattern = r"\nChapter\s+(\d+):\s+[^\n]+"
    matches = list(re.finditer(pattern, text))

    if not matches:
        print("WARNING: No 'Chapter N:' headings found!", file=sys.stderr)
        return {}

    chapters = {}
    for i, match in enumerate(matches):
        chapter_num = int(match.group(1))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapters[chapter_num] = text[start:end].strip()

    return chapters


def split_sections(chapter_text: str, chapter_num: int) -> dict[str, str]:
    """Split a chapter into sections using 'N.N' headings."""
    pattern = rf"(?:^|\n)({chapter_num}\.\d+\s+[^\n]+)"
    matches = list(re.finditer(pattern, chapter_text))

    if not matches:
        return {f"{chapter_num}.0": chapter_text}

    sections = {}
    for i, match in enumerate(matches):
        # Extract section number from heading
        sec_match = re.match(rf"({chapter_num}\.\d+)", match.group(1))
        sec_id = sec_match.group(1) if sec_match else f"{chapter_num}.{i}"
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(chapter_text)
        sections[sec_id] = chapter_text[start:end].strip()

    return sections


def save_chapters(chapters: dict[int, str], output_dir: Path) -> None:
    """Save each chapter to a numbered text file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for num, text in sorted(chapters.items()):
        path = output_dir / f"ch{num:02d}.txt"
        path.write_text(text, encoding="utf-8")
        line_count = len(text.split("\n"))
        print(f"  ch{num:02d}.txt: {line_count} lines")


def main():
    project_root = Path(__file__).parent.parent

    pdfs = {
        "original": project_root / "IntroductiontoSociology3e-WEB_9QTqRGQ.pdf",
        "florida": project_root / "the-new-introduction-to-sociology-textbook.pdf",
    }

    for label, pdf_path in pdfs.items():
        print(f"\nExtracting: {label} ({pdf_path.name})")
        if not pdf_path.exists():
            print(f"  ERROR: File not found: {pdf_path}", file=sys.stderr)
            continue

        raw_text = extract_text(str(pdf_path))
        print(f"  Raw text: {len(raw_text)} characters")

        cleaned = clean_text(raw_text)
        if label == "original":
            chapters = split_chapters_original(cleaned)
        else:
            chapters = split_chapters_florida(cleaned)
        print(f"  Found {len(chapters)} chapters: {sorted(chapters.keys())}")

        output_dir = project_root / "text" / label
        save_chapters(chapters, output_dir)

        # Also save section-level splits
        sections_dir = project_root / "text" / f"{label}_sections"
        sections_dir.mkdir(parents=True, exist_ok=True)
        for num, ch_text in sorted(chapters.items()):
            sections = split_sections(ch_text, num)
            for sec_id, sec_text in sections.items():
                sec_path = sections_dir / f"ch{num:02d}_s{sec_id}.txt"
                sec_path.write_text(sec_text, encoding="utf-8")
            print(f"  ch{num:02d}: {len(sections)} sections")

    print("\nDone. Verify output in text/original/ and text/florida/")


if __name__ == "__main__":
    main()

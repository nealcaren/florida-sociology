"""Utilities for parsing extracted textbook text into paragraphs."""

import re


def clean_text(text: str) -> str:
    """Clean OCR artifacts and normalize whitespace in extracted text."""
    lines = text.split("\n")
    cleaned = []
    skip_until_blank = False
    stop_processing = False

    for line in lines:
        stripped = line.strip()

        # Stop at back-matter sections (key terms, references, etc.)
        if stripped in ("Key Terms", "KEY TERMS", "References", "REFERENCES",
                        "Section Summary", "SECTION SUMMARY",
                        "Further Research", "FURTHER RESEARCH",
                        "Short Answer", "SHORT ANSWER"):
            stop_processing = True
        if stop_processing:
            continue

        # Skip figure captions (both "FIGURE 2.1 ..." and "Figure 2.1 ...")
        # These can span multiple lines, so skip until blank line
        if re.match(r"^(?:FIGURE|Figure)\s+\d+\.\d+\s", stripped):
            skip_until_blank = True
            continue

        # Skip CHAPTER OUTLINE blocks (header + following section list)
        if stripped == "CHAPTER OUTLINE":
            skip_until_blank = True
            continue

        # Skip LEARNING OBJECTIVES blocks
        if stripped in ("LEARNING OBJECTIVES", "Learning Objectives"):
            skip_until_blank = True
            continue

        if skip_until_blank:
            if stripped == "":
                skip_until_blank = False
            continue

        # Skip bullet-only lines (lone bullet points from learning objectives)
        if stripped == "•":
            continue

        # Skip page headers like "1.4 • Why Study Sociology?" or "2 • Sociological Research"
        if re.match(r"^\d+(\.\d+)?\s*[•·]\s", stripped):
            continue

        # Skip "Chapter N: Title" lines from Florida PDF
        if re.match(r"^Chapter\s+\d+:", stripped):
            continue

        cleaned.append(stripped)

    text = "\n".join(cleaned)
    # Normalize multiple spaces to single
    text = re.sub(r"  +", " ", text)
    return text.strip()


def detect_section_header(line: str) -> str | None:
    """Detect if a line is a section header. Returns section ID or None.

    Matches patterns like '2.1 Title' or '14.2 Title'.
    Also matches 'INTRODUCTION' / 'Introduction' as section 'intro'.
    """
    stripped = line.strip()

    if stripped.upper() == "INTRODUCTION":
        return "intro"

    match = re.match(r"^(\d+\.\d+)\s+[A-Z]", stripped)
    if match:
        return match.group(1)

    return None


def split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs, joining broken lines within paragraphs.

    Paragraphs are separated by blank lines (double newline).
    Within a paragraph, single newlines are treated as line breaks
    from PDF extraction and joined with spaces.
    """
    # Split on blank lines
    raw_paragraphs = re.split(r"\n\s*\n", text)

    result = []
    for para in raw_paragraphs:
        # Join broken lines within paragraph
        joined = " ".join(line.strip() for line in para.split("\n") if line.strip())
        if joined:
            result.append(joined)

    return result

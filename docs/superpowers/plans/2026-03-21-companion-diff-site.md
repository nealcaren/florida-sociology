# Companion Diff Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-text two-column comparison site showing both textbook versions side by side, with diff highlighting, margin page thumbnails, and moved-text annotations.

**Architecture:** Python alignment script produces `data/aligned/ch{NN}.json` from existing extracted text files and change data. A separate script renders full PDF pages as WebP images. A new static HTML page (`compare.html`) with its own JS/CSS loads the aligned data and renders a two-column/one-column hybrid layout.

**Tech Stack:** Python 3.12+ (difflib, PyMuPDF/Pillow), vanilla JS, CSS Grid, no build step.

**Spec:** `docs/superpowers/specs/2026-03-21-companion-diff-site-design.md`

---

## Phase 1: Data Pipeline

### Task 1: Chapter Mapping Module

**Files:**
- Create: `scripts/chapter_map.py`
- Test: `scripts/test_chapter_map.py`

This module encodes the original→Florida chapter mapping from the spec. Every other script imports it.

- [ ] **Step 1: Write the test file**

```python
# scripts/test_chapter_map.py
"""Tests for chapter mapping module."""
from chapter_map import CHAPTER_MAP, get_original_text_files, get_florida_text_file

def test_total_aligned_chapters():
    """17 aligned files: 21 original minus 4 merged-away stubs."""
    assert len(CHAPTER_MAP) == 17

def test_removed_chapters_have_no_florida():
    for ch in [8, 9, 10, 11, 12]:
        entry = CHAPTER_MAP[ch]
        assert entry["florida_text"] is None
        assert entry["type"] == "removed"

def test_merged_chapters():
    ch03 = CHAPTER_MAP[3]
    assert ch03["original_texts"] == ["text/original/ch03.txt", "text/original/ch04.txt"]
    assert ch03["florida_text"] == "text/florida/ch03.txt"
    assert ch03["type"] == "merged"

    ch14 = CHAPTER_MAP[14]
    assert ch14["original_texts"] == ["text/original/ch14.txt", "text/original/ch18.txt"]
    assert ch14["florida_text"] == "text/florida/ch09.txt"

    ch15 = CHAPTER_MAP[15]
    assert ch15["original_texts"] == ["text/original/ch15.txt", "text/original/ch16.txt", "text/original/ch17.txt"]
    assert ch15["florida_text"] == "text/florida/ch10.txt"

def test_renumbered_chapters():
    ch05 = CHAPTER_MAP[5]
    assert ch05["original_texts"] == ["text/original/ch05.txt"]
    assert ch05["florida_text"] == "text/florida/ch04.txt"
    assert ch05["type"] == "renumbered"

def test_one_to_one_chapters():
    ch01 = CHAPTER_MAP[1]
    assert ch01["original_texts"] == ["text/original/ch01.txt"]
    assert ch01["florida_text"] == "text/florida/ch01.txt"
    assert ch01["type"] == "matched"

def test_merged_away_stubs_not_in_map():
    for ch in [4, 16, 17, 18]:
        assert ch not in CHAPTER_MAP

def test_get_original_text_files():
    assert get_original_text_files(3) == ["text/original/ch03.txt", "text/original/ch04.txt"]

def test_get_florida_text_file():
    assert get_florida_text_file(3) == "text/florida/ch03.txt"
    assert get_florida_text_file(11) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -m pytest scripts/test_chapter_map.py -v`
Expected: FAIL — `chapter_map` module does not exist yet.

- [ ] **Step 3: Implement the chapter mapping module**

```python
# scripts/chapter_map.py
"""Chapter mapping between original (1-21) and Florida (1-12) textbooks.

The original OpenStax has 21 chapters. Florida restructured to 12:
- 5 chapters removed entirely (8, 9, 10, 11, 12)
- 4 chapters merged into others (4→3, 16→15, 17→15, 18→14)
- Remaining chapters renumbered
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Each entry: chapter_num -> {original_texts, florida_text, type, data_file}
CHAPTER_MAP = {
    1:  {"original_texts": ["text/original/ch01.txt"], "florida_text": "text/florida/ch01.txt",
         "type": "matched", "data_file": "data/ch01.json"},
    2:  {"original_texts": ["text/original/ch02.txt"], "florida_text": "text/florida/ch02.txt",
         "type": "matched", "data_file": "data/ch02.json"},
    3:  {"original_texts": ["text/original/ch03.txt", "text/original/ch04.txt"],
         "florida_text": "text/florida/ch03.txt",
         "type": "merged", "data_file": "data/ch03.json"},
    5:  {"original_texts": ["text/original/ch05.txt"], "florida_text": "text/florida/ch04.txt",
         "type": "renumbered", "data_file": "data/ch05.json"},
    6:  {"original_texts": ["text/original/ch06.txt"], "florida_text": "text/florida/ch07.txt",
         "type": "renumbered", "data_file": "data/ch06.json"},
    7:  {"original_texts": ["text/original/ch07.txt"], "florida_text": "text/florida/ch08.txt",
         "type": "renumbered", "data_file": "data/ch07.json"},
    8:  {"original_texts": ["text/original/ch08.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch08.json"},
    9:  {"original_texts": ["text/original/ch09.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch09.json"},
    10: {"original_texts": ["text/original/ch10.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch10.json"},
    11: {"original_texts": ["text/original/ch11.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch11.json"},
    12: {"original_texts": ["text/original/ch12.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch12.json"},
    13: {"original_texts": ["text/original/ch13.txt"], "florida_text": "text/florida/ch05.txt",
         "type": "renumbered", "data_file": "data/ch13.json"},
    14: {"original_texts": ["text/original/ch14.txt", "text/original/ch18.txt"],
         "florida_text": "text/florida/ch09.txt",
         "type": "merged", "data_file": "data/ch14.json"},
    15: {"original_texts": ["text/original/ch15.txt", "text/original/ch16.txt", "text/original/ch17.txt"],
         "florida_text": "text/florida/ch10.txt",
         "type": "merged", "data_file": "data/ch15.json"},
    19: {"original_texts": ["text/original/ch19.txt"], "florida_text": "text/florida/ch06.txt",
         "type": "renumbered", "data_file": "data/ch19.json"},
    20: {"original_texts": ["text/original/ch20.txt"], "florida_text": "text/florida/ch11.txt",
         "type": "renumbered", "data_file": "data/ch20.json"},
    21: {"original_texts": ["text/original/ch21.txt"], "florida_text": "text/florida/ch12.txt",
         "type": "renumbered", "data_file": "data/ch21.json"},
}

# Chapters that were merged into another chapter (stub → target)
MERGED_AWAY = {4: 3, 16: 15, 17: 15, 18: 14}


def get_original_text_files(chapter: int) -> list[str]:
    """Return list of original text file paths for a chapter."""
    return CHAPTER_MAP[chapter]["original_texts"]


def get_florida_text_file(chapter: int) -> str | None:
    """Return Florida text file path, or None if chapter was removed."""
    return CHAPTER_MAP[chapter]["florida_text"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -m pytest scripts/test_chapter_map.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/chapter_map.py scripts/test_chapter_map.py
git commit -m "feat: add chapter mapping module for original→Florida alignment"
```

---

### Task 2: Text Parsing Utilities

**Files:**
- Create: `scripts/text_parser.py`
- Create: `scripts/test_text_parser.py`

Handles splitting raw chapter text into paragraphs, detecting section headers, and cleaning OCR artifacts. The alignment script depends on this.

- [ ] **Step 1: Write tests**

```python
# scripts/test_text_parser.py
"""Tests for text parsing utilities."""
from text_parser import split_paragraphs, detect_section_header, clean_text

def test_split_paragraphs_basic():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = split_paragraphs(text)
    assert len(result) == 3
    assert result[0] == "First paragraph."
    assert result[2] == "Third paragraph."

def test_split_paragraphs_joins_broken_lines():
    """PDF extraction breaks lines mid-sentence. These should be joined."""
    text = "This is a sentence that was\nbroken across two lines.\n\nNew paragraph here."
    result = split_paragraphs(text)
    assert len(result) == 2
    assert "broken across two lines." in result[0]

def test_detect_section_header():
    assert detect_section_header("2.1 Approaches to Sociological Research") == "2.1"
    assert detect_section_header("2.1   Approaches to Sociological Research ") == "2.1"
    assert detect_section_header("14.2 Some Section Title") == "14.2"
    assert detect_section_header("This is a regular paragraph.") is None
    assert detect_section_header("LEARNING OBJECTIVES") is None

def test_detect_section_header_intro():
    """Lines like 'INTRODUCTION' or 'Introduction' are section 'intro'."""
    assert detect_section_header("INTRODUCTION") == "intro"
    assert detect_section_header("Introduction") == "intro"

def test_clean_text_normalizes_whitespace():
    text = "Hello   world.  Multiple   spaces."
    assert clean_text(text) == "Hello world. Multiple spaces."

def test_clean_text_strips_figure_captions():
    """FIGURE lines from PDF extraction should be removed."""
    text = "FIGURE 2.1 Some caption here.\nActual paragraph text."
    result = clean_text(text)
    assert "FIGURE" not in result
    assert "Actual paragraph text." in result

def test_clean_text_strips_chapter_outline():
    """CHAPTER OUTLINE headers and learning objectives should be removed."""
    text = "CHAPTER OUTLINE\n2.1 Approaches\n2.2 Methods\nActual text."
    result = clean_text(text)
    assert "CHAPTER OUTLINE" not in result

def test_split_paragraphs_skips_empty():
    text = "First.\n\n\n\nSecond."
    result = split_paragraphs(text)
    assert len(result) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -m pytest scripts/test_text_parser.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement text_parser.py**

```python
# scripts/text_parser.py
"""Utilities for parsing extracted textbook text into paragraphs."""

import re


def clean_text(text: str) -> str:
    """Clean OCR artifacts and normalize whitespace in extracted text."""
    lines = text.split("\n")
    cleaned = []
    skip_until_blank = False

    for line in lines:
        stripped = line.strip()

        # Skip figure captions
        if re.match(r"^FIGURE\s+\d+\.\d+\s", stripped):
            continue

        # Skip CHAPTER OUTLINE blocks (header + following section list)
        if stripped == "CHAPTER OUTLINE":
            skip_until_blank = True
            continue

        # Skip LEARNING OBJECTIVES blocks
        if stripped == "LEARNING OBJECTIVES":
            skip_until_blank = True
            continue

        if skip_until_blank:
            if stripped == "":
                skip_until_blank = False
            continue

        # Skip bullet-only lines (lone bullet points from learning objectives)
        if stripped == "•":
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -m pytest scripts/test_text_parser.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/text_parser.py scripts/test_text_parser.py
git commit -m "feat: add text parsing utilities for paragraph splitting and cleanup"
```

---

### Task 3: Paragraph Alignment Core

**Files:**
- Create: `scripts/aligner.py`
- Create: `scripts/test_aligner.py`

The core alignment logic: takes two lists of paragraphs and produces aligned blocks (same/modified/removed/added). Uses difflib.SequenceMatcher.

- [ ] **Step 1: Write tests**

```python
# scripts/test_aligner.py
"""Tests for paragraph alignment logic."""
from aligner import align_paragraphs

def test_identical_paragraphs():
    original = ["Hello world.", "Second paragraph."]
    florida = ["Hello world.", "Second paragraph."]
    blocks = align_paragraphs(original, florida)
    assert len(blocks) == 2
    assert all(b["type"] == "same" for b in blocks)
    assert blocks[0]["text"] == "Hello world."

def test_removed_paragraph():
    original = ["Keep this.", "Remove this.", "Keep this too."]
    florida = ["Keep this.", "Keep this too."]
    blocks = align_paragraphs(original, florida)
    types = [b["type"] for b in blocks]
    assert "same" in types
    assert "removed" in types
    # The removed block should contain "Remove this."
    removed = [b for b in blocks if b["type"] == "removed"]
    assert len(removed) == 1
    assert removed[0]["original_text"] == "Remove this."

def test_added_paragraph():
    original = ["Keep this.", "Keep this too."]
    florida = ["Keep this.", "New content.", "Keep this too."]
    blocks = align_paragraphs(original, florida)
    added = [b for b in blocks if b["type"] == "added"]
    assert len(added) == 1
    assert added[0]["florida_text"] == "New content."

def test_modified_paragraph():
    original = ["The sociologist studied race and class."]
    florida = ["The sociologist studied class and economics."]
    blocks = align_paragraphs(original, florida)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "modified"
    assert blocks[0]["original_text"] == "The sociologist studied race and class."
    assert blocks[0]["florida_text"] == "The sociologist studied class and economics."

def test_all_removed():
    """For removed chapters, all paragraphs appear as removed."""
    original = ["Para one.", "Para two."]
    florida = []
    blocks = align_paragraphs(original, florida)
    assert all(b["type"] == "removed" for b in blocks)

def test_empty_both():
    blocks = align_paragraphs([], [])
    assert blocks == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -m pytest scripts/test_aligner.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement aligner.py**

```python
# scripts/aligner.py
"""Paragraph-level alignment between original and Florida textbook versions."""

from difflib import SequenceMatcher

# Minimum similarity ratio to consider two paragraphs as "modified" vs separate remove+add
SIMILARITY_THRESHOLD = 0.5


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align two lists of paragraphs, producing typed blocks.

    Returns list of dicts with keys:
      type: "same" | "modified" | "removed" | "added"
      text: (for "same") the shared text
      original_text: (for "modified"/"removed") text from original
      florida_text: (for "modified"/"added") text from Florida
    """
    if not original and not florida:
        return []

    if not florida:
        return [{"type": "removed", "original_text": p} for p in original]

    if not original:
        return [{"type": "added", "florida_text": p} for p in florida]

    # Use SequenceMatcher to find the best alignment
    matcher = SequenceMatcher(None, original, florida)
    blocks = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                blocks.append({"type": "same", "text": original[i1 + k]})

        elif tag == "replace":
            # Check if paragraphs are similar enough to be "modified"
            orig_slice = original[i1:i2]
            fl_slice = florida[j1:j2]

            # Try to pair up paragraphs by similarity
            paired = _pair_by_similarity(orig_slice, fl_slice)
            blocks.extend(paired)

        elif tag == "delete":
            for k in range(i1, i2):
                blocks.append({"type": "removed", "original_text": original[k]})

        elif tag == "insert":
            for k in range(j1, j2):
                blocks.append({"type": "added", "florida_text": florida[k]})

    return blocks


def _pair_by_similarity(
    orig_paragraphs: list[str],
    fl_paragraphs: list[str],
) -> list[dict]:
    """Pair paragraphs from a 'replace' block by similarity.

    If paragraphs are similar enough, emit 'modified'.
    Otherwise emit 'removed' + 'added'.
    """
    results = []
    used_fl = set()

    for orig in orig_paragraphs:
        best_ratio = 0.0
        best_idx = -1

        for idx, fl in enumerate(fl_paragraphs):
            if idx in used_fl:
                continue
            ratio = SequenceMatcher(None, orig.split(), fl.split()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx

        if best_ratio >= SIMILARITY_THRESHOLD and best_idx >= 0:
            # Emit any unmatched Florida paragraphs before this match as "added"
            for j in range(len(fl_paragraphs)):
                if j == best_idx:
                    break
                if j not in used_fl:
                    results.append({"type": "added", "florida_text": fl_paragraphs[j]})
                    used_fl.add(j)

            results.append({
                "type": "modified",
                "original_text": orig,
                "florida_text": fl_paragraphs[best_idx],
            })
            used_fl.add(best_idx)
        else:
            results.append({"type": "removed", "original_text": orig})

    # Any remaining unmatched Florida paragraphs
    for idx, fl in enumerate(fl_paragraphs):
        if idx not in used_fl:
            results.append({"type": "added", "florida_text": fl})

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -m pytest scripts/test_aligner.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/aligner.py scripts/test_aligner.py
git commit -m "feat: add paragraph alignment core using difflib SequenceMatcher"
```

---

### Task 4: Alignment Script — Main Entry Point

**Files:**
- Create: `scripts/align_texts.py`

Orchestrates the full alignment pipeline: reads text files per the chapter mapping, splits into paragraphs, aligns, matches against existing change data for `change_id` and page numbers, writes `data/aligned/ch{NN}.json`.

- [ ] **Step 1: Write align_texts.py**

The main script that ties together `chapter_map`, `text_parser`, and `aligner`. This is an orchestration script, so we test it by running it on real data and inspecting output.

```python
# scripts/align_texts.py
"""Produce aligned chapter JSON files for the companion diff site.

Usage:
    uv run python scripts/align_texts.py              # all chapters
    uv run python scripts/align_texts.py --chapter 2   # single chapter
    uv run python scripts/align_texts.py --dry-run      # report stats only
"""

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

# Ensure scripts/ is on the path so we can import sibling modules
sys.path.insert(0, str(Path(__file__).parent))

from chapter_map import CHAPTER_MAP, PROJECT_ROOT
from text_parser import clean_text, detect_section_header, split_paragraphs
from aligner import align_paragraphs

DATA_DIR = PROJECT_ROOT / "data"
ALIGNED_DIR = DATA_DIR / "aligned"
CHANGE_MATCH_THRESHOLD = 0.85


def load_text(filepath: str) -> str:
    """Load a text file relative to PROJECT_ROOT."""
    return (PROJECT_ROOT / filepath).read_text(encoding="utf-8")


def load_change_data(chapter: int) -> dict:
    """Load the existing change JSON for a chapter."""
    data_file = CHAPTER_MAP[chapter]["data_file"]
    path = PROJECT_ROOT / data_file
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"changes": []}


def parse_chapter_text(text: str) -> list[dict]:
    """Parse chapter text into a list of {section_id, paragraphs} groups.

    Each group has:
      section_id: str (e.g., "2.1", "intro", or "body")
      heading: str (the full heading line)
      paragraphs: list[str]
    """
    cleaned = clean_text(text)
    lines = cleaned.split("\n")

    sections = []
    current_section = {"section_id": "intro", "heading": "Introduction", "paragraphs": []}
    current_para_lines = []

    def flush_para():
        if current_para_lines:
            para = " ".join(current_para_lines)
            if para.strip():
                current_section["paragraphs"].append(para.strip())
            current_para_lines.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_para()
            continue

        sec_id = detect_section_header(stripped)
        if sec_id and sec_id != "intro":
            flush_para()
            if current_section["paragraphs"]:
                sections.append(current_section)
            current_section = {
                "section_id": sec_id,
                "heading": stripped,
                "paragraphs": [],
            }
        elif sec_id == "intro":
            # If we see "Introduction" and current section is still empty intro, skip the header line
            if not current_section["paragraphs"] and current_section["section_id"] == "intro":
                continue
            else:
                flush_para()
                if current_section["paragraphs"]:
                    sections.append(current_section)
                current_section = {"section_id": "intro", "heading": "Introduction", "paragraphs": []}
        else:
            current_para_lines.append(stripped)

    flush_para()
    if current_section["paragraphs"]:
        sections.append(current_section)

    return sections


def match_change_id(
    block: dict,
    changes: list[dict],
    chapter: int,
) -> str | None:
    """Try to match an aligned block to an existing change entry by text similarity.

    Returns change_id string like 'ch02_change_3' or None.
    """
    block_orig = block.get("original_text", "")
    block_fl = block.get("florida_text", "")

    for idx, change in enumerate(changes):
        change_orig = change.get("original_text") or ""
        change_fl = change.get("florida_text") or ""

        # Compare original texts
        if block_orig and change_orig:
            ratio = SequenceMatcher(None, block_orig.split(), change_orig.split()).ratio()
            if ratio >= CHANGE_MATCH_THRESHOLD:
                return f"ch{chapter:02d}_change_{idx}"

        # Compare Florida texts
        if block_fl and change_fl:
            ratio = SequenceMatcher(None, block_fl.split(), change_fl.split()).ratio()
            if ratio >= CHANGE_MATCH_THRESHOLD:
                return f"ch{chapter:02d}_change_{idx}"

    return None


def get_change_metadata(change_id: str, changes: list[dict]) -> dict:
    """Extract page numbers and context from source change data."""
    if not change_id:
        return {}

    # Parse index from change_id like "ch02_change_3"
    idx = int(change_id.rsplit("_", 1)[1])
    if idx >= len(changes):
        return {}

    change = changes[idx]
    meta = {}
    if change.get("original_page"):
        meta["original_page"] = change["original_page"]
    if change.get("florida_page"):
        meta["florida_page"] = change["florida_page"]
    if change.get("context"):
        meta["context"] = change["context"]
    if change.get("original_evidence"):
        meta["original_evidence"] = change["original_evidence"]
    if change.get("florida_evidence"):
        meta["florida_evidence"] = change["florida_evidence"]
    if change.get("type") == "moved":
        if change.get("original_location"):
            meta["original_location"] = change["original_location"]
        if change.get("florida_location"):
            meta["florida_location"] = change["florida_location"]
    return meta


def interpolate_pages(blocks: list[dict]) -> None:
    """Fill in missing page numbers by interpolating from nearest anchored block.

    Mutates blocks in place. Uses nearest preceding anchor;
    if none, uses nearest following anchor.
    """
    # Forward pass: carry last known page forward
    last_orig_page = None
    last_fl_page = None
    for block in blocks:
        if block.get("original_page"):
            last_orig_page = block["original_page"]
        elif last_orig_page and block["type"] != "added":
            block["original_page"] = last_orig_page

        if block.get("florida_page"):
            last_fl_page = block["florida_page"]
        elif last_fl_page and block["type"] != "removed":
            block["florida_page"] = last_fl_page

    # Backward pass: fill any remaining gaps at the start
    last_orig_page = None
    last_fl_page = None
    for block in reversed(blocks):
        if block.get("original_page"):
            last_orig_page = block["original_page"]
        elif last_orig_page and "original_page" not in block and block["type"] != "added":
            block["original_page"] = last_orig_page

        if block.get("florida_page"):
            last_fl_page = block["florida_page"]
        elif last_fl_page and "florida_page" not in block and block["type"] != "removed":
            block["florida_page"] = last_fl_page


def align_chapter(chapter: int, dry_run: bool = False) -> dict:
    """Align a single chapter and return the aligned JSON structure."""
    entry = CHAPTER_MAP[chapter]
    change_data = load_change_data(chapter)
    changes = change_data.get("changes", [])

    # Load original text (concatenate for merged chapters)
    orig_text = "\n\n".join(
        load_text(f) for f in entry["original_texts"]
    )
    orig_sections = parse_chapter_text(orig_text)

    # Load Florida text (if not removed)
    if entry["florida_text"]:
        fl_text = load_text(entry["florida_text"])
        fl_sections = parse_chapter_text(fl_text)
    else:
        fl_sections = []

    # Build section-aligned output
    aligned_sections = []

    if not fl_sections:
        # Removed chapter — all original text as-is
        for sec in orig_sections:
            blocks = [{"type": "removed", "original_text": p} for p in sec["paragraphs"]]
            aligned_sections.append({
                "id": sec["section_id"],
                "original_heading": sec["heading"],
                "florida_heading": None,
                "blocks": blocks,
            })
    else:
        # Match sections between original and Florida
        fl_by_id = {s["section_id"]: s for s in fl_sections}
        used_fl_sections = set()

        for orig_sec in orig_sections:
            fl_sec = fl_by_id.get(orig_sec["section_id"])

            if fl_sec:
                used_fl_sections.add(orig_sec["section_id"])
                blocks = align_paragraphs(orig_sec["paragraphs"], fl_sec["paragraphs"])
            else:
                # Section removed in Florida
                blocks = [{"type": "removed", "original_text": p} for p in orig_sec["paragraphs"]]

            # Enrich blocks with change_id and metadata
            for block in blocks:
                if block["type"] != "same":
                    cid = match_change_id(block, changes, chapter)
                    if cid:
                        block["change_id"] = cid
                        meta = get_change_metadata(cid, changes)
                        block.update(meta)
                        # Promote to "moved" if the source change is type "moved"
                        idx = int(cid.rsplit("_", 1)[1])
                        if idx < len(changes) and changes[idx].get("type") == "moved":
                            block["type"] = "moved"
                    else:
                        block["change_id"] = None

            aligned_sections.append({
                "id": orig_sec["section_id"],
                "original_heading": orig_sec["heading"],
                "florida_heading": fl_sec["heading"] if fl_sec else None,
                "blocks": blocks,
            })

        # Any Florida sections not in original (added sections)
        for fl_sec in fl_sections:
            if fl_sec["section_id"] not in used_fl_sections:
                blocks = [{"type": "added", "florida_text": p} for p in fl_sec["paragraphs"]]
                for block in blocks:
                    cid = match_change_id(block, changes, chapter)
                    if cid:
                        block["change_id"] = cid
                        meta = get_change_metadata(cid, changes)
                        block.update(meta)
                        idx = int(cid.rsplit("_", 1)[1])
                        if idx < len(changes) and changes[idx].get("type") == "moved":
                            block["type"] = "moved"
                    else:
                        block["change_id"] = None

                aligned_sections.append({
                    "id": fl_sec["section_id"],
                    "original_heading": None,
                    "florida_heading": fl_sec["heading"],
                    "blocks": blocks,
                })

    # Flatten all blocks for page interpolation
    all_blocks = [b for sec in aligned_sections for b in sec["blocks"]]
    interpolate_pages(all_blocks)

    result = {
        "chapter": chapter,
        "title": change_data.get("title", f"Chapter {chapter}"),
        "florida_title": change_data.get("florida_title"),
        "chapter_type": entry["type"],
        "sections": aligned_sections,
    }

    if dry_run:
        total = len(all_blocks)
        by_type = {}
        for b in all_blocks:
            by_type[b["type"]] = by_type.get(b["type"], 0) + 1
        print(f"  Ch {chapter:2d}: {total} blocks — {by_type}")
    else:
        ALIGNED_DIR.mkdir(parents=True, exist_ok=True)
        out_path = ALIGNED_DIR / f"ch{chapter:02d}.json"
        out_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        total = len(all_blocks)
        print(f"  Ch {chapter:2d}: wrote {out_path.name} ({total} blocks)")

    return result


def main():
    parser = argparse.ArgumentParser(description="Align textbook chapters for companion diff site.")
    parser.add_argument("--chapter", type=int, help="Align a single chapter (original numbering)")
    parser.add_argument("--dry-run", action="store_true", help="Report stats without writing files")
    args = parser.parse_args()

    chapters = [args.chapter] if args.chapter else sorted(CHAPTER_MAP.keys())

    print(f"Aligning {len(chapters)} chapter(s)...")
    for ch in chapters:
        try:
            align_chapter(ch, dry_run=args.dry_run)
        except Exception as e:
            print(f"  Ch {ch:2d}: ERROR — {e}", file=sys.stderr)

    if not args.dry_run:
        print(f"\nDone. Aligned files in {ALIGNED_DIR}/")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run dry-run on all chapters to verify it works**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python scripts/align_texts.py --dry-run`
Expected: Stats printed for all 17 chapters, no errors.

- [ ] **Step 3: Run full alignment to generate data**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python scripts/align_texts.py`
Expected: 17 JSON files created in `data/aligned/`.

- [ ] **Step 4: Spot-check output for ch02**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -c "import json; d=json.load(open('data/aligned/ch02.json')); print(len(d['sections']), 'sections'); print(sum(len(s['blocks']) for s in d['sections']), 'total blocks'); types={b['type'] for s in d['sections'] for b in s['blocks']}; print('types:', types)"`
Expected: Multiple sections, mix of block types including "same", "modified", "removed", "added".

- [ ] **Step 5: Spot-check a removed chapter (ch11)**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python -c "import json; d=json.load(open('data/aligned/ch11.json')); types={b['type'] for s in d['sections'] for b in s['blocks']}; print('types:', types); print('chapter_type:', d['chapter_type'])"`
Expected: All blocks are `type: "removed"`, `chapter_type: "removed"`.

- [ ] **Step 6: Commit**

```bash
git add scripts/align_texts.py data/aligned/
git commit -m "feat: add alignment script and generate aligned chapter data"
```

---

### Task 5: Full-Page Render Script

**Files:**
- Create: `scripts/render_pages.py`

Renders every page of both PDFs as WebP images for margin thumbnails.

**Note:** This task requires both PDF files to be present in the project root. If they are not available, skip this task and use placeholder images in the frontend.

- [ ] **Step 1: Write render_pages.py**

```python
# scripts/render_pages.py
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

DEFAULT_DPI = 100  # Lower than evidence renders to manage disk space
WEBP_QUALITY = 60  # Aggressive compression for thumbnails


def render_pdf_pages(pdf_path: Path, output_dir: Path, dpi: int, dry_run: bool = False) -> int:
    """Render all pages of a PDF as WebP images.

    Returns number of pages rendered.
    """
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
```

- [ ] **Step 2: Run dry-run to check page counts**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python scripts/render_pages.py --dry-run`
Expected: Page counts printed for both PDFs (or warnings if PDFs not found).

- [ ] **Step 3: Run full render (if PDFs available)**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python scripts/render_pages.py`
Expected: WebP images created in `img/pages/original/` and `img/pages/florida/`.

- [ ] **Step 4: Add img/pages/ to .gitignore (too large for repo)**

Append `img/pages/` to `.gitignore` since these files are large and can be regenerated. They should be generated locally or served from a CDN.

- [ ] **Step 5: Commit**

```bash
git add scripts/render_pages.py .gitignore
git commit -m "feat: add full-page PDF render script for margin thumbnails"
```

---

## Phase 2: Frontend

### Task 6: HTML Shell and Basic Routing

**Files:**
- Create: `compare.html`
- Create: `js/compare.js`
- Create: `css/compare.css`

Minimal working page: loads `chapters.json`, renders a table of contents sidebar, and routes to individual chapters via hash.

- [ ] **Step 1: Create compare.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Full Comparison — What Florida Changed in Your Sociology Textbook</title>
  <link rel="stylesheet" href="css/style.css">
  <link rel="stylesheet" href="css/compare.css">
</head>
<body class="compare-page">
  <nav id="site-nav">
    <div class="nav-inner">
      <a href="./" class="nav-title" aria-label="Home">&larr;</a>
      <span class="nav-label">Full Text Comparison</span>
      <button id="toc-toggle" class="menu-toggle" aria-label="Toggle table of contents">
        <span></span><span></span><span></span>
      </button>
    </div>
  </nav>

  <aside id="toc" class="toc-sidebar" aria-label="Table of contents">
    <h2 class="toc-title">Chapters</h2>
    <ol id="toc-list" class="toc-list"></ol>
  </aside>

  <div id="page-thumb-left" class="page-thumb page-thumb-left" aria-label="Original textbook page">
    <img id="thumb-left-img" src="" alt="Original page">
    <span id="thumb-left-label" class="page-thumb-label"></span>
  </div>

  <div id="page-thumb-right" class="page-thumb page-thumb-right" aria-label="Florida textbook page">
    <img id="thumb-right-img" src="" alt="Florida page">
    <span id="thumb-right-label" class="page-thumb-label"></span>
  </div>

  <main id="content" class="compare-content">
    <div id="chapter-display"></div>
  </main>

  <div id="lightbox" class="lightbox" hidden>
    <button class="lightbox-close" aria-label="Close">&times;</button>
    <img id="lightbox-img" src="" alt="Full page view">
  </div>

  <script src="js/compare.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create css/compare.css with basic layout**

```css
/* compare.css — Companion diff site styles */

/* --- Layout --- */
.compare-page {
  display: grid;
  grid-template-columns: 260px 1fr;
  grid-template-rows: auto 1fr;
  min-height: 100vh;
}

.compare-page #site-nav {
  grid-column: 1 / -1;
}

.nav-label {
  font-family: system-ui, sans-serif;
  font-size: 0.875rem;
  color: var(--color-nav-text);
  opacity: 0.7;
}

/* --- Table of Contents Sidebar --- */
.toc-sidebar {
  grid-column: 1;
  grid-row: 2;
  padding: 1.5rem 1rem;
  border-right: 1px solid var(--color-border);
  overflow-y: auto;
  max-height: calc(100vh - 3.5rem);
  position: sticky;
  top: 3.5rem;
  background: var(--color-bg);
}

.toc-title {
  font-family: system-ui, sans-serif;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}

.toc-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-family: system-ui, sans-serif;
  font-size: 0.875rem;
  line-height: 1.4;
}

.toc-list li {
  margin-bottom: 0.25rem;
}

.toc-list a {
  display: block;
  padding: 0.35rem 0.5rem;
  color: var(--color-text);
  text-decoration: none;
  border-radius: 4px;
  transition: background 0.15s;
}

.toc-list a:hover {
  background: rgba(0, 0, 0, 0.05);
}

.toc-list a.active {
  background: rgba(37, 99, 235, 0.1);
  color: var(--color-added-border);
  font-weight: 600;
}

.toc-item-removed a {
  color: var(--color-removed-text);
}

.toc-item-merged a {
  color: var(--color-text-muted);
  font-style: italic;
  font-size: 0.8rem;
}

.toc-section-list {
  list-style: none;
  padding-left: 1rem;
  margin: 0.25rem 0 0.5rem;
}

.toc-section-list a {
  font-size: 0.8rem;
  padding: 0.2rem 0.5rem;
  color: var(--color-text-muted);
}

/* --- Main Content --- */
.compare-content {
  grid-column: 2;
  grid-row: 2;
  padding: 2rem 3rem;
  max-width: 72rem;
}

/* --- Chapter Header --- */
.compare-chapter-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--color-border);
}

.compare-chapter-header h1 {
  font-size: 1.75rem;
  line-height: 1.3;
}

.compare-chapter-titles {
  display: flex;
  gap: 2rem;
  margin-top: 0.5rem;
  font-family: system-ui, sans-serif;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

/* --- Section Headers --- */
.compare-section-header {
  margin: 2.5rem 0 1.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.compare-section-header h2 {
  font-size: 1.35rem;
  line-height: 1.3;
}

.compare-section-headings {
  display: flex;
  gap: 2rem;
}

.compare-section-headings span {
  font-family: system-ui, sans-serif;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

/* --- Diff Blocks --- */
.diff-row {
  margin-bottom: 1rem;
}

.diff-row-same {
  max-width: 52rem;
  margin-left: auto;
  margin-right: auto;
}

.diff-row-split {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.diff-col {
  padding: 0.75rem 1rem;
  border-radius: 4px;
}

.diff-col-original {
  /* Left column */
}

.diff-col-florida {
  /* Right column */
}

/* Column labels — appear at the top of the first split block */
.diff-col-label {
  font-family: system-ui, sans-serif;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}

/* --- Diff Highlighting --- */
.diff-del {
  background: var(--color-removed-bg);
  color: var(--color-removed-text);
  text-decoration: line-through;
  padding: 0.05rem 0.1rem;
  border-radius: 2px;
}

.diff-add {
  background: rgba(22, 163, 74, 0.12);
  color: #166534;
  text-decoration: underline;
  text-decoration-color: rgba(22, 163, 74, 0.4);
  padding: 0.05rem 0.1rem;
  border-radius: 2px;
}

/* Removed blocks */
.diff-row-removed .diff-col-original {
  background: var(--color-removed-bg);
  border-left: 3px solid var(--color-removed-text);
}

.diff-row-removed .diff-col-original p {
  text-decoration: line-through;
  color: var(--color-removed-text);
}

/* Added blocks */
.diff-row-added .diff-col-florida {
  background: rgba(22, 163, 74, 0.08);
  border-left: 3px solid #16a34a;
}

.diff-row-added .diff-col-florida p {
  color: #166534;
}

/* Modified blocks */
.diff-row-modified .diff-col-original {
  background: rgba(220, 38, 38, 0.04);
  border-left: 3px solid rgba(220, 38, 38, 0.3);
}

.diff-row-modified .diff-col-florida {
  background: rgba(22, 163, 74, 0.04);
  border-left: 3px solid rgba(22, 163, 74, 0.3);
}

/* Moved blocks */
.diff-row-moved .diff-col {
  border: 2px dashed var(--color-moved-border);
  background: var(--color-moved-bg);
  position: relative;
}

.diff-moved-tooltip {
  display: none;
  position: absolute;
  top: -2rem;
  left: 0;
  font-family: system-ui, sans-serif;
  font-size: 0.75rem;
  background: #1c1917;
  color: #fafaf9;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 10;
}

.diff-row-moved .diff-col:hover .diff-moved-tooltip,
.diff-row-moved .diff-col:focus-within .diff-moved-tooltip {
  display: block;
}

/* Context annotation */
.diff-context {
  font-family: system-ui, sans-serif;
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-style: italic;
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 4px;
}

/* --- Removed Chapter Banner --- */
.removed-chapter-banner {
  background: var(--color-removed-bg);
  border: 1px solid rgba(220, 38, 38, 0.3);
  border-radius: 6px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 2rem;
  font-family: system-ui, sans-serif;
  color: var(--color-removed-text);
}

.removed-chapter-banner strong {
  display: block;
  margin-bottom: 0.25rem;
}

/* --- Page Thumbnails --- */
.page-thumb {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 50;
  cursor: pointer;
  transition: opacity 0.2s;
  text-align: center;
}

.page-thumb img {
  width: 80px;
  border: 1px solid var(--color-border);
  border-radius: 3px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.page-thumb-left {
  left: 10px;
}

.page-thumb-right {
  right: 10px;
}

.page-thumb-label {
  display: block;
  font-family: system-ui, sans-serif;
  font-size: 0.65rem;
  color: var(--color-text-muted);
  margin-top: 0.25rem;
}

.page-thumb[hidden] {
  display: none;
}

/* --- Lightbox --- */
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
}

.lightbox[hidden] {
  display: none;
}

.lightbox img {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 4px;
  background: white;
}

.lightbox-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: none;
  border: none;
  color: white;
  font-size: 2rem;
  cursor: pointer;
}

/* --- Responsive --- */
@media (max-width: 1199px) {
  .page-thumb { display: none; }

  .compare-page {
    grid-template-columns: 1fr;
  }

  .toc-sidebar {
    position: fixed;
    left: -280px;
    top: 3.5rem;
    bottom: 0;
    width: 260px;
    z-index: 100;
    transition: left 0.3s;
    box-shadow: 2px 0 10px rgba(0,0,0,0.1);
  }

  .toc-sidebar.open {
    left: 0;
  }

  .compare-content {
    grid-column: 1;
    padding: 1.5rem 1rem;
  }
}

@media (max-width: 767px) {
  .diff-row-split {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .diff-col-original::before {
    content: "Original";
    display: block;
    font-family: system-ui, sans-serif;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted);
    margin-bottom: 0.25rem;
  }

  .diff-col-florida::before {
    content: "Florida";
    display: block;
    font-family: system-ui, sans-serif;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-text-muted);
    margin-bottom: 0.25rem;
  }
}
```

- [ ] **Step 3: Create js/compare.js with routing and TOC**

```javascript
// js/compare.js — Companion diff site: full-text two-column comparison

(function () {
  "use strict";

  // --- State ---
  const cache = {};  // chapter data cache
  let chaptersIndex = null;

  // Merged-away chapter stubs
  const MERGED_AWAY = { 4: 3, 16: 15, 17: 15, 18: 14 };

  // --- DOM refs ---
  const tocList = document.getElementById("toc-list");
  const chapterDisplay = document.getElementById("chapter-display");
  const tocToggle = document.getElementById("toc-toggle");
  const tocSidebar = document.getElementById("toc");

  // --- Init ---
  async function init() {
    const resp = await fetch("data/chapters.json");
    chaptersIndex = await resp.json();
    renderTOC();
    window.addEventListener("hashchange", handleRoute);
    handleRoute();

    // Mobile TOC toggle
    if (tocToggle) {
      tocToggle.addEventListener("click", () => {
        tocSidebar.classList.toggle("open");
      });
    }
  }

  // --- Table of Contents ---
  function renderTOC() {
    tocList.innerHTML = "";
    const chapters = chaptersIndex.chapters;

    for (let i = 1; i <= 21; i++) {
      const li = document.createElement("li");

      // Check if this is a merged-away stub
      if (MERGED_AWAY[i]) {
        const target = MERGED_AWAY[i];
        const targetChapter = chapters.find(c => c.chapter === target);
        li.className = "toc-item-merged";
        li.innerHTML = `<a href="#ch-${target}">Ch ${i} → see Ch ${target}</a>`;
        tocList.appendChild(li);
        continue;
      }

      const ch = chapters.find(c => c.chapter === i);
      if (!ch) continue;

      const isRemoved = ch.florida_title === null;
      if (isRemoved) li.className = "toc-item-removed";

      const label = `${i}. ${ch.title}`;
      li.innerHTML = `<a href="#ch-${i}" id="toc-ch-${i}">${escapeHtml(label)}</a>`;

      tocList.appendChild(li);
    }
  }

  function updateTOCActive(chapter) {
    tocList.querySelectorAll("a.active").forEach(a => a.classList.remove("active"));
    const el = document.getElementById(`toc-ch-${chapter}`);
    if (el) el.classList.add("active");
  }

  // --- Routing ---
  function getRoute() {
    const hash = window.location.hash;
    const match = hash.match(/^#ch-(\d+)$/);
    if (match) return { chapter: parseInt(match[1], 10) };
    return null;
  }

  function handleRoute() {
    const route = getRoute();
    if (route) {
      // Resolve merged-away stubs
      const ch = MERGED_AWAY[route.chapter] || route.chapter;
      updateTOCActive(ch);
      loadAndRenderChapter(ch);
    } else {
      renderWelcome();
    }
    // Close mobile TOC on navigation
    tocSidebar.classList.remove("open");
  }

  async function loadAndRenderChapter(chapter) {
    if (!cache[chapter]) {
      const resp = await fetch(`data/aligned/ch${String(chapter).padStart(2, "0")}.json`);
      if (!resp.ok) {
        chapterDisplay.innerHTML = `<p>Chapter ${chapter} data not found.</p>`;
        return;
      }
      cache[chapter] = await resp.json();
    }
    renderChapter(cache[chapter]);
  }

  // --- Welcome (no chapter selected) ---
  function renderWelcome() {
    chapterDisplay.innerHTML = `
      <div style="max-width: 40rem; margin: 4rem auto; text-align: center;">
        <h1>Full Text Comparison</h1>
        <p style="margin-top: 1rem; color: var(--color-text-muted);">
          Select a chapter from the sidebar to see the complete text of both versions side by side.
        </p>
      </div>
    `;
  }

  // --- Chapter Rendering ---
  function renderChapter(data) {
    blockCounter = 0;
    let html = "";

    // Chapter header
    html += `<div class="compare-chapter-header">`;
    html += `<h1>Chapter ${data.chapter}: ${escapeHtml(data.title)}</h1>`;
    if (data.florida_title) {
      html += `<div class="compare-chapter-titles">`;
      html += `<span>Original: ${escapeHtml(data.title)}</span>`;
      html += `<span>Florida: ${escapeHtml(data.florida_title)}</span>`;
      html += `</div>`;
    }
    html += `</div>`;

    // Removed chapter banner
    if (data.chapter_type === "removed") {
      html += `<div class="removed-chapter-banner">
        <strong>This entire chapter was removed from the Florida version.</strong>
        The text below shows the original content that Florida students no longer have access to.
      </div>`;
    }

    // Sections
    for (const section of data.sections) {
      html += renderSection(section, data.chapter_type);
    }

    // Prev/Next nav
    html += renderChapterNav(data.chapter);

    chapterDisplay.innerHTML = html;
    window.scrollTo(0, 0);

    // Set up scroll tracking for page thumbnails
    setupScrollTracking();
  }

  function renderSection(section, chapterType) {
    let html = "";

    // Section header
    html += `<div class="compare-section-header" id="section-${section.id}">`;
    html += `<h2>${escapeHtml(section.original_heading || section.florida_heading || "")}</h2>`;

    if (section.original_heading && section.florida_heading &&
        section.original_heading !== section.florida_heading) {
      html += `<div class="compare-section-headings">`;
      html += `<span>Original: ${escapeHtml(section.original_heading)}</span>`;
      html += `<span>Florida: ${escapeHtml(section.florida_heading)}</span>`;
      html += `</div>`;
    }
    html += `</div>`;

    // Blocks
    for (const block of section.blocks) {
      html += renderBlock(block, chapterType);
    }

    return html;
  }

  let blockCounter = 0;
  function renderBlock(block, chapterType) {
    const blockId = blockCounter++;
    const pageData = `data-orig-page="${block.original_page || ""}" data-fl-page="${block.florida_page || ""}"`;

    switch (block.type) {
      case "same":
        return `<div class="diff-row diff-row-same" ${pageData}>
          <p>${escapeHtml(block.text)}</p>
        </div>`;

      case "modified":
        return renderModifiedBlock(block, pageData);

      case "removed":
        return `<div class="diff-row diff-row-split diff-row-removed" ${pageData}>
          <div class="diff-col diff-col-original" aria-label="Original text">
            <p>${escapeHtml(block.original_text)}</p>
          </div>
          <div class="diff-col diff-col-florida" aria-label="Florida text">
            ${chapterType === "removed" ? "" : "<p style=\"color: var(--color-text-muted); font-style: italic;\">Removed</p>"}
          </div>
        </div>${block.context ? `<div class="diff-context">${escapeHtml(block.context)}</div>` : ""}`;

      case "added":
        return `<div class="diff-row diff-row-split diff-row-added" ${pageData}>
          <div class="diff-col diff-col-original" aria-label="Original text"></div>
          <div class="diff-col diff-col-florida" aria-label="Florida text">
            <p>${escapeHtml(block.florida_text)}</p>
          </div>
        </div>${block.context ? `<div class="diff-context">${escapeHtml(block.context)}</div>` : ""}`;

      case "moved":
        return renderMovedBlock(block, pageData, blockId);

      default:
        return "";
    }
  }

  function renderModifiedBlock(block, pageData) {
    const diff = wordDiff(block.original_text, block.florida_text);

    // Left column: original text with deletions highlighted
    let leftHtml = "";
    for (const part of diff) {
      const escaped = escapeHtml(part.text);
      if (part.type === "same") leftHtml += escaped;
      else if (part.type === "del") leftHtml += `<span class="diff-del">${escaped}</span>`;
      // Skip "add" parts in left column
    }

    // Right column: florida text with additions highlighted
    let rightHtml = "";
    for (const part of diff) {
      const escaped = escapeHtml(part.text);
      if (part.type === "same") rightHtml += escaped;
      else if (part.type === "add") rightHtml += `<span class="diff-add">${escaped}</span>`;
      // Skip "del" parts in right column
    }

    return `<div class="diff-row diff-row-split diff-row-modified" ${pageData}>
      <div class="diff-col diff-col-original" aria-label="Original text">
        <p>${leftHtml}</p>
      </div>
      <div class="diff-col diff-col-florida" aria-label="Florida text">
        <p>${rightHtml}</p>
      </div>
    </div>${block.context ? `<div class="diff-context">${escapeHtml(block.context)}</div>` : ""}`;
  }

  function renderMovedBlock(block, pageData, blockId) {
    const origTooltip = block.florida_location
      ? `Moved to ${escapeHtml(block.florida_location)}`
      : "Moved";
    const flTooltip = block.original_location
      ? `Moved from ${escapeHtml(block.original_location)}`
      : "Moved";

    return `<div class="diff-row diff-row-split diff-row-moved" ${pageData}>
      <div class="diff-col diff-col-original" tabindex="0" aria-describedby="moved-orig-${blockId}">
        <span class="diff-moved-tooltip" id="moved-orig-${blockId}" role="tooltip">${origTooltip}</span>
        <p>${escapeHtml(block.original_text || "")}</p>
      </div>
      <div class="diff-col diff-col-florida" tabindex="0" aria-describedby="moved-fl-${blockId}">
        <span class="diff-moved-tooltip" id="moved-fl-${blockId}" role="tooltip">${flTooltip}</span>
        <p>${escapeHtml(block.florida_text || "")}</p>
      </div>
    </div>`;
  }

  function renderChapterNav(currentChapter) {
    const allChapters = Object.keys(CHAPTER_MAP_KEYS).map(Number).sort((a, b) => a - b);
    const idx = allChapters.indexOf(currentChapter);
    const prev = idx > 0 ? allChapters[idx - 1] : null;
    const next = idx < allChapters.length - 1 ? allChapters[idx + 1] : null;

    return `<div style="display: flex; justify-content: space-between; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--color-border);">
      ${prev ? `<a href="#ch-${prev}">&larr; Previous Chapter</a>` : "<span></span>"}
      ${next ? `<a href="#ch-${next}">Next Chapter &rarr;</a>` : "<span></span>"}
    </div>`;
  }

  // Valid chapter numbers (not merged-away)
  const CHAPTER_MAP_KEYS = {1:1,2:1,3:1,5:1,6:1,7:1,8:1,9:1,10:1,11:1,12:1,13:1,14:1,15:1,19:1,20:1,21:1};

  // --- Word Diff (LCS) ---
  function wordDiff(oldText, newText) {
    const oldWords = oldText.split(/(\s+)/);
    const newWords = newText.split(/(\s+)/);
    const m = oldWords.length;
    const n = newWords.length;

    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (oldWords[i - 1] === newWords[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1] + 1;
        } else {
          dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
        }
      }
    }

    const result = [];
    let i = m, j = n;
    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && oldWords[i - 1] === newWords[j - 1]) {
        result.unshift({ type: "same", text: oldWords[i - 1] });
        i--; j--;
      } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
        result.unshift({ type: "add", text: newWords[j - 1] });
        j--;
      } else {
        result.unshift({ type: "del", text: oldWords[i - 1] });
        i--;
      }
    }
    return result;
  }

  // --- Scroll Tracking for Page Thumbnails ---
  function setupScrollTracking() {
    const thumbLeft = document.getElementById("page-thumb-left");
    const thumbRight = document.getElementById("page-thumb-right");
    const thumbLeftImg = document.getElementById("thumb-left-img");
    const thumbRightImg = document.getElementById("thumb-right-img");
    const thumbLeftLabel = document.getElementById("thumb-left-label");
    const thumbRightLabel = document.getElementById("thumb-right-label");
    const lightbox = document.getElementById("lightbox");
    const lightboxImg = document.getElementById("lightbox-img");

    let lastOrigPage = null;
    let lastFlPage = null;

    function updateThumbs() {
      const blocks = document.querySelectorAll(".diff-row[data-orig-page]");
      const viewMid = window.innerHeight / 2;

      let closestBlock = null;
      let closestDist = Infinity;

      for (const block of blocks) {
        const rect = block.getBoundingClientRect();
        const dist = Math.abs(rect.top + rect.height / 2 - viewMid);
        if (dist < closestDist) {
          closestDist = dist;
          closestBlock = block;
        }
      }

      if (!closestBlock) return;

      const origPage = closestBlock.dataset.origPage;
      const flPage = closestBlock.dataset.flPage;

      if (origPage && origPage !== lastOrigPage) {
        lastOrigPage = origPage;
        const src = `img/pages/original/page_${origPage.padStart(3, "0")}.webp`;
        thumbLeftImg.src = src;
        thumbLeftLabel.textContent = `Original p. ${origPage}`;
        thumbLeft.hidden = false;
        thumbLeft.onclick = () => openLightbox(src);
      } else if (!origPage) {
        thumbLeft.hidden = true;
      }

      if (flPage && flPage !== lastFlPage) {
        lastFlPage = flPage;
        const src = `img/pages/florida/page_${flPage.padStart(3, "0")}.webp`;
        thumbRightImg.src = src;
        thumbRightLabel.textContent = `Florida p. ${flPage}`;
        thumbRight.hidden = false;
        thumbRight.onclick = () => openLightbox(src);
      } else if (!flPage) {
        thumbRight.hidden = true;
      }
    }

    function openLightbox(src) {
      lightboxImg.src = src;
      lightbox.hidden = false;
    }

    lightbox.querySelector(".lightbox-close").addEventListener("click", () => {
      lightbox.hidden = true;
    });
    lightbox.addEventListener("click", (e) => {
      if (e.target === lightbox) lightbox.hidden = true;
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !lightbox.hidden) lightbox.hidden = true;
    });

    // Throttle scroll handler with requestAnimationFrame
    let ticking = false;
    window.addEventListener("scroll", () => {
      if (!ticking) {
        requestAnimationFrame(() => { updateThumbs(); ticking = false; });
        ticking = true;
      }
    }, { passive: true });
    updateThumbs();
  }

  // --- Utilities ---
  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // --- Boot ---
  init();
})();
```

- [ ] **Step 4: Test in browser**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && python3 -m http.server 8000`

Then open `http://localhost:8000/compare.html` in a browser. Verify:
- TOC sidebar lists all 21 chapters with correct labels
- Merged-away chapters show redirect links
- Removed chapters are styled in red
- Clicking a chapter loads and renders its aligned data
- Two-column layout appears for modified/removed/added blocks
- Same-text blocks render as single column
- Word-level diff highlighting works in modified blocks
- Page thumbnails appear (if page images are available) or fail gracefully

- [ ] **Step 5: Commit**

```bash
git add compare.html js/compare.js css/compare.css
git commit -m "feat: add companion diff site with two-column layout and routing"
```

---

### Task 7: Polish and Cross-Links

**Files:**
- Modify: `compare.html`
- Modify: `js/compare.js`
- Modify: `css/compare.css`
- Modify: `chapters.html`

Final polish: section-level TOC navigation, cross-links between sites, and visual refinements.

- [ ] **Step 1: Add section-level nav to TOC**

In `js/compare.js`, after rendering a chapter, populate section links inside the TOC for the active chapter. Update the TOC rendering to insert a `<ul class="toc-section-list">` under the active chapter's `<li>` populated with the section headings from the loaded aligned data.

- [ ] **Step 2: Add cross-links**

In `chapters.html` chapter view, add a link: `<a href="compare.html#ch-{N}">View full text comparison</a>`.

In `compare.html` chapter header, add: `<a href="chapters.html#chapter-{N}">View highlighted changes</a>`.

- [ ] **Step 3: Test cross-links in browser**

Navigate between `chapters.html#chapter-2` and `compare.html#ch-2` to verify links work both ways.

- [ ] **Step 4: Commit**

```bash
git add compare.html js/compare.js css/compare.css chapters.html
git commit -m "feat: add section nav and cross-links between comparison views"
```

---

### Task 8: Removed Chapter Single-Column Styling

**Files:**
- Modify: `css/compare.css`
- Modify: `js/compare.js`

For removed chapters, the right column and Florida thumbnail should be hidden entirely, and the original text should render as a readable single column (not struck-through — it's the *full* original text presented for reference).

- [ ] **Step 1: Update renderBlock for removed chapters**

In `js/compare.js`, when `chapterType === "removed"`, render all blocks as `diff-row-same` style (single column, no strikethrough) instead of the `diff-row-removed` split layout. The banner at the top already communicates the removal.

- [ ] **Step 2: Hide right thumbnail for removed chapters**

In `setupScrollTracking`, if the chapter data has `chapter_type === "removed"`, hide the right thumbnail permanently.

- [ ] **Step 3: Test with chapter 11 (removed chapter)**

Open `http://localhost:8000/compare.html#ch-11` and verify:
- Banner appears at top
- Text renders as single readable column
- No right thumbnail
- No strikethrough

- [ ] **Step 4: Commit**

```bash
git add js/compare.js css/compare.css
git commit -m "fix: render removed chapters as readable single column with banner"
```

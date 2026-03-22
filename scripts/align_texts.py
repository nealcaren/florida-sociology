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

sys.path.insert(0, str(Path(__file__).parent))

from chapter_map import CHAPTER_MAP, PROJECT_ROOT
from text_parser import clean_text, detect_section_header, split_paragraphs
from aligner import align_paragraphs
from parse_cnxml import get_chapter_sections

DATA_DIR = PROJECT_ROOT / "data"
ALIGNED_DIR = DATA_DIR / "aligned"
CHANGE_MATCH_THRESHOLD = 0.85


def load_text(filepath: str) -> str:
    return (PROJECT_ROOT / filepath).read_text(encoding="utf-8")


def load_change_data(chapter: int) -> dict:
    data_file = CHAPTER_MAP[chapter]["data_file"]
    path = PROJECT_ROOT / data_file
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"changes": []}


def _remove_outline_blocks(lines: list[str]) -> list[str]:
    """Remove chapter outline blocks from PDF-extracted text.

    Chapter outlines are consecutive lines that all match section header
    patterns (e.g., "2.1 ...\n2.2 ...\n2.3 ..."). These are tables of
    contents embedded in the PDF, not actual section boundaries.
    """
    # Find runs of consecutive section-header lines (2+ in a row)
    outline_lines = set()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        sid = detect_section_header(stripped)
        if sid and sid != "intro":
            # Look ahead for consecutive headers
            run_start = i
            j = i + 1
            while j < len(lines):
                s2 = lines[j].strip()
                if not s2:
                    j += 1
                    continue
                sid2 = detect_section_header(s2)
                if sid2 and sid2 != "intro":
                    j += 1
                else:
                    break
            # Count actual header lines in this run
            header_count = sum(
                1 for k in range(run_start, j)
                if lines[k].strip() and detect_section_header(lines[k].strip())
                and detect_section_header(lines[k].strip()) != "intro"
            )
            if header_count >= 2:
                # This is a chapter outline block — mark all lines for removal
                for k in range(run_start, j):
                    outline_lines.add(k)
            i = j
        else:
            i += 1

    return [line for idx, line in enumerate(lines) if idx not in outline_lines]


def parse_chapter_text(text: str) -> list[dict]:
    """Parse chapter text into a list of {section_id, heading, paragraphs} groups."""
    cleaned = clean_text(text)
    lines = cleaned.split("\n")

    # Remove chapter outline blocks (consecutive section headers from PDF TOC)
    lines = _remove_outline_blocks(lines)

    sections = []
    current_section = {"section_id": "intro", "heading": "Introduction", "paragraphs": []}
    current_para_lines = []

    pending_para = None  # holds a paragraph that ended mid-sentence

    def flush_para():
        nonlocal pending_para
        if current_para_lines:
            para = " ".join(current_para_lines)
            if para.strip():
                para = para.strip()
                # If previous paragraph ended mid-sentence, merge
                if pending_para:
                    para = pending_para + " " + para
                    pending_para = None

                # Check if this paragraph ends mid-sentence (page break)
                if re.search(r"[,;:\-—]$", para):
                    pending_para = para
                else:
                    current_section["paragraphs"].append(para)
            current_para_lines.clear()

    def commit_pending():
        """Commit any pending mid-sentence paragraph."""
        nonlocal pending_para
        if pending_para:
            current_section["paragraphs"].append(pending_para)
            pending_para = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_para()
            continue

        sec_id = detect_section_header(stripped)
        if sec_id and sec_id != "intro":
            flush_para()
            commit_pending()
            if current_section["paragraphs"]:
                sections.append(current_section)
            current_section = {
                "section_id": sec_id,
                "heading": stripped,
                "paragraphs": [],
            }
        elif sec_id == "intro":
            if not current_section["paragraphs"] and current_section["section_id"] == "intro":
                continue
            else:
                flush_para()
                commit_pending()
                if current_section["paragraphs"]:
                    sections.append(current_section)
                current_section = {"section_id": "intro", "heading": "Introduction", "paragraphs": []}
        else:
            current_para_lines.append(stripped)

    flush_para()
    commit_pending()
    if current_section["paragraphs"]:
        sections.append(current_section)

    # Consolidate duplicate section IDs (PDF extraction may still have
    # re-detected section headers from inline references).
    consolidated = []
    seen = {}
    for sec in sections:
        sid = sec["section_id"]
        if sid in seen:
            seen[sid]["paragraphs"].extend(sec["paragraphs"])
        else:
            seen[sid] = sec
            consolidated.append(sec)

    return consolidated


def match_change_id(block: dict, changes: list[dict], chapter: int) -> str | None:
    block_orig = block.get("original_text", "")
    block_fl = block.get("florida_text", "")

    for idx, change in enumerate(changes):
        change_orig = change.get("original_text") or ""
        change_fl = change.get("florida_text") or ""

        if block_orig and change_orig:
            ratio = SequenceMatcher(None, block_orig.split(), change_orig.split()).ratio()
            if ratio >= CHANGE_MATCH_THRESHOLD:
                return f"ch{chapter:02d}_change_{idx}"

        if block_fl and change_fl:
            ratio = SequenceMatcher(None, block_fl.split(), change_fl.split()).ratio()
            if ratio >= CHANGE_MATCH_THRESHOLD:
                return f"ch{chapter:02d}_change_{idx}"

    return None


def get_change_metadata(change_id: str, changes: list[dict]) -> dict:
    if not change_id:
        return {}
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
    entry = CHAPTER_MAP[chapter]
    change_data = load_change_data(chapter)
    changes = change_data.get("changes", [])

    # Use CNXML source for original text (cleaner than PDF extraction).
    # For merged chapters, original_texts lists multiple files like
    # ["text/original/ch03.txt", "text/original/ch04.txt"] — extract the
    # chapter numbers and concatenate CNXML sections from each.
    import re as _re
    orig_sections = []
    for orig_path in entry["original_texts"]:
        m = _re.search(r"ch(\d+)\.txt$", orig_path)
        if m:
            orig_ch = int(m.group(1))
            orig_sections.extend(get_chapter_sections(orig_ch))

    if entry["florida_text"]:
        fl_text = load_text(entry["florida_text"])
        fl_sections = parse_chapter_text(fl_text)
    else:
        fl_sections = []

    aligned_sections = []

    if not fl_sections:
        for sec in orig_sections:
            blocks = [{"type": "removed", "original_text": p} for p in sec["paragraphs"]]
            aligned_sections.append({
                "id": sec["section_id"],
                "original_heading": sec["heading"],
                "florida_heading": None,
                "blocks": blocks,
            })
    else:
        fl_by_id = {s["section_id"]: s for s in fl_sections}
        # Also build a lookup by sub-section number (e.g., "1" from "5.1")
        # to handle renumbered chapters where "5.1" in original = "4.1" in Florida
        fl_by_sub = {}
        for s in fl_sections:
            parts = s["section_id"].split(".")
            if len(parts) == 2:
                fl_by_sub[parts[1]] = s
        used_fl_sections = set()

        for orig_sec in orig_sections:
            fl_sec = None

            if entry["type"] == "merged":
                # For merged chapters, always use content-based matching
                # since section numbers are meaningless across merged chapters
                pass
            else:
                # Try matching by section ID first
                fl_sec = fl_by_id.get(orig_sec["section_id"])
                # Try matching by sub-section number for renumbered chapters
                # e.g., original "5.1" -> Florida "4.1" (both sub ".1")
                if fl_sec is None:
                    orig_parts = orig_sec["section_id"].split(".")
                    if len(orig_parts) == 2:
                        fl_sec = fl_by_sub.get(orig_parts[1])

            # Content-based matching for unmatched sections
            if fl_sec is None and orig_sec["section_id"] != "intro":
                from difflib import SequenceMatcher as _SM
                orig_words = " ".join(orig_sec["paragraphs"]).split()
                best_ratio = 0.3  # minimum threshold
                best_fl = None
                for candidate in fl_sections:
                    if candidate["section_id"] in used_fl_sections:
                        continue
                    fl_words = " ".join(candidate["paragraphs"]).split()
                    ratio = _SM(None, orig_words[:200], fl_words[:200]).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_fl = candidate
                if best_fl:
                    fl_sec = best_fl

            if fl_sec:
                used_fl_sections.add(fl_sec["section_id"])
                blocks = align_paragraphs(orig_sec["paragraphs"], fl_sec["paragraphs"])
            else:
                blocks = [{"type": "removed", "original_text": p} for p in orig_sec["paragraphs"]]

            for block in blocks:
                if block["type"] != "same":
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
                "id": orig_sec["section_id"],
                "original_heading": orig_sec["heading"],
                "florida_heading": fl_sec["heading"] if fl_sec else None,
                "blocks": blocks,
            })

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

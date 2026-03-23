"""Definitive sentence-level change counts between original and Florida textbooks.

For each original sentence (from clean CNXML source), searches the
entire Florida chapter text for a match. No section matching, no
paragraph splitting — just direct sentence-by-sentence comparison.

Usage:
    uv run python scripts/count_changes.py
    uv run python scripts/count_changes.py --chapter 2
    uv run python scripts/count_changes.py --verbose
    uv run python scripts/count_changes.py --output data/sentence_counts.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

import nltk
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)
from nltk.tokenize import sent_tokenize

sys.path.insert(0, str(Path(__file__).parent))

from chapter_map import CHAPTER_MAP, PROJECT_ROOT
from parse_cnxml import get_chapter_sections
from text_parser import clean_text


SAME_THRESHOLD = 0.98  # Near-identical (catches single-word changes in long sentences)
MODIFIED_THRESHOLD = 0.4  # Changed but recognizable


def get_original_sentences(chapter: int) -> list[str]:
    """Get all sentences from the CNXML source for a chapter."""
    sections = get_chapter_sections(chapter, include_notes=True)
    sentences = []
    for sec in sections:
        for para in sec["paragraphs"]:
            for sent in sent_tokenize(para):
                sent = sent.strip()
                if len(sent) <= 10 or len(sent.split()) < 5:
                    continue
                # Skip bibliographic entries
                if re.match(r'^"[^"]+[."]', sent) and len(sent.split()) < 20:
                    continue
                sentences.append(sent)
    return sentences


def _strip_headers(text: str) -> str:
    """Remove section headers and standalone title lines from cleaned text.

    These are lines like "Introduction", "2.1 Approaches to Sociological Research",
    "The Scientific Method", etc. that get merged into adjacent sentences by
    sent_tokenize if not removed.
    """
    import re
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue

        # Section headers: "2.1 Title" or "Introduction"
        if re.match(r"^\d+\.\d+\s+[A-Z]", stripped):
            continue
        if stripped.upper() == "INTRODUCTION":
            continue

        # Short title-like lines (subsection headers from PDF)
        # e.g., "The Scientific Method", "Step 1: Ask A Question"
        words = stripped.split()
        if (len(words) <= 8
                and not stripped.endswith((".", "!", "?", ",", ";"))
                and stripped[0].isupper()):
            continue

        cleaned.append(line)
    return "\n".join(cleaned)


def get_florida_sentences(chapter: int) -> list[str]:
    """Get all sentences from the Florida PDF text for a chapter."""
    entry = CHAPTER_MAP[chapter]
    if entry["florida_text"] is None:
        return []

    # Prefer v2 extraction (layout-aware) if available, fall back to v1
    fl_v2_path = PROJECT_ROOT / "text" / "florida_v2" / Path(entry["florida_text"]).name
    if fl_v2_path.exists():
        fl_clean = fl_v2_path.read_text(encoding="utf-8")
    else:
        fl_path = PROJECT_ROOT / entry["florida_text"]
        fl_raw = fl_path.read_text(encoding="utf-8")
        fl_clean = clean_text(fl_raw)
    fl_clean = _strip_headers(fl_clean)

    # Join broken lines within paragraphs (PDF hard line breaks)
    paragraphs = re.split(r"\n\s*\n", fl_clean)
    joined = []
    for para in paragraphs:
        p = " ".join(line.strip() for line in para.split("\n") if line.strip())
        if p:
            joined.append(p)

    # Truncate at the references section — find where body content ends
    # and bibliographic entries begin (consecutive short citation-like paragraphs)
    body_end = len(joined)
    for i in range(len(joined)):
        p = joined[i]
        words = p.split()
        if (len(words) < 30
                and re.match(r"^[A-Z][a-z]+,?\s+[A-Z]", p)
                and re.search(r"\d{4}", p)):
            # Check if next few paragraphs also look like references
            ref_count = sum(
                1 for j in range(i, min(i + 5, len(joined)))
                if len(joined[j].split()) < 30 and re.search(r"\d{4}", joined[j])
            )
            if ref_count >= 3:
                body_end = i
                break

    fl_text = " ".join(joined[:body_end])

    sentences = []
    for sent in sent_tokenize(fl_text):
        sent = sent.strip()
        words = sent.split()

        # Skip very short fragments
        if len(sent) <= 10 or len(words) < 5:
            continue

        # Skip references, citations, URLs
        if sent.startswith("http") or sent.startswith("Retrieved "):
            continue
        if re.match(r"^\d{4}\.", sent):
            continue

        # Skip bibliographic entries — multiple patterns
        # "Author, First." or "Author, First and Last."
        if re.match(r"^[A-Z][a-z]+,\s+[A-Z]", sent) and len(words) < 30:
            continue
        # Quoted article titles: "Title Here."
        if re.match(r'^"[^"]+[."]', sent) and len(words) < 25:
            continue
        # Publisher lines: "New York: Publisher" or "Cambridge, MA:"
        if re.match(r"^[A-Z][a-z]+,?\s+(MA|NY|CA|UK|DC)[\s:.)]", sent):
            continue
        if re.match(r"^(New York|Cambridge|Chicago|London|Oxford|Washington|Boston):", sent):
            continue
        # Journal/book references with page numbers
        if re.search(r"\d+[–-]\d+\s+in\s+", sent) and len(words) < 25:
            continue
        # Ends with publisher or "Retrieved"
        if re.search(r"(University Press|Sage Foundation|Retrieved \w+ \d+)\.$", sent):
            continue
        # Short fragments that are just organization names
        if len(words) <= 8 and re.match(r"^[A-Z]", sent) and not sent.endswith(('.', '!', '?')):
            continue
        # Pattern: "N N N" (numbers like "50 47 36")
        if re.match(r"^\d+\s+\d+\s+\d+", sent):
            continue

        # Skip table content
        if re.match(r"^(Table\s+\d|Informal|Formal|Positive|Negative|Hypothesis|Independent|Dependent)", sent):
            continue

        sentences.append(sent)
    return sentences


def word_sim(a: str, b: str) -> float:
    """Word-level similarity between two strings."""
    return SequenceMatcher(None, a.lower().split(), b.lower().split()).ratio()


def classify_sentences(orig_sents: list[str], fl_sents: list[str]) -> dict:
    """Classify each original sentence as same/modified/removed.

    Also identifies Florida sentences not matched to any original (added).

    Returns dict with:
        same: list of (orig_sent, fl_sent) pairs
        modified: list of (orig_sent, fl_sent, similarity) triples
        removed: list of orig_sent
        added: list of fl_sent
    """
    result = {
        "same": [],
        "modified": [],
        "removed": [],
        "added": [],
    }

    if not fl_sents:
        result["removed"] = list(orig_sents)
        return result

    if not orig_sents:
        result["added"] = list(fl_sents)
        return result

    # Build all plausible pairs with scores
    pairs = []  # (score, orig_idx, fl_idx)
    for i, orig_sent in enumerate(orig_sents):
        for j, fl_sent in enumerate(fl_sents):
            # Quick length filter
            len_ratio = len(orig_sent) / max(len(fl_sent), 1)
            if len_ratio < 0.25 or len_ratio > 4.0:
                continue
            score = word_sim(orig_sent, fl_sent)
            if score >= MODIFIED_THRESHOLD:
                pairs.append((score, i, j))

    # Greedily match highest-scoring pairs first (avoids stealing)
    pairs.sort(reverse=True)
    orig_matched = {}  # i -> (j, score)
    fl_matched = set()

    for score, i, j in pairs:
        if i in orig_matched or j in fl_matched:
            continue
        orig_matched[i] = (j, score)
        fl_matched.add(j)

    # Classify
    for i, orig_sent in enumerate(orig_sents):
        if i in orig_matched:
            j, score = orig_matched[i]
            if score >= SAME_THRESHOLD:
                result["same"].append((orig_sent, fl_sents[j]))
            else:
                result["modified"].append((orig_sent, fl_sents[j], score))
        else:
            result["removed"].append(orig_sent)

    # Florida sentences not matched to any original
    for j, fl_sent in enumerate(fl_sents):
        if j not in fl_matched:
            result["added"].append(fl_sent)

    return result


def count_chapter(chapter: int, verbose: bool = False) -> dict:
    """Count sentence-level changes for one chapter."""
    entry = CHAPTER_MAP[chapter]

    # Get original sentences from all contributing chapters
    # (for merged chapters, this includes multiple original chapters)
    orig_chapters = []
    for path in entry["original_texts"]:
        import re
        m = re.search(r"ch(\d+)\.txt$", path)
        if m:
            orig_chapters.append(int(m.group(1)))

    all_orig = []
    for oc in orig_chapters:
        all_orig.extend(get_original_sentences(oc))

    fl_sents = get_florida_sentences(chapter)

    result = classify_sentences(all_orig, fl_sents)

    counts = {
        "chapter": chapter,
        "title": entry.get("data_file", ""),
        "type": entry["type"],
        "original_sentences": len(all_orig),
        "florida_sentences": len(fl_sents),
        "same": len(result["same"]),
        "modified": len(result["modified"]),
        "removed": len(result["removed"]),
        "added": len(result["added"]),
    }

    if verbose:
        print(f"\n  Sample removed sentences:")
        for s in result["removed"][:3]:
            print(f"    - {s[:100]}")
        print(f"  Sample modified sentences:")
        for orig, fl, sim in result["modified"][:3]:
            print(f"    - [{sim:.2f}] {orig[:80]}")
            print(f"      → {fl[:80]}")

    return counts


def main():
    parser = argparse.ArgumentParser(description="Count sentence-level changes.")
    parser.add_argument("--chapter", type=int, help="Single chapter")
    parser.add_argument("--verbose", action="store_true", help="Show example sentences")
    parser.add_argument("--output", type=str, help="Save JSON output to file")
    args = parser.parse_args()

    chapters = [args.chapter] if args.chapter else sorted(CHAPTER_MAP.keys())

    # Load chapter titles
    chapters_json = json.loads((PROJECT_ROOT / "data" / "chapters.json").read_text())
    title_map = {c["chapter"]: c["title"] for c in chapters_json["chapters"]}

    all_counts = []

    print(f"{'Ch':>4} {'Title':<45} {'Orig':>5} {'Same':>5} {'Edit':>5} {'Cut':>5} {'Add':>5}")
    print("-" * 80)

    totals = {"original": 0, "same": 0, "modified": 0, "removed": 0, "added": 0}

    for ch in chapters:
        counts = count_chapter(ch, verbose=args.verbose)
        title = title_map.get(ch, f"Chapter {ch}")[:42]

        print(f"{ch:>4} {title:<45} {counts['original_sentences']:>5} "
              f"{counts['same']:>5} {counts['modified']:>5} "
              f"{counts['removed']:>5} {counts['added']:>5}")

        totals["original"] += counts["original_sentences"]
        totals["same"] += counts["same"]
        totals["modified"] += counts["modified"]
        totals["removed"] += counts["removed"]
        totals["added"] += counts["added"]

        counts["title"] = title_map.get(ch, f"Chapter {ch}")
        all_counts.append(counts)

    print("-" * 80)
    print(f"{'':>4} {'TOTAL':<45} {totals['original']:>5} "
          f"{totals['same']:>5} {totals['modified']:>5} "
          f"{totals['removed']:>5} {totals['added']:>5}")

    print()
    orig = totals["original"]
    print(f"Original sentences: {orig}")
    print(f"  Kept unchanged:   {totals['same']:>5} ({totals['same']/orig*100:.1f}%)")
    print(f"  Edited:           {totals['modified']:>5} ({totals['modified']/orig*100:.1f}%)")
    print(f"  Removed:          {totals['removed']:>5} ({totals['removed']/orig*100:.1f}%)")
    print(f"  Added by Florida: {totals['added']:>5}")

    if args.output:
        out_path = PROJECT_ROOT / args.output
        out_path.write_text(json.dumps({
            "totals": totals,
            "chapters": all_counts,
        }, indent=2) + "\n")
        print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()

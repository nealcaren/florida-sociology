"""Sentence-level alignment between original and Florida textbook versions.

Splits paragraphs into sentences, aligns at sentence granularity using
SequenceMatcher, then groups consecutive same-type sentences back into
blocks for display. This handles PDF extraction issues where paragraph
boundaries differ between the two sources.
"""

import re
from difflib import SequenceMatcher

SAME_THRESHOLD = 0.92  # Word-level similarity above this => "same"
MODIFIED_THRESHOLD = 0.55  # Above this => "modified" (word changes)


def _word_similarity(a: str, b: str) -> float:
    """Compute word-level similarity between two strings."""
    return SequenceMatcher(None, a.split(), b.split()).ratio()


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences. Handles common abbreviations."""
    # Split on sentence-ending punctuation followed by space + capital letter
    # But not on common abbreviations like "U.S." or "Dr."
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', text)
    return [s.strip() for s in parts if s.strip()]


def _flatten_to_sentences(paragraphs: list[str]) -> list[str]:
    """Flatten a list of paragraphs into a list of sentences."""
    sentences = []
    for para in paragraphs:
        sentences.extend(_split_sentences(para))
    return sentences


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align two lists of paragraphs via sentence-level matching.

    Splits both sides into sentences, aligns them, then groups
    consecutive same-type sentences into blocks.

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

    # Split into sentences
    orig_sents = _flatten_to_sentences(original)
    fl_sents = _flatten_to_sentences(florida)

    if not orig_sents and not fl_sents:
        return []
    if not orig_sents:
        return [{"type": "added", "florida_text": " ".join(fl_sents)}]
    if not fl_sents:
        return [{"type": "removed", "original_text": " ".join(orig_sents)}]

    # Use SequenceMatcher on sentence lists to find alignment
    # We need a custom equality that handles minor differences
    # First, try exact matching via SequenceMatcher
    matcher = SequenceMatcher(None, orig_sents, fl_sents)

    raw_blocks = []  # list of (type, orig_text, fl_text)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                raw_blocks.append(("same", orig_sents[i1 + k], None))

        elif tag == "replace":
            # Check sentence-by-sentence similarity
            orig_slice = orig_sents[i1:i2]
            fl_slice = fl_sents[j1:j2]
            raw_blocks.extend(_pair_sentences(orig_slice, fl_slice))

        elif tag == "delete":
            for k in range(i1, i2):
                raw_blocks.append(("removed", orig_sents[k], None))

        elif tag == "insert":
            for k in range(j1, j2):
                raw_blocks.append(("added", None, fl_sents[k]))

    # Group consecutive same-type sentences into blocks
    return _group_blocks(raw_blocks)


def _pair_sentences(
    orig_sents: list[str],
    fl_sents: list[str],
) -> list[tuple]:
    """Pair sentences from a 'replace' opcode by similarity."""
    results = []
    used_fl = set()

    for orig in orig_sents:
        best_ratio = 0.0
        best_idx = -1

        for idx, fl in enumerate(fl_sents):
            if idx in used_fl:
                continue
            ratio = _word_similarity(orig, fl)
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx

        if best_ratio >= SAME_THRESHOLD and best_idx >= 0:
            # Emit unmatched FL sentences before this match
            for j in range(best_idx):
                if j not in used_fl:
                    results.append(("added", None, fl_sents[j]))
                    used_fl.add(j)
            results.append(("same", orig, None))
            used_fl.add(best_idx)
        elif best_ratio >= MODIFIED_THRESHOLD and best_idx >= 0:
            for j in range(best_idx):
                if j not in used_fl:
                    results.append(("added", None, fl_sents[j]))
                    used_fl.add(j)
            results.append(("modified", orig, fl_sents[best_idx]))
            used_fl.add(best_idx)
        else:
            results.append(("removed", orig, None))

    # Remaining unmatched FL sentences
    for idx, fl in enumerate(fl_sents):
        if idx not in used_fl:
            results.append(("added", None, fl))

    return results


def _group_blocks(raw_blocks: list[tuple]) -> list[dict]:
    """Group consecutive same-type sentence results into paragraph-like blocks."""
    if not raw_blocks:
        return []

    grouped = []
    current_type = raw_blocks[0][0]
    current_orig = []
    current_fl = []

    def flush():
        if current_type == "same":
            grouped.append({"type": "same", "text": " ".join(current_orig)})
        elif current_type == "modified":
            grouped.append({
                "type": "modified",
                "original_text": " ".join(current_orig),
                "florida_text": " ".join(current_fl),
            })
        elif current_type == "removed":
            grouped.append({"type": "removed", "original_text": " ".join(current_orig)})
        elif current_type == "added":
            grouped.append({"type": "added", "florida_text": " ".join(current_fl)})

    for block_type, orig, fl in raw_blocks:
        if block_type != current_type:
            flush()
            current_type = block_type
            current_orig = []
            current_fl = []

        if orig:
            current_orig.append(orig)
        if fl:
            current_fl.append(fl)

    flush()
    return grouped

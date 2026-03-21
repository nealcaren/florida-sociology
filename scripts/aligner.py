"""Paragraph-level alignment between original and Florida textbook versions.

Handles the case where paragraph boundaries differ between sources:
CNXML source has proper paragraph breaks while PDF extraction often
merges multiple paragraphs into large text blocks. Uses word-level
subsequence matching to detect when an original paragraph's content
appears within a (potentially larger) Florida paragraph.
"""

import re
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.5
SAME_THRESHOLD = 0.95  # Word-level similarity above this => "same"
CONTAINMENT_THRESHOLD = 0.80  # Fraction of orig words found in FL paragraph


def _word_similarity(a: str, b: str) -> float:
    """Compute word-level similarity between two strings."""
    return SequenceMatcher(None, a.split(), b.split()).ratio()


def _containment_ratio(needle: str, haystack: str) -> float:
    """What fraction of needle's words appear (in order) in haystack?

    Uses LCS on word lists to handle minor word changes.
    """
    n_words = needle.lower().split()
    h_words = haystack.lower().split()
    if not n_words:
        return 0.0

    # LCS length
    matcher = SequenceMatcher(None, n_words, h_words)
    lcs_len = sum(block.size for block in matcher.get_matching_blocks())
    return lcs_len / len(n_words)


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align two lists of paragraphs, producing typed blocks.

    For each original paragraph, tries to find a Florida paragraph that
    contains its content (handling merged paragraphs in PDF extraction).

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

    # For each original paragraph, find the best matching Florida paragraph.
    # Use both word similarity and containment ratio (for merged FL paragraphs).
    matches = []  # (orig_idx, fl_idx, score, is_same)
    fl_matched_by = {}  # fl_idx -> list of orig_idx that matched it

    for i, orig in enumerate(original):
        best_score = 0.0
        best_j = -1

        for j, fl in enumerate(florida):
            # Try direct similarity
            sim = _word_similarity(orig, fl)

            # Try containment (orig paragraph contained within larger FL paragraph)
            cont = _containment_ratio(orig, fl)

            score = max(sim, cont)
            if score > best_score:
                best_score = score
                best_j = j

        if best_score >= CONTAINMENT_THRESHOLD and best_j >= 0:
            matches.append((i, best_j, best_score))
            fl_matched_by.setdefault(best_j, []).append(i)

    # Enforce monotonicity
    monotonic = []
    last_fl = -1
    for orig_idx, fl_idx, score in matches:
        if fl_idx >= last_fl:  # >= allows multiple orig to map to same fl
            monotonic.append((orig_idx, fl_idx, score))
            if fl_idx > last_fl:
                last_fl = fl_idx

    matched_orig = {}
    fl_used = set()
    for orig_idx, fl_idx, score in monotonic:
        matched_orig[orig_idx] = (fl_idx, score)
        fl_used.add(fl_idx)

    # Build output blocks
    blocks = []
    fl_cursor = 0

    for i, orig in enumerate(original):
        if i in matched_orig:
            fl_idx, score = matched_orig[i]

            # Emit unmatched Florida paragraphs before this match
            while fl_cursor < fl_idx:
                if fl_cursor not in fl_used:
                    blocks.append({"type": "added", "florida_text": florida[fl_cursor]})
                fl_cursor += 1

            # Check if this FL paragraph was matched by multiple orig paragraphs
            # If so, only emit it once as context
            fl_multi = fl_matched_by.get(fl_idx, [])
            is_first_match = (fl_multi[0] == i) if fl_multi else True

            # Determine block type
            direct_sim = _word_similarity(orig, florida[fl_idx])
            if direct_sim >= SAME_THRESHOLD:
                blocks.append({"type": "same", "text": orig})
            elif direct_sim >= SIMILARITY_THRESHOLD:
                blocks.append({
                    "type": "modified",
                    "original_text": orig,
                    "florida_text": florida[fl_idx] if is_first_match else None,
                })
            else:
                # Contained within but not directly similar (merged FL paragraph)
                blocks.append({
                    "type": "same",
                    "text": orig,
                })

            if fl_idx >= fl_cursor:
                fl_cursor = fl_idx + 1
        else:
            blocks.append({"type": "removed", "original_text": orig})

    # Emit remaining unmatched Florida paragraphs
    while fl_cursor < len(florida):
        if fl_cursor not in fl_used:
            blocks.append({"type": "added", "florida_text": florida[fl_cursor]})
        fl_cursor += 1

    # Clean up: remove None florida_text from modified blocks
    for block in blocks:
        if block.get("type") == "modified" and block.get("florida_text") is None:
            block["type"] = "same"
            block["text"] = block.pop("original_text")
            block.pop("florida_text", None)

    return blocks

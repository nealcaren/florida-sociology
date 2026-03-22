"""Sentence-level alignment between original and Florida textbook versions.

Strategy: split the original (clean CNXML) into sentences, then check
each sentence against the Florida text (noisy PDF) using containment
matching. This handles the common case where Florida's PDF extraction
merges multiple paragraphs/sentences into one large block.

For each original sentence, we search for it in the Florida full text.
If found with high similarity, it's "same". If found with moderate
similarity, it's "modified". If not found, it's "removed".
Any Florida text not covered by any original sentence is "added".
"""

import re
from difflib import SequenceMatcher

SAME_THRESHOLD = 0.90
MODIFIED_THRESHOLD = 0.55


def _word_similarity(a: str, b: str) -> float:
    """Compute word-level similarity ratio."""
    return SequenceMatcher(None, a.lower().split(), b.lower().split()).ratio()


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    # Split on sentence-ending punctuation followed by space + capital
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\u2018\u201c])', text)
    return [s.strip() for s in parts if s.strip() and len(s.strip()) > 5]


def _flatten_to_sentences(paragraphs: list[str]) -> list[str]:
    """Flatten paragraphs into sentences."""
    sentences = []
    for para in paragraphs:
        sentences.extend(_split_sentences(para))
    return sentences


def _find_best_match(sentence: str, candidates: list[str], min_threshold: float) -> tuple[int, float]:
    """Find the best matching candidate for a sentence.

    Returns (index, score) or (-1, 0.0) if no match found.
    """
    words = sentence.lower().split()
    if not words:
        return -1, 0.0

    best_idx = -1
    best_score = 0.0

    for idx, cand in enumerate(candidates):
        score = _word_similarity(sentence, cand)
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_score >= min_threshold:
        return best_idx, best_score
    return -1, 0.0


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align original paragraphs against Florida paragraphs.

    Splits both into sentences, matches original sentences against
    Florida sentences, and groups results into blocks.
    """
    if not original and not florida:
        return []
    if not florida:
        return [{"type": "removed", "original_text": " ".join(original)}]
    if not original:
        return [{"type": "added", "florida_text": " ".join(florida)}]

    orig_sents = _flatten_to_sentences(original)
    fl_sents = _flatten_to_sentences(florida)

    if not orig_sents and not fl_sents:
        return []
    if not orig_sents:
        return [{"type": "added", "florida_text": " ".join(florida)}]
    if not fl_sents:
        return [{"type": "removed", "original_text": " ".join(original)}]

    # For each original sentence, find the best matching Florida sentence.
    # Use greedy matching that respects ordering.
    raw_blocks = []  # (type, orig_text, fl_text)
    fl_used = set()
    fl_search_start = 0  # enforce rough ordering

    for orig_sent in orig_sents:
        best_idx = -1
        best_score = 0.0

        # Search Florida sentences from current position
        for j in range(len(fl_sents)):
            if j in fl_used:
                continue
            score = _word_similarity(orig_sent, fl_sents[j])
            if score > best_score:
                best_score = score
                best_idx = j

        if best_score >= SAME_THRESHOLD and best_idx >= 0:
            # Emit unmatched FL sentences before this match as "added"
            for j in range(fl_search_start, best_idx):
                if j not in fl_used:
                    raw_blocks.append(("added", None, fl_sents[j]))
                    fl_used.add(j)
            raw_blocks.append(("same", orig_sent, None))
            fl_used.add(best_idx)
            fl_search_start = best_idx + 1

        elif best_score >= MODIFIED_THRESHOLD and best_idx >= 0:
            for j in range(fl_search_start, best_idx):
                if j not in fl_used:
                    raw_blocks.append(("added", None, fl_sents[j]))
                    fl_used.add(j)
            raw_blocks.append(("modified", orig_sent, fl_sents[best_idx]))
            fl_used.add(best_idx)
            fl_search_start = best_idx + 1

        else:
            raw_blocks.append(("removed", orig_sent, None))

    # Emit remaining unmatched Florida sentences
    for j in range(len(fl_sents)):
        if j not in fl_used:
            raw_blocks.append(("added", None, fl_sents[j]))

    # Post-process: remove "added" fragments that are contained within
    # matched original or Florida sentences (PDF extraction artifacts)
    matched_texts = set()
    for btype, orig, fl in raw_blocks:
        if btype in ("same", "modified"):
            if orig:
                matched_texts.add(orig.lower())
            if fl:
                matched_texts.add(fl.lower())

    filtered = []
    for btype, orig, fl in raw_blocks:
        if btype == "added" and fl:
            fl_words = fl.lower().split()
            # Check if this fragment's words are mostly contained in any matched text
            if len(fl_words) >= 3:
                absorbed = False
                for matched in matched_texts:
                    m_words = matched.split()
                    matcher = SequenceMatcher(None, fl_words, m_words)
                    lcs = sum(b.size for b in matcher.get_matching_blocks())
                    if lcs / len(fl_words) >= 0.8:
                        absorbed = True
                        break
                if absorbed:
                    continue
        if btype == "removed" and orig:
            orig_words = orig.lower().split()
            if len(orig_words) >= 3:
                absorbed = False
                for matched in matched_texts:
                    m_words = matched.split()
                    matcher = SequenceMatcher(None, orig_words, m_words)
                    lcs = sum(b.size for b in matcher.get_matching_blocks())
                    if lcs / len(orig_words) >= 0.8:
                        absorbed = True
                        break
                if absorbed:
                    continue
        filtered.append((btype, orig, fl))

    return _group_blocks(filtered)


def _group_blocks(raw_blocks: list[tuple]) -> list[dict]:
    """Group consecutive same-type results into blocks."""
    if not raw_blocks:
        return []

    grouped = []
    current_type = raw_blocks[0][0]
    current_orig = []
    current_fl = []

    def flush():
        if not current_orig and not current_fl:
            return
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

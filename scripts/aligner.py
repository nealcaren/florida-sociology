"""Sentence-level alignment with paragraph-aware grouping.

Strategy:
1. Split original paragraphs into sentences (preserving which paragraph each came from)
2. Concatenate Florida text and split into sentences
3. Match each original sentence to the best Florida sentence
4. Group consecutive same-type sentences, inserting paragraph breaks
   from the original CNXML structure
"""

import re
from difflib import SequenceMatcher

import nltk
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)
from nltk.tokenize import sent_tokenize


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using nltk's trained tokenizer."""
    sents = sent_tokenize(text)
    return [s.strip() for s in sents if s.strip() and len(s.strip()) > 5]


def _word_sim(a: str, b: str) -> float:
    """Word-level similarity ratio."""
    return SequenceMatcher(None, a.lower().split(), b.lower().split()).ratio()


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align at sentence level, group by original paragraph structure."""
    if not original and not florida:
        return []
    if not florida or not " ".join(florida).strip():
        return [{"type": "removed", "original_text": "\n\n".join(original)}]
    if not original or not " ".join(original).strip():
        return [{"type": "added", "florida_text": " ".join(florida)}]

    # Split original into sentences, tracking paragraph boundaries
    orig_sents = []  # (sentence_text, para_idx)
    for pi, para in enumerate(original):
        for sent in _split_sentences(para):
            orig_sents.append((sent, pi))

    # Split Florida into sentences (flat list)
    fl_text = " ".join(florida)
    fl_sents = _split_sentences(fl_text)

    if not orig_sents:
        return [{"type": "removed", "original_text": "\n\n".join(original)}]
    if not fl_sents:
        return [{"type": "removed", "original_text": "\n\n".join(original)}]

    # Match each original sentence to the best Florida sentence
    # Greedy, roughly order-preserving
    SAME_THRESH = 0.98
    MOD_THRESH = 0.5

    fl_used = set()
    matches = []  # (orig_idx, match_type, fl_idx_or_none)

    for oi, (orig_sent, _) in enumerate(orig_sents):
        best_score = 0.0
        best_j = -1

        for j, fl_sent in enumerate(fl_sents):
            if j in fl_used:
                continue
            score = _word_sim(orig_sent, fl_sent)
            if score > best_score:
                best_score = score
                best_j = j

        if best_score >= SAME_THRESH and best_j >= 0:
            matches.append((oi, "same", best_j))
            fl_used.add(best_j)
        elif best_score >= MOD_THRESH and best_j >= 0:
            matches.append((oi, "modified", best_j))
            fl_used.add(best_j)
        else:
            matches.append((oi, "removed", None))

    # Build raw result list with paragraph break markers,
    # interleaving unmatched Florida sentences at their natural positions
    raw = []
    last_para = -1
    fl_emitted = set()

    for oi, match_type, fl_idx in matches:
        orig_sent, para_idx = orig_sents[oi]
        new_para = (para_idx != last_para)
        last_para = para_idx

        # Before emitting this match, emit any unmatched FL sentences
        # that come before the matched FL sentence
        if fl_idx is not None:
            for j in range(fl_idx):
                if j not in fl_used and j not in fl_emitted:
                    raw.append(("added", None, fl_sents[j], False))
                    fl_emitted.add(j)

        if match_type == "same":
            raw.append(("same", orig_sent, None, new_para))
        elif match_type == "modified":
            raw.append(("modified", orig_sent, fl_sents[fl_idx], new_para))
        elif match_type == "removed":
            raw.append(("removed", orig_sent, None, new_para))

        if fl_idx is not None:
            fl_emitted.add(fl_idx)

    # Emit remaining unmatched FL sentences at the end
    for j in range(len(fl_sents)):
        if j not in fl_used and j not in fl_emitted:
            raw.append(("added", None, fl_sents[j], False))

    # Group consecutive same-type entries into blocks, respecting paragraph breaks
    blocks = _group_into_blocks(raw)

    # Post-process: if mostly unmatched, collapse
    if len(blocks) > 4:
        same_mod = sum(1 for b in blocks if b["type"] in ("same", "modified"))
        total = len(blocks)
        if same_mod / total < 0.3:
            return [
                {"type": "removed", "original_text": "\n\n".join(original)},
                {"type": "added", "florida_text": " ".join(florida)},
            ]

    return blocks


def _group_into_blocks(raw: list[tuple]) -> list[dict]:
    """Group consecutive same-type sentences into blocks.

    Inserts paragraph breaks (\n\n) when the original had a paragraph
    boundary between sentences, but only within same-type runs.
    """
    if not raw:
        return []

    blocks = []
    current_type = raw[0][0]
    current_orig_parts = []
    current_fl_parts = []

    def flush():
        if not current_orig_parts and not current_fl_parts:
            return
        orig_text = "\n\n".join(" ".join(group) for group in current_orig_parts if group)
        fl_text = " ".join(s for group in current_fl_parts for s in group)

        if current_type == "same" and orig_text:
            blocks.append({"type": "same", "text": orig_text})
        elif current_type == "modified" and orig_text:
            blocks.append({
                "type": "modified",
                "original_text": orig_text,
                "florida_text": fl_text,
            })
        elif current_type == "removed" and orig_text:
            blocks.append({"type": "removed", "original_text": orig_text})

    # Track sentences grouped by paragraph
    current_para_orig = []
    current_para_fl = []

    for entry_type, orig_text, fl_text, new_para in raw:
        if entry_type != current_type:
            # Type changed — flush current paragraph group and block
            if current_para_orig or current_para_fl:
                current_orig_parts.append(current_para_orig)
                current_fl_parts.append(current_para_fl)
            flush()
            current_type = entry_type
            current_orig_parts = []
            current_fl_parts = []
            current_para_orig = [orig_text] if orig_text else []
            current_para_fl = [fl_text] if fl_text else []
        else:
            if new_para and (current_para_orig or current_para_fl):
                # Same type but new paragraph — save current para group
                current_orig_parts.append(current_para_orig)
                current_fl_parts.append(current_para_fl)
                current_para_orig = []
                current_para_fl = []

            if orig_text:
                current_para_orig.append(orig_text)
            if fl_text:
                current_para_fl.append(fl_text)

    # Flush remaining
    if current_para_orig or current_para_fl:
        current_orig_parts.append(current_para_orig)
        current_fl_parts.append(current_para_fl)
    flush()

    return blocks

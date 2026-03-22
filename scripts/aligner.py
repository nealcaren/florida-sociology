"""Word-level alignment between original and Florida textbook versions.

Strategy: treat each section's text as a single stream of words,
use SequenceMatcher to find the longest common subsequences, then
segment the diff output into same/modified/removed/added blocks
based on runs of matching vs non-matching words.

This avoids the fragile sentence/paragraph boundary detection that
fails when PDF extraction merges or splits text differently.
"""

import re
from difflib import SequenceMatcher


def _tokenize(text: str) -> list[str]:
    """Split text into words, preserving punctuation as part of words."""
    return text.split()


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align original and Florida text at the word level.

    Joins all paragraphs into a single word stream, diffs them,
    then segments into blocks.
    """
    if not original and not florida:
        return []

    orig_text = " ".join(original)
    fl_text = " ".join(florida)

    if not orig_text.strip() and not fl_text.strip():
        return []
    if not fl_text.strip():
        return [{"type": "removed", "original_text": orig_text}]
    if not orig_text.strip():
        return [{"type": "added", "florida_text": fl_text}]

    orig_words = _tokenize(orig_text)
    fl_words = _tokenize(fl_text)

    matcher = SequenceMatcher(None, orig_words, fl_words, autojunk=False)
    opcodes = matcher.get_opcodes()

    # Build a list of (type, orig_words, fl_words) segments
    segments = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            segments.append(("same", orig_words[i1:i2], []))
        elif tag == "replace":
            segments.append(("modified", orig_words[i1:i2], fl_words[j1:j2]))
        elif tag == "delete":
            segments.append(("removed", orig_words[i1:i2], []))
        elif tag == "insert":
            segments.append(("added", [], fl_words[j1:j2]))

    # Merge small segments into neighbors to avoid word-level noise.
    # A "modified" segment of just 1-2 words surrounded by "same" segments
    # is better merged into a single "modified" block with its neighbors.
    merged = _merge_small_segments(segments)

    # Convert to output blocks
    return _segments_to_blocks(merged)


def _merge_small_segments(segments: list[tuple], min_same_words: int = 30) -> list[tuple]:
    """Merge small segments to create readable blocks.

    The word-level diff produces very fine-grained segments. We merge
    aggressively: any "same" segment shorter than min_same_words gets
    absorbed into the surrounding diff context, creating larger but
    more readable modified blocks.

    The goal is blocks that correspond roughly to sentences or short
    paragraphs, not individual words.
    """
    if len(segments) <= 1:
        return segments

    # Pass 1: absorb small "same" segments between diff segments
    # This is the key step — it turns word-level diffs into sentence-level blocks
    result = []
    for seg_type, orig_w, fl_w in segments:
        if seg_type == "same" and len(orig_w) < min_same_words and result:
            # Check if previous segment was a diff
            if result[-1][0] != "same":
                # Absorb into previous diff as shared context
                prev_type, prev_orig, prev_fl = result[-1]
                result[-1] = ("modified", prev_orig + orig_w, prev_fl + orig_w)
                continue
        result.append((seg_type, list(orig_w), list(fl_w)))

    # Pass 2: absorb small diff segments (< min_diff_words) into a modified
    # block with their surrounding same context.
    # "same(100w) → added(1w 'almost') → same(100w)" becomes one modified block.
    min_diff_words = 15
    result2 = []
    i = 0
    while i < len(result):
        seg_type, orig_w, fl_w = result[i]
        if seg_type != "same" and max(len(orig_w), len(fl_w)) < min_diff_words:
            # Small diff — merge with previous same (as context) and following same
            # Take up to 30 words of context from each side
            ctx = 30
            if result2 and result2[-1][0] == "same":
                prev_type, prev_orig, prev_fl = result2.pop()
                # Split: keep first part as same, use last ctx words as context
                if len(prev_orig) > ctx:
                    result2.append(("same", prev_orig[:-ctx], []))
                    context_before_o = prev_orig[-ctx:]
                    context_before_f = prev_fl[-ctx:] if prev_fl else prev_orig[-ctx:]
                else:
                    context_before_o = prev_orig
                    context_before_f = prev_fl if prev_fl else prev_orig
            else:
                context_before_o = []
                context_before_f = []

            # Build the modified block
            mod_orig = context_before_o + orig_w
            mod_fl = context_before_f + fl_w

            # Absorb following same context too
            if i + 1 < len(result) and result[i + 1][0] == "same":
                next_type, next_orig, next_fl = result[i + 1]
                if len(next_orig) > ctx:
                    mod_orig += next_orig[:ctx]
                    mod_fl += next_orig[:ctx]  # same words go to both
                    result[i + 1] = ("same", next_orig[ctx:], next_fl[ctx:] if next_fl else [])
                else:
                    mod_orig += next_orig
                    mod_fl += next_orig
                    i += 1  # skip the consumed same segment

            result2.append(("modified", mod_orig, mod_fl))
        else:
            result2.append((seg_type, orig_w, fl_w))
        i += 1

    # Pass 3: merge consecutive non-same segments
    merged = []
    for seg_type, orig_w, fl_w in result2:
        if merged and merged[-1][0] == seg_type:
            prev_type, prev_orig, prev_fl = merged[-1]
            merged[-1] = (seg_type, prev_orig + orig_w, prev_fl + fl_w)
        elif merged and seg_type != "same" and merged[-1][0] != "same":
            # Merge adjacent diff types into "modified"
            prev_type, prev_orig, prev_fl = merged[-1]
            merged[-1] = ("modified", prev_orig + orig_w, prev_fl + fl_w)
        else:
            merged.append((seg_type, orig_w, fl_w))

    return merged


def _segments_to_blocks(segments: list[tuple]) -> list[dict]:
    """Convert merged word segments into output blocks."""
    blocks = []

    for seg_type, orig_words, fl_words in segments:
        orig_text = " ".join(orig_words).strip()
        fl_text = " ".join(fl_words).strip()

        if seg_type == "same" and orig_text:
            blocks.append({"type": "same", "text": orig_text})
        elif seg_type == "modified" and (orig_text or fl_text):
            block = {"type": "modified"}
            if orig_text:
                block["original_text"] = orig_text
            if fl_text:
                block["florida_text"] = fl_text
            # If one side is empty, it's really removed/added
            if not fl_text:
                block = {"type": "removed", "original_text": orig_text}
            elif not orig_text:
                block = {"type": "added", "florida_text": fl_text}
            blocks.append(block)
        elif seg_type == "removed" and orig_text:
            blocks.append({"type": "removed", "original_text": orig_text})
        elif seg_type == "added" and fl_text:
            blocks.append({"type": "added", "florida_text": fl_text})

    return blocks

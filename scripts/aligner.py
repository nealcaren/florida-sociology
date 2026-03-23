"""Word-level alignment between original and Florida textbook versions.

Strategy: treat each section's text as a single stream of words,
use SequenceMatcher to find the longest common subsequences, then
segment the diff output into same/modified/removed/added blocks.

Preserves paragraph breaks from the original (CNXML) source so
the output reads like natural paragraphs, not one long text wall.
"""

import re
from difflib import SequenceMatcher


def _tokenize_with_breaks(paragraphs: list[str]) -> tuple[list[str], set[int]]:
    """Tokenize paragraphs into words, tracking paragraph break positions.

    Returns (words, break_positions) where break_positions is the set of
    word indices where a new paragraph starts.
    """
    words = []
    breaks = set()
    for para in paragraphs:
        if words:
            breaks.add(len(words))
        words.extend(para.split())
    return words, breaks


def _words_to_text(words: list[str], break_positions: set[int], offset: int = 0) -> str:
    """Join words into text, inserting \\n\\n at original paragraph boundaries."""
    if not words:
        return ""
    parts = []
    for i, word in enumerate(words):
        if (offset + i) in break_positions and parts:
            parts.append("\n\n")
        elif parts:
            parts.append(" ")
        parts.append(word)
    return "".join(parts)


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align original and Florida text at the word level.

    Preserves paragraph breaks from the original (CNXML) source.
    """
    if not original and not florida:
        return []

    orig_joined = " ".join(original)
    fl_joined = " ".join(florida)

    if not orig_joined.strip() and not fl_joined.strip():
        return []
    if not fl_joined.strip():
        return [{"type": "removed", "original_text": "\n\n".join(original)}]
    if not orig_joined.strip():
        return [{"type": "added", "florida_text": fl_joined}]

    orig_words, orig_breaks = _tokenize_with_breaks(original)
    fl_words = fl_joined.split()

    matcher = SequenceMatcher(None, orig_words, fl_words, autojunk=False)
    opcodes = matcher.get_opcodes()

    # Build segments: (type, orig_start, orig_words, fl_words)
    segments = []
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            segments.append(("same", i1, orig_words[i1:i2], []))
        elif tag == "replace":
            segments.append(("modified", i1, orig_words[i1:i2], fl_words[j1:j2]))
        elif tag == "delete":
            segments.append(("removed", i1, orig_words[i1:i2], []))
        elif tag == "insert":
            segments.append(("added", i1, [], fl_words[j1:j2]))

    # Merge small segments to avoid word-level noise
    merged = _merge_small_segments(segments)

    # Convert to output blocks with paragraph breaks
    return _segments_to_blocks(merged, orig_breaks)


def _merge_small_segments(segments: list[tuple], min_same_words: int = 40) -> list[tuple]:
    """Merge small segments to create readable blocks.

    Input/output: list of (type, orig_start, orig_words, fl_words).
    """
    if len(segments) <= 1:
        return segments

    # Pass 1: absorb small "same" segments between diff segments
    result = []
    for seg_type, orig_start, orig_w, fl_w in segments:
        if seg_type == "same" and len(orig_w) < min_same_words and result:
            if result[-1][0] != "same":
                prev_type, prev_start, prev_orig, prev_fl = result[-1]
                result[-1] = ("modified", prev_start, prev_orig + list(orig_w), prev_fl + list(orig_w))
                continue
        result.append((seg_type, orig_start, list(orig_w), list(fl_w)))

    # Pass 2: absorb small diff segments with surrounding same context
    min_diff_words = 15
    ctx = 30
    result2 = []
    i = 0
    while i < len(result):
        seg_type, orig_start, orig_w, fl_w = result[i]
        if seg_type != "same" and max(len(orig_w), len(fl_w)) < min_diff_words:
            if result2 and result2[-1][0] == "same":
                prev_type, prev_start, prev_orig, prev_fl = result2.pop()
                if len(prev_orig) > ctx:
                    result2.append(("same", prev_start, prev_orig[:-ctx], []))
                    context_o = prev_orig[-ctx:]
                else:
                    context_o = prev_orig
            else:
                context_o = []

            mod_orig = context_o + orig_w
            mod_fl = list(context_o) + fl_w

            if i + 1 < len(result) and result[i + 1][0] == "same":
                next_type, next_start, next_orig, next_fl = result[i + 1]
                if len(next_orig) > ctx:
                    mod_orig += next_orig[:ctx]
                    mod_fl += next_orig[:ctx]
                    result[i + 1] = ("same", next_start + ctx, next_orig[ctx:], [])
                else:
                    mod_orig += next_orig
                    mod_fl += next_orig
                    i += 1

            # Calculate the start position for paragraph break tracking
            mod_start = orig_start - len(context_o) if context_o else orig_start
            result2.append(("modified", mod_start, mod_orig, mod_fl))
        else:
            result2.append((seg_type, orig_start, orig_w, fl_w))
        i += 1

    # Pass 3: merge consecutive non-same segments
    merged = []
    for seg_type, orig_start, orig_w, fl_w in result2:
        if merged and merged[-1][0] == seg_type:
            prev_type, prev_start, prev_orig, prev_fl = merged[-1]
            merged[-1] = (seg_type, prev_start, prev_orig + orig_w, prev_fl + fl_w)
        elif merged and seg_type != "same" and merged[-1][0] != "same":
            prev_type, prev_start, prev_orig, prev_fl = merged[-1]
            merged[-1] = ("modified", prev_start, prev_orig + orig_w, prev_fl + fl_w)
        else:
            merged.append((seg_type, orig_start, orig_w, fl_w))

    return merged


def _segments_to_blocks(segments: list[tuple], orig_breaks: set[int]) -> list[dict]:
    """Convert merged word segments into output blocks with paragraph breaks."""
    blocks = []

    for seg_type, orig_start, orig_words, fl_words in segments:
        orig_text = _words_to_text(orig_words, orig_breaks, orig_start)
        fl_text = " ".join(fl_words).strip()

        if seg_type == "same" and orig_text:
            blocks.append({"type": "same", "text": orig_text})
        elif seg_type == "modified" and (orig_text or fl_text):
            if not fl_text:
                blocks.append({"type": "removed", "original_text": orig_text})
            elif not orig_text:
                blocks.append({"type": "added", "florida_text": fl_text})
            else:
                # If the word counts are very lopsided (>4:1 ratio),
                # the word diff would be unreadable — split into
                # separate removed + added blocks instead
                ow = len(orig_words)
                fw = len(fl_words)
                ratio = max(ow, fw) / max(min(ow, fw), 1)
                if ratio > 4 and max(ow, fw) > 50:
                    blocks.append({"type": "removed", "original_text": orig_text})
                    blocks.append({"type": "added", "florida_text": fl_text})
                else:
                    blocks.append({
                        "type": "modified",
                        "original_text": orig_text,
                        "florida_text": fl_text,
                    })
        elif seg_type == "removed" and orig_text:
            blocks.append({"type": "removed", "original_text": orig_text})
        elif seg_type == "added" and fl_text:
            blocks.append({"type": "added", "florida_text": fl_text})

    return blocks

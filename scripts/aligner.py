"""Paragraph-preserving alignment between original and Florida textbook versions.

Strategy:
1. Concatenate all text from both sides into word streams
2. Use SequenceMatcher to find word-level correspondences
3. Map each original paragraph to the Florida words it corresponds to
4. Output one block per original paragraph (preserving CNXML structure)
5. Any Florida-only content emitted as "added" blocks between paragraphs
"""

from difflib import SequenceMatcher


def align_paragraphs(
    original: list[str],
    florida: list[str],
) -> list[dict]:
    """Align original paragraphs against Florida text.

    Each original paragraph becomes one output block, preserving
    the CNXML paragraph structure. Changes are shown inline.
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

    # Build word lists with paragraph boundary tracking
    orig_words = []
    orig_para_ranges = []  # (start_idx, end_idx) for each paragraph
    for para in original:
        start = len(orig_words)
        words = para.split()
        orig_words.extend(words)
        orig_para_ranges.append((start, len(orig_words)))

    fl_words = fl_joined.split()

    # Get word-level alignment
    matcher = SequenceMatcher(None, orig_words, fl_words, autojunk=False)
    opcodes = matcher.get_opcodes()

    # For each original word, record what Florida word(s) it maps to
    # Build a mapping: orig_word_idx -> (tag, fl_start, fl_end)
    orig_word_map = {}  # orig_idx -> ("equal"|"replace"|"delete", fl_range)
    fl_covered = set()  # Florida word indices that are covered

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            for k in range(i2 - i1):
                orig_word_map[i1 + k] = ("equal", j1 + k, j1 + k + 1)
                fl_covered.add(j1 + k)
        elif tag == "replace":
            # Map the original words to the Florida replacement range
            for k in range(i2 - i1):
                orig_word_map[i1 + k] = ("replace", j1, j2)
            for k in range(j1, j2):
                fl_covered.add(k)
        elif tag == "delete":
            for k in range(i2 - i1):
                orig_word_map[i1 + k] = ("delete", -1, -1)
        elif tag == "insert":
            for k in range(j1, j2):
                fl_covered.add(k)

    # Now build output: one block per original paragraph
    blocks = []
    fl_emitted_up_to = 0  # track Florida words we've accounted for

    for para_idx, (p_start, p_end) in enumerate(orig_para_ranges):
        para_text = " ".join(orig_words[p_start:p_end])

        # Find the Florida word range this paragraph maps to
        fl_min = None
        fl_max = None
        has_changes = False

        for oi in range(p_start, p_end):
            if oi in orig_word_map:
                tag, fs, fe = orig_word_map[oi]
                if tag == "equal":
                    if fl_min is None or fs < fl_min:
                        fl_min = fs
                    if fl_max is None or fe > fl_max:
                        fl_max = fe
                elif tag == "replace":
                    has_changes = True
                    if fl_min is None or fs < fl_min:
                        fl_min = fs
                    if fl_max is None or fe > fl_max:
                        fl_max = fe
                elif tag == "delete":
                    has_changes = True

        # Emit any Florida-only content before this paragraph's range
        if fl_min is not None and fl_emitted_up_to < fl_min:
            gap_words = fl_words[fl_emitted_up_to:fl_min]
            # Check if any of these words are uncovered (truly added)
            added_words = [fl_words[k] for k in range(fl_emitted_up_to, fl_min) if k not in fl_covered]
            if added_words and len(added_words) > 3:
                blocks.append({"type": "added", "florida_text": " ".join(added_words)})

        if fl_min is None:
            # No Florida correspondence at all — paragraph was removed
            blocks.append({"type": "removed", "original_text": para_text})
        elif not has_changes:
            # All words matched — paragraph is the same
            blocks.append({"type": "same", "text": para_text})
        else:
            # Has changes — emit as modified with the corresponding Florida text
            fl_para_text = " ".join(fl_words[fl_min:fl_max])

            # Check if the texts are too different for a meaningful word diff.
            # If similarity is low, it's a replacement — show as removed + added.
            # If lopsided word counts, also split.
            ow = p_end - p_start
            fw = fl_max - fl_min
            ratio = max(ow, fw) / max(min(ow, fw), 1)
            similarity = SequenceMatcher(None, para_text.split(), fl_para_text.split()).ratio()

            if (ratio > 4 and max(ow, fw) > 50) or similarity < 0.5:
                blocks.append({"type": "removed", "original_text": para_text})
                blocks.append({"type": "added", "florida_text": fl_para_text})
            else:
                blocks.append({
                    "type": "modified",
                    "original_text": para_text,
                    "florida_text": fl_para_text,
                })

        if fl_max is not None:
            fl_emitted_up_to = max(fl_emitted_up_to, fl_max)

    # Emit any remaining Florida content after the last paragraph
    if fl_emitted_up_to < len(fl_words):
        remaining = [fl_words[k] for k in range(fl_emitted_up_to, len(fl_words)) if k not in fl_covered]
        if remaining and len(remaining) > 3:
            blocks.append({"type": "added", "florida_text": " ".join(remaining)})

    return blocks

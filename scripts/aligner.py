"""Paragraph-level alignment between original and Florida textbook versions."""

from difflib import SequenceMatcher

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

    matcher = SequenceMatcher(None, original, florida)
    blocks = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                blocks.append({"type": "same", "text": original[i1 + k]})

        elif tag == "replace":
            orig_slice = original[i1:i2]
            fl_slice = florida[j1:j2]
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

    for idx, fl in enumerate(fl_paragraphs):
        if idx not in used_fl:
            results.append({"type": "added", "florida_text": fl})

    return results

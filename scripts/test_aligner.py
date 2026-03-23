"""Tests for word-level alignment logic."""
from aligner import align_paragraphs

def test_identical_paragraphs():
    original = ["Hello world.", "Second paragraph."]
    florida = ["Hello world.", "Second paragraph."]
    blocks = align_paragraphs(original, florida)
    assert all(b["type"] == "same" for b in blocks)
    combined = " ".join(b["text"] for b in blocks)
    assert "Hello world." in combined
    assert "Second paragraph." in combined

def test_removed_text():
    original = ["Keep this. Remove this entirely. Keep this too."]
    florida = ["Keep this. Keep this too."]
    blocks = align_paragraphs(original, florida)
    # Should have same text and some removed/modified text
    all_text = " ".join(
        b.get("text", "") + b.get("original_text", "")
        for b in blocks
    )
    assert "Keep this." in all_text
    assert "Remove this entirely." in all_text or "Remove" in all_text

def test_replacement_shows_as_removed_plus_added():
    """When text is replaced (low similarity), show as removed + added, not modified."""
    original = ["Critical sociology focuses on deconstruction of existing sociological research and theory."]
    florida = ["Other frameworks in sociology describe and analytically investigate various social phenomena."]
    blocks = align_paragraphs(original, florida)
    types = [b["type"] for b in blocks]
    # Low similarity → should NOT be a single modified block with interleaved diff
    assert "modified" not in types or len(blocks) > 1

def test_modified_text():
    original = ["The sociologist studied race and class."]
    florida = ["The sociologist studied class and economics."]
    blocks = align_paragraphs(original, florida)
    # Should detect the word-level change
    has_mod = any(b["type"] == "modified" for b in blocks)
    assert has_mod

def test_all_removed():
    """For removed chapters, all text appears as removed."""
    original = ["Para one.", "Para two."]
    florida = []
    blocks = align_paragraphs(original, florida)
    assert all(b["type"] == "removed" for b in blocks)

def test_empty_both():
    blocks = align_paragraphs([], [])
    assert blocks == []

def test_cross_paragraph_match():
    """Text that's in different paragraphs should still match."""
    original = ["First sentence.", "Second sentence."]
    florida = ["First sentence. Second sentence."]  # merged into one paragraph
    blocks = align_paragraphs(original, florida)
    assert all(b["type"] == "same" for b in blocks)

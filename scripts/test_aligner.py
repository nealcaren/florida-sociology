"""Tests for paragraph alignment logic."""
from aligner import align_paragraphs

def test_identical_paragraphs():
    original = ["Hello world.", "Second paragraph."]
    florida = ["Hello world.", "Second paragraph."]
    blocks = align_paragraphs(original, florida)
    assert all(b["type"] == "same" for b in blocks)
    # Sentence-level aligner groups consecutive same sentences
    combined = " ".join(b["text"] for b in blocks)
    assert "Hello world." in combined
    assert "Second paragraph." in combined

def test_removed_paragraph():
    original = ["Keep this.", "Remove this.", "Keep this too."]
    florida = ["Keep this.", "Keep this too."]
    blocks = align_paragraphs(original, florida)
    types = [b["type"] for b in blocks]
    assert "same" in types
    assert "removed" in types
    removed = [b for b in blocks if b["type"] == "removed"]
    assert len(removed) == 1
    assert removed[0]["original_text"] == "Remove this."

def test_added_paragraph():
    original = ["Keep this.", "Keep this too."]
    florida = ["Keep this.", "New content.", "Keep this too."]
    blocks = align_paragraphs(original, florida)
    added = [b for b in blocks if b["type"] == "added"]
    assert len(added) == 1
    assert added[0]["florida_text"] == "New content."

def test_modified_paragraph():
    original = ["The sociologist studied race and class."]
    florida = ["The sociologist studied class and economics."]
    blocks = align_paragraphs(original, florida)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "modified"
    assert blocks[0]["original_text"] == "The sociologist studied race and class."
    assert blocks[0]["florida_text"] == "The sociologist studied class and economics."

def test_all_removed():
    """For removed chapters, all paragraphs appear as removed."""
    original = ["Para one.", "Para two."]
    florida = []
    blocks = align_paragraphs(original, florida)
    assert all(b["type"] == "removed" for b in blocks)

def test_empty_both():
    blocks = align_paragraphs([], [])
    assert blocks == []

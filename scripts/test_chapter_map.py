"""Tests for chapter mapping module."""
from chapter_map import CHAPTER_MAP, get_original_text_files, get_florida_text_file

def test_total_aligned_chapters():
    """17 aligned files: 21 original minus 4 merged-away stubs."""
    assert len(CHAPTER_MAP) == 17

def test_removed_chapters_have_no_florida():
    for ch in [8, 9, 10, 11, 12]:
        entry = CHAPTER_MAP[ch]
        assert entry["florida_text"] is None
        assert entry["type"] == "removed"

def test_merged_chapters():
    ch03 = CHAPTER_MAP[3]
    assert ch03["original_texts"] == ["text/original/ch03.txt", "text/original/ch04.txt"]
    assert ch03["florida_text"] == "text/florida/ch03.txt"
    assert ch03["type"] == "merged"

    ch14 = CHAPTER_MAP[14]
    assert ch14["original_texts"] == ["text/original/ch14.txt", "text/original/ch18.txt"]
    assert ch14["florida_text"] == "text/florida/ch09.txt"

    ch15 = CHAPTER_MAP[15]
    assert ch15["original_texts"] == ["text/original/ch15.txt", "text/original/ch16.txt", "text/original/ch17.txt"]
    assert ch15["florida_text"] == "text/florida/ch10.txt"

def test_renumbered_chapters():
    ch05 = CHAPTER_MAP[5]
    assert ch05["original_texts"] == ["text/original/ch05.txt"]
    assert ch05["florida_text"] == "text/florida/ch04.txt"
    assert ch05["type"] == "renumbered"

def test_one_to_one_chapters():
    ch01 = CHAPTER_MAP[1]
    assert ch01["original_texts"] == ["text/original/ch01.txt"]
    assert ch01["florida_text"] == "text/florida/ch01.txt"
    assert ch01["type"] == "matched"

def test_merged_away_stubs_not_in_map():
    for ch in [4, 16, 17, 18]:
        assert ch not in CHAPTER_MAP

def test_get_original_text_files():
    assert get_original_text_files(3) == ["text/original/ch03.txt", "text/original/ch04.txt"]

def test_get_florida_text_file():
    assert get_florida_text_file(3) == "text/florida/ch03.txt"
    assert get_florida_text_file(11) is None

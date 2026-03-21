"""Chapter mapping between original (1-21) and Florida (1-12) textbooks.

The original OpenStax has 21 chapters. Florida restructured to 12:
- 5 chapters removed entirely (8, 9, 10, 11, 12)
- 4 chapters merged into others (4→3, 16→15, 17→15, 18→14)
- Remaining chapters renumbered
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

CHAPTER_MAP = {
    1:  {"original_texts": ["text/original/ch01.txt"], "florida_text": "text/florida/ch01.txt",
         "type": "matched", "data_file": "data/ch01.json"},
    2:  {"original_texts": ["text/original/ch02.txt"], "florida_text": "text/florida/ch02.txt",
         "type": "matched", "data_file": "data/ch02.json"},
    3:  {"original_texts": ["text/original/ch03.txt", "text/original/ch04.txt"],
         "florida_text": "text/florida/ch03.txt",
         "type": "merged", "data_file": "data/ch03.json"},
    5:  {"original_texts": ["text/original/ch05.txt"], "florida_text": "text/florida/ch04.txt",
         "type": "renumbered", "data_file": "data/ch05.json"},
    6:  {"original_texts": ["text/original/ch06.txt"], "florida_text": "text/florida/ch07.txt",
         "type": "renumbered", "data_file": "data/ch06.json"},
    7:  {"original_texts": ["text/original/ch07.txt"], "florida_text": "text/florida/ch08.txt",
         "type": "renumbered", "data_file": "data/ch07.json"},
    8:  {"original_texts": ["text/original/ch08.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch08.json"},
    9:  {"original_texts": ["text/original/ch09.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch09.json"},
    10: {"original_texts": ["text/original/ch10.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch10.json"},
    11: {"original_texts": ["text/original/ch11.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch11.json"},
    12: {"original_texts": ["text/original/ch12.txt"], "florida_text": None,
         "type": "removed", "data_file": "data/ch12.json"},
    13: {"original_texts": ["text/original/ch13.txt"], "florida_text": "text/florida/ch05.txt",
         "type": "renumbered", "data_file": "data/ch13.json"},
    14: {"original_texts": ["text/original/ch14.txt", "text/original/ch18.txt"],
         "florida_text": "text/florida/ch09.txt",
         "type": "merged", "data_file": "data/ch14.json"},
    15: {"original_texts": ["text/original/ch15.txt", "text/original/ch16.txt", "text/original/ch17.txt"],
         "florida_text": "text/florida/ch10.txt",
         "type": "merged", "data_file": "data/ch15.json"},
    19: {"original_texts": ["text/original/ch19.txt"], "florida_text": "text/florida/ch06.txt",
         "type": "renumbered", "data_file": "data/ch19.json"},
    20: {"original_texts": ["text/original/ch20.txt"], "florida_text": "text/florida/ch11.txt",
         "type": "renumbered", "data_file": "data/ch20.json"},
    21: {"original_texts": ["text/original/ch21.txt"], "florida_text": "text/florida/ch12.txt",
         "type": "renumbered", "data_file": "data/ch21.json"},
}

MERGED_AWAY = {4: 3, 16: 15, 17: 15, 18: 14}


def get_original_text_files(chapter: int) -> list[str]:
    """Return list of original text file paths for a chapter."""
    return CHAPTER_MAP[chapter]["original_texts"]


def get_florida_text_file(chapter: int) -> str | None:
    """Return Florida text file path, or None if chapter was removed."""
    return CHAPTER_MAP[chapter]["florida_text"]

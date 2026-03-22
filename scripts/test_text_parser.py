"""Tests for text parsing utilities."""
from text_parser import split_paragraphs, detect_section_header, clean_text

def test_split_paragraphs_basic():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = split_paragraphs(text)
    assert len(result) == 3
    assert result[0] == "First paragraph."
    assert result[2] == "Third paragraph."

def test_split_paragraphs_joins_broken_lines():
    """PDF extraction breaks lines mid-sentence. These should be joined."""
    text = "This is a sentence that was\nbroken across two lines.\n\nNew paragraph here."
    result = split_paragraphs(text)
    assert len(result) == 2
    assert "broken across two lines." in result[0]

def test_detect_section_header():
    assert detect_section_header("2.1 Approaches to Sociological Research") == "2.1"
    assert detect_section_header("2.1   Approaches to Sociological Research ") == "2.1"
    assert detect_section_header("14.2 Some Section Title") == "14.2"
    assert detect_section_header("This is a regular paragraph.") is None
    assert detect_section_header("LEARNING OBJECTIVES") is None

def test_detect_section_header_intro():
    """Lines like 'INTRODUCTION' or 'Introduction' are section 'intro'."""
    assert detect_section_header("INTRODUCTION") == "intro"
    assert detect_section_header("Introduction") == "intro"

def test_clean_text_normalizes_whitespace():
    text = "Hello   world.  Multiple   spaces."
    assert clean_text(text) == "Hello world. Multiple spaces."

def test_clean_text_strips_figure_captions():
    """FIGURE lines from PDF extraction should be removed."""
    text = "FIGURE 2.1 Some caption here.\nCaption continued.\n\nActual paragraph text."
    result = clean_text(text)
    assert "FIGURE" not in result
    assert "Caption continued" not in result
    assert "Actual paragraph text." in result

def test_clean_text_strips_chapter_outline():
    """CHAPTER OUTLINE headers and learning objectives should be removed."""
    text = "CHAPTER OUTLINE\n2.1 Approaches\n2.2 Methods\nActual text."
    result = clean_text(text)
    assert "CHAPTER OUTLINE" not in result

def test_split_paragraphs_skips_empty():
    text = "First.\n\n\n\nSecond."
    result = split_paragraphs(text)
    assert len(result) == 2

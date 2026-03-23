# scripts/parse_cnxml.py
"""Parse OpenStax CNXML source into structured section/paragraph data."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

CNXML_NS = "http://cnx.rice.edu/cnxml"
MODULES_DIR = Path(__file__).parent.parent / "openstax-source" / "modules"

# Section classes to skip (not body content)
SKIP_SECTION_CLASSES = {
    "references",
    "further-research",
    "section-quiz",
    "short-answer",
    "section-summary",
    "section-exercises",
}

# Chapter number -> list of module IDs (first is intro, rest are numbered sections)
CHAPTER_MODULES = {
    1: ["m90141", "m90142", "m90143", "m90144", "m90145"],
    2: ["m90146", "m90147", "m90148", "m90149"],
    3: ["m90150", "m90151", "m90152", "m90153", "m90154"],
    4: ["m90155", "m90156", "m90157", "m90158"],
    5: ["m90159", "m90160", "m90161", "m90162", "m90163"],
    6: ["m90164", "m90165", "m90166", "m90180"],
    7: ["m90167", "m90168", "m90169", "m90170"],
    8: ["m90171", "m90172", "m90173", "m90181", "m90179"],
    9: ["m90182", "m90183", "m90184", "m90185", "m90186"],
    10: ["m90187", "m90188", "m90189", "m90190"],
    11: ["m90191", "m90192", "m90193", "m90194", "m90195", "m90196"],
    12: ["m90197", "m90198", "m90199", "m90200"],
    13: ["m90201", "m90202", "m90203", "m90204", "m90205"],
    14: ["m90206", "m90207", "m90208", "m90209"],
    15: ["m90210", "m90211", "m90212", "m90213"],
    16: ["m90214", "m90215", "m90216", "m90217"],
    17: ["m90218", "m90219", "m90220", "m90221", "m90222"],
    18: ["m90223", "m90224", "m90225", "m90226"],
    19: ["m90227", "m90228", "m90229", "m90230", "m90231", "m90232"],
    20: ["m90233", "m90234", "m90235", "m90236"],
    21: ["m90237", "m90238", "m90239", "m90240"],
}


def extract_text(element, include_notes: bool = False) -> str:
    """Recursively extract text from an element, including inline children."""
    skip_tags = {"figure", "table", "media", "list", "equation", "code"}
    if not include_notes:
        skip_tags.add("note")

    text = element.text or ""
    for child in element:
        tag = child.tag.replace(f"{{{CNXML_NS}}}", "")
        if tag in skip_tags:
            # Still get tail text after skipped elements
            text += child.tail or ""
            continue
        # For inline elements (term, emphasis, link, foreign, sub, sup, etc.), recurse
        text += extract_text(child, include_notes=include_notes)
        text += child.tail or ""
    return text


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def parse_module(module_id: str, include_notes: bool = False) -> dict:
    """Parse a single CNXML module into {title, paragraphs, subsections}.

    Returns:
        {
            "title": "Section Title",
            "paragraphs": ["para1", "para2", ...],
            "subsections": [
                {"title": "Subsection", "paragraphs": ["p1", "p2"]},
                ...
            ]
        }
    """
    path = MODULES_DIR / module_id / "index.cnxml"
    tree = ET.parse(path)
    root = tree.getroot()

    ns = {"cnx": CNXML_NS}

    title_el = root.find("cnx:title", ns)
    title = title_el.text if title_el is not None else module_id

    content = root.find("cnx:content", ns)
    if content is None:
        return {"title": title, "paragraphs": [], "subsections": []}

    result = {"title": title, "paragraphs": [], "subsections": []}

    for child in content:
        tag = child.tag.replace(f"{{{CNXML_NS}}}", "")
        if tag == "para":
            text = _normalize_whitespace(extract_text(child, include_notes=include_notes))
            if text:
                result["paragraphs"].append(text)
        elif tag == "note" and include_notes:
            # Extract text from note elements (sidebars, feature boxes)
            for note_child in child:
                note_tag = note_child.tag.replace(f"{{{CNXML_NS}}}", "")
                if note_tag == "para":
                    text = _normalize_whitespace(extract_text(note_child, include_notes=True))
                    if text:
                        result["paragraphs"].append(text)
                elif note_tag == "section":
                    subsec = _parse_section(note_child, ns, include_notes=True)
                    if subsec:
                        result["subsections"].append(subsec)
        elif tag == "section":
            sec_class = child.get("class", "")
            if sec_class in SKIP_SECTION_CLASSES:
                continue
            subsec = _parse_section(child, ns, include_notes=include_notes)
            if subsec:
                result["subsections"].append(subsec)

    return result


def _parse_section(section_el, ns, include_notes: bool = False) -> dict:
    """Parse a <section> element into {title, paragraphs}."""
    title_el = section_el.find("cnx:title", ns)
    title = title_el.text if title_el is not None else ""

    paragraphs = []
    for child in section_el:
        tag = child.tag.replace(f"{{{CNXML_NS}}}", "")
        if tag == "para":
            text = _normalize_whitespace(extract_text(child, include_notes=include_notes))
            if text:
                paragraphs.append(text)
        elif tag == "note" and include_notes:
            for note_child in child:
                note_tag = note_child.tag.replace(f"{{{CNXML_NS}}}", "")
                if note_tag == "para":
                    text = _normalize_whitespace(extract_text(note_child, include_notes=True))
                    if text:
                        paragraphs.append(text)
        elif tag == "section":
            sec_class = child.get("class", "")
            if sec_class in SKIP_SECTION_CLASSES:
                continue
            sub = _parse_section(child, ns, include_notes=include_notes)
            if sub["paragraphs"]:
                paragraphs.extend(sub["paragraphs"])

    return {"title": title, "paragraphs": paragraphs}


def get_chapter_sections(chapter: int, include_notes: bool = False) -> list[dict]:
    """Get all sections for a chapter from CNXML source.

    Returns list of dicts matching the format expected by align_texts.py:
        [
            {"section_id": "intro", "heading": "Introduction", "paragraphs": [...]},
            {"section_id": "2.1", "heading": "2.1 Approaches to...", "paragraphs": [...]},
            ...
        ]
    """
    modules = CHAPTER_MODULES.get(chapter, [])
    if not modules:
        return []

    sections = []

    for i, mod_id in enumerate(modules):
        parsed = parse_module(mod_id, include_notes=include_notes)

        if i == 0:
            section_id = "intro"
            heading = "Introduction"
        else:
            section_id = f"{chapter}.{i}"
            heading = f"{section_id} {parsed['title']}"

        # Collect all paragraphs: top-level + from subsections
        all_paragraphs = list(parsed["paragraphs"])
        for subsec in parsed.get("subsections", []):
            all_paragraphs.extend(subsec["paragraphs"])

        if all_paragraphs:
            sections.append({
                "section_id": section_id,
                "heading": heading,
                "paragraphs": all_paragraphs,
            })

    return sections

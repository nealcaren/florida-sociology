# Textbook Censorship Diff Website — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static website comparing OpenStax Sociology 3e with Florida's modified version, highlighting censorship through redaction-style diffs.

**Architecture:** Python scripts extract text from PDFs and build a chapter index. The website is a single-page app (one HTML file) that loads per-chapter JSON diff data via fetch(). No framework, no build step — pure HTML/CSS/JS served via GitHub Pages.

**Tech Stack:** Python 3.13 (uv for deps), PyMuPDF for PDF extraction, vanilla HTML/CSS/JS

**Spec:** `docs/superpowers/specs/2026-03-17-textbook-censorship-diff-design.md`

---

## File Map

| File | Responsibility |
|------|---------------|
| `scripts/extract.py` | Extract text from both PDFs, split by chapter and section |
| `scripts/build_index.py` | Aggregate per-chapter JSONs into `data/chapters.json` |
| `index.html` | SPA shell: nav, landing page container, chapter view container |
| `css/style.css` | All styles: layout, redaction treatments, responsive |
| `js/app.js` | Routing, data loading, rendering (landing + chapter views) |
| `data/chapters.json` | Master index with severity/counts per chapter |
| `data/ch01.json` ... `data/ch21.json` | Per-chapter diff data |
| `pyproject.toml` | Python project config for uv |
| `.gitignore` | Ignore PDFs and .superpowers/ |

---

### Task 1: Project Setup

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`

- [ ] **Step 1: Create .gitignore**

```
*.pdf
.superpowers/
__pycache__/
.venv/
.DS_Store
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "florida-sociology"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pymupdf>=1.25.0",
]
```

- [ ] **Step 3: Install dependencies with uv**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv sync`
Expected: Virtual environment created, pymupdf installed

- [ ] **Step 4: Create directory structure**

Run:
```bash
mkdir -p text/original text/florida data scripts css js
```

- [ ] **Step 5: Initialize git and commit**

Run:
```bash
git init
git add .gitignore pyproject.toml uv.lock docs/
git commit -m "chore: project setup with spec and uv config"
```

---

### Task 2: PDF Text Extraction Script

**Files:**
- Create: `scripts/extract.py`

This script extracts text from both PDFs and splits into per-chapter text files. It needs to handle:
- Chapter boundary detection via "CHAPTER N" headings
- Section headers (e.g., "1.1 What Is Sociology?")
- Cleaning up page headers/footers and page numbers

- [ ] **Step 1: Write extract.py — PDF reading and chapter splitting**

```python
"""Extract text from OpenStax and Florida sociology PDFs, split by chapter."""

import re
import sys
from pathlib import Path

import fitz  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def clean_text(text: str) -> str:
    """Remove common PDF artifacts: page numbers, headers, footers."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip standalone page numbers
        if re.match(r"^\d+$", stripped):
            continue
        # Skip common OpenStax footer
        if "Access for free at openstax.org" in stripped:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def split_chapters(text: str) -> dict[int, str]:
    """Split extracted text into chapters using 'CHAPTER N' headings."""
    # Match "CHAPTER 1", "CHAPTER 2", etc. (case-insensitive, flexible spacing)
    pattern = r"(?:^|\n)\s*CHAPTER\s+(\d+)\s*\n"
    matches = list(re.finditer(pattern, text, re.IGNORECASE))

    if not matches:
        print("WARNING: No chapter headings found!", file=sys.stderr)
        return {}

    chapters = {}
    for i, match in enumerate(matches):
        chapter_num = int(match.group(1))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapters[chapter_num] = text[start:end].strip()

    return chapters


def split_sections(chapter_text: str, chapter_num: int) -> dict[str, str]:
    """Split a chapter into sections using 'N.N' headings."""
    pattern = rf"(?:^|\n)({chapter_num}\.\d+\s+[^\n]+)"
    matches = list(re.finditer(pattern, chapter_text))

    if not matches:
        return {f"{chapter_num}.0": chapter_text}

    sections = {}
    for i, match in enumerate(matches):
        # Extract section number from heading
        sec_match = re.match(rf"({chapter_num}\.\d+)", match.group(1))
        sec_id = sec_match.group(1) if sec_match else f"{chapter_num}.{i}"
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(chapter_text)
        sections[sec_id] = chapter_text[start:end].strip()

    return sections


def save_chapters(chapters: dict[int, str], output_dir: Path) -> None:
    """Save each chapter to a numbered text file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for num, text in sorted(chapters.items()):
        path = output_dir / f"ch{num:02d}.txt"
        path.write_text(text, encoding="utf-8")
        line_count = len(text.split("\n"))
        print(f"  ch{num:02d}.txt: {line_count} lines")


def main():
    project_root = Path(__file__).parent.parent

    pdfs = {
        "original": project_root / "IntroductiontoSociology3e-WEB_9QTqRGQ.pdf",
        "florida": project_root / "the-new-introduction-to-sociology-textbook.pdf",
    }

    for label, pdf_path in pdfs.items():
        print(f"\nExtracting: {label} ({pdf_path.name})")
        if not pdf_path.exists():
            print(f"  ERROR: File not found: {pdf_path}", file=sys.stderr)
            continue

        raw_text = extract_text(str(pdf_path))
        print(f"  Raw text: {len(raw_text)} characters")

        cleaned = clean_text(raw_text)
        chapters = split_chapters(cleaned)
        print(f"  Found {len(chapters)} chapters: {sorted(chapters.keys())}")

        output_dir = project_root / "text" / label
        save_chapters(chapters, output_dir)

        # Also save section-level splits
        sections_dir = project_root / "text" / f"{label}_sections"
        sections_dir.mkdir(parents=True, exist_ok=True)
        for num, ch_text in sorted(chapters.items()):
            sections = split_sections(ch_text, num)
            for sec_id, sec_text in sections.items():
                sec_path = sections_dir / f"ch{num:02d}_s{sec_id}.txt"
                sec_path.write_text(sec_text, encoding="utf-8")
            print(f"  ch{num:02d}: {len(sections)} sections")

    print("\nDone. Verify output in text/original/ and text/florida/")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit extraction script**

Run:
```bash
git add scripts/extract.py
git commit -m "feat: add PDF text extraction script with chapter and section splitting"
```

Note: The actual extraction is run in Task 8. This task only writes and commits the script.

---

### Task 3: Build Index Script

**Files:**
- Create: `scripts/build_index.py`

This script reads all `data/ch*.json` files and produces `data/chapters.json`.

- [ ] **Step 1: Write build_index.py**

```python
"""Build chapters.json master index from per-chapter JSON files."""

import json
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"

    chapters = []
    total_changes = 0

    for i in range(1, 22):
        path = data_dir / f"ch{i:02d}.json"
        if not path.exists():
            print(f"  WARNING: {path.name} not found, skipping")
            continue

        with open(path) as f:
            ch = json.load(f)

        total_changes += ch.get("change_count", 0)
        chapters.append({
            "chapter": ch["chapter"],
            "title": ch["title"],
            "severity": ch.get("severity", "none"),
            "change_count": ch.get("change_count", 0),
            "summary_short": ch.get("summary", "")[:200],
        })

    index = {
        "title": "What Florida Changed in Your Sociology Textbook",
        "description": "A chapter-by-chapter comparison of the original OpenStax Introduction to Sociology 3e with Florida's state-modified version, highlighting every edit, deletion, and relocation.",
        "total_changes": total_changes,
        "chapters": chapters,
    }

    out_path = data_dir / "chapters.json"
    with open(out_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Built index: {len(chapters)} chapters, {total_changes} total changes")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create a sample chapter JSON for development**

Create `data/ch11.json` as a realistic sample so we can develop the website against real-ish data:

```json
{
  "chapter": 11,
  "title": "Race and Ethnicity",
  "summary": "This chapter underwent extensive modification in the Florida version. Multiple passages discussing systemic racism, institutional discrimination, and the historical context of racial inequality in the United States were removed or significantly reworded. References to specific contemporary events and movements were deleted.",
  "changes": [
    {
      "type": "removed",
      "section": "11.3",
      "original_text": "This is a placeholder for an actual removed passage that will be filled in during manual comparison.",
      "florida_text": null,
      "context": "Passage on institutional racism removed entirely from the section on prejudice and discrimination."
    },
    {
      "type": "modified",
      "section": "11.5",
      "original_text": "Original placeholder text that discusses systemic inequality.",
      "florida_text": "Modified placeholder text with softened language.",
      "context": "Language about systemic factors replaced with individual-focused framing."
    },
    {
      "type": "added",
      "section": "11.1",
      "original_text": null,
      "florida_text": "Placeholder for Florida-added text emphasizing individual achievement.",
      "context": "New paragraph added to the introduction of the chapter."
    },
    {
      "type": "moved",
      "section": "11.4",
      "original_location": "Chapter 11, Section 11.4 Intergroup Relationships",
      "florida_location": "Chapter 11, Section 11.1 (condensed into introduction)",
      "original_text": "Placeholder for a passage that was relocated within the chapter.",
      "context": "Discussion of intergroup relations moved from its own section into the chapter introduction, reducing its prominence."
    }
  ],
  "change_count": 4,
  "severity": "major"
}
```

Also create a minimal `data/ch01.json` for an unchanged chapter:

```json
{
  "chapter": 1,
  "title": "An Introduction to Sociology",
  "summary": "This chapter was not modified in the Florida version.",
  "changes": [],
  "change_count": 0,
  "severity": "none"
}
```

- [ ] **Step 3: Run build_index.py and verify**

Run: `uv run python scripts/build_index.py`
Expected: `data/chapters.json` created with 2 chapters listed

Run: `cat data/chapters.json` to verify structure matches spec

- [ ] **Step 4: Commit**

Run:
```bash
git add scripts/build_index.py data/
git commit -m "feat: add build_index script and sample chapter data"
```

---

### Task 4: Website HTML Shell

**Files:**
- Create: `index.html`

The single HTML file that serves as the SPA. Contains the nav, landing page container, and chapter view container. All content is dynamically rendered by `app.js`.

- [ ] **Step 1: Write index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>What Florida Changed in Your Sociology Textbook</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <nav id="site-nav">
    <div class="nav-inner">
      <a href="#" class="nav-title">FL Sociology Diff</a>
      <div class="nav-chapter-select">
        <select id="chapter-select" aria-label="Select chapter">
          <option value="">Jump to chapter...</option>
        </select>
      </div>
      <button id="menu-toggle" class="menu-toggle" aria-label="Toggle menu">
        <span></span><span></span><span></span>
      </button>
    </div>
  </nav>

  <main id="app">
    <!-- Landing page -->
    <section id="landing" class="view">
      <header class="hero">
        <h1>What Florida Changed in Your Sociology Textbook</h1>
        <p class="hero-sub">A chapter-by-chapter comparison of the original OpenStax <em>Introduction to Sociology 3e</em> with Florida's state-modified version.</p>
        <div id="stats" class="stats"></div>
      </header>
      <div id="chapter-grid" class="chapter-grid"></div>
    </section>

    <!-- Chapter view -->
    <section id="chapter-view" class="view" hidden>
      <div class="chapter-header">
        <a href="#" class="back-link">&larr; All Chapters</a>
        <h2 id="chapter-title"></h2>
        <div id="chapter-severity" class="severity-badge"></div>
      </div>
      <div id="chapter-summary" class="chapter-summary"></div>
      <div id="change-nav" class="change-nav">
        <span id="change-count"></span>
        <div id="change-jump" class="change-jump"></div>
      </div>
      <div id="changes-list" class="changes-list"></div>
      <div class="chapter-footer">
        <a id="prev-chapter" href="#" class="chapter-nav-link">&larr; Previous</a>
        <a id="next-chapter" href="#" class="chapter-nav-link">Next &rarr;</a>
      </div>
    </section>

    <!-- Error state -->
    <section id="error-view" class="view" hidden>
      <div class="error-content">
        <p>Unable to load chapter data. Please try refreshing.</p>
        <button onclick="location.reload()">Retry</button>
      </div>
    </section>
  </main>

  <footer id="site-footer">
    <p>Data sourced from <a href="https://openstax.org/details/books/introduction-sociology-3e" target="_blank" rel="noopener">OpenStax Introduction to Sociology 3e</a> (CC BY 4.0) and the Florida state-modified edition.</p>
  </footer>

  <script src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Commit**

Run:
```bash
git add index.html
git commit -m "feat: add HTML shell for SPA"
```

---

### Task 5: CSS Styles

**Files:**
- Create: `css/style.css`

All styles including layout, typography, redaction treatments, severity colors, responsive breakpoints.

- [ ] **Step 1: Write style.css**

```css
/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --color-bg: #fafaf9;
  --color-text: #1c1917;
  --color-text-muted: #57534e;
  --color-border: #e7e5e4;
  --color-nav-bg: #1c1917;
  --color-nav-text: #fafaf9;
  --color-removed-bg: rgba(220, 38, 38, 0.12);
  --color-removed-text: #991b1b;
  --color-modified-border: #6b7280;
  --color-modified-text: #4b5563;
  --color-added-bg: rgba(37, 99, 235, 0.1);
  --color-added-border: #2563eb;
  --color-moved-bg: rgba(217, 119, 6, 0.1);
  --color-moved-border: #d97706;
  --color-severity-none: #16a34a;
  --color-severity-minor: #ca8a04;
  --color-severity-major: #dc2626;
  --max-width: 52rem;
}

body {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.125rem;
  line-height: 1.7;
  color: var(--color-text);
  background: var(--color-bg);
}

/* === Navigation === */
#site-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--color-nav-bg);
  color: var(--color-nav-text);
  padding: 0.75rem 1.5rem;
}

.nav-inner {
  max-width: var(--max-width);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.nav-title {
  color: var(--color-nav-text);
  text-decoration: none;
  font-weight: 700;
  font-size: 1rem;
  font-family: system-ui, sans-serif;
  white-space: nowrap;
}

.nav-chapter-select { flex: 1; }

#chapter-select {
  width: 100%;
  max-width: 20rem;
  padding: 0.35rem 0.5rem;
  border: 1px solid #555;
  border-radius: 4px;
  background: #2a2a2a;
  color: var(--color-nav-text);
  font-size: 0.875rem;
}

.menu-toggle {
  display: none;
  flex-direction: column;
  gap: 4px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
}
.menu-toggle span {
  display: block;
  width: 20px;
  height: 2px;
  background: var(--color-nav-text);
}

/* === Main Layout === */
main {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.view[hidden] { display: none; }

/* === Landing Page === */
.hero {
  text-align: center;
  margin-bottom: 3rem;
}

.hero h1 {
  font-size: 2.25rem;
  line-height: 1.2;
  margin-bottom: 1rem;
}

.hero-sub {
  font-size: 1.125rem;
  color: var(--color-text-muted);
  max-width: 36rem;
  margin: 0 auto 1.5rem;
}

.stats {
  display: flex;
  justify-content: center;
  gap: 2rem;
  font-family: system-ui, sans-serif;
  font-size: 0.95rem;
}

.stat { text-align: center; }
.stat-number {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
}
.stat-label {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* === Chapter Grid === */
.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 1rem;
}

.chapter-card {
  display: block;
  padding: 1.25rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  text-decoration: none;
  color: var(--color-text);
  transition: border-color 0.15s, box-shadow 0.15s;
  cursor: pointer;
}
.chapter-card:hover {
  border-color: #a8a29e;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.chapter-card-number {
  font-family: system-ui, sans-serif;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}

.chapter-card-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.3;
  margin-bottom: 0.5rem;
}

.chapter-card-meta {
  font-family: system-ui, sans-serif;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.severity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.severity-dot.none { background: var(--color-severity-none); }
.severity-dot.minor { background: var(--color-severity-minor); }
.severity-dot.major { background: var(--color-severity-major); }

/* === Chapter View === */
.chapter-header {
  margin-bottom: 2rem;
}

.back-link {
  font-family: system-ui, sans-serif;
  font-size: 0.875rem;
  color: var(--color-text-muted);
  text-decoration: none;
  display: inline-block;
  margin-bottom: 0.75rem;
}
.back-link:hover { color: var(--color-text); }

.chapter-header h2 {
  font-size: 1.75rem;
  line-height: 1.3;
  margin-bottom: 0.5rem;
}

.severity-badge {
  display: inline-block;
  font-family: system-ui, sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0.2rem 0.6rem;
  border-radius: 3px;
}
.severity-badge.none { background: #dcfce7; color: #166534; }
.severity-badge.minor { background: #fef9c3; color: #854d0e; }
.severity-badge.major { background: #fee2e2; color: #991b1b; }

.chapter-summary {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--color-border);
}

/* === Change Navigation === */
.change-nav {
  font-family: system-ui, sans-serif;
  font-size: 0.875rem;
  color: var(--color-text-muted);
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.change-jump {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.change-jump a {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 3px;
  text-decoration: none;
  color: var(--color-text-muted);
  font-size: 0.75rem;
}
.change-jump a:hover {
  background: var(--color-border);
  color: var(--color-text);
}

/* === Change Blocks === */
.change-block {
  margin-bottom: 2rem;
  padding: 1.25rem;
  border-radius: 6px;
  position: relative;
}

.change-block-header {
  font-family: system-ui, sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.change-type-tag {
  display: inline-block;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-size: 0.7rem;
}

.change-section {
  color: var(--color-text-muted);
}

.change-context {
  font-family: system-ui, sans-serif;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-style: italic;
  margin-bottom: 0.75rem;
}

/* Removed */
.change-block.removed {
  background: var(--color-removed-bg);
}
.change-block.removed .change-type-tag {
  background: #fee2e2;
  color: var(--color-removed-text);
}
.change-block.removed .original-text {
  text-decoration: line-through;
  color: var(--color-removed-text);
}

/* Modified */
.change-block.modified {
  background: var(--color-removed-bg);
}
.change-block.modified .change-type-tag {
  background: #fee2e2;
  color: var(--color-removed-text);
}
.change-block.modified .original-text {
  text-decoration: line-through;
  color: var(--color-removed-text);
  margin-bottom: 1rem;
}
.change-block.modified .florida-text {
  border-left: 3px solid var(--color-modified-border);
  color: var(--color-modified-text);
  background: rgba(255,255,255,0.6);
  padding: 0.75rem 1rem;
  border-radius: 0 4px 4px 0;
}
.florida-text-label {
  font-family: system-ui, sans-serif;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-modified-border);
  margin-bottom: 0.25rem;
}

/* Added */
.change-block.added {
  background: var(--color-added-bg);
  border-left: 3px solid var(--color-added-border);
}
.change-block.added .change-type-tag {
  background: #dbeafe;
  color: #1e40af;
}

/* Moved */
.change-block.moved {
  background: var(--color-moved-bg);
  border-left: 3px solid var(--color-moved-border);
}
.change-block.moved .change-type-tag {
  background: #fef3c7;
  color: #92400e;
}
.move-locations {
  font-family: system-ui, sans-serif;
  font-size: 0.8rem;
  color: #92400e;
  margin-bottom: 0.5rem;
}

/* === No Changes State === */
.no-changes {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-severity-none);
  font-family: system-ui, sans-serif;
}
.no-changes-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

/* === Chapter Footer Nav === */
.chapter-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 2rem;
  margin-top: 2rem;
  border-top: 1px solid var(--color-border);
}

.chapter-nav-link {
  font-family: system-ui, sans-serif;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  text-decoration: none;
}
.chapter-nav-link:hover { color: var(--color-text); }
.chapter-nav-link[hidden] { visibility: hidden; }

/* === Error State === */
.error-content {
  text-align: center;
  padding: 4rem 1rem;
}
.error-content button {
  margin-top: 1rem;
  padding: 0.5rem 1.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.9rem;
}

/* === Footer === */
#site-footer {
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 2rem 1.5rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.85rem;
  color: var(--color-text-muted);
}
#site-footer a { color: var(--color-text-muted); }

/* === Responsive === */
@media (max-width: 768px) {
  .hero h1 { font-size: 1.5rem; }
  .stats { flex-direction: column; gap: 1rem; }
  .chapter-grid { grid-template-columns: 1fr; }
  main { padding: 1.5rem 1rem; }

  .nav-chapter-select { display: none; }
  .nav-chapter-select.open { display: block; position: absolute; top: 100%; left: 0; right: 0; background: var(--color-nav-bg); padding: 0.5rem 1.5rem 1rem; }
  .nav-chapter-select.open #chapter-select { max-width: 100%; }
  .menu-toggle { display: flex; }
}
```

- [ ] **Step 2: Commit**

Run:
```bash
git add css/style.css
git commit -m "feat: add complete CSS with redaction visual treatments"
```

---

### Task 6: JavaScript — App Logic

**Files:**
- Create: `js/app.js`

Handles: loading data, hash routing, rendering landing page, rendering chapter view, navigation.

- [ ] **Step 1: Write app.js**

```javascript
(function () {
  "use strict";

  let chaptersIndex = null;
  const chapterCache = {};

  // --- Data Loading ---

  async function loadIndex() {
    const res = await fetch("data/chapters.json");
    if (!res.ok) throw new Error("Failed to load chapters.json");
    return res.json();
  }

  async function loadChapter(num) {
    if (chapterCache[num]) return chapterCache[num];
    const padded = String(num).padStart(2, "0");
    const res = await fetch(`data/ch${padded}.json`);
    if (!res.ok) throw new Error(`Failed to load ch${padded}.json`);
    const data = await res.json();
    chapterCache[num] = data;
    return data;
  }

  // --- Rendering: Landing Page ---

  function renderLanding() {
    document.getElementById("landing").hidden = false;
    document.getElementById("chapter-view").hidden = true;
    document.getElementById("error-view").hidden = true;

    if (!chaptersIndex) return;

    // Stats
    const totalChanges = chaptersIndex.total_changes;
    const majorCount = chaptersIndex.chapters.filter(
      (c) => c.severity === "major"
    ).length;
    const statsEl = document.getElementById("stats");
    statsEl.innerHTML = `
      <div class="stat">
        <span class="stat-number">${totalChanges}</span>
        <span class="stat-label">Changes Found</span>
      </div>
      <div class="stat">
        <span class="stat-number">${chaptersIndex.chapters.length}</span>
        <span class="stat-label">Chapters Compared</span>
      </div>
      <div class="stat">
        <span class="stat-number">${majorCount}</span>
        <span class="stat-label">Heavily Modified</span>
      </div>
    `;

    // Chapter grid
    const grid = document.getElementById("chapter-grid");
    grid.innerHTML = chaptersIndex.chapters
      .map(
        (ch) => `
      <a class="chapter-card" href="#chapter-${ch.chapter}">
        <div class="chapter-card-number">Chapter ${ch.chapter}</div>
        <div class="chapter-card-title">${escapeHtml(ch.title)}</div>
        <div class="chapter-card-meta">
          <span class="severity-dot ${ch.severity}"></span>
          <span>${ch.change_count} change${ch.change_count !== 1 ? "s" : ""}</span>
        </div>
      </a>
    `
      )
      .join("");
  }

  // --- Rendering: Chapter View ---

  function renderChapter(data) {
    document.getElementById("landing").hidden = true;
    document.getElementById("chapter-view").hidden = false;
    document.getElementById("error-view").hidden = true;

    document.getElementById("chapter-title").textContent =
      `Chapter ${data.chapter}: ${data.title}`;

    const badge = document.getElementById("chapter-severity");
    badge.className = `severity-badge ${data.severity}`;
    badge.textContent = data.severity === "none" ? "No changes" : `${data.severity} changes`;

    document.getElementById("chapter-summary").innerHTML =
      data.summary.split("\n\n")
        .map((p) => `<p>${escapeHtml(p.trim())}</p>`)
        .join("");

    // Change count and jump nav
    document.getElementById("change-count").textContent =
      `${data.changes.length} change${data.changes.length !== 1 ? "s" : ""}`;

    const jumpNav = document.getElementById("change-jump");
    jumpNav.innerHTML = data.changes
      .map(
        (_, i) =>
          `<a href="#change-${i}" onclick="document.getElementById('change-${i}').scrollIntoView({behavior:'smooth'});return false;">${i + 1}</a>`
      )
      .join("");

    // Changes list
    const list = document.getElementById("changes-list");

    if (data.changes.length === 0) {
      list.innerHTML = `
        <div class="no-changes">
          <div class="no-changes-icon">&#10003;</div>
          <p>This chapter was not modified in the Florida version.</p>
        </div>
      `;
    } else {
      list.innerHTML = data.changes.map((change, i) => renderChange(change, i)).join("");
    }

    // Prev/next navigation
    renderChapterNav(data.chapter);

    // Scroll to top
    window.scrollTo(0, 0);
  }

  function renderChange(change, index) {
    let content = "";

    const header = `
      <div class="change-block-header">
        <span class="change-type-tag">${change.type}</span>
        <span class="change-section">Section ${escapeHtml(change.section)}</span>
      </div>
    `;

    const context = change.context
      ? `<div class="change-context">${escapeHtml(change.context)}</div>`
      : "";

    switch (change.type) {
      case "removed":
        content = `
          ${header}${context}
          <div class="original-text">${escapeHtml(change.original_text)}</div>
        `;
        break;

      case "modified":
        content = `
          ${header}${context}
          <div class="original-text">${escapeHtml(change.original_text)}</div>
          <div class="florida-text">
            <div class="florida-text-label">Florida replacement:</div>
            ${escapeHtml(change.florida_text)}
          </div>
        `;
        break;

      case "added":
        content = `
          ${header}${context}
          <div class="florida-text">${escapeHtml(change.florida_text)}</div>
        `;
        break;

      case "moved":
        content = `
          ${header}${context}
          <div class="move-locations">
            From: ${escapeHtml(change.original_location)}<br>
            To: ${escapeHtml(change.florida_location)}
          </div>
          <div class="original-text" style="text-decoration:none;color:var(--color-text);">
            ${escapeHtml(change.original_text)}
          </div>
        `;
        break;
    }

    return `<div id="change-${index}" class="change-block ${change.type}">${content}</div>`;
  }

  function renderChapterNav(currentNum) {
    const prev = document.getElementById("prev-chapter");
    const next = document.getElementById("next-chapter");
    const chapterNums = chaptersIndex.chapters.map((c) => c.chapter).sort((a, b) => a - b);
    const currentIdx = chapterNums.indexOf(currentNum);

    if (currentIdx > 0) {
      prev.href = `#chapter-${chapterNums[currentIdx - 1]}`;
      prev.hidden = false;
    } else {
      prev.hidden = true;
    }

    if (currentIdx < chapterNums.length - 1) {
      next.href = `#chapter-${chapterNums[currentIdx + 1]}`;
      next.hidden = false;
    } else {
      next.hidden = true;
    }
  }

  function showError() {
    document.getElementById("landing").hidden = true;
    document.getElementById("chapter-view").hidden = true;
    document.getElementById("error-view").hidden = false;
  }

  // --- Routing ---

  function getRoute() {
    const hash = window.location.hash;
    const match = hash.match(/^#chapter-(\d+)$/);
    if (match) return { view: "chapter", num: parseInt(match[1], 10) };
    return { view: "landing" };
  }

  async function handleRoute() {
    const route = getRoute();

    if (route.view === "chapter") {
      const chapterInfo = chaptersIndex?.chapters.find(
        (c) => c.chapter === route.num
      );
      if (!chapterInfo) {
        window.location.hash = "";
        return;
      }
      try {
        const data = await loadChapter(route.num);
        renderChapter(data);
      } catch (e) {
        console.error(e);
        showError();
      }
    } else {
      renderLanding();
    }

    // Update chapter select
    document.getElementById("chapter-select").value =
      route.view === "chapter" ? String(route.num) : "";
  }

  // --- Nav Setup ---

  function setupNav() {
    if (!chaptersIndex) return;

    const select = document.getElementById("chapter-select");
    select.innerHTML =
      '<option value="">Jump to chapter...</option>' +
      chaptersIndex.chapters
        .map(
          (ch) =>
            `<option value="${ch.chapter}">Ch. ${ch.chapter}: ${escapeHtml(ch.title)}</option>`
        )
        .join("");

    select.addEventListener("change", function () {
      if (this.value) {
        window.location.hash = `#chapter-${this.value}`;
      } else {
        window.location.hash = "";
      }
    });

    // Mobile menu toggle
    document.getElementById("menu-toggle").addEventListener("click", function () {
      document.querySelector(".nav-chapter-select").classList.toggle("open");
    });
  }

  // --- Utilities ---

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // --- Init ---

  async function init() {
    try {
      chaptersIndex = await loadIndex();
      setupNav();
      handleRoute();
    } catch (e) {
      console.error("Failed to initialize:", e);
      showError();
    }
  }

  window.addEventListener("hashchange", handleRoute);
  document.addEventListener("DOMContentLoaded", init);
})();
```

- [ ] **Step 2: Commit**

Run:
```bash
git add js/app.js
git commit -m "feat: add SPA JavaScript with routing, rendering, and redaction display"
```

---

### Task 7: Test the Site Locally

**Files:** None (verification only)

- [ ] **Step 1: Serve the site locally and test**

Run:
```bash
cd /Users/nealcaren/Documents/GitHub/florida-sociology && python3 -m http.server 8000
```

Open `http://localhost:8000` in a browser. Verify:
- Landing page loads with chapter grid (should show ch01 and ch11 from sample data)
- Clicking ch11 shows the chapter view with redaction-style diffs
- Clicking ch01 shows the "no changes" state
- Back link returns to landing
- Chapter select dropdown works
- URL hash routing works (navigate directly to `#chapter-11`)
- Prev/next links work
- Mobile responsive (resize browser to narrow width)

- [ ] **Step 2: Fix any rendering issues found during testing**

Address any visual or functional issues. Common things to watch for:
- Text overflow on mobile
- Dropdown not populating
- fetch() path issues (relative paths)

- [ ] **Step 3: Commit any fixes**

Run:
```bash
git add -A
git commit -m "fix: address issues found during local testing"
```

---

### Task 8: Extract PDF Text

**Files:**
- Modify: `scripts/extract.py` (if regex tuning needed)
- Create: `text/original/ch01.txt` ... `text/original/ch21.txt`
- Create: `text/florida/ch01.txt` ... `text/florida/ch21.txt`

- [ ] **Step 1: Run the extraction script**

Run: `cd /Users/nealcaren/Documents/GitHub/florida-sociology && uv run python scripts/extract.py`

Check output for:
- Both PDFs found
- 21 chapters detected in each
- Reasonable line counts

- [ ] **Step 2: Validate extraction**

Run:
```bash
echo "=== Original ===" && wc -l text/original/ch*.txt
echo "=== Florida ===" && wc -l text/florida/ch*.txt
```

Then spot-check a few chapters by reading first 30 lines:
```bash
head -30 text/original/ch11.txt
head -30 text/florida/ch11.txt
```

If chapters are missing or garbled, adjust the regex in `extract.py` and re-run.

- [ ] **Step 3: Commit extracted text**

Run:
```bash
git add text/ scripts/extract.py
git commit -m "feat: extract chapter text from both PDF versions"
```

---

### Task 9: Manual Chapter Comparison (per chapter)

**Files:**
- Create/Update: `data/ch01.json` ... `data/ch21.json`

This is the most labor-intensive task. For each chapter:

1. Start with a quick diff to identify obvious changes: `diff text/original/chNN.txt text/florida/chNN.txt | head -100`
2. Read both `text/original/chNN.txt` and `text/florida/chNN.txt` to understand context around each diff
3. Also compare section-level files in `text/original_sections/` and `text/florida_sections/` for finer-grained alignment
4. Identify all differences (removed, modified, added, moved)
5. Write the chapter JSON with accurate text excerpts and editorial context
6. Write the editorial summary

**Priority order:**
1. Ch 11: Race and Ethnicity
2. Ch 12: Gender, Sex, and Sexuality
3. Ch 17: Government and Politics
4. Ch 9: Social Stratification in the United States
5. Ch 21: Social Movements and Social Change
6. Ch 14: Relationships, Marriage, and Family
7. Remaining chapters in order (1-8, 10, 13, 15-16, 18-20)

- [ ] **Step 1: Compare one chapter at a time**

For each chapter, read both text files, diff them, and produce a JSON file. After each chapter:

Run: `uv run python scripts/build_index.py` to update the master index

Commit after every 3-4 chapters:
```bash
git add data/
git commit -m "feat: add chapter comparisons for ch X, Y, Z"
```

- [ ] **Step 2: Rebuild index after all chapters complete**

Run: `uv run python scripts/build_index.py`
Verify: `cat data/chapters.json | python3 -m json.tool | head -20`

- [ ] **Step 3: Final commit of all chapter data**

Run:
```bash
git add data/
git commit -m "feat: complete all 21 chapter comparisons"
```

---

### Task 10: Final QC and Deploy

- [ ] **Step 1: Test complete site locally**

Run: `python3 -m http.server 8000`

Walk through every chapter. Verify:
- All 21 chapters load
- Severity colors match actual content
- Change counts are correct
- No broken rendering
- Editorial summaries read well
- Mobile layout works

- [ ] **Step 2: Set up GitHub Pages**

Ensure the repository is pushed to GitHub. Enable GitHub Pages in repo settings:
- Source: Deploy from a branch
- Branch: main, root directory (/)

- [ ] **Step 3: Verify live site**

Visit the GitHub Pages URL and confirm everything works.

- [ ] **Step 4: Final commit**

Run:
```bash
git add -A
git commit -m "chore: final QC and deploy prep"
git push origin main
```

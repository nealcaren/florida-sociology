# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Static website comparing OpenStax *Introduction to Sociology 3e* with Florida's state-modified version, highlighting censorship through redaction-style diffs. Deployed via GitHub Pages at `nealcaren.github.io/florida-sociology/`.

## Commands

```bash
# Install Python dependencies
uv sync

# Extract text from PDFs (requires both PDFs in project root)
uv run python scripts/extract.py

# Rebuild master index after editing any data/ch*.json
uv run python scripts/build_index.py

# Render evidence images from PDFs (requires both PDFs in project root)
uv run python scripts/render_evidence.py

# Render for a single chapter (original numbering)
uv run python scripts/render_evidence.py --chapter 5

# Local dev server
python3 -m http.server 8000
```

No build step. The site is static HTML/CSS/JS loading JSON via fetch().

## Architecture

**Data pipeline:** PDFs → `extract.py` → `text/` (plain text per chapter) → manual comparison → `data/ch*.json` (structured diffs) → `build_index.py` → `data/chapters.json` (master index) → frontend renders.

**Frontend:** Single-page app in one HTML file. Hash routing (`#chapter-11`). `app.js` fetches `chapters.json` for the landing page, then loads individual `ch{NN}.json` files on demand with caching. Word-level inline diffs computed client-side for "modified" changes.

**Chapter mapping:** The original has 21 chapters; Florida restructured to 12. Five chapters were removed entirely (Race/Ethnicity, Gender/Sex/Sexuality, Social Stratification, Global Inequality, Media/Technology). Four were merged into other chapters. All `data/` JSON files use **original** chapter numbering (1-21). The `data_file` field in `chapters.json` maps chapter numbers to filenames.

## Data Format

Each `data/ch{NN}.json` has: `chapter`, `title`, `florida_title` (null if removed entirely), `summary` (editorial prose, double-newline separated paragraphs), `changes` array, `change_count`, `severity`.

Optional fields: `original_sections` / `florida_sections` (section number arrays), `original_chapters` (for removed chapters that were part of the original), `key_terms` (array of `{"term", "status", "original_definition", "florida_definition"}` for glossary changes).

Change types: `removed`, `modified`, `added`, `moved`. Each has `section`, `original_text`, `florida_text`, `context`. The `moved` type additionally has `original_location` and `florida_location`.

After editing any chapter JSON, always run `build_index.py` to regenerate `chapters.json`.

**Extracted text:** `text/original/` and `text/florida/` contain per-chapter plain text (e.g., `ch01.txt`). `text/original_sections/` and `text/florida_sections/` have section-level splits. These are the source-of-truth for verifying quoted text in `original_text`/`florida_text` fields.

## Style Constraints

- Editorial summaries: no mid-sentence em dashes, no throat-clearing openers, lead with the most important finding
- Quoted text in `original_text`/`florida_text` fields must be verbatim from the extracted text files in `text/`
- The `context` field is free-form editorial commentary

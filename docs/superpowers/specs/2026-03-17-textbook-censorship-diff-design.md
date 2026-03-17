# Florida Sociology Textbook Censorship Diff — Design Spec

## Overview

A static website that shows a chapter-by-chapter comparison between the official OpenStax *Introduction to Sociology 3e* and the Florida state-modified version, highlighting censorship through a redaction-style visual treatment. Targeted at general public and journalists.

Hosted on GitHub Pages from the `florida-sociology` repository.

## Source Materials

- **Original:** `IntroductiontoSociology3e-WEB_9QTqRGQ.pdf` (44MB, 21 chapters, ~660 pages)
- **Florida:** `the-new-introduction-to-sociology-textbook.pdf` (164MB)

Both are PDFs requiring text extraction.

## Data Pipeline

### Step 1: Text Extraction

A Python script (`scripts/extract.py`) using PyMuPDF or pdfplumber:

1. Extracts full text from both PDFs
2. Splits by chapter using heading detection ("CHAPTER 1", "CHAPTER 2", etc.)
3. Also splits at section level (e.g., "1.1", "1.2") for finer-grained alignment
4. Outputs to `text/original/ch01.txt` ... `ch21.txt` and `text/florida/ch01.txt` ... `ch21.txt`

### Step 2: Manual Comparison

For each of the 21 chapter pairs, manually read and identify all differences. Produce a structured JSON file per chapter in `data/`:

```json
{
  "chapter": 11,
  "title": "Race and Ethnicity",
  "summary": "Editorial summary of what changed and why it matters",
  "changes": [
    {
      "type": "removed",
      "section": "11.3",
      "original_text": "The full original passage...",
      "florida_text": null,
      "context": "Brief note on what surrounds this passage"
    },
    {
      "type": "modified",
      "section": "11.5",
      "original_text": "Original wording...",
      "florida_text": "Florida replacement wording...",
      "context": "What this change does"
    },
    {
      "type": "added",
      "section": "11.2",
      "original_text": null,
      "florida_text": "New Florida-only text...",
      "context": "What was added and why it matters"
    },
    {
      "type": "moved",
      "section": "12.3",
      "original_location": "Chapter 12, Section 12.3 Sexuality",
      "florida_location": "Chapter 12, Section 12.1 (merged into introduction)",
      "original_text": "The passage that moved...",
      "context": "Why the relocation matters"
    }
  ],
  "change_count": 12,
  "severity": "major"
}
```

Change types: `removed`, `modified`, `added`, `moved`.

Severity per chapter: `none`, `minor`, `major`.

Chapters with no changes are still recorded — "this chapter was left untouched" is itself informative.

### Step 3: Editorial Summaries

Each chapter gets a 2-3 paragraph editorial summary explaining what was changed and why it matters. The landing page gets an overall summary with aggregate statistics.

## Website Design

### Technology

Static site: one HTML file, one CSS file, one JS file. No framework, no build step. Loads chapter data via `fetch()` from JSON files. Single-page app behavior — `index.html` dynamically loads chapter content to avoid 22 separate HTML files.

### Landing Page

- **Headline:** Explains what this is (e.g., "What Florida Removed from Your Sociology Textbook")
- **Summary stats:** Total changes across all chapters, chapters most affected
- **Chapter grid:** Visual overview of all 21 chapters, color-coded by severity (green = unchanged, yellow = minor, red = major). Click any chapter to see its diff.

### Chapter View

- **Editorial summary** at top (2-3 paragraphs)
- **Diffs in redaction style:**
  - Original text shown in normal type
  - **Removed** passages: red background with strikethrough
  - **Modified** passages: original shown in red, Florida replacement shown below in a muted style
  - **Added** passages: Florida-only text shown with a distinct indicator
  - **Moved** passages: shown with a relocation indicator (from → to)
- **Sidebar or sticky nav** to jump between changes within the chapter

### Navigation

- Chapter list always accessible (sidebar or top nav)
- URL hash routing (`#chapter-11`) for direct linking to specific chapters
- Previous/next chapter navigation

## File Structure

```
florida-sociology/
  index.html                    # Landing page + chapter viewer (SPA)
  css/
    style.css                   # All styles
  js/
    app.js                      # Navigation, filtering, interaction
  data/
    chapters.json               # Master index of all chapters + stats
    ch01.json ... ch21.json     # Per-chapter diff data
  text/                         # Extracted text (working files)
    original/
      ch01.txt ... ch21.txt
    florida/
      ch01.txt ... ch21.txt
  scripts/
    extract.py                  # PDF text extraction script
    build_index.py              # Generates chapters.json from per-chapter JSONs
  docs/
    superpowers/
      specs/                    # This spec
```

### .gitignore

```
*.pdf
.superpowers/
```

PDFs are too large for git. Extracted text files are kept for reproducibility.

### GitHub Pages Configuration

Serve from repository root (not `docs/`). The `docs/` directory is for internal specs only, not the deployed site.

## chapters.json Schema

The master index is auto-generated by a small script (`scripts/build_index.py`) that reads all `data/ch*.json` files and produces:

```json
{
  "title": "What Florida Changed in Your Sociology Textbook",
  "description": "A chapter-by-chapter comparison...",
  "total_changes": 87,
  "chapters": [
    {
      "chapter": 1,
      "title": "An Introduction to Sociology",
      "severity": "none",
      "change_count": 0,
      "summary_short": "No changes."
    },
    {
      "chapter": 11,
      "title": "Race and Ethnicity",
      "severity": "major",
      "change_count": 23,
      "summary_short": "Extensive removals of content on systemic racism..."
    }
  ]
}
```

## Chapter List (OpenStax 3e)

1. An Introduction to Sociology
2. Sociological Research
3. Culture
4. Society and Social Interaction
5. Socialization
6. Groups and Organization
7. Deviance, Crime, and Social Control
8. Media and Technology
9. Social Stratification in the United States
10. Global Inequality
11. Race and Ethnicity
12. Gender, Sex, and Sexuality
13. Aging and the Elderly
14. Relationships, Marriage, and Family
15. Religion
16. Education
17. Government and Politics
18. Work and the Economy
19. Health and Medicine
20. Population, Urbanization, and the Environment
21. Social Movements and Social Change

## Change Type Field Requirements

| Field | removed | modified | added | moved |
|-------|---------|----------|-------|-------|
| `type` | required | required | required | required |
| `section` | required | required | required | required |
| `original_text` | required | required | null | required |
| `florida_text` | null | required | required | null |
| `original_location` | — | — | — | required |
| `florida_location` | — | — | — | required |
| `context` | required | required | required | required |

The `context` field is free-form editorial commentary: what surrounds the passage, what the change accomplishes, or why a relocation matters.

## Extraction Validation

After running `extract.py`, verify:
- All 21 chapter files exist for both versions
- Line counts are in a plausible range (not empty, not wildly different from expected page counts)
- Spot-check first and last paragraphs of 3-4 chapters against the PDF
- Chapter headings and section numbers extracted correctly

## UI Details

### Navigation

Use a **sticky top nav** with a chapter dropdown (not a sidebar) — works better on mobile and keeps the full viewport for content.

### Redaction Visual Treatment

- **Removed:** `background: rgba(220, 38, 38, 0.12); text-decoration: line-through; color: #991b1b;`
- **Modified (original):** Same as removed
- **Modified (Florida replacement):** Shown in a bordered block below, `border-left: 3px solid #6b7280; padding-left: 1rem; color: #4b5563;`
- **Added:** `background: rgba(37, 99, 235, 0.1); border-left: 3px solid #2563eb;`
- **Moved:** `background: rgba(217, 119, 6, 0.1); border-left: 3px solid #d97706;` with from/to labels

### Responsive Behavior

On narrow viewports (< 768px):
- Chapter nav collapses to a hamburger menu
- Change blocks stack vertically (no side-by-side)
- Font sizes reduce slightly for readability
- Sticky jump-nav becomes a floating button that opens a change list

### Empty and Error States

- **Chapter with no changes:** Show the editorial note "This chapter was not modified in the Florida version" with a green checkmark
- **Failed JSON fetch:** Show "Unable to load chapter data. Please try refreshing." with a retry button
- **Invalid URL hash:** Redirect to landing page

## Build Process

1. **Extract** — `python scripts/extract.py` pulls text from both PDFs into `text/`
2. **Validate** — Spot-check extracted text against PDFs (see Extraction Validation section)
3. **Compare** — Manually read each chapter pair, identify all changes, write per-chapter JSON to `data/`
4. **Summarize** — Write editorial summaries for each chapter and landing page
5. **Index** — `python scripts/build_index.py` generates `data/chapters.json` from per-chapter files
6. **Build site** — Create `index.html`, `style.css`, `app.js`
7. **QC** — Review in browser, fix rendering issues
8. **Deploy** — Push to GitHub, enable GitHub Pages

Steps 2-3 are the most labor-intensive. Priority order: chapters likely to have the most changes first (Race & Ethnicity, Gender/Sex/Sexuality, Government & Politics), then systematically through the rest.

## Success Criteria

- All 21 chapters compared and documented
- Every difference accurately captured with correct change type
- Editorial summaries provide accessible context for non-academics
- Site loads fast, works on mobile, requires no server
- Direct-linkable chapters for journalists to reference specific changes

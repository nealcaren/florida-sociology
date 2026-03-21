# Companion Diff Site — Design Spec

**Date:** 2026-03-21
**Status:** Draft

## Overview

A full-text, two-column companion site that presents the complete OpenStax *Introduction to Sociology 3e* alongside Florida's modified version, styled like a textbook. Unlike the existing `chapters.html` (which shows only documented changes), this site shows every paragraph of both books with differences highlighted in context.

## Core Layout

### Two-Column / One-Column Hybrid

- **Divergent text:** Two columns — original on the left, Florida on the right
- **Identical text:** Columns merge into a single centered column
- **Removed chapters** (11, 12, 13, 17, 8): Single column (original only) with a banner explaining the chapter was removed entirely
- **Removed sections within modified chapters:** Left column shows the original text with deletion highlighting; right column shows a "Section removed" placeholder or is simply absent for that block

### Page Image Thumbnails in Margins

- Fixed-position thumbnail images in the left and right margins showing the current page from each textbook
- Thumbnails track with scroll position — as the reader scrolls through text, the margin thumbnails update to show the corresponding page from each PDF
- Click a thumbnail to open the full page image in a lightbox
- **Data requirement:** A new script renders full-page images from both PDFs (not cropped evidence — full pages). File naming: `img/pages/original/page_NNN.webp`, `img/pages/florida/page_NNN.webp`
- **Mapping requirement:** The alignment data must include page numbers for both versions so the frontend knows which thumbnail to display at each scroll position

### Navigation

- **Chapter table of contents:** Sidebar or top nav listing all 21 original chapters, with Florida chapter numbers shown where applicable
- **Section nav:** Within each chapter page, a mini table of contents listing all sections — click to jump
- **Each chapter is its own page** (hash route like `#ch-2`), scrollable top to bottom, broken into sections with clear section headers
- Prev/Next chapter links at bottom

## Diff Highlighting

### Within Columns

- **Deletions** (text in original but not Florida): Highlighted in red in the left (original) column
- **Additions** (text in Florida but not original): Highlighted in green in the right (Florida) column
- No interweaving — each column shows its own complete, readable text with highlights marking what changed

### Moved Text

- Moved text gets a subtle visual marker (e.g., dashed border or icon)
- **Hover tooltip** shows where it moved to/from: "Moved to Section 4.2" or "Moved from Section 2.1"
- Both the source location (in the original column) and destination (in the Florida column) are annotated

### Unchanged Text

- Rendered in normal body text with no highlighting
- Visually identical in the merged single column

## Data Pipeline

### New: Paragraph Alignment Script (`scripts/align_texts.py`)

**Input:**
- Full chapter text files: `text/original/ch{NN}.txt` and `text/florida/ch{NN}.txt`
- Existing change data: `data/ch{NN}.json` (used as alignment anchors)

**Output:**
- Aligned chapter files: `data/aligned/ch{NN}.json`

**Alignment strategy:**

1. **Split** each chapter's full text into paragraphs (double-newline or section-header boundaries)
2. **Use existing changes as anchors:** The `original_text` and `florida_text` fields in documented changes provide known correspondence points between the two texts
3. **Align unchanged paragraphs** between anchors using sequence matching (difflib or similar). Paragraphs that match above a similarity threshold are paired; unmatched paragraphs are marked as additions or deletions
4. **Section boundaries:** Detect section headers (e.g., "2.1 Approaches to Sociological Research") in both texts to provide structural alignment points
5. **Page mapping:** Use the existing `original_page` and `florida_page` fields from changes, plus the PDF text extraction coordinates, to map paragraphs to page numbers

**Aligned output format:**

```json
{
  "chapter": 2,
  "title": "Sociological Research",
  "florida_title": "Sociological Research & Methods of Inquiry",
  "sections": [
    {
      "id": "intro",
      "original_heading": "Introduction",
      "florida_heading": "Introduction",
      "blocks": [
        {
          "type": "same",
          "text": "As sociology made its way into American universities...",
          "original_page": 47,
          "florida_page": 25
        },
        {
          "type": "modified",
          "original_text": "When sociologists apply the sociological perspective and begin to ask questions, no topic is off limits.",
          "florida_text": "When sociologists apply the sociological perspective and begin to ask questions, almost no topic is off limits.",
          "original_page": 48,
          "florida_page": 25,
          "change_index": 1
        },
        {
          "type": "removed",
          "original_text": "Critical Sociology focuses on deconstruction...",
          "original_page": 52,
          "change_index": 2,
          "context": "Entire Critical Sociology subsection removed."
        },
        {
          "type": "added",
          "florida_text": "Other Frameworks in Sociology...",
          "florida_page": 29,
          "change_index": 3,
          "context": "Replaces Critical Sociology with vague placeholder."
        },
        {
          "type": "moved",
          "original_text": "...",
          "florida_text": "...",
          "original_location": "Section 3.1",
          "florida_location": "Section 2.2",
          "original_page": 45,
          "florida_page": 30
        }
      ]
    }
  ]
}
```

Key: `change_index` links back to the corresponding entry in the original `data/ch{NN}.json` for editorial context and evidence images.

### New: Full-Page Render Script (`scripts/render_pages.py`)

- Renders every page of both PDFs as WebP images
- Output: `img/pages/original/page_NNN.webp`, `img/pages/florida/page_NNN.webp`
- Resolution: 150 DPI (same as evidence renders), medium WebP quality
- Uses PyMuPDF (already a dependency)

### Existing Data (Unchanged)

- `data/ch{NN}.json` — editorial context, evidence image paths, change metadata
- `img/evidence/ch{NN}/` — cropped evidence images (still used for detail views)
- `data/chapters.json` — master index for chapter listing

## Frontend

### New Files

- `compare.html` — entry point for the companion site
- `js/compare.js` — rendering logic for the two-column diff view
- `css/compare.css` — styles specific to the companion layout (imports shared styles from `style.css`)

### Rendering Logic

1. On page load, fetch `data/chapters.json` for chapter listing → render table of contents
2. On chapter navigation, fetch `data/aligned/ch{NN}.json`
3. For each section, iterate through `blocks`:
   - `type: "same"` → render one merged column
   - `type: "modified"` → render two columns; run word-level diff within each column to highlight specific word changes in red (original) and green (Florida)
   - `type: "removed"` → render left column only with red highlight; right column empty or "removed" marker
   - `type: "added"` → render right column only with green highlight; left column empty
   - `type: "moved"` → render in both columns with dashed border and hover tooltip for location info
4. Track scroll position → update margin page thumbnails based on `original_page` / `florida_page` of nearest block
5. Section headers render as full-width dividers with section number and title

### Page Thumbnail Behavior

- Two fixed-position elements: one on the far left (original page), one on the far right (Florida page)
- As the user scrolls, JavaScript determines which `block` is currently in view and updates the thumbnails to show the corresponding page images
- Clicking a thumbnail opens a lightbox showing the full-resolution page
- For removed chapters (no Florida version), only the left thumbnail is active
- Thumbnails hide on narrow screens (< 1200px) since there's no margin space

### Word-Level Diff (Modified Blocks)

Reuse the existing LCS `wordDiff()` algorithm from `app.js`, but render differently:
- In the **left column**: show the full original text; words that were deleted are highlighted in red
- In the **right column**: show the full Florida text; words that were added are highlighted in green
- This replaces the current interweaved rendering with a clean per-column approach

## Styling

### Typography & Colors

- Same Georgia/serif body font, system-ui for navigation
- Same color palette from existing `style.css`:
  - Red (`--color-removed-bg`, `--color-removed-text`) for deletions
  - Green/blue (`--color-added-bg`, `--color-added-border`) for additions
  - Orange (`--color-moved-bg`) for moved text
- Textbook feel: generous line-height (1.7), comfortable max-width per column, clear section breaks

### Two-Column Layout

- CSS Grid: `grid-template-columns: 1fr 1fr` for divergent blocks
- Single column: `grid-template-columns: 1fr` spanning full width
- Column gap: ~2rem
- Each column has a subtle header label ("Original" / "Florida") that appears when columns split

### Responsive Behavior

- **Desktop (≥ 1200px):** Two columns + page thumbnails in margins
- **Tablet (768–1199px):** Two columns, no margin thumbnails (use inline page references instead)
- **Mobile (< 768px):** Stacked layout — original block on top, Florida below, with clear labels

## Relationship to Existing Site

- The companion site is a **separate page** (`compare.html`), not a replacement for `chapters.html`
- Cross-links between the two: the existing chapter view can link to "View full comparison" and vice versa
- Shared assets: same CSS variables, same evidence images, same data directory

## Open Questions

1. **Text quality:** The extracted text files have some OCR artifacts and line-break issues from PDF extraction. May need a cleanup pass before the alignment script can produce clean output.
2. **Performance:** Full chapter text could be large. May need virtual scrolling or lazy section loading for longer chapters.
3. **Section mapping between versions:** Florida reorganized chapters — some original sections map to different Florida sections. The alignment script needs to handle cross-section moves gracefully.

# Page Evidence Feature — Design Spec

## Problem

Users reading the diff comparisons have no way to verify changes against the actual textbook pages. They must trust the extracted text. Adding linkable page images for each modification lets readers see the evidence themselves.

## Solution

Pre-render cropped regions from both PDFs for each documented change. Store as WebP images in the repo. Display in an expandable inline panel showing original and Florida versions side by side.

## Components

### 1. Evidence Renderer (`scripts/render_evidence.py`)

New script that maps each change to its source PDF page and extracts a cropped image of the relevant region.

**Inputs:**
- `data/ch*.json` — all chapter files with their `changes` arrays
- `IntroductiontoSociology3e-WEB_9QTqRGQ.pdf` — original textbook
- `the-new-introduction-to-sociology-textbook.pdf` — Florida version

**Search strategy:** Search for the first ~60-80 characters of `original_text` or `florida_text`, not the full string. PyMuPDF's `page.search_for()` works best with short phrases, and a unique prefix avoids false matches while staying reliable.

**Process per change:**
1. Take `original_text` (if present), extract a search prefix (~60-80 chars), search the original PDF using `page.search_for()` across all pages
2. Collect bounding rectangles for matched text spans on the matched page
3. Compute a union bounding box, expand with ~30pt padding on all sides (clamped to page bounds). PyMuPDF works in points (1/72 inch); 30pt at 150 DPI renders as ~62px.
4. Render the cropped region at 150 DPI as WebP (quality 80)
5. If the text spans two pages, crop the relevant region from both pages and stitch them vertically into a single image
6. Repeat for `florida_text` against the Florida PDF
7. Save images to `img/evidence/ch{NN}/change_{I}_original.webp` and `change_{I}_florida.webp`

**Output — fields added to each change object in the chapter JSON:**
- `original_page` (int or null) — 1-indexed PDF page number where text was found
- `florida_page` (int or null) — same for Florida version
- `original_evidence` (string or null) — relative path to cropped image, e.g. `img/evidence/ch01/change_0_original.webp`
- `florida_evidence` (string or null) — same for Florida version

**Edge cases:**
- Text not found in PDF: skip that side, log a warning, leave field null
- Text spans two pages: crop the relevant region from both pages and stitch vertically into one image. Record the first page number.
- Removed chapters (`florida_title` is null): skip evidence rendering entirely. These chapters use editorial descriptions as `original_text`, not verbatim quotes, so `search_for()` will not match. The evidence for removed chapters is the chapter's absence itself.
- Added changes (`original_text` is null): only search Florida PDF, original fields stay null
- `moved` type changes: search `original_text` in the original PDF for the original-side evidence, and search `original_text` in the Florida PDF for the Florida-side evidence (showing where it was relocated to)
- Very short text snippets (under ~20 chars): search may be ambiguous. If multiple matches, prefer the match closest to other changes in the same section.
- Idempotency: by default, skip rendering for changes that already have evidence images on disk. Use `--force` flag to re-render all.

**CLI interface:**
```bash
uv run python scripts/render_evidence.py              # process all chapters
uv run python scripts/render_evidence.py --chapter 5   # process one chapter (original numbering)
uv run python scripts/render_evidence.py --dry-run     # report matches without rendering
uv run python scripts/render_evidence.py --force       # re-render even if images exist
```

`--chapter` uses original chapter numbering (1-21), consistent with the data file naming.

After running, also run `build_index.py` to regenerate `chapters.json`.

### 2. Frontend — Expandable Evidence Panel (`js/app.js`)

Each change block gains a "View in textbook" toggle button below the existing content.

**Collapsed state (default):**
- Small button/link: "View in textbook" with a page icon
- Shows page numbers if available: "Original p. 47 | Florida p. 23"

**Expanded state:**
- Inline panel expands below the change block (JS-driven height measurement for smooth animation)
- Two-column layout: "Original (p. 47)" left, "Florida (p. 23)" right
- Images inserted into DOM only when panel is first expanded (not on page load)
- Images use `alt="Cropped page from [original/Florida] textbook showing this passage"` for accessibility
- Clicking an image opens it full-size in a new tab (`target="_blank"`)
- Toggle button text changes to "Hide textbook view"

**Rendering approach:** The evidence toggle and panel HTML are included in the `renderChange()` output (consistent with existing architecture). The image `<img>` tags are injected on first expand via a click handler.

**Single-side cases:**
- Removed changes (no Florida text): show only the original crop, right column shows "Not present in Florida version" label
- Added changes (no original text): show only the Florida crop, left column shows "Not in original version" label
- If evidence image is null (text not found): show "Page image unavailable" in that column

### 3. Styles (`css/style.css`)

- `.evidence-toggle` — button styling consistent with existing change block aesthetics
- `.evidence-panel` — expandable container with smooth open/close transition
- `.evidence-columns` — flexbox two-column layout, responsive (stacks vertically on mobile)
- `.evidence-img` — max-width: 100%, subtle border/shadow to distinguish from page background
- `.evidence-label` — "Original (p. 47)" / "Florida (p. 23)" column headers
- `.evidence-unavailable` — muted placeholder text for missing images

## Data Flow

```
PDFs + data/ch*.json
        │
        ▼
render_evidence.py
        │
        ├──► img/evidence/ch{NN}/*.webp  (cropped page images)
        │
        └──► data/ch*.json  (updated with evidence paths + page numbers)
                │
                ▼
        build_index.py  (regenerate chapters.json)
                │
                ▼
        app.js renders evidence panels using paths from JSON
```

## Storage

Estimated ~200 changes across all chapters. Most have both original and Florida text, yielding ~350 cropped images. At ~10-15 KB per cropped WebP, total storage is approximately **3-6 MB**. Acceptable for GitHub Pages.

## What This Does NOT Include

- Full-page rendering or highlight overlays (decided against in brainstorming)
- Lightbox/modal viewer (expandable panel chosen instead)
- Client-side PDF rendering or pdf.js
- Any server-side components

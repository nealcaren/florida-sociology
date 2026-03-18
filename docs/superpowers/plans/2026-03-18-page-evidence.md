# Page Evidence Feature — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add cropped PDF page images as visual evidence for each documented textbook change, displayed in expandable side-by-side panels.

**Architecture:** A new Python script (`render_evidence.py`) searches both PDFs for each change's quoted text, crops the matching region, saves as WebP, and writes image paths + page numbers back into the chapter JSON. The frontend (`app.js` + `style.css`) renders an expandable evidence panel below each change block.

**Tech Stack:** Python 3.12, PyMuPDF (fitz), Pillow (PIL), vanilla JS, CSS

**Spec:** `docs/superpowers/specs/2026-03-18-page-evidence-design.md`

---

## File Structure

- **Create:** `scripts/render_evidence.py` — CLI script that searches PDFs, crops regions, saves WebP images, updates chapter JSON
- **Create:** `img/evidence/ch{NN}/` — output directories for cropped WebP images
- **Modify:** `js/app.js:133-184` — update `renderChange()` to include evidence toggle + panel HTML, add click handler for expand/collapse and lazy image injection
- **Modify:** `css/style.css:277+` — add evidence panel styles (toggle button, two-column layout, responsive stacking)
- **Modify:** `data/ch*.json` — updated by script with `original_page`, `florida_page`, `original_evidence`, `florida_evidence` fields per change
- **Modify:** `CLAUDE.md` — add render_evidence.py to commands section

No test files — this is a static site with no test framework. Verification is done by running the script and visually inspecting output.

---

### Task 1: Core PDF Search Function

**Files:**
- Create: `scripts/render_evidence.py`

Build the foundational search logic that finds text in a PDF and returns page number + bounding rectangles.

- [ ] **Step 1: Create the script with imports and search function**

```python
"""Render cropped PDF evidence images for each documented change."""

import argparse
import json
import sys
from pathlib import Path

import fitz  # PyMuPDF


PROJECT_ROOT = Path(__file__).parent.parent
ORIGINAL_PDF = PROJECT_ROOT / "IntroductiontoSociology3e-WEB_9QTqRGQ.pdf"
FLORIDA_PDF = PROJECT_ROOT / "the-new-introduction-to-sociology-textbook.pdf"
EVIDENCE_DIR = PROJECT_ROOT / "img" / "evidence"
DATA_DIR = PROJECT_ROOT / "data"

# Padding around matched text region, in PDF points (1/72 inch)
PAD_PT = 30
# Render resolution
DPI = 150
# WebP quality
WEBP_QUALITY = 80
# Search prefix length — first N chars of text used for page.search_for()
SEARCH_PREFIX_LEN = 80


def make_search_prefix(text: str) -> str:
    """Extract a search prefix from text, truncating at a word boundary."""
    if len(text) <= SEARCH_PREFIX_LEN:
        return text
    prefix = text[:SEARCH_PREFIX_LEN]
    # Truncate at last space to avoid partial words
    last_space = prefix.rfind(" ")
    if last_space > 40:
        prefix = prefix[:last_space]
    return prefix


def find_text_in_pdf(
    doc: fitz.Document, text: str
) -> list[dict]:
    """Search for text across all pages of a PDF.

    Returns list of {"page": int, "rects": [fitz.Rect, ...]} sorted by page number.
    Only returns matches for the first page where text is found (lowest page number).
    """
    prefix = make_search_prefix(text)
    if not prefix.strip():
        return []

    for page_num in range(len(doc)):
        page = doc[page_num]
        rects = page.search_for(prefix)
        if rects:
            return [{"page": page_num, "rects": rects}]

    # Fallback: try shorter prefix if no match found
    if len(prefix) > 40:
        short_prefix = make_search_prefix(text[:50])
        for page_num in range(len(doc)):
            page = doc[page_num]
            rects = page.search_for(short_prefix)
            if rects:
                return [{"page": page_num, "rects": rects}]

    return []
```

- [ ] **Step 2: Verify the search function works against the actual PDFs**

Run:
```bash
uv run python -c "
import fitz, sys
sys.path.insert(0, 'scripts')
from render_evidence import find_text_in_pdf, ORIGINAL_PDF

doc = fitz.open(str(ORIGINAL_PDF))
# Known text from ch01 change 0
results = find_text_in_pdf(doc, 'Remember, though, that culture is a product of the people in a society.')
print(f'Found: {len(results)} match(es)')
for r in results:
    print(f'  Page {r[\"page\"] + 1}, {len(r[\"rects\"])} rects')
doc.close()
"
```

Expected: At least 1 match with page number and rectangles.

- [ ] **Step 3: Commit**

```bash
git add scripts/render_evidence.py
git commit -m "feat: add PDF text search for evidence rendering"
```

---

### Task 2: Crop and Render Function

**Files:**
- Modify: `scripts/render_evidence.py`

Add the function that takes search results and renders a cropped WebP image. Handle the two-page stitching case.

- [ ] **Step 1: Add crop_and_render function**

Append to `scripts/render_evidence.py`:

Add these imports **at the top of the file** with the other imports:

```python
from PIL import Image
import io
```

Then append the function:

```python
def crop_and_render(
    doc: fitz.Document,
    search_results: list[dict],
    output_path: Path,
) -> bool:
    """Render cropped region around matched text as WebP.

    If text spans two pages, stitches both crops vertically.
    Returns True if image was saved, False on failure.
    """
    if not search_results:
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    images = []

    for result in search_results:
        page = doc[result["page"]]
        page_rect = page.rect

        # Union all match rects, then add padding
        union = result["rects"][0]
        for r in result["rects"][1:]:
            union = union | r  # fitz.Rect union operator

        # Expand to full page width with vertical padding
        clip = fitz.Rect(
            page_rect.x0,
            max(page_rect.y0, union.y0 - PAD_PT),
            page_rect.x1,
            min(page_rect.y1, union.y1 + PAD_PT),
        )

        # Render clipped region
        mat = fitz.Matrix(DPI / 72, DPI / 72)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)

    if len(images) == 1:
        final = images[0]
    else:
        # Stitch vertically
        total_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        final = Image.new("RGB", (total_width, total_height), (255, 255, 255))
        y_offset = 0
        for img in images:
            final.paste(img, (0, y_offset))
            y_offset += img.height

    final.save(str(output_path), "WEBP", quality=WEBP_QUALITY)
    return True
```

- [ ] **Step 2: Test crop rendering on a known change**

Run:
```bash
uv run python -c "
import fitz, sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from render_evidence import find_text_in_pdf, crop_and_render, ORIGINAL_PDF

doc = fitz.open(str(ORIGINAL_PDF))
results = find_text_in_pdf(doc, 'Remember, though, that culture is a product of the people in a society.')
out = Path('img/evidence/test_crop.webp')
ok = crop_and_render(doc, results, out)
print(f'Saved: {ok}, exists: {out.exists()}, size: {out.stat().st_size if out.exists() else 0} bytes')
doc.close()
"
```

Expected: File saved, reasonable size (5-30 KB).

- [ ] **Step 3: Clean up test file and commit**

```bash
rm -f img/evidence/test_crop.webp
git add scripts/render_evidence.py
git commit -m "feat: add crop and render function with two-page stitching"
```

---

### Task 3: Chapter Processing Logic

**Files:**
- Modify: `scripts/render_evidence.py`

Add the function that processes all changes in a chapter JSON, calling search + crop for each, and writing evidence fields back into the JSON.

- [ ] **Step 1: Add process_chapter function**

Append to `scripts/render_evidence.py`:

```python
def process_chapter(
    chapter_path: Path,
    original_doc: fitz.Document,
    florida_doc: fitz.Document,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Process all changes in a chapter JSON file.

    Returns stats dict: {"matched": int, "skipped": int, "failed": int}
    """
    with open(chapter_path) as f:
        chapter_data = json.load(f)

    ch_num = chapter_data["chapter"]
    ch_dir = EVIDENCE_DIR / f"ch{ch_num:02d}"
    stats = {"matched": 0, "skipped": 0, "failed": 0}

    # Skip removed chapters — their original_text is editorial, not verbatim
    if chapter_data.get("florida_title") is None:
        print(f"  ch{ch_num:02d}: skipped (removed chapter)")
        return stats

    changes = chapter_data.get("changes", [])
    modified = False

    for i, change in enumerate(changes):
        change_type = change.get("type", "")

        # Determine which texts to search in which PDFs
        searches = []  # list of (text, doc, field_page, field_evidence, label)

        original_text = change.get("original_text")
        florida_text = change.get("florida_text")

        if change_type == "moved":
            # Show original location in original PDF, relocated text in Florida PDF
            if original_text:
                searches.append((original_text, original_doc, "original_page", "original_evidence", "original"))
                searches.append((original_text, florida_doc, "florida_page", "florida_evidence", "florida"))
        else:
            if original_text:
                searches.append((original_text, original_doc, "original_page", "original_evidence", "original"))
            if florida_text:
                searches.append((florida_text, florida_doc, "florida_page", "florida_evidence", "florida"))

        for text, doc, page_field, evidence_field, label in searches:
            img_path = ch_dir / f"change_{i}_{label}.webp"
            rel_path = f"img/evidence/ch{ch_num:02d}/change_{i}_{label}.webp"

            # Idempotency: skip if image exists and not forcing
            if not force and img_path.exists():
                if page_field not in change or evidence_field not in change:
                    # Image exists but JSON fields missing — re-search for page number only
                    results = find_text_in_pdf(doc, text)
                    if results:
                        change[page_field] = results[0]["page"] + 1
                        change[evidence_field] = rel_path
                        stats["matched"] += 1
                    else:
                        change[page_field] = None
                        change[evidence_field] = None
                        stats["failed"] += 1
                    modified = True
                else:
                    stats["skipped"] += 1
                continue

            results = find_text_in_pdf(doc, text)

            if not results:
                print(f"  ch{ch_num:02d} change {i} ({label}): NO MATCH")
                change[page_field] = None
                change[evidence_field] = None
                stats["failed"] += 1
                modified = True
                continue

            page_1indexed = results[0]["page"] + 1
            change[page_field] = page_1indexed
            change[evidence_field] = rel_path
            modified = True

            if dry_run:
                print(f"  ch{ch_num:02d} change {i} ({label}): p.{page_1indexed}")
                stats["matched"] += 1
                continue

            ok = crop_and_render(doc, results, img_path)
            if ok:
                stats["matched"] += 1
            else:
                stats["failed"] += 1
                change[evidence_field] = None

        # Set null for fields not searched
        for field in ["original_page", "original_evidence", "florida_page", "florida_evidence"]:
            if field not in change:
                change[field] = None
                modified = True

    if modified and not dry_run:
        with open(chapter_path, "w") as f:
            json.dump(chapter_data, f, indent=2)
            f.write("\n")

    return stats
```

- [ ] **Step 2: Commit**

```bash
git add scripts/render_evidence.py
git commit -m "feat: add chapter processing with evidence field updates"
```

---

### Task 4: CLI Entry Point

**Files:**
- Modify: `scripts/render_evidence.py`

Add argparse CLI with `--chapter`, `--dry-run`, `--force` flags and the `main()` function.

- [ ] **Step 1: Add main function and argparse**

Append to `scripts/render_evidence.py`:

```python
def main():
    parser = argparse.ArgumentParser(
        description="Render cropped PDF evidence images for documented changes."
    )
    parser.add_argument(
        "--chapter", type=int,
        help="Process only this chapter (original numbering, 1-21)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Report matches without rendering images"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-render even if images already exist"
    )
    args = parser.parse_args()

    # Check PDFs exist
    for pdf_path, label in [(ORIGINAL_PDF, "Original"), (FLORIDA_PDF, "Florida")]:
        if not pdf_path.exists():
            print(f"ERROR: {label} PDF not found: {pdf_path}", file=sys.stderr)
            sys.exit(1)

    print("Opening PDFs...")
    original_doc = fitz.open(str(ORIGINAL_PDF))
    florida_doc = fitz.open(str(FLORIDA_PDF))

    # Collect chapter files to process
    if args.chapter:
        paths = sorted(DATA_DIR.glob(f"ch{args.chapter:02d}*.json"))
        paths = [p for p in paths if p.name != "chapters.json"]
        if not paths:
            print(f"ERROR: No data file found for chapter {args.chapter}", file=sys.stderr)
            sys.exit(1)
    else:
        paths = sorted(DATA_DIR.glob("ch*.json"))
        paths = [p for p in paths if p.name != "chapters.json"]

    totals = {"matched": 0, "skipped": 0, "failed": 0}

    for path in paths:
        print(f"Processing {path.name}...")
        stats = process_chapter(
            path, original_doc, florida_doc,
            force=args.force, dry_run=args.dry_run,
        )
        for k in totals:
            totals[k] += stats[k]

    original_doc.close()
    florida_doc.close()

    print(f"\nDone: {totals['matched']} matched, {totals['skipped']} skipped, {totals['failed']} failed")
    if not args.dry_run:
        print("Run 'uv run python scripts/build_index.py' to regenerate chapters.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test dry run on a single chapter**

Run:
```bash
uv run python scripts/render_evidence.py --chapter 1 --dry-run
```

Expected: Prints page numbers for each change in ch01, no images written.

- [ ] **Step 3: Test actual render on a single chapter**

Run:
```bash
uv run python scripts/render_evidence.py --chapter 1
```

Expected: Images saved to `img/evidence/ch01/`, ch01.json updated with evidence fields.

- [ ] **Step 4: Verify output**

Run:
```bash
ls -la img/evidence/ch01/ | head -20
uv run python -c "
import json
d = json.load(open('data/ch01.json'))
for i, c in enumerate(d['changes'][:3]):
    print(f'Change {i}: orig_p={c.get(\"original_page\")}, fl_p={c.get(\"florida_page\")}, orig_ev={c.get(\"original_evidence\")}, fl_ev={c.get(\"florida_evidence\")}')
"
```

Expected: Evidence fields populated, image files present.

- [ ] **Step 5: Commit**

```bash
git add scripts/render_evidence.py
git commit -m "feat: add CLI entry point for render_evidence.py"
```

---

### Task 5: Run Full Evidence Render

**Files:**
- Modify: `data/ch*.json` (updated by script)
- Create: `img/evidence/ch*/` (generated images)

Run the script on all chapters and commit the results.

- [ ] **Step 1: Run full render**

Run:
```bash
uv run python scripts/render_evidence.py
```

Expected: Processes all 21 chapters, skips 9 removed chapters, renders evidence for the rest. Reports match/skip/fail counts.

- [ ] **Step 2: Rebuild index**

Run:
```bash
uv run python scripts/build_index.py
```

- [ ] **Step 3: Check output stats**

Run:
```bash
find img/evidence -name "*.webp" | wc -l
du -sh img/evidence/
```

Expected: ~200-350 images, ~3-6 MB total.

- [ ] **Step 4: Commit generated evidence and updated JSON**

```bash
git add img/evidence/ data/ch*.json data/chapters.json
git commit -m "feat: generate evidence images for all chapters"
```

---

### Task 6: Evidence Panel CSS

**Files:**
- Modify: `css/style.css:277+` (after the change block styles)

Add styles for the evidence toggle button and expandable panel.

- [ ] **Step 1: Add evidence styles to style.css**

Add before the `/* === No Changes State === */` comment (around line 381):

```css
/* === Evidence Panel === */
.evidence-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.75rem;
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-muted);
  font-family: system-ui, sans-serif;
  font-size: 0.78rem;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.evidence-toggle:hover {
  border-color: #a8a29e;
  color: var(--color-text);
}
.evidence-toggle-icon {
  font-size: 0.9rem;
}

.evidence-panel {
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.3s ease-out;
}
.evidence-panel.open {
  max-height: 2000px;
  transition: max-height 0.5s ease-in;
}

.evidence-columns {
  display: flex;
  gap: 1rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
}

.evidence-column {
  flex: 1;
  min-width: 0;
}

.evidence-label {
  font-family: system-ui, sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  margin-bottom: 0.5rem;
}

.evidence-img {
  max-width: 100%;
  height: auto;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.evidence-unavailable {
  font-family: system-ui, sans-serif;
  font-size: 0.82rem;
  color: var(--color-text-muted);
  font-style: italic;
  padding: 1.5rem;
  text-align: center;
  border: 1px dashed var(--color-border);
  border-radius: 4px;
}

@media (max-width: 768px) {
  .evidence-columns {
    flex-direction: column;
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add css/style.css
git commit -m "feat: add evidence panel CSS styles"
```

---

### Task 7: Evidence Panel JavaScript

**Files:**
- Modify: `js/app.js:133-184` — update `renderChange()` to include evidence HTML
- Modify: `js/app.js` — add evidence toggle handler after chapter renders

Update the `renderChange` function to include the evidence toggle button and panel, and add a delegated click handler for expand/collapse with lazy image loading.

- [ ] **Step 1: Add renderEvidence helper function**

Add this function in `js/app.js` before the `renderChange` function (around line 133):

```javascript
  // --- Evidence Panel ---

  function renderEvidencePanel(change) {
    const hasOriginal = change.original_evidence;
    const hasFlorida = change.florida_evidence;

    if (!hasOriginal && !hasFlorida) return "";

    const pageInfo = [];
    if (change.original_page) pageInfo.push(`Original p.\u00a0${change.original_page}`);
    if (change.florida_page) pageInfo.push(`Florida p.\u00a0${change.florida_page}`);
    const pageText = pageInfo.length ? ` \u2014 ${pageInfo.join(" | ")}` : "";

    // Column labels — use location info for moved changes
    let origLabel = change.original_page ? `Original (p. ${change.original_page})` : "Original";
    let flLabel = change.florida_page ? `Florida (p. ${change.florida_page})` : "Florida";
    if (change.type === "moved") {
      if (change.original_location) origLabel = `Original \u2014 ${change.original_location} (p. ${change.original_page || "?"})`;
      if (change.florida_location) flLabel = `Florida \u2014 ${change.florida_location} (p. ${change.florida_page || "?"})`;
    }

    // Build columns
    let origCol, flCol;

    if (hasOriginal) {
      origCol = `
        <div class="evidence-column">
          <div class="evidence-label">${escapeHtml(origLabel)}</div>
          <a href="${change.original_evidence}" target="_blank">
            <img class="evidence-img" data-src="${change.original_evidence}"
                 alt="Cropped page from original textbook showing this passage">
          </a>
        </div>`;
    } else {
      origCol = `
        <div class="evidence-column">
          <div class="evidence-label">${escapeHtml(origLabel)}</div>
          <div class="evidence-unavailable">${
            change.type === "added" ? "Not in original version" : "Page image unavailable"
          }</div>
        </div>`;
    }

    if (hasFlorida) {
      flCol = `
        <div class="evidence-column">
          <div class="evidence-label">${escapeHtml(flLabel)}</div>
          <a href="${change.florida_evidence}" target="_blank">
            <img class="evidence-img" data-src="${change.florida_evidence}"
                 alt="Cropped page from Florida textbook showing this passage">
          </a>
        </div>`;
    } else {
      flCol = `
        <div class="evidence-column">
          <div class="evidence-label">${escapeHtml(flLabel)}</div>
          <div class="evidence-unavailable">${
            change.type === "removed" ? "Not present in Florida version" : "Page image unavailable"
          }</div>
        </div>`;
    }

    return `
      <button class="evidence-toggle" data-evidence-loaded="false">
        <span class="evidence-toggle-icon">&#128196;</span>
        <span class="evidence-toggle-text">View in textbook${pageText}</span>
      </button>
      <div class="evidence-panel">
        <div class="evidence-columns">
          ${origCol}
          ${flCol}
        </div>
      </div>
    `;
  }
```

- [ ] **Step 2: Update renderChange to include evidence panel**

In `js/app.js`, replace the last line of `renderChange` (line ~183):

Old:
```javascript
    return `<div id="change-${index}" class="change-block ${change.type}">${content}</div>`;
```

New:
```javascript
    const evidence = renderEvidencePanel(change);
    return `<div id="change-${index}" class="change-block ${change.type}">${content}${evidence}</div>`;
```

- [ ] **Step 3: Add delegated click handler for evidence toggles**

Add this at the end of the `renderChapter` function in `js/app.js`, just before `// Scroll to top` (around line 129):

```javascript
    // Evidence panel toggle (delegated, attach once)
    if (!list.dataset.evidenceHandler) {
      list.dataset.evidenceHandler = "true";
      list.addEventListener("click", function (e) {
      const btn = e.target.closest(".evidence-toggle");
      if (!btn) return;

      const panel = btn.nextElementSibling;
      const isOpen = panel.classList.contains("open");

      if (isOpen) {
        panel.classList.remove("open");
        btn.querySelector(".evidence-toggle-text").textContent =
          btn.querySelector(".evidence-toggle-text").textContent.replace("Hide textbook view", "View in textbook");
      } else {
        // Lazy-load images on first open
        if (btn.dataset.evidenceLoaded === "false") {
          panel.querySelectorAll("img[data-src]").forEach((img) => {
            img.src = img.dataset.src;
            img.removeAttribute("data-src");
          });
          btn.dataset.evidenceLoaded = "true";
        }
        panel.classList.add("open");
        btn.querySelector(".evidence-toggle-text").textContent =
          btn.querySelector(".evidence-toggle-text").textContent.replace("View in textbook", "Hide textbook view");
      }
    });
    }
```

- [ ] **Step 4: Commit**

```bash
git add js/app.js
git commit -m "feat: add evidence panel toggle and lazy image loading"
```

---

### Task 8: Visual Verification and Polish

**Files:**
- Possibly modify: `js/app.js`, `css/style.css` (if adjustments needed)

Start the local dev server, open the site in a browser, and verify the evidence panels work correctly.

- [ ] **Step 1: Start local server**

Run:
```bash
python3 -m http.server 8000
```

- [ ] **Step 2: Open in browser and verify**

Check the following in the browser at `http://localhost:8000`:
1. Chapter 1: click "View in textbook" on a `removed` change — should show original image, "Not present in Florida version" on right
2. Chapter 1: click on a `modified` change — should show both original and Florida crops side by side
3. Chapter 1: click on an `added` change — should show "Not in original version" on left, Florida image on right
4. Verify images open full-size in new tab when clicked
5. Verify toggle button text switches between "View in textbook" and "Hide textbook view"
6. Verify panel animates open/close smoothly
7. Check mobile responsiveness (narrow browser window) — columns should stack vertically
8. Chapter 11 (removed chapter): verify no evidence buttons appear (no evidence rendered for removed chapters)

- [ ] **Step 3: Fix any issues found**

Address any visual or functional problems discovered during verification.

- [ ] **Step 4: Commit any fixes**

```bash
git add js/app.js css/style.css
git commit -m "fix: polish evidence panel based on visual review"
```

---

### Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

Add the render_evidence.py command to the commands section.

- [ ] **Step 1: Add render command to CLAUDE.md**

In the Commands section, add after the `build_index.py` entry:

```bash
# Render evidence images from PDFs (requires both PDFs in project root)
uv run python scripts/render_evidence.py

# Render for a single chapter (original numbering)
uv run python scripts/render_evidence.py --chapter 5
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add render_evidence.py to CLAUDE.md commands"
```

(function () {
  "use strict";

  // --- State ---
  let chaptersIndex = null;
  const chapterCache = {};
  let blockCounter = 0;

  // Valid chapters (not merged-away)
  const VALID_CHAPTERS = [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 19, 20, 21];
  // Merged-away redirects
  const REDIRECTS = { 4: 3, 16: 15, 17: 15, 18: 14 };

  // --- Data Loading ---

  async function loadIndex() {
    const res = await fetch("data/chapters.json");
    if (!res.ok) throw new Error("Failed to load chapters.json");
    return res.json();
  }

  async function loadAlignedChapter(num) {
    if (chapterCache[num]) return chapterCache[num];
    const filename = `ch${String(num).padStart(2, "0")}.json`;
    const res = await fetch(`data/aligned/${filename}`);
    if (!res.ok) throw new Error(`Failed to load aligned/${filename}`);
    const data = await res.json();
    chapterCache[num] = data;
    return data;
  }

  // --- Utilities ---

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // --- Word Diff (LCS) ---

  function wordDiff(oldText, newText) {
    const oldWords = oldText.split(/(\s+)/);
    const newWords = newText.split(/(\s+)/);
    const m = oldWords.length;
    const n = newWords.length;

    const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (oldWords[i - 1] === newWords[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1] + 1;
        } else {
          dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
        }
      }
    }

    const result = [];
    let i = m, j = n;
    while (i > 0 || j > 0) {
      if (i > 0 && j > 0 && oldWords[i - 1] === newWords[j - 1]) {
        result.unshift({ type: "same", text: oldWords[i - 1] });
        i--; j--;
      } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
        result.unshift({ type: "add", text: newWords[j - 1] });
        j--;
      } else {
        result.unshift({ type: "del", text: oldWords[i - 1] });
        i--;
      }
    }
    return result;
  }

  function renderWordDiffOriginal(oldText, newText) {
    const diff = wordDiff(oldText, newText);
    let html = "";
    for (const part of diff) {
      const escaped = escapeHtml(part.text);
      if (part.type === "same") {
        html += escaped;
      } else if (part.type === "del") {
        html += `<span class="wdiff-del" aria-label="deleted text">${escaped}</span>`;
      }
      // skip "add" tokens for original column
    }
    return html;
  }

  function renderWordDiffFlorida(oldText, newText) {
    const diff = wordDiff(oldText, newText);
    let html = "";
    for (const part of diff) {
      const escaped = escapeHtml(part.text);
      if (part.type === "same") {
        html += escaped;
      } else if (part.type === "add") {
        html += `<span class="wdiff-add" aria-label="added text">${escaped}</span>`;
      }
      // skip "del" tokens for florida column
    }
    return html;
  }

  // --- Rendering: TOC Sidebar ---

  function renderTOC() {
    const list = document.getElementById("toc-list");
    if (!chaptersIndex) return;

    let html = "";
    // All 21 original chapters
    for (let num = 1; num <= 21; num++) {
      const ch = chaptersIndex.chapters.find(c => c.chapter === num);
      if (!ch) continue;

      const isRemoved = ch.status === "removed";
      const isMergedAway = num in REDIRECTS;
      const removedClass = isRemoved ? " removed" : "";

      if (isMergedAway) {
        const target = REDIRECTS[num];
        html += `<li>
          <a class="toc-item${removedClass}" href="#ch-${target}" aria-label="Chapter ${num}: ${escapeHtml(ch.title)} (merged into Chapter ${target})">
            <span class="toc-ch-num">${num}.</span> ${escapeHtml(ch.title)}
            <span class="toc-redirect">Merged into Ch. ${target}</span>
          </a>
        </li>`;
      } else {
        html += `<li>
          <a class="toc-item${removedClass}" href="#ch-${num}" data-chapter="${num}" aria-label="Chapter ${num}: ${escapeHtml(ch.title)}${isRemoved ? ' (removed)' : ''}">
            <span class="toc-ch-num">${num}.</span> ${escapeHtml(ch.title)}
          </a>
        </li>`;
      }
    }
    list.innerHTML = html;
  }

  function updateTOCActive(chapterNum) {
    const items = document.querySelectorAll(".toc-item");
    items.forEach(item => {
      item.classList.remove("active");
      if (item.dataset.chapter && parseInt(item.dataset.chapter, 10) === chapterNum) {
        item.classList.add("active");
      }
    });
  }

  // --- Rendering: Chapter ---

  function renderChapter(data) {
    document.getElementById("compare-landing").hidden = true;
    document.getElementById("compare-chapter").hidden = false;
    document.getElementById("error-view").hidden = true;

    blockCounter = 0;

    // Title
    const titleEl = document.getElementById("chapter-title");
    titleEl.textContent = `Chapter ${data.chapter}: ${data.title}`;

    // Cross-link to highlighted changes view
    const changesLink = document.getElementById("changes-link");
    if (changesLink) {
      changesLink.href = `chapters.html#chapter-${data.chapter}`;
      changesLink.hidden = false;
    }

    // Subtitle showing Florida title if different
    const subtitleEl = document.getElementById("chapter-subtitle");
    if (data.florida_title && data.florida_title !== data.title) {
      subtitleEl.textContent = `Florida title: ${data.florida_title}`;
      subtitleEl.hidden = false;
    } else if (!data.florida_title) {
      subtitleEl.textContent = "This chapter was removed in the Florida version.";
      subtitleEl.hidden = false;
    } else {
      subtitleEl.hidden = true;
    }

    // Banner for removed chapters
    const bannerEl = document.getElementById("chapter-banner");
    if (data.chapter_type === "removed") {
      bannerEl.innerHTML = `<div class="removed-banner" role="alert">
        <strong>Entire Chapter Removed</strong>
        This chapter does not appear in the Florida version of the textbook. The original text is shown below for reference.
      </div>`;
    } else {
      bannerEl.innerHTML = "";
    }

    // Content
    const contentEl = document.getElementById("chapter-content");
    const isRemoved = data.chapter_type === "removed";

    let html = "";

    if (!isRemoved) {
      html += `<div class="diff-col-headers" role="presentation">
        <span>Original (OpenStax)</span>
        <span>Florida Version</span>
      </div>`;
    }

    if (isRemoved) {
      html += '<div class="removed-chapter-content">';
    }

    for (const section of data.sections) {
      html += renderSection(section, isRemoved);
    }

    if (isRemoved) {
      html += "</div>";
    }

    contentEl.innerHTML = html;

    // Chapter nav
    renderChapterNav(data.chapter);
    updateTOCActive(data.chapter);

    // Scroll to top
    window.scrollTo(0, 0);

    // Setup scroll tracking for page thumbnails
    setupScrollTracking();
  }

  function renderSection(section, isRemoved) {
    let html = '<div class="section-block">';

    // Section heading
    if (isRemoved || section.original_heading === section.florida_heading) {
      html += `<div class="section-heading-full">${escapeHtml(section.original_heading || section.florida_heading || "")}</div>`;
    } else if (section.original_heading && section.florida_heading) {
      html += `<div class="section-heading">
        <div class="section-heading-original">${escapeHtml(section.original_heading)}</div>
        <div class="section-heading-florida">${escapeHtml(section.florida_heading)}</div>
      </div>`;
    } else if (section.original_heading) {
      html += `<div class="section-heading-full">${escapeHtml(section.original_heading)}</div>`;
    } else if (section.florida_heading) {
      html += `<div class="section-heading-full">${escapeHtml(section.florida_heading)}</div>`;
    }

    // Blocks
    for (const block of section.blocks) {
      html += renderBlock(block, isRemoved);
    }

    html += "</div>";
    return html;
  }

  function renderBlock(block, isRemoved) {
    blockCounter++;
    const blockId = `block-${blockCounter}`;

    // Data attributes for page tracking
    const pageAttrs = [];
    if (block.original_page) pageAttrs.push(`data-orig-page="${block.original_page}"`);
    if (block.florida_page) pageAttrs.push(`data-fl-page="${block.florida_page}"`);
    const pageAttrStr = pageAttrs.length ? " " + pageAttrs.join(" ") : "";

    switch (block.type) {
      case "same":
        return `<div id="${blockId}" class="diff-row type-same"${pageAttrStr} role="row">
          <div class="diff-col" role="cell">${escapeHtml(block.text)}</div>
        </div>`;

      case "removed":
        if (isRemoved) {
          // For removed chapters, show as plain readable text
          return `<div id="${blockId}" class="diff-row type-same"${pageAttrStr} role="row">
            <div class="diff-col" role="cell">${escapeHtml(block.original_text)}</div>
          </div>`;
        }
        return `<div id="${blockId}" class="diff-row type-removed"${pageAttrStr} role="row" aria-label="Removed text">
          <div class="diff-col diff-col-original" role="cell">${escapeHtml(block.original_text)}</div>
          <div class="diff-col diff-col-florida" role="cell" aria-label="Text not present in Florida version">Removed</div>
        </div>`;

      case "added":
        return `<div id="${blockId}" class="diff-row type-added"${pageAttrStr} role="row" aria-label="Added text">
          <div class="diff-col diff-col-original" role="cell" aria-label="Text not present in original">Added in Florida</div>
          <div class="diff-col diff-col-florida" role="cell">${escapeHtml(block.florida_text)}</div>
        </div>`;

      case "modified":
        return `<div id="${blockId}" class="diff-row type-modified"${pageAttrStr} role="row" aria-label="Modified text">
          <div class="diff-col diff-col-original" role="cell">${renderWordDiffOriginal(block.original_text, block.florida_text)}</div>
          <div class="diff-col diff-col-florida" role="cell">${renderWordDiffFlorida(block.original_text, block.florida_text)}</div>
        </div>`;

      case "moved": {
        const origLoc = block.original_location ? escapeHtml(block.original_location) : "";
        const flLoc = block.florida_location ? escapeHtml(block.florida_location) : "";
        const tooltipOrig = flLoc ? `<span class="moved-tooltip" tabindex="0" aria-label="Moved to ${flLoc}">Moved to: ${flLoc}<span class="moved-tooltip-text">Moved to ${flLoc}</span></span>` : "";
        const tooltipFl = origLoc ? `<span class="moved-tooltip" tabindex="0" aria-label="Moved from ${origLoc}">Moved from: ${origLoc}<span class="moved-tooltip-text">Moved from ${origLoc}</span></span>` : "";

        // If both texts exist and differ, show word diff; otherwise show same text
        let origHtml, flHtml;
        if (block.original_text && block.florida_text && block.original_text !== block.florida_text) {
          origHtml = renderWordDiffOriginal(block.original_text, block.florida_text);
          flHtml = renderWordDiffFlorida(block.original_text, block.florida_text);
        } else {
          const text = block.original_text || block.florida_text || "";
          origHtml = escapeHtml(text);
          flHtml = escapeHtml(text);
        }

        return `<div id="${blockId}" class="diff-row type-moved"${pageAttrStr} role="row" aria-label="Moved text">
          <div class="diff-col diff-col-original" role="cell">
            ${tooltipOrig ? `<div style="margin-bottom:0.35rem;font-family:system-ui,sans-serif;font-size:0.8rem;">${tooltipOrig}</div>` : ""}
            ${origHtml}
          </div>
          <div class="diff-col diff-col-florida" role="cell">
            ${tooltipFl ? `<div style="margin-bottom:0.35rem;font-family:system-ui,sans-serif;font-size:0.8rem;">${tooltipFl}</div>` : ""}
            ${flHtml}
          </div>
        </div>`;
      }

      default:
        return "";
    }
  }

  // --- Chapter Navigation ---

  function renderChapterNav(currentNum) {
    const prev = document.getElementById("prev-chapter");
    const next = document.getElementById("next-chapter");
    const currentIdx = VALID_CHAPTERS.indexOf(currentNum);

    if (currentIdx > 0) {
      prev.href = `#ch-${VALID_CHAPTERS[currentIdx - 1]}`;
      prev.hidden = false;
    } else {
      prev.hidden = true;
    }

    if (currentIdx < VALID_CHAPTERS.length - 1) {
      next.href = `#ch-${VALID_CHAPTERS[currentIdx + 1]}`;
      next.hidden = false;
    } else {
      next.hidden = true;
    }
  }

  // --- Page Thumbnail Scroll Tracking ---

  let scrollRAF = null;

  let currentScrollHandler = null;

  function setupScrollTracking() {
    // Cancel any existing handler
    if (scrollRAF) cancelAnimationFrame(scrollRAF);
    if (currentScrollHandler) {
      window.removeEventListener("scroll", currentScrollHandler);
    }

    const rows = document.querySelectorAll(".diff-row[data-orig-page], .diff-row[data-fl-page]");
    if (rows.length === 0) {
      document.getElementById("page-thumb").hidden = true;
      return;
    }

    function findAndUpdateThumb() {
      const viewMid = window.innerHeight / 2;
      let closest = null;
      let closestDist = Infinity;

      for (const row of rows) {
        const rect = row.getBoundingClientRect();
        const dist = Math.abs(rect.top + rect.height / 2 - viewMid);
        if (dist < closestDist) {
          closestDist = dist;
          closest = row;
        }
      }

      if (closest) {
        const origPage = closest.dataset.origPage;
        const flPage = closest.dataset.flPage;
        updatePageThumb(origPage, flPage);
      }
    }

    function onScroll() {
      if (scrollRAF) return;
      scrollRAF = requestAnimationFrame(() => {
        scrollRAF = null;
        findAndUpdateThumb();
      });
    }

    currentScrollHandler = onScroll;
    window.addEventListener("scroll", onScroll, { passive: true });

    // Run immediately for initial state
    findAndUpdateThumb();
  }

  function updatePageThumb(origPage, flPage) {
    const thumb = document.getElementById("page-thumb");
    const label = document.getElementById("page-thumb-label");
    const img = document.getElementById("page-thumb-img");

    if (!origPage && !flPage) {
      thumb.hidden = true;
      return;
    }

    // Try to show original page image first
    const pageNum = origPage || flPage;
    const src = origPage
      ? `img/pages/original/page_${String(origPage).padStart(3, "0")}.webp`
      : `img/pages/florida/page_${String(flPage).padStart(3, "0")}.webp`;

    const labelParts = [];
    if (origPage) labelParts.push(`Original p. ${origPage}`);
    if (flPage) labelParts.push(`Florida p. ${flPage}`);
    label.textContent = labelParts.join(" | ");

    // Only show if image exists (test with onerror)
    img.onerror = function () {
      thumb.hidden = true;
    };
    img.onload = function () {
      thumb.hidden = false;
    };
    img.src = src;
    img.alt = `Page ${pageNum}`;
  }

  // --- Lightbox ---

  function openLightbox(src, labelText) {
    const lb = document.getElementById("lightbox");
    document.getElementById("lightbox-img").src = src;
    document.getElementById("lightbox-img").alt = labelText;
    document.getElementById("lightbox-label").textContent = labelText;
    lb.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    document.getElementById("lightbox").hidden = true;
    document.body.style.overflow = "";
  }

  // Lightbox event listeners
  document.addEventListener("click", function (e) {
    if (e.target.closest(".lightbox-close") || e.target.classList.contains("lightbox-backdrop")) {
      closeLightbox();
    }
    // Click on page thumb opens lightbox
    if (e.target.closest(".page-thumb")) {
      const img = document.getElementById("page-thumb-img");
      const label = document.getElementById("page-thumb-label");
      if (img.src) {
        openLightbox(img.src, label.textContent);
      }
    }
  });

  document.addEventListener("keydown", function (e) {
    if (document.getElementById("lightbox").hidden) return;
    if (e.key === "Escape") closeLightbox();
  });

  // --- Routing ---

  function getRoute() {
    const hash = window.location.hash;
    const match = hash.match(/^#ch-(\d+)$/);
    if (match) return { view: "chapter", num: parseInt(match[1], 10) };
    return { view: "landing" };
  }

  function showError() {
    document.getElementById("compare-landing").hidden = true;
    document.getElementById("compare-chapter").hidden = true;
    document.getElementById("error-view").hidden = false;
  }

  async function handleRoute() {
    const route = getRoute();

    if (route.view === "chapter") {
      let targetNum = route.num;

      // Handle redirects for merged-away chapters
      if (targetNum in REDIRECTS) {
        window.location.hash = `#ch-${REDIRECTS[targetNum]}`;
        return;
      }

      // Validate chapter
      if (!VALID_CHAPTERS.includes(targetNum)) {
        window.location.hash = "";
        return;
      }

      try {
        const data = await loadAlignedChapter(targetNum);
        renderChapter(data);
      } catch (e) {
        console.error(e);
        showError();
      }
    } else {
      // Landing
      document.getElementById("compare-landing").hidden = false;
      document.getElementById("compare-chapter").hidden = true;
      document.getElementById("error-view").hidden = true;
      updateTOCActive(-1);
      document.getElementById("page-thumb").hidden = true;
    }

    // Update chapter select
    const select = document.getElementById("chapter-select");
    if (select) {
      select.value = route.view === "chapter" ? String(route.num) : "";
    }
  }

  // --- Nav Setup ---

  function setupNav() {
    if (!chaptersIndex) return;

    const select = document.getElementById("chapter-select");
    select.innerHTML =
      '<option value="">Jump to chapter...</option>' +
      chaptersIndex.chapters
        .map(ch => {
          const isMerged = ch.chapter in REDIRECTS;
          const suffix = isMerged ? ` (see Ch. ${REDIRECTS[ch.chapter]})` : "";
          return `<option value="${ch.chapter}">Ch. ${ch.chapter}: ${escapeHtml(ch.title)}${suffix}</option>`;
        })
        .join("");

    select.addEventListener("change", function () {
      if (this.value) {
        const num = parseInt(this.value, 10);
        const target = num in REDIRECTS ? REDIRECTS[num] : num;
        window.location.hash = `#ch-${target}`;
      } else {
        window.location.hash = "";
      }
    });

    // Mobile menu toggle
    document.getElementById("menu-toggle").addEventListener("click", function () {
      document.querySelector(".nav-chapter-select").classList.toggle("open");
    });
  }

  // --- TOC sidebar mobile toggle ---

  function setupTOCToggle() {
    // Create toggle button
    const btn = document.createElement("button");
    btn.className = "toc-toggle";
    btn.id = "toc-toggle";
    btn.setAttribute("aria-label", "Toggle table of contents");
    btn.textContent = "\u2630"; // hamburger
    document.body.appendChild(btn);

    const sidebar = document.getElementById("toc-sidebar");
    const closeBtn = document.getElementById("toc-close");

    btn.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });

    closeBtn.addEventListener("click", function () {
      sidebar.classList.remove("open");
    });

    // Close sidebar on link click (mobile)
    sidebar.addEventListener("click", function (e) {
      if (e.target.closest(".toc-item")) {
        sidebar.classList.remove("open");
      }
    });
  }

  // --- Init ---

  async function init() {
    try {
      chaptersIndex = await loadIndex();
      setupNav();
      renderTOC();
      setupTOCToggle();
      handleRoute();
    } catch (e) {
      console.error("Failed to initialize:", e);
      showError();
    }
  }

  window.addEventListener("hashchange", handleRoute);
  document.addEventListener("DOMContentLoaded", init);
})();

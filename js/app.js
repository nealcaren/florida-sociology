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
    // Use the data_file from the index if available
    const chapterInfo = chaptersIndex?.chapters.find((c) => c.chapter === num);
    const filename = chapterInfo?.data_file || `ch${String(num).padStart(2, "0")}.json`;
    const res = await fetch(`data/${filename}`);
    if (!res.ok) throw new Error(`Failed to load ${filename}`);
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
    const removedCount = chaptersIndex.chapters_removed ||
      chaptersIndex.chapters.filter((c) => c.status === "removed").length;
    const majorCount = chaptersIndex.chapters.filter(
      (c) => c.severity === "major"
    ).length;
    const statsEl = document.getElementById("stats");
    statsEl.innerHTML = `
      <div class="stat">
        <span class="stat-number">${chaptersIndex.original_chapter_count || 21}</span>
        <span class="stat-label">Original Chapters</span>
      </div>
      <div class="stat">
        <span class="stat-number">${removedCount}</span>
        <span class="stat-label">Chapters Eliminated</span>
      </div>
      <div class="stat">
        <span class="stat-number">${totalChanges}</span>
        <span class="stat-label">Changes Found</span>
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
      <a class="chapter-card ${ch.status === "removed" ? "chapter-removed" : ""}" href="#chapter-${ch.chapter}">
        <div class="chapter-card-number">Chapter ${ch.chapter}</div>
        <div class="chapter-card-title">${escapeHtml(ch.title)}</div>
        <div class="chapter-card-meta">
          <span class="severity-dot ${ch.severity}"></span>
          <span>${ch.status === "removed" ? "Entire chapter removed" : ch.change_count + " change" + (ch.change_count !== 1 ? "s" : "")}</span>
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

    // Evidence lightbox toggle (delegated, attach once)
    if (!list.dataset.evidenceHandler) {
      list.dataset.evidenceHandler = "true";
      list.addEventListener("click", function (e) {
        const btn = e.target.closest(".evidence-toggle");
        if (!btn) return;
        var slides = JSON.parse(btn.dataset.evidenceSlides || "[]");
        if (slides.length) openLightbox(slides, 0);
      });
    }

    // Prev/next navigation
    renderChapterNav(data.chapter);

    // Scroll to top
    window.scrollTo(0, 0);
  }

  // --- Evidence Lightbox ---

  function renderEvidencePanel(change) {
    const hasOriginal = change.original_evidence;
    const hasFlorida = change.florida_evidence;

    if (!hasOriginal && !hasFlorida) return "";

    const pageInfo = [];
    if (change.original_page) pageInfo.push(`Original p.\u00a0${change.original_page}`);
    if (change.florida_page) pageInfo.push(`Florida p.\u00a0${change.florida_page}`);
    const pageText = pageInfo.length ? ` \u2014 ${pageInfo.join(" | ")}` : "";

    // Build slides array for lightbox
    var slides = [];
    if (hasOriginal) {
      let label = change.original_page ? `Original (p. ${change.original_page})` : "Original";
      if (change.type === "moved" && change.original_location)
        label = `Original \u2014 ${change.original_location} (p. ${change.original_page || "?"})`;
      slides.push({ src: change.original_evidence, label: label });
    }
    if (hasFlorida) {
      let label = change.florida_page ? `Florida (p. ${change.florida_page})` : "Florida";
      if (change.type === "moved" && change.florida_location)
        label = `Florida \u2014 ${change.florida_location} (p. ${change.florida_page || "?"})`;
      slides.push({ src: change.florida_evidence, label: label });
    }

    return `
      <button class="evidence-toggle" data-evidence-slides='${JSON.stringify(slides).replace(/'/g, "&#39;")}'>
        <span class="evidence-toggle-icon">📖</span>
        <span class="evidence-toggle-text">View in textbook${pageText}</span>
      </button>
    `;
  }

  var lightboxSlides = [];
  var lightboxIndex = 0;

  function openLightbox(slides, index) {
    lightboxSlides = slides;
    lightboxIndex = index;
    showLightboxSlide();
    document.getElementById("evidence-lightbox").hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    document.getElementById("evidence-lightbox").hidden = true;
    document.body.style.overflow = "";
  }

  function showLightboxSlide() {
    var slide = lightboxSlides[lightboxIndex];
    document.getElementById("lightbox-img").src = slide.src;
    document.getElementById("lightbox-img").alt = slide.label;
    document.getElementById("lightbox-label").textContent = slide.label;
    document.getElementById("lightbox-counter").textContent =
      lightboxSlides.length > 1 ? (lightboxIndex + 1) + " / " + lightboxSlides.length : "";

    var prevBtn = document.getElementById("lightbox-prev");
    var nextBtn = document.getElementById("lightbox-next");

    if (lightboxSlides.length <= 1) {
      prevBtn.hidden = true;
      nextBtn.hidden = true;
    } else {
      prevBtn.hidden = false;
      nextBtn.hidden = false;
      prevBtn.disabled = lightboxIndex === 0;
      nextBtn.disabled = lightboxIndex === lightboxSlides.length - 1;
      prevBtn.textContent = "\u2190 " + (lightboxSlides[lightboxIndex - 1]
        ? lightboxSlides[lightboxIndex - 1].label.split(" (")[0]
        : "");
      nextBtn.textContent = (lightboxSlides[lightboxIndex + 1]
        ? lightboxSlides[lightboxIndex + 1].label.split(" (")[0]
        : "") + " \u2192";
    }
  }

  // Lightbox event listeners (once)
  document.addEventListener("click", function (e) {
    if (e.target.closest(".lightbox-close") || e.target.classList.contains("lightbox-backdrop")) {
      closeLightbox();
    }
    if (e.target.closest(".lightbox-prev") && lightboxIndex > 0) {
      lightboxIndex--;
      showLightboxSlide();
    }
    if (e.target.closest(".lightbox-next") && lightboxIndex < lightboxSlides.length - 1) {
      lightboxIndex++;
      showLightboxSlide();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (document.getElementById("evidence-lightbox").hidden) return;
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft" && lightboxIndex > 0) { lightboxIndex--; showLightboxSlide(); }
    if (e.key === "ArrowRight" && lightboxIndex < lightboxSlides.length - 1) { lightboxIndex++; showLightboxSlide(); }
  });

  // Touch swipe support
  (function () {
    var startX = 0;
    var lb = document.getElementById("evidence-lightbox");
    if (!lb) return;
    lb.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; }, { passive: true });
    lb.addEventListener("touchend", function (e) {
      var dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) < 50) return;
      if (dx < 0 && lightboxIndex < lightboxSlides.length - 1) { lightboxIndex++; showLightboxSlide(); }
      if (dx > 0 && lightboxIndex > 0) { lightboxIndex--; showLightboxSlide(); }
    }, { passive: true });
  })();

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
          <div class="diff-text">${renderInlineDiff(change.original_text, change.florida_text)}</div>
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

    const evidence = renderEvidencePanel(change);
    return `<div id="change-${index}" class="change-block ${change.type}">${content}${evidence}</div>`;
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

  // --- Word Diff ---

  function wordDiff(oldText, newText) {
    const oldWords = oldText.split(/(\s+)/);
    const newWords = newText.split(/(\s+)/);
    const m = oldWords.length;
    const n = newWords.length;

    // LCS via Hunt-Szymanski for word sequences
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

    // Backtrack to build diff
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

  function renderInlineDiff(oldText, newText) {
    const diff = wordDiff(oldText, newText);
    let html = "";
    for (const part of diff) {
      const escaped = escapeHtml(part.text);
      if (part.type === "same") {
        html += escaped;
      } else if (part.type === "del") {
        html += `<span class="diff-del">${escaped}</span>`;
      } else {
        html += `<span class="diff-add">${escaped}</span>`;
      }
    }
    return html;
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

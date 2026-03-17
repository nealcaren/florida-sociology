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

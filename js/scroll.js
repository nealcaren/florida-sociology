(function () {
  "use strict";

  // --- Scrollama Setup ---

  function initScrollama() {
    var scroller = scrollama();
    window.__scroller = scroller;
    scroller
      .setup({
        step: ".scroll-beat",
        offset: 0.85,
        once: true,
      })
      .onStepEnter(function (response) {
        response.element.classList.add("is-active");

        // Trigger stat counter animation when stats beat enters
        if (response.element.id === "stats-beat") {
          animateCounters();
        }

        // Trigger pivot counter
        if (response.element.classList.contains("beat-pivot")) {
          animatePivotCounter();
        }
      });

    // Show/hide nav based on scroll past hero
    var nav = document.getElementById("site-nav");
    if (nav) {
      nav.style.opacity = "0";
      nav.style.transition = "opacity 0.4s ease";
      window.addEventListener("scroll", function () {
        var heroHeight = document.querySelector(".beat-hero").offsetHeight;
        nav.style.opacity = window.scrollY > heroHeight * 0.6 ? "1" : "0";
      });
    }

    // Handle resize
    window.addEventListener("resize", scroller.resize);
  }

  // --- Pivot Counter Animation ---

  function animatePivotCounter() {
    var el = document.querySelector(".pivot-count");
    if (!el) return;
    var target = parseInt(el.dataset.target, 10);
    var duration = 1600;
    var start = performance.now();

    function update(now) {
      var elapsed = now - start;
      var progress = Math.min(elapsed / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 4);
      el.textContent = Math.round(eased * target).toLocaleString();
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  // --- Stat Counter Animation ---

  function animateCounters() {
    var counters = document.querySelectorAll("[data-target]");
    counters.forEach(function (el) {
      var target = parseFloat(el.dataset.target);
      var decimals = (String(target).split(".")[1] || "").length;
      var suffix = el.dataset.suffix || "";
      var duration = 1200;
      var start = performance.now();

      function update(now) {
        var elapsed = now - start;
        var progress = Math.min(elapsed / duration, 1);
        // Ease out cubic
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = eased * target;
        var display = decimals > 0 ? current.toFixed(decimals) : Math.round(current).toLocaleString();
        el.textContent = display + suffix;
        if (progress < 1) {
          requestAnimationFrame(update);
        }
      }
      requestAnimationFrame(update);
    });
  }

  // --- Words Chart ---

  var wordsData = [
    { word: "poverty", original: 237, florida: 55 },
    { word: "inequality", original: 152, florida: 24 },
    { word: "discrimination", original: 118, florida: 18 },
    { word: "racism", original: 108, florida: 6 },
    { word: "prejudice", original: 80, florida: 7 },
    { word: "transgender", original: 65, florida: 1 },
    { word: "socialism", original: 43, florida: 0 },
    { word: "feminist", original: 41, florida: 1 },
    { word: "slavery", original: 39, florida: 1 },
    { word: "privilege", original: 28, florida: 1 },
    { word: "genocide", original: 21, florida: 0 },
    { word: "sexism", original: 14, florida: 0 },
  ];

  function renderWordsChart() {
    var container = document.getElementById("words-chart");
    if (!container) return;

    var maxCount = wordsData[0].original;

    container.innerHTML = wordsData.map(function (d, i) {
      var origPct = (d.original / maxCount * 100).toFixed(1) + "%";
      var flPct = (d.florida / maxCount * 100).toFixed(1) + "%";
      var stagger = (i * 0.12).toFixed(2) + "s";

      var countDelay = (i * 0.12 + 1.2).toFixed(2) + "s";

      return '<div class="word-row" style="--stagger-counts:' + countDelay + ';">' +
        '<span class="word-label">' + d.word + '</span>' +
        '<div class="word-bar-track">' +
          '<div class="word-bar-fill" style="--bar-original:' + origPct + '; --bar-florida:' + flPct + '; --stagger:' + stagger + ';"></div>' +
        '</div>' +
        '<span class="word-counts">' +
          '<span class="word-count-original">' + d.original + '</span>' +
          '<span class="word-count-arrow"> \u2192 </span>' +
          '<span class="word-count-florida">' + d.florida + '</span>' +
        '</span>' +
        '</div>';
    }).join("");
  }

  // --- Data Loading & Rendering ---

  async function loadJSON(url) {
    var res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load " + url);
    return res.json();
  }

  function escapeHtml(str) {
    if (!str) return "";
    var div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // --- Stats Rendering ---

  function renderStats(index) {
    var container = document.getElementById("narrative-stats");
    var stats = [
      { value: index.word_count_difference, label: "Words Cut", suffix: "", accent: true, primary: true },
      { value: index.original_content_cut_pct, label: "Of Original Removed", suffix: "%", accent: true, primary: true },
      { value: index.chapters_removed, label: "Chapters Eliminated", suffix: "", accent: true, primary: false },
      { value: index.total_changes, label: "Total Changes", suffix: "", accent: false, primary: false },
      { value: index.sections_removed, label: "Sections Removed", suffix: "", accent: true, primary: false },
      { value: index.glossary_terms_changed, label: "Glossary Terms Changed", suffix: "", accent: false, primary: false },
    ];

    container.innerHTML = stats.map(function (s) {
      var classes = "stat-item" + (s.primary ? " primary" : "");
      var numClasses = "stat-number" + (s.accent ? " accent" : "");
      return '<div class="' + classes + '">' +
        '<span class="' + numClasses + '" data-target="' + s.value + '" data-suffix="' + s.suffix + '">0' + s.suffix + '</span>' +
        '<span class="stat-label">' + escapeHtml(s.label) + '</span>' +
        '</div>';
    }).join("");
  }

  // --- Theme Rendering ---

  async function renderThemes(themesData, chaptersIndex) {
    var container = document.getElementById("themes-container");
    var html = "";

    for (var t = 0; t < themesData.themes.length; t++) {
      var theme = themesData.themes[t];

      // Theme header beat
      html += '<section class="scroll-beat theme-beat-header">' +
        '<h2>' + escapeHtml(theme.title) + '</h2>' +
        '</section>';

      // Theme prose beat
      var prose = theme.prose.split("\n\n")
        .map(function (p) { return "<p>" + escapeHtml(p.trim()) + "</p>"; })
        .join("");

      var eliminated = "";
      if (theme.eliminated_chapters && theme.eliminated_chapters.length > 0) {
        var chNames = theme.eliminated_chapters.map(function (num) {
          var ch = chaptersIndex.chapters.find(function (c) { return c.chapter === num; });
          return ch ? "Ch.\u00a0" + num + ": " + ch.title : "Ch.\u00a0" + num;
        });
        eliminated = '<div class="theme-eliminated">Entire chapter' +
          (chNames.length > 1 ? "s" : "") + ' eliminated: ' +
          escapeHtml(chNames.join(", ")) + '</div>';
      }

      html += '<section class="scroll-beat theme-beat-prose">' +
        '<div class="prose-column">' + prose + eliminated + '</div>' +
        '</section>';

      // Example beats (2-3 per theme)
      var examples = theme.examples.slice(0, 3);
      for (var e = 0; e < examples.length; e++) {
        var ex = examples[e];
        try {
          var chData = await loadChapterCached(ex.chapter);
          var change = chData.changes[ex.change_index];
          if (!change) continue;
          html += renderExampleBeat(change, ex, chData.chapter);
        } catch (err) {
          console.error("Failed to load example:", ex, err);
        }
      }
    }

    container.innerHTML = html;
  }

  var chapterCache = {};
  async function loadChapterCached(num) {
    if (chapterCache[num]) return chapterCache[num];
    var filename = "ch" + String(num).padStart(2, "0") + ".json";
    var data = await loadJSON("data/" + filename);
    chapterCache[num] = data;
    return data;
  }

  function renderExampleBeat(change, example, chapterNum) {
    var typeClass = change.type;
    var tagHtml = '<span class="change-type-tag ' + typeClass + '">' + change.type.toUpperCase() + '</span>';
    var chapterRef = '<span style="color: var(--color-text-muted);">Chapter ' + chapterNum + '</span>';

    var textHtml = "";
    if (change.type === "removed") {
      textHtml = '<div class="example-text removed">' + escapeHtml(change.original_text) + '</div>';
    } else if (change.type === "modified") {
      textHtml = '<div class="example-text">' + renderInlineDiff(change.original_text, change.florida_text) + '</div>';
    } else {
      textHtml = '<div class="example-text">' + escapeHtml(change.original_text || change.florida_text) + '</div>';
    }

    var contextHtml = example.description
      ? '<div class="example-context">' + escapeHtml(example.description) + '</div>'
      : "";

    var linkHtml = '<a class="example-link" href="chapters.html#chapter-' + chapterNum + '">See all changes in Chapter ' + chapterNum + ' \u2192</a>';

    return '<section class="scroll-beat theme-beat-example">' +
      '<div class="example-inner ' + typeClass + '">' +
      '<div class="example-header">' + tagHtml + chapterRef + '</div>' +
      contextHtml + textHtml + linkHtml +
      '</div></section>';
  }

  // --- Word Diff (copied from app.js) ---

  function wordDiff(oldText, newText) {
    var oldWords = oldText.split(/(\s+)/);
    var newWords = newText.split(/(\s+)/);
    var m = oldWords.length;
    var n = newWords.length;
    var dp = [];
    for (var i = 0; i <= m; i++) {
      dp[i] = [];
      for (var j = 0; j <= n; j++) {
        if (i === 0 || j === 0) { dp[i][j] = 0; }
        else if (oldWords[i - 1] === newWords[j - 1]) { dp[i][j] = dp[i - 1][j - 1] + 1; }
        else { dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]); }
      }
    }
    var result = [];
    var i = m, j = n;
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
    var diff = wordDiff(oldText, newText);
    var html = "";
    for (var k = 0; k < diff.length; k++) {
      var escaped = escapeHtml(diff[k].text);
      if (diff[k].type === "same") { html += escaped; }
      else if (diff[k].type === "del") { html += '<span class="diff-del">' + escaped + '</span>'; }
      else { html += '<span class="diff-add">' + escaped + '</span>'; }
    }
    return html;
  }

  // --- Init ---

  async function init() {
    // Words chart has no data dependencies — render immediately
    renderWordsChart();

    try {
      var chaptersIndex = await loadJSON("data/chapters.json");
      var themesData = await loadJSON("data/themes.json");

      renderStats(chaptersIndex);
      await renderThemes(themesData, chaptersIndex);
      initScrollama();
    } catch (e) {
      console.error("Failed to initialize narrative:", e);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();

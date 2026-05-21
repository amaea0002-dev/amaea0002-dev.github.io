/*  Amaea intranet command palette
 *  -------------------------------
 *  Cmd-K (or Ctrl-K on Windows / Linux) opens a fullscreen modal that
 *  searches across every page title + every h1/h2/h3 on the static
 *  intranet. Lightweight scoring: token-match against title and
 *  heading text, weighted by heading level. No dependencies.
 *
 *  The index is fetched lazily on first open from /search-index.json
 *  (generated at build time by scripts/build-search-index.mjs). */
(function () {
  'use strict';

  // ────────────────────────────────────────────────────────────────
  // UI scaffolding
  // ────────────────────────────────────────────────────────────────

  function createPalette() {
    const overlay = document.createElement('div');
    overlay.className = 'cmdk-overlay';
    overlay.setAttribute('hidden', '');
    overlay.innerHTML = `
      <div class="cmdk-modal" role="dialog" aria-label="Search the intranet" aria-modal="true">
        <div class="cmdk-input-wrap">
          <svg class="cmdk-icon" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input
            type="text"
            class="cmdk-input"
            placeholder="Search pages, sections, runbooks…"
            autocomplete="off"
            spellcheck="false"
            aria-label="Search query"
          />
          <kbd class="cmdk-kbd">esc</kbd>
        </div>
        <div class="cmdk-results" role="listbox" aria-label="Search results"></div>
        <div class="cmdk-foot">
          <span><kbd>↑↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>esc</kbd> close</span>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);
    return overlay;
  }

  // ────────────────────────────────────────────────────────────────
  // State
  // ────────────────────────────────────────────────────────────────

  let overlayEl = null;
  let inputEl = null;
  let resultsEl = null;
  let modalEl = null;
  let index = null;
  let activeRow = 0;
  let lastResults = [];

  // ────────────────────────────────────────────────────────────────
  // Search
  // ────────────────────────────────────────────────────────────────

  function tokenize(q) {
    return q.toLowerCase().split(/\s+/).filter(Boolean);
  }

  function scoreText(text, tokens) {
    const t = text.toLowerCase();
    let score = 0;
    for (const tok of tokens) {
      if (!tok) continue;
      const i = t.indexOf(tok);
      if (i === -1) return -1; // every token must match
      score += 10 - Math.min(i, 9); // earlier-in-string scores higher
      if (i === 0 || t[i - 1] === ' ') score += 4; // word-boundary bonus
    }
    return score;
  }

  function buildRows() {
    if (!index) return [];
    const rows = [];
    for (const page of index) {
      rows.push({
        kind: 'page',
        title: page.title,
        eyebrow: page.eyebrow || '',
        url: page.url,
      });
      for (const h of page.headings) {
        rows.push({
          kind: 'heading',
          title: h.text,
          eyebrow: page.title,
          url: h.anchor ? page.url + '#' + h.anchor : page.url,
          level: h.level,
        });
      }
    }
    return rows;
  }

  let allRows = null;
  function search(query) {
    if (!allRows) allRows = buildRows();
    const q = query.trim();
    if (!q) {
      // No query — show top page-level destinations as a default list.
      return allRows.filter(r => r.kind === 'page').slice(0, 10);
    }
    const tokens = tokenize(q);
    const scored = [];
    for (const row of allRows) {
      const s = scoreText(row.title + ' ' + row.eyebrow, tokens);
      if (s < 0) continue;
      const kindBonus = row.kind === 'page' ? 8 : (4 - (row.level || 2));
      scored.push({ row, score: s + kindBonus });
    }
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, 12).map(s => s.row);
  }

  // ────────────────────────────────────────────────────────────────
  // Rendering
  // ────────────────────────────────────────────────────────────────

  function render(rows) {
    lastResults = rows;
    activeRow = 0;
    if (!rows.length) {
      resultsEl.innerHTML = `<div class="cmdk-empty">No matches. Try a different query.</div>`;
      return;
    }
    resultsEl.innerHTML = rows.map((r, i) => {
      const tag = r.kind === 'heading'
        ? `<span class="cmdk-tag">H${r.level || 2}</span>`
        : `<span class="cmdk-tag cmdk-tag-page">Page</span>`;
      return `
        <a href="${r.url}" class="cmdk-row${i === 0 ? ' is-active' : ''}" role="option" data-i="${i}">
          ${tag}
          <div class="cmdk-row-body">
            <div class="cmdk-row-title">${escapeHtml(r.title)}</div>
            ${r.eyebrow ? `<div class="cmdk-row-eyebrow">${escapeHtml(r.eyebrow)}</div>` : ''}
          </div>
          <svg class="cmdk-row-arrow" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>
        </a>
      `;
    }).join('');
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function setActive(i) {
    const rows = resultsEl.querySelectorAll('.cmdk-row');
    if (!rows.length) return;
    activeRow = ((i % rows.length) + rows.length) % rows.length;
    rows.forEach((r, j) => r.classList.toggle('is-active', j === activeRow));
    const active = rows[activeRow];
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  // ────────────────────────────────────────────────────────────────
  // Open / close
  // ────────────────────────────────────────────────────────────────

  async function open() {
    if (!overlayEl) {
      overlayEl = createPalette();
      inputEl = overlayEl.querySelector('.cmdk-input');
      resultsEl = overlayEl.querySelector('.cmdk-results');
      modalEl = overlayEl.querySelector('.cmdk-modal');
      attachHandlers();
    }
    overlayEl.removeAttribute('hidden');
    document.body.classList.add('cmdk-open');
    inputEl.value = '';
    inputEl.focus();

    if (!index) {
      try {
        const res = await fetch('/search-index.json', { cache: 'no-store' });
        if (res.ok) index = await res.json();
      } catch (_) { index = []; }
      allRows = null;
    }
    render(search(''));
  }

  function close() {
    if (!overlayEl) return;
    overlayEl.setAttribute('hidden', '');
    document.body.classList.remove('cmdk-open');
  }

  function attachHandlers() {
    inputEl.addEventListener('input', () => render(search(inputEl.value)));

    overlayEl.addEventListener('click', e => {
      if (e.target === overlayEl) close();
    });

    overlayEl.addEventListener('keydown', e => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); setActive(activeRow + 1); return; }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setActive(activeRow - 1); return; }
      if (e.key === 'Enter') {
        e.preventDefault();
        const rows = resultsEl.querySelectorAll('.cmdk-row');
        const active = rows[activeRow];
        if (active) window.location.href = active.getAttribute('href');
      }
    });

    resultsEl.addEventListener('mouseover', e => {
      const row = e.target.closest('.cmdk-row');
      if (!row) return;
      const i = parseInt(row.getAttribute('data-i'), 10);
      if (!Number.isNaN(i)) setActive(i);
    });
  }

  // ────────────────────────────────────────────────────────────────
  // Global keybinding (Cmd-K / Ctrl-K)
  // ────────────────────────────────────────────────────────────────

  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (overlayEl && !overlayEl.hasAttribute('hidden')) close();
      else open();
    }
  });

  // ────────────────────────────────────────────────────────────────
  // Topbar trigger — opt-in: any element with [data-cmdk-trigger]
  // ────────────────────────────────────────────────────────────────

  document.addEventListener('click', e => {
    const t = e.target.closest('[data-cmdk-trigger]');
    if (t) { e.preventDefault(); open(); }
  });

  // Expose for manual triggers from inline event handlers.
  window.amaeaSearch = { open, close };
})();

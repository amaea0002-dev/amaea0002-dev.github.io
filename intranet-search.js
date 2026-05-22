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
  let lastFocusedEl = null;

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
      resultsEl.innerHTML = renderEmpty(inputEl ? inputEl.value : '');
      inputEl && inputEl.setAttribute('aria-activedescendant', '');
      return;
    }
    resultsEl.innerHTML = rows.map((r, i) => {
      const tag = r.kind === 'heading'
        ? `<span class="cmdk-tag">H${r.level || 2}</span>`
        : `<span class="cmdk-tag cmdk-tag-page">Page</span>`;
      const id = `cmdk-row-${i}`;
      const selected = i === 0 ? 'true' : 'false';
      return `
        <a href="${escapeAttr(r.url)}" id="${id}" class="cmdk-row${i === 0 ? ' is-active' : ''}" role="option" aria-selected="${selected}" data-i="${i}">
          ${tag}
          <div class="cmdk-row-body">
            <div class="cmdk-row-title">${escapeHtml(r.title)}</div>
            ${r.eyebrow ? `<div class="cmdk-row-eyebrow">${escapeHtml(r.eyebrow)}</div>` : ''}
          </div>
          <svg aria-hidden="true" class="cmdk-row-arrow" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>
        </a>
      `;
    }).join('');
    inputEl.setAttribute('aria-activedescendant', rows.length ? 'cmdk-row-0' : '');
  }

  function renderEmpty(query) {
    const q = (query || '').trim();
    const titleHtml = q
      ? `No matches for <em>&ldquo;${escapeHtml(q)}&rdquo;</em>.`
      : `Type to search pages, sections, and runbooks.`;
    return `
      <div class="cmdk-empty">
        <div class="cmdk-empty-icon">
          <svg aria-hidden="true" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            <line x1="8" y1="11" x2="14" y2="11"/>
          </svg>
        </div>
        <div class="cmdk-empty-title">${titleHtml}</div>
        <div class="cmdk-empty-hints">
          <p>Search looks at page titles and section headings. Try a shorter or different word.</p>
          <ul>
            <li>Browse the <a href="/" data-cmdk-link>dashboard</a> for the canonical page list</li>
            <li>Or email <a href="mailto:milan@amaea.co.uk?subject=Intranet%20search%20miss" data-cmdk-link>milan@amaea.co.uk</a> if it should be here</li>
          </ul>
        </div>
      </div>
    `;
  }

  function escapeAttr(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
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
    rows.forEach((r, j) => {
      const isActive = j === activeRow;
      r.classList.toggle('is-active', isActive);
      r.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    const active = rows[activeRow];
    if (active) {
      active.scrollIntoView({ block: 'nearest' });
      inputEl.setAttribute('aria-activedescendant', active.id);
    }
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
      inputEl.setAttribute('role', 'combobox');
      inputEl.setAttribute('aria-controls', 'cmdk-results');
      inputEl.setAttribute('aria-expanded', 'true');
      inputEl.setAttribute('aria-autocomplete', 'list');
      resultsEl.id = 'cmdk-results';
      attachHandlers();
    }
    lastFocusedEl = document.activeElement;
    overlayEl.removeAttribute('hidden');
    document.body.classList.add('cmdk-open');
    inputEl.value = '';
    inputEl.focus();

    if (!index) {
      try {
        // Let the HTTP cache do its job; deploys publish a new search-index.json.
        const res = await fetch('/search-index.json');
        if (res.ok) index = await res.json();
      } catch (_) {
        // Leave index null so the next open retries — a single Cloudflare
        // hiccup shouldn't permanently disable search until page reload.
      }
      allRows = null;
    }
    render(search(''));
    if (!index) {
      resultsEl.innerHTML = `
        <div class="cmdk-empty">
          <div class="cmdk-empty-icon">
            <svg aria-hidden="true" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div class="cmdk-empty-title">Couldn't load the search index.</div>
          <div class="cmdk-empty-hints"><p>Press <kbd>Esc</kbd> and try again — usually a transient network hiccup.</p></div>
        </div>
      `;
    }
  }

  function close() {
    if (!overlayEl) return;
    overlayEl.setAttribute('hidden', '');
    document.body.classList.remove('cmdk-open');
    // Restore focus to whatever the user was on before opening — usually the
    // ⌘K topbar trigger, sometimes a sidebar item.
    if (lastFocusedEl && typeof lastFocusedEl.focus === 'function') {
      try { lastFocusedEl.focus(); } catch (_) {}
    }
    lastFocusedEl = null;
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
      if (e.key === 'Home')      { e.preventDefault(); setActive(0); return; }
      if (e.key === 'End')       { e.preventDefault(); setActive(-1); return; }
      if (e.key === 'Enter') {
        e.preventDefault();
        const rows = resultsEl.querySelectorAll('.cmdk-row');
        const active = rows[activeRow];
        if (active) window.location.href = active.getAttribute('href');
        return;
      }
      // Focus trap: keep Tab cycling between input and active row.
      if (e.key === 'Tab') {
        e.preventDefault();
        if (e.target === inputEl) {
          const rows = resultsEl.querySelectorAll('.cmdk-row');
          const active = rows[activeRow];
          if (active) active.focus();
        } else {
          inputEl.focus();
        }
      }
    });

    resultsEl.addEventListener('mouseover', e => {
      const row = e.target.closest('.cmdk-row');
      if (!row) return;
      const i = parseInt(row.getAttribute('data-i'), 10);
      if (!Number.isNaN(i)) setActive(i);
    });

    // Close the palette when the user clicks one of the recovery links
    // in the empty state (otherwise a mailto: would leave the modal open
    // hovering over the new tab/composer).
    resultsEl.addEventListener('click', e => {
      const link = e.target.closest('a[data-cmdk-link]');
      if (link) close();
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

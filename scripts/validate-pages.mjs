#!/usr/bin/env node
// Cross-page invariant validator for the Amaea intranet.
// Walks every .html and asserts the structural pieces that must be present
// on each surface, grouped by page type. Exits non-zero on any failure so
// it fails the `pnpm run build` pipeline.
//
// Page types:
//   app  — top-level + sector-research/* — full chrome (sidebar, topbar,
//          theme bootstrap, intranet.css, logout link, search script, skip
//          link, single h1, last-reviewed footer).
//   doc  — mvp-docs/* — printable docs; minimal chrome (no sidebar/topbar
//          required); shared invariants only.
//   shell — 404.html — standalone; theme bootstrap + intranet.css + search
//          script + h1; no sidebar/topbar/last-reviewed.

import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(process.cwd());

function listPages() {
  const top = fs.readdirSync(ROOT).filter(f => f.endsWith('.html'));
  const sector = fs.existsSync(path.join(ROOT, 'sector-research'))
    ? fs.readdirSync(path.join(ROOT, 'sector-research'))
        .filter(f => f.endsWith('.html'))
        .map(f => path.join('sector-research', f))
    : [];
  const mvp = fs.existsSync(path.join(ROOT, 'mvp-docs'))
    ? fs.readdirSync(path.join(ROOT, 'mvp-docs'))
        .filter(f => f.endsWith('.html'))
        .map(f => path.join('mvp-docs', f))
    : [];
  return [...top.map(f => ({ file: f, type: classify(f) })),
          ...sector.map(f => ({ file: f, type: 'app' })),
          ...mvp.map(f => ({ file: f, type: 'doc' }))];
}

function classify(file) {
  if (file === '404.html') return 'shell';
  return 'app';
}

// Each check: { id, pass(html, file) → boolean, describe }
const SHARED = [
  { id: 'doctype',     re: /^\s*<!DOCTYPE html>/i },
  { id: 'lang',        re: /<html\s+[^>]*lang="en"/i },
  { id: 'charset',     re: /<meta\s+charset="UTF-8"/i },
  { id: 'viewport',    re: /<meta\s+name="viewport"\s+content="[^"]*width=device-width/i },
  { id: 'title',       re: /<title>[^<]+<\/title>/i },
  { id: 'favicon',     re: /<link[^>]+rel="icon"[^>]*>/i },
  { id: 'inter-font',  re: /fonts\.googleapis\.com\/css2\?family=Inter/i },
];

const APP_AND_SHELL = [
  { id: 'theme-bootstrap', re: /localStorage\.getItem\('amaea-theme'\)/ },
  { id: 'intranet-css',    re: /<link[^>]+href="(?:\.\.\/)?intranet\.css"/ },
  { id: 'search-script',   re: /<script[^>]+src="\/?(?:\.\.\/)?intranet-search\.js"/ },
];

const APP_ONLY = [
  { id: 'skip-link',     re: /class="skip-link"\s+href="#main"/ },
  { id: 'logout-link',   re: /href="\/cdn-cgi\/access\/logout"/ },
  { id: 'main-landmark', re: /<main[^>]+id="main"/ },
  { id: 'single-h1',     fn: html => (html.match(/<h1\b/gi) || []).length === 1 },
  { id: 'last-reviewed', re: /Last reviewed/i },
];

function runChecks(html, file, type) {
  const checks = [...SHARED];
  if (type === 'app' || type === 'shell') checks.push(...APP_AND_SHELL);
  if (type === 'app') checks.push(...APP_ONLY);
  if (type === 'shell') {
    // shell still needs a single h1 and a main landmark, but no last-reviewed/sidebar/logout
    checks.push({ id: 'main-landmark', re: /<main[^>]+id="main"/ });
    checks.push({ id: 'single-h1', fn: h => (h.match(/<h1\b/gi) || []).length === 1 });
  }
  if (type === 'doc') {
    // mvp-docs sub-pages: just the shared chrome + a heading
    checks.push({ id: 'single-h1', fn: h => (h.match(/<h1\b/gi) || []).length === 1 });
  }

  const failures = [];
  for (const c of checks) {
    const ok = c.re ? c.re.test(html) : c.fn(html);
    if (!ok) failures.push(c.id);
  }
  return failures;
}

const pages = listPages();
let totalFailures = 0;
const report = [];

for (const { file, type } of pages) {
  const html = fs.readFileSync(path.join(ROOT, file), 'utf8');
  const failures = runChecks(html, file, type);
  if (failures.length) {
    totalFailures += failures.length;
    report.push({ file, type, failures });
  }
}

if (totalFailures === 0) {
  console.log(`Validated ${pages.length} pages — all invariants pass.`);
  process.exit(0);
}

console.error(`\nFAIL: ${totalFailures} invariant violations across ${report.length} pages:\n`);
for (const r of report) {
  console.error(`  ${r.file} [${r.type}]`);
  for (const id of r.failures) console.error(`    × ${id}`);
}
console.error('');
process.exit(1);

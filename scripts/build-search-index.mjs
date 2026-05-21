#!/usr/bin/env node
// Static search-index generator for the Amaea intranet.
// Crawls top-level .html pages + mvp-docs/*.html, extracts title +
// every h1/h2/h3 (with stable slug anchors if id is present, or
// generated kebab anchors otherwise), writes search-index.json.
// The runtime palette (intranet-search.js) fetches this once and
// filters in memory.

import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(process.cwd());
const SKIP_PAGES = new Set(['404.html']);

function listPages() {
  const top = fs.readdirSync(ROOT)
    .filter(f => f.endsWith('.html') && !SKIP_PAGES.has(f))
    .map(f => ({ file: f, url: '/' + f.replace(/\.html$/, '') }));
  const mvp = fs.existsSync(path.join(ROOT, 'mvp-docs'))
    ? fs.readdirSync(path.join(ROOT, 'mvp-docs'))
        .filter(f => f.endsWith('.html'))
        .map(f => ({ file: path.join('mvp-docs', f), url: '/mvp-docs/' + f }))
    : [];
  return [...top, ...mvp];
}

function decode(s) {
  return s
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#0?39;/g, "'")
    .replace(/&nbsp;/g, ' ');
}

function stripTags(s) {
  return s.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
}

function slugify(s) {
  return s.toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 60);
}

function extract(file, url) {
  const raw = fs.readFileSync(path.join(ROOT, file), 'utf8');

  const titleMatch = raw.match(/<title>([^<]*)<\/title>/i);
  const title = titleMatch
    ? decode(titleMatch[1]).split('|')[0].trim()
    : path.basename(file, '.html');

  const headings = [];
  const headingRe = /<(h[1-3])\b([^>]*)>([\s\S]*?)<\/\1>/gi;
  let m;
  while ((m = headingRe.exec(raw)) !== null) {
    const tag = m[1].toLowerCase();
    const attrs = m[2];
    const inner = stripTags(decode(m[3]));
    if (!inner || inner.length < 2) continue;
    const idMatch = attrs.match(/\bid=["']([^"']+)["']/);
    const anchor = idMatch ? idMatch[1] : null;
    headings.push({
      level: parseInt(tag.slice(1), 10),
      text: inner,
      anchor,
    });
  }

  // Page-eyebrow (used as a secondary descriptor on most intranet pages).
  let eyebrow = null;
  const eyebrowMatch = raw.match(/class="page-eyebrow"[^>]*>([^<]+)</);
  if (eyebrowMatch) eyebrow = decode(eyebrowMatch[1]).trim();

  return { url, title, eyebrow, headings };
}

function main() {
  const pages = listPages();
  const index = pages.map(({ file, url }) => extract(file, url));
  const out = path.join(ROOT, 'search-index.json');
  fs.writeFileSync(out, JSON.stringify(index));
  const headingCount = index.reduce((n, p) => n + p.headings.length, 0);
  console.log(`Indexed ${index.length} pages, ${headingCount} headings → ${path.relative(ROOT, out)}`);
}

main();

#!/usr/bin/env node
// One-shot maintenance script: walk every *.html page, find <h2>/<h3>
// without an `id` attribute, and inject a kebab-case slug derived from the
// heading's visible text. The Cmd-K palette consumes these via
// build-search-index.mjs so deep-link results land at the right section.
//
// Idempotent (re-running on a file with existing ids is a no-op for those
// headings). Safe to commit and re-run.

import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(process.cwd());

function listPages() {
  const top = fs.readdirSync(ROOT).filter(f => f.endsWith('.html'));
  const mvp = fs.existsSync(path.join(ROOT, 'mvp-docs'))
    ? fs.readdirSync(path.join(ROOT, 'mvp-docs')).filter(f => f.endsWith('.html')).map(f => path.join('mvp-docs', f))
    : [];
  return [...top, ...mvp];
}

function stripTags(s) {
  return s.replace(/<[^>]*>/g, '').replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ').replace(/&#0?39;/g, "'").replace(/\s+/g, ' ').trim();
}

function slugify(s) {
  return s.toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60);
}

function injectIds(html) {
  let added = 0;
  const seen = new Set();
  // Find existing ids so we don't collide.
  for (const m of html.matchAll(/\bid=["']([^"']+)["']/g)) seen.add(m[1]);

  const out = html.replace(/<(h[2-3])\b([^>]*)>([\s\S]*?)<\/\1>/gi, (match, tag, attrs, inner) => {
    if (/\bid=/.test(attrs)) return match;
    const text = stripTags(inner);
    if (!text) return match;
    let slug = slugify(text);
    if (!slug) return match;
    let unique = slug;
    let n = 2;
    while (seen.has(unique)) { unique = `${slug}-${n++}`; }
    seen.add(unique);
    added++;
    return `<${tag} id="${unique}"${attrs}>${inner}</${tag}>`;
  });
  return { out, added };
}

function main() {
  let total = 0;
  for (const file of listPages()) {
    const full = path.join(ROOT, file);
    const raw = fs.readFileSync(full, 'utf8');
    const { out, added } = injectIds(raw);
    if (added > 0) {
      fs.writeFileSync(full, out);
      console.log(`+${added}\t${file}`);
      total += added;
    }
  }
  console.log('---');
  console.log(`Injected ${total} heading ids.`);
}

main();

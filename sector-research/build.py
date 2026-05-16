#!/usr/bin/env python3
"""
Render the four sector research markdown memos from
~/Documents/Amaea/sector-research/*.md into branded intranet HTML pages
inside this folder.

Usage:  python3 build.py

Inputs:  /Users/milan/Documents/Amaea/sector-research/*.md
Outputs: ./mortgage-brokers.html, ./insurance-intermediaries.html,
         ./accountants.html, ./wealth-platforms-dfms.html

Wraps each rendered article in the standard Amaea intranet shell
(sidebar + topbar + theme toggle + Cloudflare identity). Markdown styling
is inlined per page so this folder stays self-contained.
"""

from __future__ import annotations
import html
import re
from pathlib import Path

ROOT = Path(__file__).parent
SRC_DIR = Path("/Users/milan/Documents/Amaea/sector-research")

MEMOS = [
    {
        "src": "mortgage-brokers.md",
        "out": "mortgage-brokers.html",
        "title": "Mortgage Brokers",
        "eyebrow": "Sector 1 · Q3 2026 priority",
        "next_review": "16 Aug 2026",
    },
    {
        "src": "insurance-intermediaries.md",
        "out": "insurance-intermediaries.html",
        "title": "Insurance Intermediaries",
        "eyebrow": "Sector 2 · Q4 2026 priority",
        "next_review": "16 Nov 2026",
    },
    {
        "src": "accountants.md",
        "out": "accountants.html",
        "title": "Accountants",
        "eyebrow": "Sector 3 · Q1 2027 priority",
        "next_review": "16 Feb 2027",
    },
    {
        "src": "wealth-platforms-dfms.md",
        "out": "wealth-platforms-dfms.html",
        "title": "Wealth Platforms & DFMs",
        "eyebrow": "Sector 4 · Q2 2027 priority",
        "next_review": "16 May 2027",
    },
]


# -----------------------------------------------------------
# Markdown → HTML  (adapted from mvp-docs/build.py)
# -----------------------------------------------------------
INLINE_CODE_RE = re.compile(r"`([^`\n]+?)`")
BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")
ITALIC_RE = re.compile(r"(?<![*\w])\*([^*\n]+?)\*(?!\*)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
ORDERED_LI_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
UNORDERED_LI_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
TABLE_SEP_RE = re.compile(r"^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def render_inline(text: str) -> str:
    placeholders: dict[str, str] = {}

    def stash(frag: str) -> str:
        token = f"\x00P{len(placeholders)}\x00"
        placeholders[token] = frag
        return token

    def code_repl(m: re.Match) -> str:
        return stash(f"<code>{html.escape(m.group(1))}</code>")
    text = INLINE_CODE_RE.sub(code_repl, text)

    def link_repl(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        return stash(f'<a href="{html.escape(url, quote=True)}">{render_inline_plain(label)}</a>')
    text = LINK_RE.sub(link_repl, text)

    text = html.escape(text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = ITALIC_RE.sub(r"<em>\1</em>", text)

    for token, frag in placeholders.items():
        text = text.replace(token, frag)
    return text


def render_inline_plain(text: str) -> str:
    text = html.escape(text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = ITALIC_RE.sub(r"<em>\1</em>", text)
    return text


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", s)


def render_table(rows: list[str]) -> str:
    def split_cells(line: str) -> list[str]:
        line = line.strip()
        if line.startswith("|"):
            line = line[1:]
        if line.endswith("|"):
            line = line[:-1]
        return [c.strip() for c in line.split("|")]

    header = split_cells(rows[0])
    body = [split_cells(r) for r in rows[2:]]

    out = ['<table>', '<thead><tr>']
    for h in header:
        out.append(f"<th>{render_inline(h)}</th>")
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>')
        for c in r:
            out.append(f"<td>{render_inline(c)}</td>")
        out.append('</tr>')
    out.append('</tbody></table>')
    return "\n".join(out)


def parse_list(lines: list[str], start: int, ordered: bool) -> tuple[str, int]:
    re_li = ORDERED_LI_RE if ordered else UNORDERED_LI_RE
    re_other = UNORDERED_LI_RE if ordered else ORDERED_LI_RE
    tag = "ol" if ordered else "ul"
    items: list[str] = []
    i = start
    base_indent: int | None = None

    while i < len(lines):
        line = lines[i]
        m = re_li.match(line)
        if not m:
            if line.strip() == "":
                k = i + 1
                while k < len(lines) and lines[k].strip() == "":
                    k += 1
                if k < len(lines):
                    mk = re_li.match(lines[k])
                    if mk and (base_indent is None or len(mk.group(1)) == base_indent):
                        i = k
                        continue
            break

        indent_str = m.group(1)
        indent = len(indent_str)

        if base_indent is None:
            base_indent = indent
        if indent < base_indent:
            break
        if indent > base_indent:
            break

        text = m.group(3) if ordered else m.group(2)

        item_continuation: list[str] = []
        nested_blocks: list[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if nxt.strip() == "":
                k = j
                while k < len(lines) and lines[k].strip() == "":
                    k += 1
                if k < len(lines):
                    mn = ORDERED_LI_RE.match(lines[k]) or UNORDERED_LI_RE.match(lines[k])
                    if mn and len(mn.group(1)) > base_indent:
                        j = k
                        continue
                break

            mn_ord = ORDERED_LI_RE.match(nxt)
            mn_un = UNORDERED_LI_RE.match(nxt)
            if mn_ord and len(mn_ord.group(1)) > base_indent:
                nested_html, j = parse_list(lines, j, ordered=True)
                nested_blocks.append(nested_html)
                continue
            if mn_un and len(mn_un.group(1)) > base_indent:
                nested_html, j = parse_list(lines, j, ordered=False)
                nested_blocks.append(nested_html)
                continue

            if re_li.match(nxt) and len(re_li.match(nxt).group(1)) == base_indent:
                break
            if re_other.match(nxt) and len(re_other.match(nxt).group(1)) == base_indent:
                break

            if nxt.strip() != "" and (nxt.startswith(" " * (base_indent + 2)) or (not nxt.startswith("|") and not HEADING_RE.match(nxt))):
                item_continuation.append(nxt.strip())
                j += 1
                continue
            break

        full_text = text + (" " + " ".join(item_continuation) if item_continuation else "")
        rendered = render_inline(full_text)
        if nested_blocks:
            items.append(f"<li>{rendered}\n" + "\n".join(nested_blocks) + "</li>")
        else:
            items.append(f"<li>{rendered}</li>")
        i = j

    return f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>", i


def md_to_html(md: str) -> tuple[str, str]:
    """Strip YAML front-matter, return (h1_title, body_html). H1 dropped from body."""
    # Strip --- frontmatter --- if present
    if md.startswith("---\n"):
        end = md.find("\n---\n", 4)
        if end != -1:
            md = md[end + 5:]

    lines = md.replace("\r\n", "\n").split("\n")
    i = 0
    body: list[str] = []
    h1_title = ""

    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            j = i + 1
            code_lines: list[str] = []
            while j < len(lines) and not lines[j].startswith("```"):
                code_lines.append(lines[j])
                j += 1
            code_html = html.escape("\n".join(code_lines))
            body.append(f"<pre><code>{code_html}</code></pre>")
            i = j + 1
            continue

        if line.lstrip().startswith("|") and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1] or ""):
            rows = [line]
            j = i + 1
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(lines[j])
                j += 1
            body.append(render_table(rows))
            i = j
            continue

        if re.match(r"^\s*---+\s*$", line):
            body.append("<hr/>")
            i += 1
            continue

        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1 and not h1_title:
                h1_title = text
                i += 1
                continue
            sid = slugify(text)
            body.append(f'<h{level} id="{sid}">{render_inline(text)}</h{level}>')
            i += 1
            continue

        if ORDERED_LI_RE.match(line):
            items, j = parse_list(lines, i, ordered=True)
            body.append(items)
            i = j
            continue

        if UNORDERED_LI_RE.match(line):
            items, j = parse_list(lines, i, ordered=False)
            body.append(items)
            i = j
            continue

        if line.strip() == "":
            i += 1
            continue

        para_lines = [line]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if (
                nxt.strip() == ""
                or HEADING_RE.match(nxt)
                or nxt.startswith("```")
                or (nxt.lstrip().startswith("|") and j + 1 < len(lines)
                    and TABLE_SEP_RE.match(lines[j + 1] or ""))
                or ORDERED_LI_RE.match(nxt)
                or UNORDERED_LI_RE.match(nxt)
                or re.match(r"^\s*---+\s*$", nxt)
            ):
                break
            para_lines.append(nxt)
            j += 1
        para = " ".join(p.strip() for p in para_lines)
        body.append(f"<p>{render_inline(para)}</p>")
        i = j

    return h1_title, "\n".join(body)


# -----------------------------------------------------------
# Page template — intranet shell
# -----------------------------------------------------------
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} | Sector Research | Amaea Intranet</title>
  <link rel="icon" href="../logo-plum.png"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="../intranet.css"/>
  <script>(function(){{var t=localStorage.getItem('amaea-theme')||(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t)}})();</script>
  <style>
    .memo-meta-bar {{ display: flex; align-items: center; gap: 14px; flex-wrap: wrap; padding: 14px 18px; background: var(--gray-50); border: 1px solid var(--gray-200); border-radius: var(--r-md); margin-bottom: 24px; font-size: 0.78rem; color: var(--gray-700); }}
    .memo-meta-bar strong {{ color: var(--gray-900); font-weight: 600; }}
    .memo-meta-sep {{ color: var(--gray-300); }}
    .memo-back {{ display: inline-flex; align-items: center; gap: 6px; font-size: 0.78rem; color: var(--gray-600); text-decoration: none; margin-bottom: 18px; }}
    .memo-back:hover {{ color: var(--gray-900); }}

    .memo-body {{ font-size: 0.88rem; line-height: 1.7; color: var(--gray-800); }}
    .memo-body h2 {{ font-size: 1.35rem; font-weight: 700; color: var(--gray-900); margin: 38px 0 14px; letter-spacing: -0.02em; padding-bottom: 8px; border-bottom: 1px solid var(--gray-200); }}
    .memo-body h2:first-child {{ margin-top: 0; }}
    .memo-body h3 {{ font-size: 1.08rem; font-weight: 700; color: var(--gray-900); margin: 28px 0 10px; letter-spacing: -0.01em; }}
    .memo-body h4 {{ font-size: 0.95rem; font-weight: 700; color: var(--gray-800); margin: 22px 0 8px; }}
    .memo-body p {{ margin: 0 0 14px; }}
    .memo-body strong {{ color: var(--gray-900); font-weight: 600; }}
    .memo-body em {{ font-style: italic; color: var(--gray-700); }}
    .memo-body a {{ color: var(--accent, #4C2C4B); text-decoration: underline; text-underline-offset: 2px; }}
    .memo-body a:hover {{ text-decoration: none; }}
    .memo-body ul, .memo-body ol {{ margin: 0 0 16px; padding-left: 22px; }}
    .memo-body li {{ margin: 4px 0; }}
    .memo-body li > ul, .memo-body li > ol {{ margin: 6px 0 6px; }}
    .memo-body code {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 0.84em; background: var(--gray-100); padding: 1px 5px; border-radius: 4px; color: var(--gray-900); }}
    .memo-body pre {{ background: var(--gray-50); border: 1px solid var(--gray-200); border-radius: var(--r-md); padding: 14px 16px; overflow-x: auto; margin: 0 0 18px; }}
    .memo-body pre code {{ background: transparent; padding: 0; font-size: 0.82rem; line-height: 1.55; }}
    .memo-body table {{ width: 100%; border-collapse: collapse; margin: 8px 0 22px; font-size: 0.82rem; }}
    .memo-body th, .memo-body td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--gray-200); vertical-align: top; }}
    .memo-body th {{ font-weight: 600; color: var(--gray-900); background: var(--gray-50); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.03em; }}
    .memo-body tr:last-child td {{ border-bottom: none; }}
    .memo-body hr {{ border: none; border-top: 1px solid var(--gray-200); margin: 28px 0; }}
    .memo-body blockquote {{ border-left: 3px solid var(--gray-300); padding: 4px 0 4px 16px; margin: 0 0 16px; color: var(--gray-600); font-style: italic; }}

    /* Constrain to readable width on wide screens */
    .memo-body {{ max-width: 880px; }}
  </style>
</head>
<body>

<div class="sidebar-overlay" id="sidebarOverlay"></div>
<aside class="sidebar">
  <div class="sidebar-logo">
    <img src="../logo-white.png" alt="Amaea"/>
    <span class="sidebar-logo-badge">Intranet</span>
  </div>
  <nav class="sidebar-nav">
    <div class="sidebar-label">Workspace</div>
    <a href="../index" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
      Dashboard
    </a>
    <a href="../brand" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
      Brand
    </a>
    <a href="../team" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      Team
    </a>
    <a href="../docs" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
      Documents
    </a>
    <a href="../mvp-docs/" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
      Product Docs
    </a>
    <a href="../features" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>
      Product Features
    </a>
    <a href="../roadmap" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      Roadmap
    </a>
    <a href="../decisions" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
      Decisions
    </a>
    <a href="../sector-research" class="sidebar-item active">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      Sector Research
    </a>
    <a href="../investor" class="sidebar-item">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>
      Funding
    </a>
    <div class="sidebar-label">External</div>
    <a href="https://amaea0002-dev.github.io/webpage" class="sidebar-item" target="_blank">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
      Website <span class="ext">↗</span>
    </a>
    <a href="https://amaea0002-dev.github.io/prototype/dashboard.html" class="sidebar-item" target="_blank">
      <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
      Prototype <span class="ext">↗</span>
    </a>
  </nav>
  <div class="sidebar-footer" style="position:relative;">
    <div class="sidebar-user" id="sidebarUserArea">
      <div class="sidebar-avatar" id="sidebarAvatar">H</div>
      <div style="flex:1;min-width:0;">
        <div class="sidebar-user-name" id="sidebarUserName">Hasna Sahul Hameed</div>
        <div class="sidebar-user-role" id="sidebarUserRole">CEO &amp; Co-founder</div>
      </div>
      <svg width="11" height="11" fill="none" stroke="rgba(255,255,255,0.35)" stroke-width="2" viewBox="0 0 24 24" style="flex-shrink:0;margin-left:auto;"><polyline points="6 9 12 15 18 9"/></svg>
    </div>
  </div>
</aside>

<header class="topbar">
  <div class="topbar-left">
    <button class="topbar-hamburger" id="menuBtn" aria-label="Open menu"><span></span><span></span><span></span></button>
    <span class="bc-root">Amaea</span>
    <span class="bc-sep">/</span>
    <a href="../sector-research" class="bc-link">Sector Research</a>
    <span class="bc-sep">/</span>
    <span class="bc-current">{title}</span>
  </div>
  <div class="topbar-right">
    <span class="topbar-date" id="topbar-date"></span>
    <button class="theme-toggle" aria-label="Toggle dark mode"></button>
  </div>
</header>

<main class="main">
  <div class="content">

    <a href="../sector-research" class="memo-back">← Back to Sector Research index</a>

    <div class="page-header">
      <p class="page-eyebrow">{eyebrow}</p>
      <h1 class="page-title">{title}</h1>
    </div>

    <div class="memo-meta-bar">
      <span><strong>Next review:</strong> {next_review}</span>
      <span class="memo-meta-sep">·</span>
      <span><strong>Source:</strong> <code>sector-research/{src}</code></span>
      <span class="memo-meta-sep">·</span>
      <span>Living document — update quarterly</span>
    </div>

    <div class="memo-body">
{body}
    </div>

  </div>
</main>

<script>
  document.querySelector('.theme-toggle').addEventListener('click', () => {{
    const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('amaea-theme', next);
  }});
  const menuBtn = document.getElementById('menuBtn');
  const sidebarEl = document.querySelector('.sidebar');
  const overlayEl = document.getElementById('sidebarOverlay');
  if (menuBtn && sidebarEl && overlayEl) {{
    if (window.innerWidth > 768 && localStorage.getItem('amaea-sidebar') === 'collapsed') document.body.classList.add('sidebar-collapsed');
    const closeMobile = () => {{ sidebarEl.classList.remove('open'); overlayEl.classList.remove('open'); document.body.classList.remove('mobile-nav-open'); }};
    menuBtn.addEventListener('click', () => {{
      if (window.innerWidth <= 768) {{ const open = sidebarEl.classList.toggle('open'); overlayEl.classList.toggle('open', open); document.body.classList.toggle('mobile-nav-open', open); }}
      else {{ const c = document.body.classList.toggle('sidebar-collapsed'); localStorage.setItem('amaea-sidebar', c ? 'collapsed' : 'expanded'); }}
    }});
    overlayEl.addEventListener('click', closeMobile);
    sidebarEl.querySelectorAll('a.sidebar-item').forEach(a => a.addEventListener('click', () => {{ if (window.innerWidth <= 768) closeMobile(); }}));
  }}
</script>
<script>
(function () {{
  const userArea  = document.getElementById('sidebarUserArea');
  const nameEl    = document.getElementById('sidebarUserName');
  const roleEl    = document.getElementById('sidebarUserRole');
  const avatarEl  = document.getElementById('sidebarAvatar');
  if (userArea) {{
    const chevron = userArea.querySelector('svg');
    if (chevron) {{
      const logout = document.createElement('a');
      logout.href  = '/cdn-cgi/access/logout';
      logout.title = 'Sign out';
      logout.setAttribute('aria-label', 'Sign out');
      logout.style.cssText = 'display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:6px;color:rgba(255,255,255,0.4);text-decoration:none;flex-shrink:0;margin-left:auto;transition:background .15s ease, color .15s ease;';
      logout.addEventListener('mouseenter', () => {{ logout.style.background = 'rgba(255,255,255,0.08)'; logout.style.color = 'rgba(255,255,255,0.85)'; }});
      logout.addEventListener('mouseleave', () => {{ logout.style.background = 'transparent';            logout.style.color = 'rgba(255,255,255,0.4)';   }});
      logout.innerHTML = '<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>';
      chevron.replaceWith(logout);
    }}
  }}
  const ROLE_BY_EMAIL = {{
    'milan@amaea.co.uk': {{ role: 'CTO & Co-Founder', bg: 'linear-gradient(135deg,#1a4080,#4292c6)' }},
    'hasna@amaea.co.uk': {{ role: 'CEO & Co-Founder', bg: 'linear-gradient(135deg,#4C2C4B,#8B6189)' }},
  }};
  fetch('/cdn-cgi/access/get-identity', {{ credentials: 'include' }})
    .then(r => (r.ok ? r.json() : null))
    .then(id => {{
      if (!id || !id.email) return;
      const email     = id.email;
      const name      = id.name || email.split('@')[0];
      const initial   = (name || '?').charAt(0).toUpperCase();
      const meta      = ROLE_BY_EMAIL[email] || {{ role: 'Team', bg: 'linear-gradient(135deg,#3D3651,#8B809C)' }};
      if (nameEl)    nameEl.textContent    = name;
      if (roleEl)    roleEl.textContent    = meta.role;
      if (avatarEl)  {{ avatarEl.textContent = initial; avatarEl.style.background = meta.bg; }}
    }})
    .catch(() => {{}});
}})();
</script>
<script>
  (function(){{
    var el = document.getElementById('topbar-date');
    if (!el) return;
    el.textContent = new Date().toLocaleDateString('en-GB', {{
      weekday:'short', day:'numeric', month:'long', year:'numeric'
    }});
  }})();
</script>
</body>
</html>
"""


def build_one(meta: dict) -> None:
    src_path = SRC_DIR / meta["src"]
    if not src_path.exists():
        print(f"  ! MISSING: {src_path}")
        return
    md = src_path.read_text(encoding="utf-8")
    _h1, body_html = md_to_html(md)
    page = PAGE_TEMPLATE.format(
        title=meta["title"],
        eyebrow=meta["eyebrow"],
        next_review=meta["next_review"],
        src=meta["src"],
        body=body_html,
    )
    out_path = ROOT / meta["out"]
    out_path.write_text(page, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"  ✓ {meta['src']:35s} → {meta['out']:35s} ({size_kb} KB)")


def main() -> None:
    print("Rendering sector research memos…")
    for meta in MEMOS:
        build_one(meta)
    print("Done.")


if __name__ == "__main__":
    main()

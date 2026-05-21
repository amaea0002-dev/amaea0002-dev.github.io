#!/usr/bin/env python3
"""
Build Amaea MVP documentation: convert each /docs/*.md into a branded HTML page.

Usage:  python3 build.py

Inputs:  ../docs/01-...md  …  ../docs/05-...md
Outputs: ./01-product.html, 02-architecture.html, 03-extraction.html,
         04-ai-kb.html, 05-ops.html

Designed to be opened in Safari and exported to PDF via File → Export as PDF
(or Cmd+P → Save as PDF). The print CSS in styles.css takes care of layout.
"""

from __future__ import annotations
import html
import re
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).parent
# Canonical docs live at /Users/milan/Documents/Amaea/docs/, one level up
# from amaea-brand/, not inside it.
DOCS_DIR = ROOT.parent.parent / "docs"

# -------------------------------------------------------------------
# Metadata for each doc: drives cover page + nav + filename
# -------------------------------------------------------------------
DOCS = [
    {
        "src": "01-product-overview.md",
        "out": "01-product.html",
        "num": "Doc 01",
        "title": "Product & Architecture Overview",
        "subtitle": "What Amaea is, who it's for, key features, tech stack at a glance, and the strategic decisions that shape the build.",
        "read": "~20 min read",
        "audience": "Investors · new team · partners",
    },
    {
        "src": "02-technical-architecture.md",
        "out": "02-architecture.html",
        "num": "Doc 02",
        "title": "Technical Architecture",
        "subtitle": "System design, multi-tenancy via Row Level Security, database schema, data flow, computed views, and the rationale behind every key technical decision.",
        "read": "~30 min read",
        "audience": "Engineers · technical due diligence",
    },
    {
        "src": "03-document-extraction.md",
        "out": "03-extraction.html",
        "num": "Doc 03",
        "title": "Document Extraction & Compliance Flag System",
        "subtitle": "The core IP. All 19 document types, the classify-then-extract pipeline, per-type schemas, multi-page grouping, the auto-flag-raising system, and the FCA rule mapping table.",
        "read": "~40 min read",
        "audience": "Compliance evaluation · technical reviewers",
    },
    {
        "src": "04-ai-and-knowledge-base.md",
        "out": "04-ai-kb.html",
        "num": "Doc 04",
        "title": "AI Layer & FCA Knowledge Base",
        "subtitle": "Claude integration, Voyage embeddings, the 11,645-chunk FCA corpus, dual RAG retrieval, prompt structure, evaluation framework, AI-generated reports, and the cron jobs that keep regulatory data fresh.",
        "read": "~30 min read",
        "audience": "AI/ML reviewers · compliance officers · technical investors",
    },
    {
        "src": "05-operations-handbook.md",
        "out": "05-ops.html",
        "num": "Doc 05",
        "title": "Operations Handbook",
        "subtitle": "Deployment procedure, environment variables, migrations, cron inventory, cost monitoring, routine maintenance, and the runbook for common issues.",
        "read": "~20 min read",
        "audience": "Anyone responsible for keeping it running",
    },
]

# -------------------------------------------------------------------
# Markdown → HTML
# -------------------------------------------------------------------
# Deliberately a small, predictable parser tuned for the patterns used
# in the Amaea docs. Block-level: fenced code, tables, headings, lists,
# horizontal rules, paragraphs. Inline: code, bold, italic, links.

INLINE_CODE_RE = re.compile(r"`([^`\n]+?)`")
BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")
ITALIC_RE = re.compile(r"(?<![*\w])\*([^*\n]+?)\*(?!\*)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def render_inline(text: str) -> str:
    """Escape HTML, then re-introduce inline markdown as tags via placeholders."""
    placeholders: dict[str, str] = {}

    def stash(html_fragment: str) -> str:
        token = f"\x00P{len(placeholders)}\x00"
        placeholders[token] = html_fragment
        return token

    # Inline code first — its contents must not be re-processed for bold/italic.
    def code_repl(m: re.Match) -> str:
        return stash(f"<code>{html.escape(m.group(1))}</code>")
    text = INLINE_CODE_RE.sub(code_repl, text)

    # Links next — also stash so URLs aren't re-escaped weirdly.
    def link_repl(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        # Remap internal .md links to the shorter .html output filenames first,
        # before any other normalisation.
        url = remap_doc_link(url)
        url_attr = html.escape(url, quote=True)
        return stash(f'<a href="{url_attr}">{render_inline_plain(label)}</a>')
    text = LINK_RE.sub(link_repl, text)

    # Now escape the remaining plain text.
    text = html.escape(text)

    # Bold and italic on the escaped text.
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = ITALIC_RE.sub(r"<em>\1</em>", text)

    # Restore placeholders.
    for token, frag in placeholders.items():
        text = text.replace(token, frag)
    return text


def render_inline_plain(text: str) -> str:
    """For text inside link labels — escape + bold/italic, no nested links/code."""
    text = html.escape(text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = ITALIC_RE.sub(r"<em>\1</em>", text)
    return text


def remap_doc_link(href: str) -> str:
    """Map references like '03-document-extraction.md' → '03-extraction.html'.

    Handles both the source `.md` form and any already-rewritten `.html` form,
    and tolerates leading "./" or directory prefixes.
    """
    mapping = {d["src"]: d["out"] for d in DOCS}
    for src, out in mapping.items():
        href = href.replace(src, out)
        # Also map the variant where the .md has already been rewritten to .html
        # with the original (long) basename.
        long_html = src.replace(".md", ".html")
        href = href.replace(long_html, out)
    return href


def render_table(rows: list[str]) -> str:
    """rows is a list of pipe-delimited markdown lines, including header & separator."""
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
        out.append(f'<th>{render_inline(h)}</th>')
    out.append('</tr></thead><tbody>')
    for r in body:
        out.append('<tr>')
        for c in r:
            out.append(f'<td>{render_inline(c)}</td>')
        out.append('</tr>')
    out.append('</tbody></table>')
    return "\n".join(out)


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
ORDERED_LI_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
UNORDERED_LI_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
TABLE_SEP_RE = re.compile(r"^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", s)


def md_to_html(md: str) -> tuple[str, str]:
    """Return (h1_title, body_html). Drops the leading H1 from body."""
    lines = md.replace("\r\n", "\n").split("\n")
    i = 0
    body: list[str] = []
    h1_title = ""

    while i < len(lines):
        line = lines[i]

        # Fenced code block
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

        # Table (header row + separator + body rows)
        if line.lstrip().startswith("|") and i + 1 < len(lines) and TABLE_SEP_RE.match(lines[i + 1] or ""):
            rows = [line]
            j = i + 1
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(lines[j])
                j += 1
            body.append(render_table(rows))
            i = j
            continue

        # Horizontal rule
        if re.match(r"^\s*---+\s*$", line):
            body.append("<hr/>")
            i += 1
            continue

        # Heading
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            if level == 1 and not h1_title:
                h1_title = text  # captured separately, do not emit in body
                i += 1
                continue
            sid = slugify(text)
            body.append(f'<h{level} id="{sid}">{render_inline(text)}</h{level}>')
            i += 1
            continue

        # Ordered list
        if ORDERED_LI_RE.match(line):
            items, j = parse_list(lines, i, ordered=True)
            body.append(items)
            i = j
            continue

        # Unordered list
        if UNORDERED_LI_RE.match(line):
            items, j = parse_list(lines, i, ordered=False)
            body.append(items)
            i = j
            continue

        # Blank line
        if line.strip() == "":
            i += 1
            continue

        # Paragraph: gather contiguous non-empty, non-block lines
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


def parse_list(lines: list[str], start: int, ordered: bool) -> tuple[str, int]:
    """Parse a (possibly nested) list starting at lines[start]. Returns (html, end_index)."""
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
            # Allow a blank line between sibling items: if a same-level same-type
            # item starts on the next non-blank line, swallow the blank(s) and continue.
            if line.strip() == "":
                k = i + 1
                while k < len(lines) and lines[k].strip() == "":
                    k += 1
                if k < len(lines):
                    mk = re_li.match(lines[k])
                    if mk and (base_indent is None or len(mk.group(1)) == base_indent):
                        i = k
                        continue
            # Otherwise, stop and let the caller pick up.
            break

        indent_str = m.group(1)
        indent = len(indent_str)

        if base_indent is None:
            base_indent = indent
        if indent < base_indent:
            break
        if indent > base_indent:
            # Shouldn't happen — nested handled inside the item loop below.
            break

        # Item text
        if ordered:
            text = m.group(3)
        else:
            text = m.group(2)

        # Look ahead: collect continuation lines + nested lists
        item_continuation: list[str] = []
        nested_blocks: list[str] = []
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if nxt.strip() == "":
                # blank line could still be inside list if next non-blank is indented
                k = j
                while k < len(lines) and lines[k].strip() == "":
                    k += 1
                if k < len(lines):
                    mn = ORDERED_LI_RE.match(lines[k]) or UNORDERED_LI_RE.match(lines[k])
                    if mn and len(mn.group(1)) > base_indent:
                        j = k
                        continue
                break

            # Nested list?
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

            # Sibling item (same indent, same type) → stop the lookahead
            if re_li.match(nxt) and len(re_li.match(nxt).group(1)) == base_indent:
                break
            # Sibling item of other type at same indent → also stop
            if re_other.match(nxt) and len(re_other.match(nxt).group(1)) == base_indent:
                break

            # Plain continuation: indented (or unindented) text continuation
            if nxt.strip() != "" and (nxt.startswith(" " * (base_indent + 2)) or (not nxt.startswith("|") and not HEADING_RE.match(nxt))):
                # treat as paragraph continuation of current item
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

    html_out = f"<{tag}>\n" + "\n".join(items) + f"\n</{tag}>"
    return html_out, i


# -------------------------------------------------------------------
# Page template
# -------------------------------------------------------------------
PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title} · Amaea MVP Docs</title>
  <link rel="icon" href="logo-plum.png"/>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <link rel="stylesheet" href="styles.css"/>
</head>
<body>

<section class="cover">
  <div class="cover-top">
    <img src="logo-white.png" alt="Amaea"/>
    <span class="cover-badge">MVP Documentation</span>
  </div>

  <div class="cover-body">
    <p class="cover-eyebrow">{num} · {audience}</p>
    <h1 class="cover-title">{title}</h1>
    <p class="cover-sub">{subtitle}</p>
  </div>

  <div class="cover-foot">
    <div>
      <p class="cover-meta-label">Status</p>
      <p class="cover-meta-value">MVP · pre-launch</p>
    </div>
    <div>
      <p class="cover-meta-label">As of</p>
      <p class="cover-meta-value">14 May 2026</p>
    </div>
    <div>
      <p class="cover-meta-label">Owners</p>
      <p class="cover-meta-value">Hasna Sahul Hameed · Milan Sajiv</p>
    </div>
    <div>
      <p class="cover-meta-label">Length</p>
      <p class="cover-meta-value">{read}</p>
    </div>
  </div>

  <div class="cover-tagline">
    <p class="cover-tagline-text">Stay compliant. Stay confident.</p>
    <p class="cover-tagline-sub">amaea</p>
  </div>
</section>

<nav class="doc-nav">
  <a href="index.html">← All documents</a>
  <span class="doc-nav-meta">{num} · {read}</span>
</nav>

<article class="doc">
{body}
</article>

</body>
</html>
"""


def build_doc(meta: dict) -> None:
    src_path = DOCS_DIR / meta["src"]
    md = src_path.read_text(encoding="utf-8")
    h1_title, body_html = md_to_html(md)

    # Patch internal .md → .html links inside body html (in case any escaped through)
    body_html = remap_doc_link(body_html)

    page = PAGE_TEMPLATE.format(
        title=meta["title"],
        num=meta["num"],
        subtitle=meta["subtitle"],
        read=meta["read"],
        audience=meta["audience"],
        body=body_html,
    )
    out_path = ROOT / meta["out"]
    out_path.write_text(page, encoding="utf-8")
    print(f"  ✓ {meta['src']:40s} → {meta['out']}")


# -------------------------------------------------------------------
# Secret-leak guard
# -------------------------------------------------------------------
# Patterns that should never appear in the rendered HTML. If they do, the
# build fails — so a stray literal secret in a source markdown file is
# caught before it ships. Add new patterns here when new secrets are minted.
SECRET_PATTERNS = [
    # Old INGEST_SECRET shape — `amaea-ingest-NNNN`. Rotation should produce a
    # high-entropy value (use openssl rand -hex 32) that doesn't match.
    re.compile(r"amaea-ingest-\d{4}"),
    # Any literal Bearer token after "Bearer ". Allows shell-variable forms
    # (`Bearer $INGEST_SECRET`, `Bearer <INGEST_SECRET>`) which start with $ or <.
    re.compile(r"Bearer\s+(?![\$<])[A-Za-z0-9_\-]{8,}"),
    # Supabase project refs leak the target Supabase tenant.
    re.compile(r"\bsqsq[a-z0-9]{16,}\.supabase\.co\b"),
    # Vercel project / team IDs.
    re.compile(r"\b(prj_|team_)[A-Za-z0-9]{20,}\b"),
]


def scan_for_secrets(name: str, content: str) -> list[str]:
    """Return a list of (pattern_label, matched_snippet) findings."""
    findings: list[str] = []
    for pat in SECRET_PATTERNS:
        for m in pat.finditer(content):
            # Show a small window around the match for context
            start = max(0, m.start() - 30)
            end = min(len(content), m.end() + 30)
            snippet = content[start:end].replace("\n", " ")
            findings.append(f"  {name}: /{pat.pattern}/ near …{snippet}…")
    return findings


def main() -> None:
    print("Building Amaea MVP documentation…")
    leaks: list[str] = []
    for meta in DOCS:
        build_doc(meta)
        # Re-read the just-written file and scan it
        out_path = ROOT / meta["out"]
        leaks.extend(scan_for_secrets(meta["out"], out_path.read_text(encoding="utf-8")))
    if leaks:
        print("\n❌ Secret-leak guard tripped — DO NOT publish this build:")
        for line in leaks:
            print(line)
        print(
            "\nReplace the literal value in the source markdown with a "
            "shell-style placeholder (e.g. `$INGEST_SECRET`) and point readers "
            "to 1Password for the live value. See audit 2026-05-19."
        )
        raise SystemExit(1)
    print("Done. (Secret-leak guard passed.)")


if __name__ == "__main__":
    main()

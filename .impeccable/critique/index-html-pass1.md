# Intranet Critique — Pass #1 — 2026-05-20

**Target:** team.amaea.co.uk (`amaea-brand`)
**Register:** Product
**Nielsen score:** 29/40 (72.5%)
**AI-slop verdict:** ~92% non-slop; two/three card-trios with template-shaped rhythm

## Heuristic scores (0-4 each)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Active sidebar is visual-only, no `aria-current="page"`. |
| 2 | Real-world match | 4 | RMAR / DISP / COBS / FG language correct. |
| 3 | User control & freedom | 3 | No "back to top" on long pages; eval-v2 has no score-undo affordance. |
| 4 | Consistency & standards | 3 | 4 duplicated script blocks per page; callout pattern split between `.ir-callout` and inline `style="background:var(--plum-tint)"`. |
| 5 | Error prevention | 2 | Eval-v2 score overwrite is silent; Export CSV lacks completion warning. |
| 6 | Recognition | 4 | Full-noun sidebar names + per-page eyebrows + TOCs. |
| 7 | Flexibility | 2 | **No search.** Single largest gap. |
| 8 | Aesthetic / minimalist | 3 | Stat-card font-size inline overrides; dashboard ecosystem nests cards. |
| 9 | Error recovery | 2 | Topbar avatar renders literal `?` when unhydrated; reads as broken. |
| 10 | Help / docs | 3 | New-joiner card present; no global "what is this site" page. |

## P0 — Ship-blockers

- **Search (Cmd-K).** Static client-side index over page titles + h2 + h3. Biggest single ergonomic gap on a 15-page knowledge base.
- **`aria-current="page"`** on active sidebar items. CSS selector swap + per-page markup edit.

## P1 — High-impact polish

- Topbar avatar fallback `?` → skeleton circle until hydrated.
- Investor.html (123 inline) + financial-model (77) distill pass #2.
- Decisions log filter strip (year/quarter) + year-jump anchors.
- Dashboard splits the "new-joiner" content out to `/onboarding`.
- Financial-model 8-col tables: add colgroup header (Identity | Volume | Revenue | Costs | Result).

## P2 — Polish

- Stat-card font-size variants (`.stat-value--sm`, `.stat-value--md`).
- Operations sidebar group has only 1 item → grow or merge.
- Extract shared footer scripts into `intranet.js`.
- Add `/404` page.
- A11y wrap em-dash data-placeholders with `aria-hidden`.
- Remove dead `user-select-panel` markup (JS unconditionally hides it).

## Absolute-ban violations (detector)

- **roadmap.html line 13** — `border-left: 4px solid var(--gray-300)` — side-stripe ban. NEW regression. Fix immediately.

## Persona red flags

- **Hasna (CEO):** dashboard top-half dominated by updates; Key Dates / Checklist below fold; Team sidebar sub-items collapsed by default.
- **Milan (CTO):** financial-model is read-optimised, not edit-optimised; "How to update" should anchor near top.
- **Investor:** sidebar exposure of Decisions / Eval / Incidents leaks internal surface; title says "Intranet" in `<title>`.
- **Compliance reviewer:** "Last reviewed" dates are claimed not verified; eval-v2 shows literal `&#039;` entities in places.

## Provocations

1. Who actually uses this and how often? Pull telemetry; dashboard bottom-half may be dead weight.
2. Is a flat sidebar the right primitive at this density? Notion-tree + Cmd-K?
3. Why does investor.html live in the intranet at all?
4. "Last reviewed" dates: assertion or evidence? Build pipeline could stamp from git.

## Strengths

1. Decisions log: best content artefact; specific dates, migration numbers, "Why:" on every entry.
2. Eval-v2 widget: most-app-like surface; pagination + localStorage + filters + CSV export.
3. Financial-model TOC + anchors: pattern to propagate.

## Bottom line

Design-only changes can push 29 → ~33/40. Past that requires architecture/scope work (search, investor-view split, dashboard refactor, automated review dates).

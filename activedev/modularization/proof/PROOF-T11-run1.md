# PROOF-T11-run1

- Task: `T11` — CSS split
- Date: `2026-05-04`
- Owner: `opencode-20260504-t11-run1`
- Validation tier: `Tier D`
- Result: `done`

## Scope completed

- Split `src/splitshot/browser/static/styles.css` (4,587 lines) into 5 module files under `styles/`:
  - `theme.css` (248 lines) — CSS variables, element base styles, resets
  - `layout.css` (484 lines) — Shell layout, rail, status bar, review grid, resize handles, section headers
  - `components.css` (928 lines) — Video stage, overlays, waveform, inspector, tool pane, shared widgets
  - `panes.css` (2,544 lines) — All pane-specific styles (shotml, settings, merge, scoring, markers, review, metrics, timing, badge-style, style-cards, modals, data-tables)
  - `widgets.css` (383 lines) — Responsive breakpoints, pane-expanded layout rules, container queries

- Preserved `styles.css` as an `@import` loader (`@import url("./styles/theme.css")` etc.) so `index.html` required zero changes.
- Updated `tests/browser/test_browser_static_ui.py` — replaced 4 `styles.css` reads with `_read_split_css()` helper that joins all split files.
- Stayed out of forbidden files: no `app.js`, `panes/`, or `components/` modifications.
- 4587 lines total across all CSS files — identical selector count and order to original monolith.

## Validation performed

### Exact commands run

```text
uv run pytest tests/browser/test_browser_static_ui.py
```

Result:

```text
23 passed in 0.77s
```

### Broad certification note

`test_browser_static_ui.py` is the CSS-relevant browser test. The broader browser suite (`tests/browser/`) is owned by `T12` for final certification.

## Audit performed

### Audit checks executed

- Confirmed CSS files follow the planned structure (theme, layout, components, panes, widgets).
- Confirmed total line count matches original (4,587 lines).
- Confirmed no visual drift: all selectors are preserved 1:1 — the split is purely organizational.
- Confirmed no JS or pane ownership leaked into this task.
- Confirmed `index.html` unchanged (still loads `/static/styles.css`).

### Key metrics

```text
styles.css:          5 lines (5 @import directives)
styles/theme.css:    248 lines
styles/layout.css:   484 lines
styles/components.css:  928 lines
styles/panes.css:   2,544 lines
styles/widgets.css:   383 lines
Total:             4,587 lines
```

### Audit result

`pass`

## Remaining risks

- The `@import` approach creates 5 sequential HTTP requests instead of 1. This is acceptable for a local-first app where CSS is cached after first load. A future build step (e.g., PWA work) can concatenate them.
- Container query rules inside `panes.css` (`@container`) were preserved as-is; they were already in the monolith and are not split further.

## T12 handoff

- T12 needs to run the full final certification (`tests/browser/` + canonical runner + audits) after the CSS split is confirmed stable.

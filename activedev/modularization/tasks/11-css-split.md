# T11 — CSS Split

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T11` |
| status | tracked in `progress.md` |
| depends-on | `T10` |
| parallel-lane | `none` |
| risk | `medium` |
| touches-files | `src/splitshot/browser/static/styles.css`, `src/splitshot/browser/static/styles/reset.css`, `src/splitshot/browser/static/styles/layout.css`, `src/splitshot/browser/static/styles/panes.css`, `src/splitshot/browser/static/styles/components.css`, `src/splitshot/browser/static/styles/widgets.css`, `src/splitshot/browser/static/styles/theme.css`, `src/splitshot/browser/static/index.html`, `tests/browser/test_browser_static_ui.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/app.js`, `src/splitshot/browser/static/panes/**`, `src/splitshot/browser/static/components/**`, `tests/browser/test_merge_export_contracts.py`, `tests/browser/test_overlay_review_contracts.py` |
| owned-tests-docs | `tests/browser/test_browser_static_ui.py` and any audit artifacts required to prove visual parity |
| proof-file | `activedev/modularization/proof/PROOF-T11-runN.md` |

## Goal

Split the monolithic stylesheet into navigable CSS modules without changing the rendered UI.

## Scope

In scope:

- create the `styles/` directory and split CSS by responsibility
- update stylesheet loading in `index.html` only as required by the split
- preserve selectors and visual output exactly

Out of scope:

- JS logic changes
- new visual design or CSS cleanup beyond what is needed for the split

## Preconditions

- [ ] `T10` is `done`
- [ ] monolith cleanup is stable
- [ ] UI audit baselines are available for comparison

## Implementation checklist

- [ ] split `styles.css` into the planned CSS files
- [ ] preserve selector behavior and cascade order
- [ ] keep `index.html` loading consistent with the final structure

## Validation

Use Tier D from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_browser_static_ui.py
uv run pytest tests/browser/
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
```

## Audit checks

Use cleanup/certification checks from `audit.md`:

- CSS files follow the intended structure
- visual drift is not introduced by selector or load-order changes
- no JS or pane ownership leaked into this task

## Handoff outputs

- split CSS structure ready for final certification
- proof of preserved visual parity for `T12`

## Done criteria

- [ ] CSS files are split and wired
- [ ] required tests and UI audit pass
- [ ] proof file was written
- [ ] `progress.md` was updated

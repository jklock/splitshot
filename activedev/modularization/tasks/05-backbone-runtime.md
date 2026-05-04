# T05 — Backbone Runtime

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T05` |
| status | tracked in `progress.md` |
| depends-on | `T04` |
| parallel-lane | `none` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/lib/api.js`, `src/splitshot/browser/static/lib/layout.js`, `src/splitshot/browser/static/lib/keys.js`, `src/splitshot/browser/static/lib/processing.js`, `src/splitshot/browser/static/lib/activity.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_control.py`, `tests/browser/test_browser_interactions.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/components/**`, `src/splitshot/browser/static/panes/**`, `src/splitshot/browser/static/styles.css` |
| owned-tests-docs | `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_control.py`, `tests/browser/test_browser_interactions.py` |
| proof-file | `activedev/modularization/proof/PROOF-T05-runN.md` |

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `pending` |
| last-synced | `2026-05-02` |
| blocker | `Awaiting T04.` |

## Goal

Extract the runtime backbone modules that handle API coordination, layout, keyboard handling, processing indicators, and activity flows.

## Scope

In scope:

- `api.js`
- `layout.js`
- `keys.js`
- `processing.js`
- `activity.js`
- the `app.js` adoption work needed to route through them

Out of scope:

- component extraction
- pane extraction
- CSS changes

## Preconditions

- [ ] `T04` is `done`
- [ ] `utils`, `event-bus`, and `store` are available
- [ ] live bootstrap/startup still passes the `T04` validation scope

## Implementation checklist

- [ ] extract runtime backbone modules with no visible behavior change
- [ ] preserve existing API payload and activity semantics
- [ ] keep layout and key behavior identical to the current browser shell
- [ ] document any temporary compatibility shims in the proof file

## Validation

Use Tier B from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py tests/browser/test_browser_interactions.py
```

## Audit checks

Use extraction-task checks from `audit.md`:

- runtime backbone boundaries are clean
- no pane/component work leaked into `T05`
- compatibility shims are intentional and recorded

## Handoff outputs

- working runtime backbone modules
- adoption notes for `T06`

## Done criteria

- [ ] runtime backbone modules exist
- [ ] `app.js` routes through them without UX drift
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated

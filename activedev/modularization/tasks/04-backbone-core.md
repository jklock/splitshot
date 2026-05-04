# T04 — Backbone Core

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T04` |
| status | tracked in `progress.md` |
| depends-on | `T03` |
| parallel-lane | `none` |
| risk | `medium` |
| touches-files | `src/splitshot/browser/static/lib/utils.js`, `src/splitshot/browser/static/lib/event-bus.js`, `src/splitshot/browser/static/lib/store.js`, `src/splitshot/browser/static/app.js`, `tests/browser/test_browser_static_ui.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/lib/api.js`, `src/splitshot/browser/static/lib/layout.js`, `src/splitshot/browser/static/lib/keys.js`, `src/splitshot/browser/static/components/**`, `src/splitshot/browser/static/panes/**` |
| owned-tests-docs | `tests/browser/test_browser_static_ui.py` and any narrow tests needed for bootstrap-safe extraction |
| proof-file | `activedev/modularization/proof/PROOF-T04-runN.md` |

## Progress snapshot

Informational only; authoritative task state remains `activedev/modularization/progress.md`.

| Field | Value |
| --- | --- |
| current-status | `pending` |
| last-synced | `2026-05-02` |
| blocker | `Awaiting accepted completion of T03.` |

## Goal

Extract the zero-dependency backbone modules that every later pane and component will rely on.

## Scope

In scope:

- `utils.js`
- `event-bus.js`
- `store.js`
- `app.js` delegation changes needed to adopt them safely

Out of scope:

- runtime backbone modules owned by `T05`
- component extraction
- pane extraction

## Preconditions

- [ ] `T03` is `done`
- [ ] shell bootstrap is module-capable
- [ ] ownership anchors for `app.js` are current

## Implementation checklist

- [ ] extract utility helpers with no behavior change
- [ ] create event-bus and store modules with thin initial APIs
- [ ] delegate from `app.js` without breaking existing flows
- [ ] keep the public/browser-visible behavior unchanged

## Validation

Use Tier B from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py
```

## Audit checks

Use extraction-task checks from `audit.md`:

- extracted files match assigned ownership
- no runtime-only backbone work leaked into `T04`
- `app.js` responsibility moved in the expected direction

## Handoff outputs

- working `utils`, `event-bus`, and `store` modules
- delegation notes for `T05`

## Done criteria

- [ ] backbone core modules exist
- [ ] `app.js` delegates safely to them
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated

# T03 — Bootstrap Module Shell

## Metadata

| Field | Value |
| --- | --- |
| task-id | `T03` |
| status | tracked in `progress.md` |
| depends-on | `T01`, `T02` |
| parallel-lane | `none` |
| risk | `high` |
| touches-files | `src/splitshot/browser/static/index.html`, `src/splitshot/browser/static/app.js`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_control.py`, `activedev/modularization/progress.md` |
| forbidden-files | `src/splitshot/browser/static/lib/**`, `src/splitshot/browser/static/components/**`, `src/splitshot/browser/static/panes/**`, `src/splitshot/browser/static/styles.css` |
| owned-tests-docs | `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_control.py` |
| proof-file | `activedev/modularization/proof/PROOF-T03-runN.md` |

## Goal

Prepare the browser shell for module loading while preserving the existing runtime behavior and DOM contract.

## Scope

In scope:

- switch the shell to a module-capable bootstrap
- keep compatibility shims in `app.js` so behavior remains unchanged
- update the static-ui and control tests only when bootstrap expectations change

Out of scope:

- creation of permanent backbone modules
- pane extraction
- CSS reorganization

## Preconditions

- [ ] `T01` and `T02` are `done`
- [ ] ownership anchors for `index.html` and `app.js` are present in `audit.md`
- [ ] QA-doc-backed tests are passing on the starting revision

## Implementation checklist

- [ ] change the shell load mode in `index.html` only as needed for module bootstrap
- [ ] keep `app.js` behavior-compatible via wrappers or delegated bootstrap logic
- [ ] preserve browser globals required by existing tests until cleanup
- [ ] reconcile static-ui and control tests with the final bootstrap shape

## Validation

Use Tier B from `validation.md`.

Required commands:

```text
uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control.py
```

Escalate to the broader browser suite if bootstrap changes affect live startup behavior.

## Audit checks

Use extraction-task checks from `audit.md`:

- no permanent backbone logic leaked into the wrong task
- no visible UI or control drift occurred
- `app.js` remains compatible while becoming module-capable

## Handoff outputs

- module-capable browser shell
- compatibility notes for `T04`

## Done criteria

- [ ] shell bootstrap is module-capable
- [ ] compatibility globals remain available when required
- [ ] required tests pass
- [ ] proof file was written
- [ ] `progress.md` was updated

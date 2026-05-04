# PROOF-T10.5-run1

- Task: `T10.5` — Cleanup bridge
- Date: `2026-05-04`
- Owner: `copilot-orchestrator-20260504-t10.5-run1`
- Validation tier: `Tier D`
- Result: `done`

## Scope completed

- Retired `LEGACY_WIRE_EVENTS_SOURCE_ANCHORS` from `src/splitshot/browser/static/app.js`.
- Narrowed the legacy page-global bridge installed by `installLegacyGlobalCompat(...)` so the shell render/event helpers plus the keepalive / auto-apply bridge helpers no longer leak onto `window`.
- Kept the intentionally retained runtime globals that the browser tests still call directly, including `createNewProject()`, `useProjectFolder()`, `renderTextBoxEditors()`, `setReviewTextBoxExpanded()`, `setPopupBubbles()`, and `autoTracePopupBubbleMotion()`.
- Migrated the shared lifecycle/export source contracts off stale `app.js` event text and onto the extracted module boundaries:
  - `tests/browser/test_project_lifecycle_contracts.py` now asserts `panes/project-pane.js` plus `lib/shell-runtime.js`
  - `tests/browser/test_merge_export_contracts.py` now asserts `panes/export-pane.js`, `panes/merge-pane.js`, plus `lib/shell-runtime.js`
  - `tests/browser/test_browser_static_ui.py` now records the narrower legacy-global bridge surface and the intentionally retained mutable globals
- Preserved zero functional change: no visible controls, copy, control ids, layout, or workflow behavior changed.

## Explicit leftover resolution

- `data-table.js` remains permanently waived.
  - Rechecked during this bridge pass; no new multi-area reuse justified reopening the helper.
- The shared debounce / keepalive / draft-flush seams named in the `T10` handoff were closed as browser-contract blockers in this run.
  - Their stale source anchors were removed.
  - Their legacy page-global exposure was reduced.
  - The underlying orchestration remains internal app/runtime coordination, which was intentionally not re-extracted in this zero-functional-change bridge pass.
- PractiScore guardrail status: reviewed and unchanged.
  - The `practiscore_session`, `practiscore_sync`, and `practiscore_options` contract surface was not modified.
  - No targeted PractiScore suite edits were required after the contract migration because the Project-pane behavior stayed identical.

## Validation performed

### Exact command run

```text
uv run pytest tests/browser/test_project_lifecycle_contracts.py::test_project_client_flushes_drafts_before_lifecycle_and_primary_import_paths tests/browser/test_merge_export_contracts.py::test_app_merge_export_commit_and_log_freshness_contracts tests/browser/test_browser_static_ui.py::test_browser_app_bootstrap_delegates_backbone_core_modules tests/browser/test_browser_interactions.py::test_project_pane_practiscore_and_primary_controls_enable_after_project_create
```

### Result

```text
4 passed in 77.81s (0:01:17)
```

### Broad certification status

- Intentionally deferred per `validation.md` Tier D and the `T10.5` task packet.
- Broad browser/audit certification owner remains `T12`.

## Diagnostics and receipts

### Diagnostics

`get_errors` reported no errors in:

- `src/splitshot/browser/static/app.js`
- `tests/browser/test_project_lifecycle_contracts.py`
- `tests/browser/test_merge_export_contracts.py`
- `tests/browser/test_browser_static_ui.py`

### Compact diff receipt

```text
git diff --stat -- src/splitshot/browser/static/app.js tests/browser/test_project_lifecycle_contracts.py tests/browser/test_merge_export_contracts.py tests/browser/test_browser_static_ui.py
```

Result:

```text
 src/splitshot/browser/static/app.js               | 306 ++++------------------
 tests/browser/test_browser_static_ui.py           |  34 ++-
 tests/browser/test_merge_export_contracts.py      |  22 +-
 tests/browser/test_project_lifecycle_contracts.py |  41 +--
 4 files changed, 132 insertions(+), 271 deletions(-)
```

## T11 handoff

- `T11` is unblocked and ready to claim.
- The bridge-cleanup proof is complete; the next task can focus on `styles.css` splitting without carrying the stale `app.js` event-anchor debt.

## Remaining risks

- Other shared contract files listed in the `T10.5` packet were reviewed during investigation but did not need edits for this exact anchor-retirement pass; if a later cleanup removes more app-owned wrapper families, those suites may need the same module-boundary migration treatment.
- Broad browser-suite, canonical-runner, and browser-audit certification remain deferred to `T12`.

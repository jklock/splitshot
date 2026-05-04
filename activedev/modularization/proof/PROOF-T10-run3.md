# PROOF-T10-run3

- Task: `T10` — Monolith cleanup
- Date: `2026-05-04`
- Owner: `copilot-orchestrator-20260504-t10-run3`
- Validation tier: `Tier D`
- Result: `done`

## Scope completed

- Moved the legacy page-global installer implementation out of `src/splitshot/browser/static/app.js` into `src/splitshot/browser/static/lib/global-compat.js` as `installLegacyGlobalCompat(...)`.
- Reduced `app.js` to a bootstrap call for the legacy global bridge instead of keeping the inline `installValueGlobals(...)` / `installMutableGlobals(...)` installer body in the monolith.
- Removed dead settings fallback scaffolding from `app.js`:
  - `settingsValueAtPath(...)`
  - `settingsHasPath(...)`
  - `sameSettingsValue(...)`
  - `settingsSourceLabel(...)`
  - `formatSettingsValue(...)`
  - `settingFieldCurrentValue(...)`
  - `settingFieldSource(...)`
- Reduced `renderSettingsLayerSummary(...)` and `renderSettingsPane()` in `app.js` to pure delegates to the extracted settings pane.
- Updated the owned static browser contract in `tests/browser/test_browser_static_ui.py` so the backbone/bootstrap assertions follow the moved legacy-global installer boundary.

## Data-table decision

- Permanent waiver for `data-table.js` in `T10`.
- Evidence: the remaining direct table-construction logic is isolated to the pane-owned `settings-pane.js`, while the other timing / scoring / metrics table surfaces already live in pane-owned renderers or static shell hosts.
- Creating a new `data-table.js` now would be speculative reuse rather than meaningful monolith cleanup.

## Temporary bridge anchors / T10.5 handoff

`T10` is complete, but the following intentionally remain for `T10.5` shared-contract cleanup:

1. `LEGACY_WIRE_EVENTS_SOURCE_ANCHORS` in `src/splitshot/browser/static/app.js`.
   - Remove only after the shared source-contract suites migrate off the legacy `wireEvents()` text anchors.
2. The broad page-global compatibility surface installed by `installLegacyGlobalCompat(...)`.
   - Narrow or replace only after shared browser/runtime suites stop depending on bare globals like `state`, `activeTool`, `createNewProject()`, `setPopupBubbles()`, and `renderTextBoxEditors()`.
3. App-level shared debounce / keepalive seams still in `app.js`:
   - `autoApplyProjectDetails`
   - `autoApplyPractiScoreContext`
   - `autoApplyProjectUiState`
   - `autoApplyOverlay`
   - `autoApplyMerge`
   - `autoApplyExportLayout`
   - `autoApplyExportSettings`
   - `autoApplyScoring`
   - `sendKeepaliveJson`
   - `sendProjectUiStateKeepalive`
   - project draft flush / keepalive sequencing around them
4. Shared browser-contract migrations owned by `T10.5`:
   - `tests/browser/test_project_lifecycle_contracts.py`
   - `tests/browser/test_merge_export_contracts.py`
   - `tests/browser/test_overlay_review_contracts.py`
   - `tests/browser/test_scoring_metrics_contracts.py`
   - `tests/browser/test_timing_waveform_contracts.py`
   - `tests/browser/test_browser_control.py`
   - `tests/browser/test_browser_remaining_controls_e2e.py`
   - any PractiScore contract suites implicated by bridge retirement

## Validation performed

### Exact command run

```text
uv run pytest tests/browser/test_browser_static_ui.py::test_browser_app_bootstrap_delegates_backbone_core_modules tests/browser/test_browser_static_ui.py::test_browser_ui_keeps_video_timeline_waveform_and_inspector_together tests/browser/test_browser_static_ui.py::test_browser_auto_apply_snapshots_form_payloads_before_debounce tests/browser/test_browser_interactions.py::test_project_pane_practiscore_and_primary_controls_enable_after_project_create
```

### Result

```text
4 passed in 84.01s (0:01:24)
```

### Broad certification status

- Intentionally deferred per `validation.md` Tier D and the `T10` task packet.
- Broad certification owner remains `T12`.

## Audit receipts

### Diagnostics

`get_errors` reported no errors in:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/global-compat.js`
- `tests/browser/test_browser_static_ui.py`

### Compact command receipt

```text
wc -l src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/global-compat.js tests/browser/test_browser_static_ui.py && echo '---' && git diff --stat -- src/splitshot/browser/static/app.js src/splitshot/browser/static/lib/global-compat.js tests/browser/test_browser_static_ui.py
```

Result:

```text
   10095 src/splitshot/browser/static/app.js
      75 src/splitshot/browser/static/lib/global-compat.js
    1926 tests/browser/test_browser_static_ui.py
   12096 total
---
 src/splitshot/browser/static/app.js               | 265 +++++-----------------
 src/splitshot/browser/static/lib/global-compat.js |  35 +++
 tests/browser/test_browser_static_ui.py           |  20 +-
 3 files changed, 107 insertions(+), 213 deletions(-)
```

## Audit conclusion

- Ownership was respected: only `T10`-owned files were edited.
- `app.js` narrowed further by removing the inline legacy-global installer body and dead settings fallback logic.
- No user-visible behavior, HTML, CSS, control ids, or workflow copy changed in this run.
- Remaining bridge seams are explicitly documented for `T10.5` instead of being silently carried forward.

## Remaining risks

- The runtime page-global bridge is still intentionally broad until `T10.5` migrates shared browser-contract suites off those globals.
- `LEGACY_WIRE_EVENTS_SOURCE_ANCHORS` remains intentionally in `app.js` until `T10.5` retires the shared source assertions that still need it.
- Shared debounce / keepalive / draft-flush orchestration remains in `app.js`; that is deliberate handoff scope for `T10.5`, not unfinished `T10`-owned work.

# PROOF-T10-run1

- Task: `T10` — Monolith cleanup
- Date: `2026-05-03`
- Owner: `copilot-orchestrator-20260503-t10-run1`
- Validation tier: `Tier D` (task packet requirement)
- Result: `blocked`

## Scope completed

- Repaired the corrupted `src/splitshot/browser/static/app.js` workspace state caused by an earlier failed T10 compat-layer edit so the browser bootstrap is healthy again.
- Restored the missing top-of-file mutable state, constants, draft helpers, runtime declarations, and backbone/store glue required by the current modularized shell, including:
  - layout / waveform / processing / activity state
  - project / merge / overlay draft state
  - `normalizeToolId()`
  - `normalizeProjectNameValue()` / `projectDetailValue()` / `applyProjectDetailsDraft()` / `mergeProjectDetailsDraft()`
  - `normalizeMergeDraftValue()` / `applyMergeDraft()` / `mergeMergeDraft()`
  - `normalizeOverlayPositionDraftValue()`
  - `appBus`, `appStore`, `syncBackboneStore()`, `setStateValue()`, `setSelectedShotIdValue()`, and `setActiveToolValue()`
- Removed the accidental duplicate top-of-file `installLegacyGlobalCompat()` block and its orphaned trailing fragment while preserving the intended bottom-of-file compatibility installer.
- Removed a duplicate top-level `$` declaration that was preventing module evaluation and stopping the compat installer from publishing the browser globals.
- Reconfirmed that the page now loads in module mode and exposes the live compatibility surface (`window.activeTool`, `window.__splitshotBackbone`, and `window.__splitshotBootstrapMode`).

## Why `T10` is blocked

The current task packet says `T10` may touch:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/lib/**`
- `src/splitshot/browser/static/components/**`
- `src/splitshot/browser/static/panes/**`
- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_interactions.py`
- `activedev/modularization/progress.md`

However, the live workspace still has shared browser-contract tests outside that touch list asserting source-visible `app.js` seams that `T10` would need to delete in order to leave a truly bootstrap-only shell.

Blocking examples confirmed during this run:

- `tests/browser/test_project_lifecycle_contracts.py` still source-asserts `wireEvents()` project/open/import handlers in `app.js`.
- `tests/browser/test_merge_export_contracts.py` still source-asserts merge/export ordering anchors and `wireEvents()` export behavior in `app.js`.
- `tests/browser/test_overlay_review_contracts.py`, `tests/browser/test_scoring_metrics_contracts.py`, and `tests/browser/test_timing_waveform_contracts.py` still source-assert many wrapper seams that remain in `app.js`.
- Runtime browser tests still use bare globals exposed by `installLegacyGlobalCompat()`, including patterns such as `activeTool`, `state`, `selectedShotId`, `createNewProject()`, `setPopupBubbles()`, `renderTextBoxEditors()`, and related page-scope helpers.

Because of those still-live cross-lane contracts, deleting `wireEvents()` or broadly retiring the compatibility shim would either:

1. break non-owned shared browser tests outside the T10 touch list, or
2. require expanding task ownership / contract migration before the cleanup can remain zero-drift.

That means the current workspace can be repaired safely, but the full T10 goal (`app.js` reduced to bootstrap-only responsibility with retired wrapper/global scaffolding removed) cannot be completed honestly under the present ownership constraints.

## Validation performed

### Required Tier D scope

The task packet requires this full scope:

```text
uv run pytest tests/browser/
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
uv run python scripts/audits/browser/run_browser_interaction_audit.py
```

That required Tier D scope was **not run** because the cleanup implementation is blocked after the bootstrap repair described above. Running the full Tier D suite would not change the ownership blocker and would not convert this run into a valid completed cleanup.

### Targeted recovery validation actually run

Command run:

```text
uv run pytest tests/browser/test_project_lifecycle_contracts.py::test_project_client_flushes_drafts_before_lifecycle_and_primary_import_paths tests/browser/test_settings_e2e.py::test_settings_section_toggles_survive_tool_route_changes -q
```

First targeted run result:

```text
1 failed, 1 passed
```

Observed failure:

```text
Page.evaluate: ReferenceError: activeTool is not defined
```

Root cause found during the follow-up Playwright smoke check:

```text
pageerror: Identifier '$' has already been declared
```

After removing the duplicate `$` declaration, the exact same targeted command was rerun unchanged and passed:

```text
2 passed in 20.76s
```

### Validation notes

- `get_errors` reported no problems in `src/splitshot/browser/static/app.js` after the repair patch.
- A direct Playwright smoke check against `BrowserControlServer` confirmed:
  - `activeTool` is readable from page scope again
  - `window.activeTool` is populated
  - `window.__splitshotBootstrapMode === "module"`
  - `window.__splitshotBackbone` exists again
- The targeted browser rerun demonstrates that the repaired `app.js` now evaluates and that the specific project/settings seams broken by the failed earlier edit are functioning again.

## Audit performed

### Audit checks executed

- Confirmed `src/splitshot/browser/static/app.js` now contains only one `function installLegacyGlobalCompat()` definition.
- Confirmed the accidental top-of-file duplicate compat installer and orphaned fragment were removed.
- Confirmed the current `app.js` size is still materially above the intended T10 endpoint and therefore should not be described as bootstrap-only.
- Confirmed the blocking shared browser-contract tests listed above still pin `app.js` wrappers / `wireEvents()` seams outside the current T10 touch list.

### Audit command run

```text
wc -l src/splitshot/browser/static/app.js
```

Result:

```text
11591 src/splitshot/browser/static/app.js
```

### Audit conclusion

- The workspace is recovered to a healthy modularized baseline.
- `app.js` is smaller than the last recorded T09E proof snapshot (`12,083` lines) but is still not narrow enough to claim the T10 cleanup goal is complete.
- The remaining cleanup work is blocked by still-live cross-lane source/runtime contracts, especially around `wireEvents()` and the broad legacy global bridge.

## Recommended next step

Before resuming T10 cleanup, expand or reconcile ownership for the shared browser-contract files that still pin `app.js` wrapper and event-wiring seams, then rerun T10 as an explicit contract-migration cleanup rather than a local-only shell shrink.

## Remaining risks

- Hidden tests may rely on the same broad page-global surface that visible browser tests still consume.
- The worktree still contains earlier modularization changes, so any future cleanup must remain surgical and avoid destructive restores.
- Full Tier D validation remains outstanding because this run is blocked rather than complete.

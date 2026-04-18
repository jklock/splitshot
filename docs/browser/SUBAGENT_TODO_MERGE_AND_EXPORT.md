# Subagent TODO: Merge and Export

This packet is one equal-priority branch of the left-pane remediation program defined in [LEFT_PANE_IMPLEMENTATION_SPEC.md](LEFT_PANE_IMPLEMENTATION_SPEC.md).

## Mission

Complete all remaining PiP and Export remediation items while preserving current merge layouts, export presets, and export output behavior.

## Owned Scope

Primary browser client ownership in `src/splitshot/browser/static/app.js`:

- `syncSecondaryPreview`
- `scheduleSecondaryPreviewSync`
- `renderMergePreviewLayer`
- `renderMergeMediaList`
- `scheduleMergeSourceCommit`
- `buildExportPayload`
- `scheduleExportLayoutApply`
- `scheduleExportSettingsApply`
- `renderExportLog`

Primary backend ownership:

- `src/splitshot/browser/server.py`
  Routes under `/api/merge*` and `/api/export*`
- `src/splitshot/ui/controller.py`
- `src/splitshot/export/pipeline.py`
- `src/splitshot/merge/layouts.py`

Preferred new test files:

- `tests/browser/test_merge_export_contracts.py`
- `tests/export/test_merge_export_contracts.py`

## Do Not Expand Into

- project lifecycle and project path behavior in the Project packet
- scoring or metrics summary logic in the Score and Metrics packet
- timing selection logic in the Splits packet
- overlay and review serializer behavior in the Overlay and Review packet

## TODO Checklist

- [ ] Lock live preview sync to persisted `sync_offset_ms` behavior.
- [ ] Guarantee drag interactions commit before autosave and export.
- [ ] Make non-PiP layout expectations explicit without changing existing layout behavior.
- [ ] Validate multi-source merge expectations beyond current source serialization.
- [ ] Lock export-path draft consistency.
- [ ] Clarify preset versus custom-mode behavior without changing current render settings.
- [ ] Prevent stale export-log state from looking like a current failure.

## Implementation Plan

### 1. Characterize preview, persistence, reopen, and export for merge offsets

- Add targeted browser and export tests for per-source `sync_offset_ms`, preview playback timing, reopened projects, and exported output.
- Ensure preview time math and export time math use the same stored source offsets.

### 2. Make drag-end commits deterministic

- Characterize PiP drag followed immediately by save, reopen, and export.
- Ensure drag end always commits through the same merge-source route path before autosave or export snapshot creation.

### 3. Document non-PiP preview limits without changing layout outputs

- Add tests that lock the current preview behavior for side-by-side and above-below.
- If copy clarification is needed, keep it descriptive and avoid changing layout results.

### 4. Expand multi-source coverage

- Add cases for source ordering, multiple offsets, and layout combinations.
- Keep current exported layout math stable.

### 5. Lock export-path draft state

- Characterize typed path, browsed path, preset change, save, reopen, and export.
- Ensure the field value, persisted export state, and final export target all stay aligned.

### 6. Clarify preset versus custom transitions

- Characterize how manual field edits move export state into custom mode today.
- Keep current preset ids and output values unchanged.
- Make the current mode boundary explicit in state handling.

### 7. Refresh export log state correctly

- Characterize the log modal after success, failure, close, reopen, and next export.
- Ensure stale failures do not present as current failures.
- Preserve the current modal and log download behavior.

## Risk Prevention

- Do not change current layout math unless characterization shows a real bug and the output today is already inconsistent.
- Do not rename export presets, export fields, or merge routes.
- Do not redesign the merge or export panes during remediation.
- Use bundled-media audits for any claim about preview/export parity.

## Validation

- `pytest tests/browser/test_merge_export_contracts.py`
- `pytest tests/export/test_merge_export_contracts.py`
- `pytest tests/scoring/test_scoring_and_merge.py -k merge`
- `python scripts/audits/browser/run_browser_interaction_audit.py --browser chromium --report-json logs/browser-interaction-audit-test-videos-merge-export.json`
- `python scripts/audits/browser/run_browser_export_matrix.py`

## Handoff Requirements

- List changed files.
- State whether any visible PiP or Export behavior changed. The expected answer is no.
- List tests run and results.
- Record any remaining merge hotspot in `app.js`, `browser/server.py`, or `export/pipeline.py`.
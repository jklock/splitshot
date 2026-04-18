# Subagent TODO: Project and Import

This packet is one equal-priority branch of the left-pane remediation program defined in [LEFT_PANE_IMPLEMENTATION_SPEC.md](LEFT_PANE_IMPLEMENTATION_SPEC.md).

## Mission

Complete all remaining Project-pane and import-lifecycle remediation items without changing the current user-visible workflow.

## Owned Scope

Primary browser client ownership in `src/splitshot/browser/static/app.js`:

- `applyProjectDetailsDraft`
- `readPractiScoreContextPayload`
- `flushPendingProjectDrafts`
- `flushPendingProjectDraftsKeepalive`
- `probeProjectFolder`
- `useProjectFolder`
- `autoApplyProjectDetails`
- `autoApplyPractiScoreContext`
- `scheduleProjectDetailsApply`
- `schedulePractiScoreContextApply`
- project-pane event listeners near the project and PractiScore controls

Primary backend ownership:

- `src/splitshot/browser/server.py`
  Routes under `/api/project/*`, `/api/files/practiscore`, `/api/import/primary`, `/api/dialog/path`
- `src/splitshot/ui/controller.py`
  Project details, project lifecycle, primary import, and PractiScore context handling
- `src/splitshot/persistence/projects.py`

Preferred new test files:

- `tests/browser/test_project_lifecycle_contracts.py`
- `tests/persistence/test_project_lifecycle_contracts.py`

## Do Not Expand Into

- scoring-summary logic in `src/splitshot/scoring/logic.py`
- timing-selection logic in the Splits packet
- merge/export preview logic in the Merge and Export packet
- overlay and review drag or serializer logic in the Overlay and Review packet

## TODO Checklist

- [ ] Freeze project detail draft and apply semantics across pane switches and save/open.
- [ ] Harden project-folder probe and chosen-path consistency.
- [ ] Lock PractiScore context reimport determinism.
- [ ] Contain primary-import side effects so unrelated pane state is not reset accidentally.
- [ ] Verify lifecycle restore behavior across new/open/save/delete flows.

## Implementation Plan

### 1. Characterize current Project detail draft behavior

- Add browser tests for typing project name and description, switching panes before debounce completes, saving, reopening, and browser refresh.
- Confirm that the current visible behavior is preserved: typed text remains visible, autosave still happens, and reopening shows the saved values.

### 2. Make draft flushing deterministic across lifecycle actions

- Ensure every project lifecycle action that can discard pending state explicitly flushes project drafts first.
- Confirm the same flush path is used by button flows and by any programmatic project open or save paths.
- Keep the current save/open/new/delete buttons and status copy unchanged.

### 3. Normalize project-folder probe and apply behavior

- Ensure `probeProjectFolder()` and `useProjectFolder()` use the same normalized path input.
- Prevent stale probe responses from driving a later open or create decision.
- Preserve the current distinction between an existing project folder and a new project folder.

### 4. Lock PractiScore reimport determinism

- Make the staged source file plus the current selected context the only inputs to reimport.
- Preserve current fallback behavior when the competitor place changes across files.
- Preserve current imported-summary auto-enable behavior only after a real PractiScore import.

### 5. Separate intended primary-import resets from accidental ones

- Keep analysis and media-bound state resets that are already intended.
- Preserve reusable settings that the current product already keeps across primary replacement.
- Ensure active tool, selection, waveform state, merge state, and export log state follow one deterministic rule set after primary replacement.

### 6. Verify lifecycle restore order

- Ensure new, open, save, and delete flows restore pane state in one consistent order.
- Preserve today’s landing pane behavior unless a separate product decision changes it.

## Risk Prevention

- Do not rename any Project pane ids, route names, or persisted project keys.
- Do not turn autosave into explicit-save-only behavior.
- Do not redesign the PractiScore import workflow.
- Do not change path chooser affordances or readonly path-field behavior.
- If you need to touch hot files outside the owned function family, stop and record the dependency instead of widening scope silently.

## Validation

- `pytest tests/browser/test_project_lifecycle_contracts.py`
- `pytest tests/persistence/test_project_lifecycle_contracts.py`
- `pytest tests/analysis/test_practiscore_import.py`
- `pytest tests/analysis/test_analysis.py -k "primary_replacement or practiscore or ingest_primary"`

## Handoff Requirements

- List changed files.
- State whether any existing user-visible Project or PractiScore behavior changed. The expected answer is no.
- List tests run and results.
- Call out any merge hotspot in `app.js`, `browser/server.py`, or `ui/controller.py`.
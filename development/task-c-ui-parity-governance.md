# Task C: UI Integration, Parity Testing, And Agent Governance

## Goal
Expose Connect/Sync in the Project pane, preserve manual fallback import behavior, and add governance docs and agent instructions to keep parity in future edits.

This task does not implement session internals or extraction internals.

## Owned Files (Exclusive)
### Source
1. `src/splitshot/browser/static/index.html`
2. `src/splitshot/browser/static/app.js`
3. `src/splitshot/browser/state.py`

### Tests
1. `tests/browser/test_browser_interactions.py`
2. `tests/browser/test_browser_control_coverage_matrix.py`

### Docs And Instructions
1. `docs/userfacing/panes/project.md`
2. `docs/project/browser-control-qa-matrix.md`
3. `.github/copilot-instructions.md` (new)
4. `.github/AGENTS.md` (new)
5. `.github/instructions/practiscore-sync.instructions.md` (new)

Do not edit files owned by Task A or Task B.

## Prerequisite Contracts
1. Task A provides stable session states.
2. Task B provides stable sync result payload keys.

## Step-by-Step Code Directions
1. Update `src/splitshot/browser/static/index.html` Project pane to include:
   - Connect PractiScore button,
   - Sync PractiScore button,
   - session/sync status display area.
2. Keep existing Select PractiScore File control in place as fallback.
3. Update `src/splitshot/browser/static/app.js`.
4. Add handler for Connect that calls Task A session start/status routes.
5. Add handler for Sync that calls Task B sync orchestration route.
6. Render clear status states:
   - connecting,
   - authenticated/ready,
   - syncing,
   - partial_failure,
   - success,
   - error.
7. Ensure no extra user fields are required beyond login/challenge.
8. Update `src/splitshot/browser/state.py` to surface payload fields required by Project-pane rendering.
9. Preserve existing fallback file import flow and option rendering.

## Step-by-Step Test Directions
1. Update `tests/browser/test_browser_interactions.py`.
2. Add UI flow test for connect then sync happy path.
3. Add UI flow test for sync error-state rendering.
4. Add UI flow test that fallback file import remains functional after adding new controls.
5. Update `tests/browser/test_browser_control_coverage_matrix.py` to include new Project/import controls and test ownership.
6. Run:
```bash
uv run pytest tests/browser/test_browser_interactions.py tests/browser/test_browser_control_coverage_matrix.py
```
7. Run PractiScore browser regressions:
```bash
uv run pytest tests/browser/test_browser_control.py -k practiscore
uv run pytest tests/browser/test_project_lifecycle_contracts.py -k practiscore
```

## Step-by-Step Documentation And Governance Directions
1. Update `docs/userfacing/panes/project.md` control table and how-to steps to include Connect + Sync + manual fallback.
2. Update `docs/project/browser-control-qa-matrix.md` Project/import row for new control coverage.
3. Create `.github/copilot-instructions.md` with mandatory parity rules:
   - update tests with workflow/state changes,
   - update docs with control/route changes,
   - keep manual fallback unless explicitly removed by product decision.
4. Create `.github/AGENTS.md` describing task boundaries and ownership model for PractiScore sync changes.
5. Create `.github/instructions/practiscore-sync.instructions.md` with file-pattern scoped guidance for source/tests/docs touched by this feature area.

## Human Verification Checklist
1. Project pane shows Connect and Sync controls.
2. Session and sync status are visible and understandable.
3. Manual file import still works.
4. Browser coverage matrix includes new controls and linked tests.
5. `.github` instruction files exist and codify parity expectations.

## Out Of Scope
1. Session module internals.
2. Extraction and normalization engine internals.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27

# Task C: UI Integration, Parity Testing, And Agent Governance

## Goal
Expose the Connect, remote-match selection, and selected-match import flow in the Project pane, preserve manual fallback import behavior, and add governance docs and agent instructions to keep parity in future edits.

This task does not implement session internals or extraction internals.

## Owned Files (Exclusive)
### Source
1. `src/splitshot/browser/static/index.html`
2. `src/splitshot/browser/static/app.js`
3. `src/splitshot/browser/static/styles.css`

### Tests
1. `tests/browser/test_browser_interactions.py`
2. `tests/browser/test_browser_static_ui.py`
3. `tests/browser/test_browser_control_inventory_audit.py`
4. `tests/browser/test_browser_control_coverage_matrix.py`

### Docs And Instructions
1. `docs/userfacing/panes/project.md`
2. `docs/project/browser-control-qa-matrix.md`
3. `.github/copilot-instructions.md` (new)
4. `.github/AGENTS.md` (new)
5. `.github/instructions/practiscore-sync.instructions.md` (new)

Do not edit files owned by Task A or Task B.

## Prerequisite Contracts
1. Task A provides the session, match-list, and selected-match import route surface.
2. Task B provides stable `/api/state` payloads:
   - `practiscore_session`
   - `practiscore_sync`
   - `practiscore_options`
3. Task B keeps `practiscore_options` as the local-stage source for `Match type`, `Stage #`, `Competitor name`, and `Place` after sync completes.

## Step-by-Step Code Directions
1. Update `src/splitshot/browser/static/index.html` Project pane PractiScore section to include:
   - `Connect PractiScore` button,
   - available remote match select control,
   - `Import Selected Match` button,
   - `Clear PractiScore Session` button,
   - persistent session/sync status area.
2. Keep the existing local PractiScore controls and `Select PractiScore File` button in place as the manual fallback path.
3. Update `src/splitshot/browser/static/app.js`.
4. Add a handler for `Connect PractiScore` that calls `POST /api/practiscore/session/start`.
5. Poll `GET /api/practiscore/session/status` only during the active connect flow.
6. When the session becomes `authenticated_ready`, request available remote matches through `GET /api/practiscore/matches`.
7. Populate the remote match select with the stable match objects from Task B.
8. Add a handler for `Import Selected Match` that calls `POST /api/practiscore/sync/start` with the selected `remote_id`.
9. Add a handler for `Clear PractiScore Session` that calls `POST /api/practiscore/session/clear`.
10. Render a stable UI state machine across the Project pane for:
   - `not_authenticated`
   - `authenticating`
   - `authenticated_ready`
   - `match_list_ready`
   - `importing_selected_match`
   - `success`
   - `expired`
   - `error`
11. Disable the remote-match import action until a session is ready and a remote match is selected.
12. After a successful selected-match import, continue rendering the existing local PractiScore controls from `practiscore_options`.
13. Preserve existing manual file import flow and existing competitor/place synchronization behavior.
14. Update `src/splitshot/browser/static/styles.css` with the status and layout styles needed for the new controls without disturbing the current Project-pane structure.

## Step-by-Step Test Directions
1. Update `tests/browser/test_browser_static_ui.py` for the new Project-pane control IDs and labels.
2. Update `tests/browser/test_browser_control_inventory_audit.py` for the new control IDs.
3. Update `tests/browser/test_browser_interactions.py`.
4. Add a UI flow test for connect, match-list load, remote-match selection, and selected-match import.
5. Add a UI flow test for expired-session or error-state rendering.
6. Add a UI flow test that manual `Select PractiScore File` import remains functional after the new controls are added.
7. Update `tests/browser/test_browser_control_coverage_matrix.py` to include the new Project/import controls and explicit test ownership.
8. Run:
```bash
uv run pytest tests/browser/test_browser_interactions.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py
```
9. Run PractiScore browser regressions:
```bash
uv run pytest tests/browser/test_browser_control.py -k practiscore
uv run pytest tests/browser/test_project_lifecycle_contracts.py -k practiscore
```

## Step-by-Step Documentation And Governance Directions
1. Update `docs/userfacing/panes/project.md` control table and how-to steps to include Connect, remote-match selection, selected-match import, clear-session behavior, and manual fallback.
2. Update `docs/project/browser-control-qa-matrix.md` Project/import row for the new controls and tests.
3. Create `.github/copilot-instructions.md` with mandatory parity rules:
   - update tests with workflow and state changes,
   - update docs with control and route changes,
   - keep manual fallback unless explicitly removed by product decision.
4. Create `.github/AGENTS.md` describing the task boundaries and ownership model for PractiScore sync changes.
5. Create `.github/instructions/practiscore-sync.instructions.md` with file-pattern scoped guidance for the source, tests, and docs touched by this feature area.

## Human Verification Checklist
1. Project pane shows Connect, remote-match selection, import, and clear-session controls.
2. Session and sync status are visible, stable, and understandable.
3. Manual file import still works.
4. Browser coverage docs include the new controls and linked tests.
5. `.github` instruction files exist and codify parity expectations.

## Out Of Scope
1. Session module internals.
2. Remote discovery, artifact download, and normalization engine internals.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27

# Task A: Authenticated Session Foundation

## Goal
Add the reusable PractiScore browser session foundation, visible manual login flow, deterministic browser profile storage, and the server route surface used by later discovery and import tasks.

This task does not implement remote match discovery, selected-match artifact download, normalization into scoring models, or Project-pane UI controls.

## Owned Files (Exclusive)
### Source
1. `src/splitshot/browser/server.py`
2. `src/splitshot/browser/practiscore_profile.py` (new)
3. `src/splitshot/browser/practiscore_session.py` (new)
4. `pyproject.toml`
5. `uv.lock` (generated companion when the Task A runtime dependency surface changes)

### Tests
1. `tests/browser/test_practiscore_session_api.py` (new)

### Docs
1. `docs/project/ARCHITECTURE.md`
2. `docs/project/DEVELOPING.md`

Do not edit files owned by Task B or Task C.

## Prerequisite Decisions This Task Must Respect
1. Authentication is manual and happens in a visible PractiScore browser window.
2. The SplitShot app manages a reusable browser profile and session state, but it does not collect credentials through app fields.
3. The session routes may exist before the remote discovery and import logic is implemented. They must fail safely with structured "not ready yet" errors when Task B hooks are absent.

## Step-by-Step Code Directions
1. Update `pyproject.toml` so the runtime browser automation dependency used by this feature is available outside the dev-only test extra.
2. Create `src/splitshot/browser/practiscore_profile.py`.
3. Add helpers that resolve deterministic app-data paths for the PractiScore browser profile.
4. Add explicit profile-clear helpers used only for session reset.
5. Create `src/splitshot/browser/practiscore_session.py`.
6. Add `PractiScoreSessionManager` with methods for:
   - `start_login_flow()`
   - `current_status()`
   - `clear_session()`
   - `serialize_status()`
   - `require_authenticated_browser()` or an equivalent accessor Task B can reuse
7. Launch the login flow in a visible browser context tied to the deterministic profile path.
8. Do not add username, password, or MFA input fields to SplitShot. The user completes login/challenge directly in the visible PractiScore browser session.
9. Ensure `serialize_status()` returns a stable payload with:
   - `state`
   - `message`
   - optional `details`
10. Support these stable states:
   - `not_authenticated`
   - `authenticating`
   - `authenticated_ready`
   - `challenge_required`
   - `expired`
   - `error`
11. In `src/splitshot/browser/server.py`, initialize one session manager at server startup and reuse it for the app lifetime.
12. Add `POST /api/practiscore/session/start`.
13. Add `GET /api/practiscore/session/status`.
14. Add `POST /api/practiscore/session/clear`.
15. Add `GET /api/practiscore/matches` as a route surface owned by Task A.
16. Add `POST /api/practiscore/sync/start` as a route surface owned by Task A.
17. For `GET /api/practiscore/matches` and `POST /api/practiscore/sync/start`, return structured JSON errors when the Task B controller hooks are not implemented yet. Do not leave a broken route path in the Task A branch.
18. Use the existing controller lock pattern in `server.py` for any mutation that touches shared state.
19. Keep existing manual PractiScore routes unchanged:
   - `/api/files/practiscore`
   - `/api/project/practiscore`
20. Preserve current `/api/state` behavior when no PractiScore session exists.

## Step-by-Step Test Directions
1. Create `tests/browser/test_practiscore_session_api.py`.
2. Add `test_practiscore_session_status_defaults_to_not_authenticated()`.
3. Add `test_practiscore_session_start_route_returns_status_payload()`.
4. Add `test_practiscore_session_clear_route_resets_state()`.
5. Add `test_practiscore_matches_route_returns_structured_unavailable_error_without_task_b_hook()`.
6. Add `test_practiscore_sync_route_returns_structured_unavailable_error_without_task_b_hook()`.
7. Add `test_practiscore_session_routes_return_structured_error_payload()`.
8. Mock the visible browser launch so the route tests stay deterministic and headless-safe in CI.
9. Run:
```bash
uv run pytest tests/browser/test_practiscore_session_api.py
```
10. Run PractiScore regression slices:
```bash
uv run pytest tests/browser/test_browser_control.py -k practiscore
uv run pytest tests/browser/test_project_lifecycle_contracts.py -k practiscore
```
11. Confirm no existing PractiScore browser tests regress.

## Step-by-Step Documentation Directions
1. Update `docs/project/ARCHITECTURE.md` Browser Surface section to include the new PractiScore session, match-list, and selected-match import routes.
2. Update `docs/project/DEVELOPING.md` with:
   - runtime dependency notes,
   - the session route test commands,
   - a manual smoke check for the visible login flow,
   - the rule that credentials are entered only in the external PractiScore browser surface.
3. Keep the two-line markdown footer format in both docs.

## Human Verification Checklist
1. Starting the login flow opens a visible PractiScore browser session.
2. Session status transitions are stable and documented.
3. Clearing the session removes the persisted login profile data expected by this feature.
4. The match-list and sync routes exist but fail safely before Task B is merged.
5. Existing manual PractiScore import behavior still works.

## Out Of Scope
1. Remote match discovery and filtering logic.
2. Downloading selected-match artifacts.
3. Import normalization into the scoring model.
4. Project-pane Connect, match selection, and import controls.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27

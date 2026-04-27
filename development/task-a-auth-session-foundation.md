# Task A: Authenticated Session Foundation

## Goal
Add a persistent authenticated PractiScore browser session surface and session API routes.

This task does not implement extraction logic, sync normalization, or Project-pane UI controls.

## Owned Files (Exclusive)
### Source
1. `src/splitshot/browser/server.py`
2. `src/splitshot/browser/practiscore_profile.py` (new)
3. `src/splitshot/browser/practiscore_session.py` (new)

### Tests
1. `tests/browser/test_practiscore_session_api.py` (new)

### Docs
1. `docs/project/ARCHITECTURE.md`
2. `docs/project/DEVELOPING.md`

Do not edit files owned by Task B or Task C.

## Step-by-Step Code Directions
1. Create `src/splitshot/browser/practiscore_profile.py`.
2. Add a profile factory for PractiScore session storage.
3. Configure deterministic profile directory under app data.
4. Configure persistent cookie/storage policy.
5. Add helper to clear profile storage for explicit session reset.
6. Create `src/splitshot/browser/practiscore_session.py`.
7. Add `PractiScoreSessionManager` with methods:
   - `start_login_flow()`
   - `current_status()`
   - `clear_session()`
   - `serialize_status()`
8. Ensure `serialize_status()` returns a stable payload with `state`, `message`, and optional `details`.
9. In `src/splitshot/browser/server.py`, initialize a session manager at server startup.
10. Add `POST /api/practiscore/session/start` route.
11. Add `GET /api/practiscore/session/status` route.
12. Add `POST /api/practiscore/session/clear` route.
13. Return structured JSON errors on recoverable failures.
14. Keep existing PractiScore routes unchanged:
   - `/api/files/practiscore`
   - `/api/project/practiscore`
15. Confirm browser state payload still works when no session exists.

## Step-by-Step Test Directions
1. Create `tests/browser/test_practiscore_session_api.py`.
2. Add `test_practiscore_session_status_defaults_to_not_authenticated()`.
3. Add `test_practiscore_session_start_route_returns_status_payload()`.
4. Add `test_practiscore_session_clear_route_resets_state()`.
5. Add `test_practiscore_session_routes_return_structured_error_payload()`.
6. Run:
```bash
uv run pytest tests/browser/test_practiscore_session_api.py
```
7. Run PractiScore regression slice:
```bash
uv run pytest tests/browser/test_browser_control.py -k practiscore
```
8. Confirm no existing PractiScore browser tests regress.

## Step-by-Step Documentation Directions
1. Update `docs/project/ARCHITECTURE.md` Browser Surface section to include the three new session routes.
2. Update `docs/project/DEVELOPING.md` with session route test commands and quick smoke-check steps.
3. Keep the two-line markdown footer format in both docs.

## Human Verification Checklist
1. Session start/status/clear routes exist and are reachable.
2. Payload states are stable and documented.
3. Existing manual PractiScore import tests continue to pass.
4. Architecture and developing docs reflect the route additions.

## Out Of Scope
1. Match extraction from authenticated pages.
2. Normalization into scoring models.
3. Project-pane Connect/Sync controls.

Last updated: 2026-04-27
Referenced files last updated: 2026-04-27

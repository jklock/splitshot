# Shared Backend Outcome Ledger

## Current status

- Lane: `Backend`
- Status: `done`
- Bundle owner: `GitHub Copilot`
- Last updated: `2026-05-26`
- Cross-lane status authority: `../../MASTER_STATUS.md`

## Execution reality

- Material execution in current pass: `yes`
- Current pass note: this lane was materially executed in Work Effort 1. The pass converted the backend docs from planning-only prose into an explicit route/state contract, validated the existing summary/persistence/import behavior, and fixed browser-visible recovery seams for Performance library stale/error states. Development wave 1 later added corroborating implementation evidence from `DEV-102`, `DEV-103`, and `DEV-104` plus an integration guardrail pack; `DEV-105` then closed the deferred `controller.landing_recent()` helper adoption and extracted the shared backend/PractiScore controller seams with additional guardrail and repo-lint evidence; `DEV-106` then tightened the landing recent backend contract so `/api/landing/recent` preserves stage/single rows before truncation and the landing widget no longer loses truthful recent stages behind newer match/library activity; the reopened DEV-301 close then added seam ID `DEV-106.landing_recent`, a dedicated recent-row interaction proof, and a fresh `691 passed` all-together rerun. That added evidence strengthens the implementation record but does not change the normalized lane status.
- Implementation and proof/signoff work completed `BEK-001` through `BEK-008`; the backend closeout now includes the final Work Effort 2 proof package, owner-suite anchors, residual-risk record, and approval.
- The earlier devil-review note to route `controller.landing_recent()` through the new persistence helpers has now closed inside the development shared-controller lane (`DEV-105`) without reopening backend scope.
- Approval record (`2026-05-26`): runtime health, the focused backend proof reruns, `artifacts/test-suite-backend-signoff.json`, and `artifacts/test-suite-backend-browser.json` all passed, and the source/aggregate/top-level ledgers were synchronized to the same backend truth.

## Deliverable status

- Route and state ownership inventory: complete
- Summary-state hardening: complete
- Status/error/activity normalization: complete
- Persistence and truth closure: complete
- Import and PractiScore protection: complete
- Match and Performance support closure: complete
- Docs sync and proof package: complete
- Approval: complete

## Test status

- Route registration / contract coverage: `50 passed in 232.11s (0:03:52)` across `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_rail_layout.py`, selected browser interactions, and `tests/browser/test_browser_control_inventory_audit.py`.
- Browser state serialization coverage: `134 passed` across `tests/browser/test_browser_control.py`, `tests/persistence/test_persistence.py`, `tests/persistence/test_workspace_persistence.py`, and `tests/browser/test_library_backend_contracts.py`.
- Persistence / reopen coverage: `2 passed` in targeted Match workspace-flow tests plus `18 passed` across the Match/Performance reopen and PractiScore browser pack.
- Import / PractiScore coverage: `18 passed` across `tests/browser/test_practiscore_session_api.py` and `tests/browser/test_practiscore_sync_controller.py`, plus `22 passed` across `tests/analysis/test_practiscore_import.py`, `tests/analysis/test_practiscore_sync_normalize.py`, and `tests/analysis/test_practiscore_web_extract.py`.
- Workspace backend coverage: covered by the `2 passed`, `18 passed`, and `134 passed` targeted packs used in this pass.
- Library backend coverage: covered by the `134 passed`, `13 passed`, and `50 passed` targeted packs used in this pass.
- Development wave 1 and DEV-105 integration evidence: focused `ruff` checks passed for `src/splitshot/browser/server.py`, `src/splitshot/browser/state.py`, `src/splitshot/persistence/library.py`, `src/splitshot/persistence/projects.py`, `src/splitshot/ui/controller.py`, and `src/splitshot/ui/services/**`; targeted pytest passed for `tests/browser/test_landing_backend_routes.py`, `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_control.py`, `tests/browser/test_library_backend_contracts.py`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`, and `tests/persistence`; the post-integration browser guardrail pack passed with `177 passed`, while the DEV-105 close pass added `77 passed` in `tests/browser/test_browser_interactions.py`, `108 passed` across the complementary frozen guardrail group, and a clean `uvx ruff check .`.
- Development DEV-106 landing recent evidence: `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py` -> `19 passed`; `./.venv/bin/python -m pytest tests/browser/test_browser_static_ui.py` -> `27 passed`; `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open` -> passed inside the reopened proof-close trio; `uvx ruff check src/splitshot/ui/services/shared_backend.py tests/browser/test_landing_backend_routes.py` -> all checks passed; and the fresh all-together suite rerun closed green with `691 passed`. This strengthens the landing route/static/interaction record without promoting the lane to final Work Effort 2 proof closure.
- Work Effort 2 backend final-gate evidence: `./.venv/bin/python -m pytest tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py tests/browser/test_browser_control.py` -> `114 passed in 60.80s (0:01:00)`; `./.venv/bin/python -m pytest tests/persistence/test_workspace_persistence.py tests/persistence/test_persistence.py tests/persistence/test_project_lifecycle_contracts.py` -> `38 passed in 1.14s`; `./.venv/bin/python -m pytest tests/browser/test_project_lifecycle_contracts.py tests/browser/test_library_backend_contracts.py` -> `22 passed in 8.47s`; `./.venv/bin/python -m pytest tests/analysis/test_practiscore_import.py tests/analysis/test_practiscore_sync_normalize.py tests/analysis/test_practiscore_web_extract.py` -> `22 passed in 1.08s`; `uv run splitshot --check` -> runtime health passed; `uv run python scripts/testing/run_test_suite.py --suite persistence --suite analysis --mode all-together --format table --json-output artifacts/test-suite-backend-signoff.json` wrote a green owner-suite artifact recording `125 passed in 11.29s`; and `uv run python scripts/testing/run_test_suite.py --suite browser --mode all-together --format table --json-output artifacts/test-suite-backend-browser.json` wrote a green browser owner-suite artifact recording `420 passed in 1672.03s`. This closes the backend proof package and final BEK gate.

## Required signoff checklist

- [x] Shared backend tests are green in the currently-owned implementation lanes.
- [x] `/api/state` summary contract is documented and proven.
- [x] Route ownership is documented and proven.
- [x] Persistence and reopen artifacts exist.
- [x] Import and PractiScore artifacts exist.
- [x] Stage, Match, and Performance bundles reference the same backend truth for Work Effort 1 handoff.
- [x] Residual risks are recorded.
- [x] Approval is recorded.

## Residual risks

- Risk: Some backend route ownership coverage remains contract-level or string-level rather than full deep-scenario proof for every route family.
  - Severity: medium
  - Owner: Shared backend accepted closeout
  - Mitigation / next action: Keep the route-family caveats explicit in the backend artifact ledger and reopen only if a later lane finds a first-order backend contract regression.

- Risk: Landing recent backend truth is now interaction-proven through seam ID `DEV-106.landing_recent`, but the backend lane still does not claim exhaustive deep-scenario proof for every route family in Work Effort 1.
  - Severity: low
  - Owner: Shared backend accepted closeout
  - Mitigation / next action: Keep the seam-specific proof record explicit instead of over-claiming exhaustive route-family coverage.

- Risk: Media GET endpoints and proxy/archive families remain less deeply exercised than the core workspace/library/PractiScore routes.
  - Severity: low
  - Owner: Shared backend accepted closeout
  - Mitigation / next action: Keep the dedicated backend proof package explicit about which route families received focused scenario validation versus broader owner-suite coverage.

## Waivers / deferrals

- None.

## Final outcome statement

Backend is `done`.

- Scope completed: `BEK-001` through `BEK-008`, including explicit route/state ownership, `/api/state` summary contract documentation, persistence/import/PractiScore validation, Match/Performance backend support closure, the accepted landing-recent backend truth refinement carried by `DEV-106`, final proof packaging, residual-risk closeout, and approval.
- Remaining scope: none inside the backend lane.
- Proof summary: the focused backend/state/persistence/library, workspace/reopen, PractiScore browser/session, PractiScore analysis, and `DEV-106.landing_recent` seam evidence all remained green; runtime health passed; the persistence+analysis owner-suite anchor recorded `125 passed`; and the browser owner-suite anchor recorded `420 passed`.
- Contract approval: recorded on `2026-05-26`.
- Merge readiness: backend proof/signoff is fully closed unless a later lane uncovers a new first-order backend blocker.

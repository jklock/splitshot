# Shared Backend Outcome Ledger

## Current status

- Lane: `Backend`
- Status: `implementation advanced / proof pending`
- Bundle owner: `GitHub Copilot`
- Last updated: `2026-05-26`
- Cross-lane status authority: `../../MASTER_STATUS.md`

## Execution reality

- Material execution in current pass: `yes`
- Current pass note: this lane was materially executed in Work Effort 1. The pass converted the backend docs from planning-only prose into an explicit route/state contract, validated the existing summary/persistence/import behavior, and fixed browser-visible recovery seams for Performance library stale/error states. Development wave 1 later added corroborating implementation evidence from `DEV-102`, `DEV-103`, and `DEV-104` plus an integration guardrail pack; `DEV-105` then closed the deferred `controller.landing_recent()` helper adoption and extracted the shared backend/PractiScore controller seams with additional guardrail and repo-lint evidence; `DEV-106` then tightened the landing recent backend contract so `/api/landing/recent` preserves stage/single rows before truncation and the landing widget no longer loses truthful recent stages behind newer match/library activity; the reopened DEV-301 close then added seam ID `DEV-106.landing_recent`, a dedicated recent-row interaction proof, and a fresh `691 passed` all-together rerun. That added evidence strengthens the implementation record but does not change the normalized lane status.
- Implementation work completed `BEK-001` through `BEK-006`; proof packaging and final signoff remain reserved for `BEK-007` and `BEK-008`.
- The earlier devil-review note to route `controller.landing_recent()` through the new persistence helpers has now closed inside the development shared-controller lane (`DEV-105`) without reopening backend scope.

## Deliverable status

- Route and state ownership inventory: complete
- Summary-state hardening: complete
- Status/error/activity normalization: complete
- Persistence and truth closure: complete
- Import and PractiScore protection: complete
- Match and Performance support closure: complete
- Docs sync and proof package: pending
- Approval: pending

## Test status

- Route registration / contract coverage: `50 passed in 232.11s (0:03:52)` across `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_rail_layout.py`, selected browser interactions, and `tests/browser/test_browser_control_inventory_audit.py`.
- Browser state serialization coverage: `134 passed` across `tests/browser/test_browser_control.py`, `tests/persistence/test_persistence.py`, `tests/persistence/test_workspace_persistence.py`, and `tests/browser/test_library_backend_contracts.py`.
- Persistence / reopen coverage: `2 passed` in targeted Match workspace-flow tests plus `18 passed` across the Match/Performance reopen and PractiScore browser pack.
- Import / PractiScore coverage: `18 passed` across `tests/browser/test_practiscore_session_api.py` and `tests/browser/test_practiscore_sync_controller.py`, plus `22 passed` across `tests/analysis/test_practiscore_import.py`, `tests/analysis/test_practiscore_sync_normalize.py`, and `tests/analysis/test_practiscore_web_extract.py`.
- Workspace backend coverage: covered by the `2 passed`, `18 passed`, and `134 passed` targeted packs used in this pass.
- Library backend coverage: covered by the `134 passed`, `13 passed`, and `50 passed` targeted packs used in this pass.
- Development wave 1 and DEV-105 integration evidence: focused `ruff` checks passed for `src/splitshot/browser/server.py`, `src/splitshot/browser/state.py`, `src/splitshot/persistence/library.py`, `src/splitshot/persistence/projects.py`, `src/splitshot/ui/controller.py`, and `src/splitshot/ui/services/**`; targeted pytest passed for `tests/browser/test_landing_backend_routes.py`, `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_control.py`, `tests/browser/test_library_backend_contracts.py`, `tests/browser/test_practiscore_session_api.py`, `tests/browser/test_practiscore_sync_controller.py`, and `tests/persistence`; the post-integration browser guardrail pack passed with `177 passed`, while the DEV-105 close pass added `77 passed` in `tests/browser/test_browser_interactions.py`, `108 passed` across the complementary frozen guardrail group, and a clean `uvx ruff check .`.
- Development DEV-106 landing recent evidence: `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py` -> `19 passed`; `./.venv/bin/python -m pytest tests/browser/test_browser_static_ui.py` -> `27 passed`; `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open` -> passed inside the reopened proof-close trio; `uvx ruff check src/splitshot/ui/services/shared_backend.py tests/browser/test_landing_backend_routes.py` -> all checks passed; and the fresh all-together suite rerun closed green with `691 passed`. This strengthens the landing route/static/interaction record without promoting the lane to final Work Effort 2 proof closure.

## Required signoff checklist

- [x] Shared backend tests are green in the currently-owned implementation lanes.
- [x] `/api/state` summary contract is documented and proven.
- [x] Route ownership is documented and proven.
- [x] Persistence and reopen artifacts exist.
- [x] Import and PractiScore artifacts exist.
- [x] Stage, Match, and Performance bundles reference the same backend truth for Work Effort 1 handoff.
- [x] Residual risks are recorded.
- [ ] Approval is recorded.

## Residual risks

- Risk: Some backend route ownership coverage remains contract-level or string-level rather than full deep-scenario proof for every route family.
  - Severity: medium
  - Owner: Work Effort 2 / `testing/`
  - Mitigation / next action: Finish `BEK-007` proof packaging with focused route/state artifact links and the final cross-bundle proof gate.

- Risk: Landing recent backend truth is now interaction-proven through seam ID `DEV-106.landing_recent`, but the backend lane still does not claim exhaustive deep-scenario proof for every route family in Work Effort 1.
  - Severity: low
  - Owner: Work Effort 2 / `testing/`
  - Mitigation / next action: Keep the seam-specific proof record explicit in the final backend proof package instead of over-claiming full-route signoff.

- Risk: Media GET endpoints and proxy/archive families remain less deeply exercised than the core workspace/library/PractiScore routes.
  - Severity: low
  - Owner: Work Effort 2 / `testing/`
  - Mitigation / next action: Keep the dedicated backend proof package explicit about which route families received focused scenario validation in Work Effort 1 versus final proof packaging in Work Effort 2.

## Waivers / deferrals

- Item: Final backend proof package, residual-risk closeout, and approval remain deferred to `BEK-007` and `BEK-008`.
  - Reason: Work Effort 1 owns implementation truth and targeted validation, not the final proof/signoff package.
  - Expiry / revisit point: Work Effort 2 / `testing/`
  - Approved by: aggregate development handoff

## Final outcome statement

Backend is `implementation advanced / proof pending` for Work Effort 1.

- Scope completed: `BEK-001` through `BEK-006`, including explicit route/state ownership, `/api/state` summary contract documentation, persistence/import/PractiScore validation, Match/Performance backend support closure, and the accepted landing-recent backend truth refinement carried by `DEV-106`.
- Remaining excluded scope: `BEK-007` and `BEK-008`, including final proof packaging, residual-risk closeout, and approval.
- Proof summary: targeted backend/state/persistence/library, workspace/reopen, PractiScore browser/session, PractiScore analysis, and the `DEV-106.landing_recent` route/static/interaction seam evidence all passed in this pass; final backend proof packaging and signoff remain reserved for Work Effort 2.
- Contract approval: pending Work Effort 2 proof/signoff.
- Merge readiness: backend implementation can hand off to `testing/` without reopening a backend development slice unless a new first-order backend blocker is discovered.

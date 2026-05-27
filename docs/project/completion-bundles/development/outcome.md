# Development Outcome Ledger

## Current status

- Bundle: `development`
- Status: `DEV-001 through DEV-301 complete`
- Bundle owner: `GitHub Copilot`
- Last updated: `2026-05-26`
- Bundle execution authority: `progress.md`, `tasks.md`, and this file
- Cross-bundle reference: `../MASTER_STATUS.md` synchronized in this closeout pass

## What changed in this reset

- Replaced the old historical Work Effort framing with an active builder-agent execution bundle.
- Added `progress.md` for shared execution state and `proof.md` for meaningful proof rules.
- Codified Stage and Match as frozen behavior baselines.
- Reset `tasks.md` to active, zero-overlap implementation lanes instead of retrospective closure notes.
- Updated the orchestration prompt to enforce research, build, devil’s-advocate, validation, and integrator passes.

## Execution reality

- Stage is treated as a frozen baseline. This bundle preserves it; it does not redesign it.
- Match is treated as a frozen baseline. This bundle preserves it; it does not redesign it.
- Performance Library remains part of the app model, but product expansion is deferred.
- Wave 1 implementation landed `DEV-101` through `DEV-104`: API runtime boundary tightening, server route-dispatch modularization, explicit `/api/state` summary slices, and persistence-helper support for landing/shared backend work.
- The integrated wave is valid within the current allowlists based on the targeted task validations, the post-integration browser guardrail pack (`177 passed`), and focused persistence lint.
- `DEV-105` has now landed the shared controller/service extraction: landing/proxy/backup support delegates through `ui/services/shared_backend.py`, PractiScore session/sync support delegates through `ui/services/practiscore_sync.py`, and the deferred `controller.landing_recent()` helper adoption is complete.
- Closing `DEV-105` also required a test-only guardrail stabilization in `tests/browser/test_browser_interactions.py` so long overlay rerenders wait for a non-zero timer-badge box before asserting size; no production route or UI behavior changed.
- `DEV-106` has now landed the Landing UI backend adoption: landing recents are fetched from `/api/landing/recent`, only stage/single entries remain authoritative for the `Recent Stages` widget, and the backend now preserves those stage rows before truncation so newer match/library activity cannot crowd them out.
- `DEV-107` has now landed the root-shell registration and fallback cleanup: shell globals are exposed through the compat seam instead of duplicate tail-end assignments, `selectedLibraryRecord` remains available through compat mutable bindings, and the risky Stage/Match routing helpers stayed untouched.
- `DEV-201` has now landed the frozen-baseline proof audit: the QA matrix, coverage plans, and Stage/Match references now distinguish browser coverage ownership from meaningful proof closure, and the current landing/shell caveats are explicit instead of implied.
- `DEV-301` has now closed honestly: the reopened proof work added the dedicated DEV-106 recent-row interaction proof, broader DEV-107 compat-consumer proof, a machine-readable seam registry plus audit coverage, and a fresh all-together full-suite rerun before republishing the Work Effort 1 handoff.

## Deliverable status

- Document-set rebuild: complete
- Frozen-baseline contract: complete
- `DEV-001` freeze contract and execution preflight: complete
- Parallel task structure: complete
- Shared progress ledger: complete
- Proof taxonomy and update obligations: complete
- `DEV-101` API runtime boundary lane: complete
- `DEV-102` server route-dispatch modularization lane: complete
- `DEV-103` `/api/state` summary-contract lane: complete
- `DEV-104` persistence-support lane: complete
- Wave 1 integrated validation: complete
- `DEV-105` shared controller/service lane: complete
- `DEV-106` landing UI backend-adoption lane: complete
- `DEV-107` root-shell registration and fallback-cleanup lane: complete
- `DEV-201` frozen-baseline proof-audit lane: complete
- `DEV-301` integrator review, devil’s advocate, and handoff lane: complete

## Validation recorded

- `DEV-101`: `./.venv/bin/python -m pytest tests/browser/test_browser_control.py tests/browser/test_automation_ui_shell_contracts.py` -> exit 0
- `DEV-102`: `uvx ruff check src/splitshot/browser/server.py tests/browser/test_landing_backend_routes.py tests/browser/test_automation_ui_shell_contracts.py` -> exit 0; `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_automation_ui_shell_contracts.py` -> exit 0
- `DEV-103`: `uvx ruff check src/splitshot/browser/state.py tests/browser/test_library_backend_contracts.py` -> exit 0; `./.venv/bin/python -m pytest tests/browser/test_browser_control.py tests/browser/test_library_backend_contracts.py` -> exit 0
- `DEV-104`: `./.venv/bin/python -m pytest tests/persistence` -> exit 0
- Post-integration guardrail pack: `./.venv/bin/python -m pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py tests/browser/test_workspace_export_and_recap.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py` -> `177 passed`
- Additional focused lint after integration: `uvx ruff check src/splitshot/persistence/library.py src/splitshot/persistence/projects.py tests/persistence` -> all checks passed
- `DEV-105`: `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py tests/browser/test_library_backend_contracts.py` -> `48 passed`
- `DEV-105` frozen guardrail follow-up: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py` -> `77 passed`; `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_workspace_flows.py tests/browser/test_workspace_export_and_recap.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py` -> `108 passed`
- Repo-wide lint gate for `DEV-105`: `uvx ruff check .` -> all checks passed
- `DEV-106`: `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py` -> `19 passed`; `./.venv/bin/python -m pytest tests/browser/test_browser_static_ui.py` -> `27 passed`; `uvx ruff check src/splitshot/ui/services/shared_backend.py tests/browser/test_landing_backend_routes.py` -> all checks passed
- `DEV-107`: `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py` -> `164 passed`; `uvx ruff check tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py` -> all checks passed
- `DEV-201`: `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py` -> `5 passed`; `uvx ruff check tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py` -> all checks passed
- `DEV-301` reopened proof closure: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py::test_shell_compat_host_on_open_project_callback_opens_saved_project tests/browser/test_browser_interactions.py::test_performance_library_compat_selected_record_and_render_rerender_detail_truth tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open` -> `3 passed`
- `DEV-301` broader DEV-106/DEV-107 pack: `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_browser_static_ui.py tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py` -> `186 passed`
- `DEV-301` closeout anchors: `./.venv/bin/splitshot --check` -> runtime health passed; `./.venv/bin/python scripts/testing/run_test_suite.py --mode all-together --format raw --raw-output artifacts/all-together-raw.txt --json-output artifacts/all-together.json --pytest-arg=-x` -> `691 passed in 1821.89s (0:30:21)`

## Review results from this planning pass

The following external review passes informed this reset:

1. **Document-set redesign research**
   - identified missing `progress.md` and `proof.md`
   - identified that the prior `tasks.md` was too historical-heavy for deterministic builder execution
   - recommended explicit frozen-baseline posture and an active-only backlog

2. **Parallel workstream audit**
   - identified the safest non-overlapping file surfaces for route, state, persistence, controller, landing, and shell-cleanup work
   - confirmed `app.js`, `server.py`, `state.py`, and `controller.py` require strict serialization rules where files overlap
   - provided the strongest Stage/Match freeze rules for task enforcement

3. **Proof-strategy audit**
   - designed the proof taxonomy now captured in `proof.md`
   - confirmed that meaningful controls must map to persisted truth or output artifacts
   - identified current QA matrix and inventory audits as necessary but not sufficient proof depth by themselves

## Current risks

- The legacy `splitshot.recentActivity` breadcrumb writer remains in `app.js` as non-authoritative compatibility state; it is a low-risk cleanup candidate, not a blocker for Work Effort 1 handoff.
- Minor root-shell compatibility leftovers still exist (`workspaceShell(...)` fallback selectors and the non-authoritative `splitshot.recentActivity` breadcrumb), but they are low-risk cleanup candidates rather than blockers after `DEV-107`.
- The proof docs are now seam-registry-backed, but the reference maps remain partly manual and the QA/inventory tests are still document-contract audits rather than exhaustive semantic proofs; drift is reduced, not eliminated.

## Required checklist for this reset

- [x] `spec.md`, `plan.md`, `tasks.md`, `progress.md`, `proof.md`, `outcome.md`, and `orchestration.prompt.md` now form one coherent set.
- [x] Stage and Match freeze rules are explicit.
- [x] `DEV-001` recorded the freeze contract and execution preflight against the live bundle docs and frozen references.
- [x] The first dependency window is released without widening scope beyond the documented allowlists.
- [x] Parallel tasks have distinct file ownership.
- [x] Shared progress communication is defined.
- [x] Proof expectations are explicit and stronger than “a button exists.”
- [x] Review-agent, devil’s-advocate, and validation roles are part of the execution model.

## Remaining work after Work Effort 1 handoff

- `testing/` now owns the remaining Performance proof/signoff package, Backend and Modularization final proof packages, the source `predev/tests/` execution bundle, screenshots/artifacts/docs sync, and the final acceptance gates.
- `predev/backend/` and `predev/modularization/` remain `implementation advanced / proof pending`; that is final proof/signoff scope reserved for Work Effort 2, not an open DEV-301 blocker.
- Future implementation regressions discovered during Work Effort 2 must reopen the relevant source lane explicitly rather than being hidden inside acceptance-language edits.

## Waivers / deferrals

- No new Stage or Match feature work is authorized inside this bundle.
- Performance Library product expansion is intentionally deferred while shared foundation work is finished first.
- `artifacts.md` is retained only as a compatibility pointer and is no longer the primary execution ledger.

## Final outcome statement

The `development/` bundle has **completed `DEV-001` through `DEV-301`**.

Stage and Match remain explicitly frozen, the bundle docs are synchronized, the DEV-106/DEV-107 seam proofs now include the missing interaction and compat-consumer coverage, and the fresh runtime plus all-together anchors are green. Work Effort 1 can now hand off honestly to `testing/`; any later implementation issue must reopen explicitly instead of living on as a caveat.

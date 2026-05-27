# Development Progress Ledger

## Purpose

This file is the shared execution and communication ledger for the active `development/` bundle.

Use it to track which task is active, what finished, what is blocked, and what the integrator must merge next.

## Editing rule

- **Only the current integrator task may edit this file.**
- Worker agents report results in their handoff packet; they do **not** edit `progress.md` directly.
- This rule prevents parallel branches from colliding in the same file.

## Current bundle status

- Bundle: `development`
- Status: `execution-complete / DEV-301 closed / Work Effort 1 handed off`
- Last updated: `2026-05-26`
- Current wave: `wave 4 closed; DEV-301 complete`
- Released now: Work Effort 1 handoff from `development/`
- Next release after current wave: Work Effort 2 / `testing/`
- Bundle execution authority: `progress.md`, `tasks.md`, and `outcome.md`
- Cross-bundle reference: `../MASTER_STATUS.md` synchronized in this closeout pass
- Integrator owner: `GitHub Copilot`

## Task board

| Task | State | Owner type | Depends on | Last note |
| --- | --- | --- | --- | --- |
| `DEV-001` | `complete` | integrator | — | Freeze contract and execution preflight recorded; Stage and Match remain explicitly frozen. |
| `DEV-101` | `complete` | worker | `DEV-001` | API runtime boundary landed; targeted browser-control and shell-contract validation passed. |
| `DEV-102` | `complete` | worker | `DEV-001` | Route-dispatch modularization landed; focused lint plus landing-route/browser contract validation passed. |
| `DEV-103` | `complete` | worker | `DEV-001` | `/api/state` summary slices landed; focused lint plus browser-control/library-contract validation passed. |
| `DEV-104` | `complete` | integrator | `DEV-001` | Persistence helpers landed; targeted persistence pytest plus focused lint passed. |
| `DEV-105` | `complete` | worker | `DEV-102`, `DEV-103`, `DEV-104` | Shared controller/service extraction landed; lane-local validation, frozen guardrails, and repo-wide lint all closed green. |
| `DEV-106` | `complete` | worker | `DEV-101`, `DEV-102`, `DEV-103`, `DEV-105` | Closed; landing recents are backend-driven, backend stage rows are preserved before truncation, and the landing static/backend contract pack passed. |
| `DEV-107` | `complete` | worker | `DEV-101`, `DEV-105`, `DEV-106` | Closed; root-shell global exposure now runs through the compat seam, library fallback mirroring is slimmer, and the owned shell/static/interaction/workspace guardrail pack reran green. |
| `DEV-201` | `complete` | integrator | `DEV-106`, `DEV-107` | Closed; proof taxonomy, QA matrix, coverage-plan honesty language, and reference caveats now align with the landing and shell seams that actually shipped. |
| `DEV-301` | `complete` | integrator | `DEV-201` and all prior active lanes | Closed honestly; the reopened DEV-106/DEV-107 proof gaps are now covered by dedicated interaction/compat tests, seam-registry-backed audits, a green runtime-health check, and a fresh `691 passed` all-together anchor. |

## Decision log

- `2026-05-26` — Stage and Match are treated as **frozen behavior baselines** for this bundle. They may be reopened only through the explicit reopen protocol in `spec.md`.
- `2026-05-26` — User-facing naming stays **Performance Library**. Internal `library` naming may remain in code and storage until a later dedicated rename pass.
- `2026-05-26` — `progress.md`, `proof.md`, and `outcome.md` are integrator-owned files. Worker tasks must not edit them directly.
- `2026-05-26` — The active plan now optimizes for **parallel, non-overlapping builder execution**, not historical Work Effort 1 narration.
- `2026-05-26` — Meaningful controls must either mutate persisted truth or appear in output/video/artifacts to count as proof-worthy closure.
- `2026-05-26` — The devil-review note to route `controller.landing_recent()` through the new persistence helpers is scoped to `DEV-105`; it does not reopen or block wave 1.
- `2026-05-26` — `DEV-106` was widened minimally to include landing recent payload shaping in `src/splitshot/ui/services/shared_backend.py` after post-build review found that mixed-feed truncation could crowd stage rows out before the landing UI filter ran.
- `2026-05-26` — `DEV-301` closeout keeps the `DEV-106` landing proof-depth caveat and the `DEV-107` compat proof-depth caveat explicit; source-lane sync does not promote either lane to final proof/signoff.
- `2026-05-26` — The first DEV-301 closeout was premature: remaining proof gaps must be eliminated, not merely narrated, before Work Effort 1 can publish its handoff.

## Execution log

- `2026-05-26` — Reviewed the existing `development/` bundle, `stage-reference.md`, `match-reference.md`, and the relevant predev backend/modularization lanes.
- `2026-05-26` — Ran focused research passes for doc-structure redesign, safe parallel workstream boundaries, and proof taxonomy design.
- `2026-05-26` — Reset the `development/` bundle into an execution-ready document set with `spec.md`, `plan.md`, `tasks.md`, `progress.md`, `proof.md`, `outcome.md`, and an updated orchestration prompt.
- `2026-05-26` — Completed `DEV-001` as a docs-only integrator pass: re-read `spec.md`, `plan.md`, `tasks.md`, `progress.md`, `proof.md`, `outcome.md`, `stage-reference.md`, and `match-reference.md`; confirmed the freeze contract and worker/integrator split are live; confirmed the task-state matrix; and released dependency window 1 (`DEV-101`, `DEV-102`, `DEV-103`, `DEV-104`). No code validation was run or claimed for this task.
- `2026-05-26` — Accepted `DEV-101` wave-1 close: `./.venv/bin/python -m pytest tests/browser/test_browser_control.py tests/browser/test_automation_ui_shell_contracts.py` -> exit 0.
- `2026-05-26` — Accepted `DEV-102` wave-1 close: `uvx ruff check src/splitshot/browser/server.py tests/browser/test_landing_backend_routes.py tests/browser/test_automation_ui_shell_contracts.py` -> exit 0; `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_automation_ui_shell_contracts.py` -> exit 0.
- `2026-05-26` — Accepted `DEV-103` wave-1 close: `uvx ruff check src/splitshot/browser/state.py tests/browser/test_library_backend_contracts.py` -> exit 0; `./.venv/bin/python -m pytest tests/browser/test_browser_control.py tests/browser/test_library_backend_contracts.py` -> exit 0.
- `2026-05-26` — Accepted `DEV-104` wave-1 close: `./.venv/bin/python -m pytest tests/persistence` -> exit 0; `uvx ruff check src/splitshot/persistence/library.py src/splitshot/persistence/projects.py tests/persistence` -> exit 0.
- `2026-05-26` — Closed integrated wave 1 within the current allowlists: `./.venv/bin/python -m pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py tests/browser/test_workspace_export_and_recap.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py` -> `177 passed`; released `DEV-105` and kept `DEV-106` blocked on it.
- `2026-05-26` — Accepted `DEV-105` lane-local close: `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py tests/browser/test_library_backend_contracts.py` -> `48 passed`; `uvx ruff check src/splitshot/ui/controller.py src/splitshot/ui/services tests/browser/test_landing_backend_routes.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py tests/browser/test_library_backend_contracts.py` -> exit 0.
- `2026-05-26` — Stabilized the overlay-font guardrail assertion in `tests/browser/test_browser_interactions.py` by waiting for a non-zero timer-badge box after overlay font rerenders; no production behavior changed.
- `2026-05-26` — Accepted post-DEV-105 frozen guardrail validation: `./.venv/bin/python -m pytest tests/browser/test_browser_interactions.py` -> `77 passed`; `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_workspace_flows.py tests/browser/test_workspace_export_and_recap.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py` -> `108 passed`; `uvx ruff check .` -> all checks passed.
- `2026-05-26` — Closed `DEV-105`, released `DEV-106`, and kept `DEV-107` dependency-blocked on the landing UI backend-adoption lane.
- `2026-05-26` — Post-build devil/validation review of `DEV-106` found a real blocker: `app.js` now filters `/api/landing/recent` to stage rows, but `shared_backend.landing_recent()` still sorts and truncates a mixed recent feed before that filter runs, so newer match/library activity can crowd stage rows out and falsely trigger the landing empty state. `DEV-106` remains active until that backend payload contract is fixed and revalidated.
- `2026-05-26` — Closed `DEV-106`: updated `shared_backend.landing_recent()` so stage/single recents are preserved before sort/truncate, added the mixed-feed crowd-out regression in `tests/browser/test_landing_backend_routes.py`, and revalidated with `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py` -> `19 passed`; `./.venv/bin/python -m pytest tests/browser/test_browser_static_ui.py` -> `27 passed`; `uvx ruff check src/splitshot/ui/services/shared_backend.py tests/browser/test_landing_backend_routes.py` -> all checks passed. Released `DEV-107` after close.
- `2026-05-26` — Closed `DEV-107`: trimmed duplicate root-shell global exposure by routing `setActiveSurface` and `renderAutomationSurface` through `installLegacyGlobalCompat(...)`, kept observable Stage/Match shell contracts alias-only, retained `selectedLibraryRecord` through compat mutable bindings, and revalidated with `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py` -> `164 passed`; `uvx ruff check tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py` -> all checks passed. Activated `DEV-201` after close.
- `2026-05-26` — Closed `DEV-201`: tightened the proof taxonomy language for DEV-106/DEV-107, added Stage/Match family proof-taxonomy summaries and honesty caveats, clarified that coverage ownership/inventory status is not a proof class, and revalidated with `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py` -> `4 passed`; `uvx ruff check tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py` -> all checks passed. Activated `DEV-301` after close.
- `2026-05-26` — Ran the `DEV-301` review/build/devil closeout passes: aggregate `development/` ledgers were internally aligned, the only remaining drift was accepted `DEV-106` evidence missing from `predev/backend/{outcome,artifacts}.md` and accepted `DEV-107` evidence missing from `predev/modularization/{outcome,artifacts}.md`, and no new implementation work or task-state changes were required in those source lanes.
- `2026-05-26` — Synchronized `predev/backend/*` and `predev/modularization/*` outcome/artifact ledgers with the accepted `DEV-106` and `DEV-107` evidence while explicitly keeping both source lanes at `implementation advanced / proof pending`; recorded the `DEV-301` handoff evidence in `development/proof.md`.
- `2026-05-26` — Closed `DEV-301`: `./.venv/bin/splitshot --check` passed the runtime health gate; `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py` -> `4 passed`; published the Work Effort 1 handoff to `testing/` with the landing recent and compat-shell proof-depth caveats preserved.
- `2026-05-26` — Reopened `DEV-301` after user review rejected the proof-depth caveats as unfinished work. Remaining closure work now includes a dedicated DEV-106 landing recent-row interaction proof, broader DEV-107 compat-consumer proof, a less-manual seam/audit anchor, and the missing full-suite all-together rerun.
- `2026-05-26` — Added the missing reopened-proof evidence: `tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open`, `::test_shell_compat_host_on_open_project_callback_opens_saved_project`, and `::test_performance_library_compat_selected_record_and_render_rerender_detail_truth` passed; `docs/project/browser-proof-seams.json` now anchors the DEV-106/DEV-107 seam records; and the browser QA/inventory audits were rewired to validate those seam IDs directly.
- `2026-05-26` — Revalidated the reopened proof-close pack: `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py` -> `5 passed`; `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_browser_static_ui.py tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py` -> `186 passed`; `./.venv/bin/splitshot --check` -> passed.
- `2026-05-26` — Re-closed `DEV-301`: fixed the reopened full-suite blocker in the compat Performance Library proof, then reran `./.venv/bin/python scripts/testing/run_test_suite.py --mode all-together --format raw --raw-output artifacts/all-together-raw.txt --json-output artifacts/all-together.json --pytest-arg=-x` -> `691 passed in 1821.89s (0:30:21)`; republished the Work Effort 1 handoff to `testing/`.

## Blockers

- None at the document-set level.
- Work Effort 1 handoff is now republished and complete for `development/`; later implementation changes should reopen explicitly instead of being hidden in proof wording.

## Worker handoff packet format

Every worker task must return the following to the integrator:

1. Task ID
2. Files changed
3. Commands run + exit codes
4. Guardrail tests run + exit codes
5. Reopen triggered: `yes` / `no`
6. Required doc/proof updates for the integrator
7. Residual risks or follow-up notes

## Next integrator action

- Hand control to Work Effort 2 / `testing/` for the remaining proof/signoff package.
- Reopen `development/` only if `testing/` finds a first-order implementation blocker rather than a documentation or acceptance-packaging gap.

# Development Task Backlog

## Usage

- This file is the active execution backlog for builder agents.
- Treat every task as **not started** until the integrator records otherwise in `progress.md` and `outcome.md`.
- Follow the task allowlist exactly. Do not widen scope on your own.
- If a task would touch the same file as another active task, stop and ask the integrator to serialize or retag the work.

## Global execution rules

0. Read this file end to end before starting any task.
1. Read `spec.md`, `plan.md`, `progress.md`, `proof.md`, and `outcome.md` before starting.
2. Read `stage-reference.md` and `match-reference.md` before touching any shared shell, route, or state seam.
3. Workers edit only their allowed implementation files and task-local tests.
4. Workers do **not** edit `progress.md`, `proof.md`, `outcome.md`, or shared source-lane ledgers.
5. Only the integrator task may merge shared ledger updates after a wave closes.
6. If a frozen-baseline reopen trigger fires, stop immediately and route it through the reopen protocol.

Per-task `Read first` sections supplement these global rules; they do not replace them.

## Command policy

- For this bundle, this command policy overrides repo-level example commands for routine execution and verification.
- Use the repo `.venv` executables for routine commands; do not use `uv run` as a harmless launcher.
- Environment repair only when actually blocked: `uv sync --extra dev`
- Runtime health: `./.venv/bin/splitshot --check`
- Targeted tests: `./.venv/bin/python -m pytest ...`
- Python lint after Python changes: `uvx ruff check .`
- Final full-suite anchor for the integrator only: `./.venv/bin/python scripts/testing/run_test_suite.py --mode all-together --format table`

## Frozen-baseline guardrail pack

Before merging any task that touched shared shell, state, server, or controller seams, keep the following guardrails green unless the task itself is a named reopen:

- `tests/browser/test_automation_ui_shell_contracts.py`
- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_interactions.py`
- `tests/browser/test_workspace_flows.py`
- `tests/browser/test_workspace_export_and_recap.py`
- `tests/browser/test_practiscore_session_api.py`
- `tests/browser/test_practiscore_sync_controller.py`

## Task state matrix

| Task | State | Depends on |
| --- | --- | --- |
| `DEV-001` | `complete` | — |
| `DEV-101` | `complete` | `DEV-001` |
| `DEV-102` | `complete` | `DEV-001` |
| `DEV-103` | `complete` | `DEV-001` |
| `DEV-104` | `complete` | `DEV-001` |
| `DEV-105` | `complete` | `DEV-102`, `DEV-103`, `DEV-104` |
| `DEV-106` | `complete` | `DEV-101`, `DEV-102`, `DEV-103`, `DEV-105` |
| `DEV-107` | `complete` | `DEV-101`, `DEV-105`, `DEV-106` |
| `DEV-201` | `complete` | `DEV-106`, `DEV-107` |
| `DEV-301` | `complete` | `DEV-201` and all prior worker lanes |

## DEV-001 — Freeze contract and execution preflight

Owner type:

- integrator only

Depends on:

- none

Can run in parallel with:

- none

Read first:

- `spec.md`
- `plan.md`
- `progress.md`
- `proof.md`
- `outcome.md`
- `stage-reference.md`
- `match-reference.md`

Allowed edit surface:

- `spec.md`
- `plan.md`
- `tasks.md`
- `progress.md`
- `proof.md`
- `outcome.md`
- `orchestration.prompt.md`
- `artifacts.md`

Forbidden edit surface:

- `src/**`
- `tests/**`
- `../predev/**`

Deliverables:

- freeze rules confirmed live
- task-state matrix confirmed accurate
- first parallel wave released in `progress.md`

Execute:

1. Confirm the document set matches `spec.md`.
2. Confirm Stage and Match freeze references are current.
3. Confirm the worker/integrator split is explicit.
4. Release the first parallel wave only after all rules are stable.

Required validation:

- doc self-consistency review only; no code validation required

Done when:

- builders can start `DEV-101`, `DEV-102`, `DEV-103`, and `DEV-104` without asking for missing rules

## DEV-101 — API runtime boundary lane

Owner type:

- worker

Depends on:

- `DEV-001`

Can run in parallel with:

- `DEV-102`
- `DEV-103`
- `DEV-104`

Read first:

- `spec.md`
- `proof.md`
- `stage-reference.md`
- `match-reference.md`

Allowed edit surface:

- `src/splitshot/browser/static/lib/api.js`
- `tests/browser/test_browser_control.py`

Forbidden edit surface:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/server.py`
- `src/splitshot/browser/state.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/static/views/match-view.js`

Deliverables:

- explicit route-response ownership remains correct
- no accidental remote-state apply on structured responses

Execute:

1. Audit which responses own full remote state and which are structured payloads only.
2. Tighten the response-ownership boundary without changing Stage or Match semantics.
3. Update only task-local tests needed to prove the boundary.

Required validation:

- `./.venv/bin/python -m pytest tests/browser/test_browser_control.py tests/browser/test_automation_ui_shell_contracts.py`

Done when:

- route-response ownership is explicit and task-local tests stay green

## DEV-102 — Server route-dispatch modularization lane

Owner type:

- worker

Depends on:

- `DEV-001`

Can run in parallel with:

- `DEV-101`
- `DEV-103`
- `DEV-104`

Read first:

- `spec.md`
- `plan.md`
- `../predev/backend/spec.md`

Allowed edit surface:

- `src/splitshot/browser/server.py`
- `tests/browser/test_landing_backend_routes.py`
- `tests/browser/test_automation_ui_shell_contracts.py`

Forbidden edit surface:

- `src/splitshot/ui/controller.py` except for import or call-site wiring already required by the existing interface
- `src/splitshot/browser/state.py`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/panes/**`

Deliverables:

- route families grouped more explicitly by owner
- `landing_recent` dispatch delegates to a single backend owner
- no public route URL changes

Execute:

1. Refactor route dispatch so owner families are clearer.
2. Keep public route paths unchanged.
3. Ensure landing recent uses a single backend owner rather than duplicated logic.

Required validation:

- `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_automation_ui_shell_contracts.py`

Done when:

- route dispatch is clearer and the landing route contract remains green

## DEV-103 — `/api/state` summary-contract lane

Owner type:

- worker

Depends on:

- `DEV-001`

Can run in parallel with:

- `DEV-101`
- `DEV-102`
- `DEV-104`

Read first:

- `spec.md`
- `proof.md`
- `../predev/backend/spec.md`
- `stage-reference.md`
- `match-reference.md`

Allowed edit surface:

- `src/splitshot/browser/state.py`
- `tests/browser/test_library_backend_contracts.py`

Forbidden edit surface:

- `src/splitshot/browser/server.py`
- `src/splitshot/ui/controller.py`
- Match workspace state semantics in frozen keys unless preserved exactly

Deliverables:

- explicit shared, Stage, Match, and Performance Library summary slices
- heavy workflow payloads kept off `/api/state`

Execute:

1. Split summary building into explicit slices.
2. Keep `/api/state` summary-only.
3. Preserve frozen Match and Stage summary semantics while clarifying ownership.

Required validation:

- `./.venv/bin/python -m pytest tests/browser/test_browser_control.py tests/browser/test_library_backend_contracts.py`

Done when:

- summary slices are explicit and tests confirm no contract drift

## DEV-104 — Persistence-support lane

Owner type:

- integrator only

Depends on:

- `DEV-001`

Can run in parallel with:

- `DEV-101`
- `DEV-102`
- `DEV-103`

Read first:

- `spec.md`
- `../predev/backend/spec.md`

Allowed edit surface:

- `src/splitshot/persistence/library.py`
- `src/splitshot/persistence/projects.py`
- `tests/persistence/**`

Forbidden edit surface:

- `src/splitshot/persistence/workspaces.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/browser/static/**`

Deliverables:

- helper seams for recent activity and library-backed support data
- no workspace schema or per-stage project format changes

Execute:

1. Add or tighten persistence helpers needed by Landing/shared backend work.
2. Preserve current project and library truth contracts.
3. Do not modify workspace schema behavior.

Required validation:

- `./.venv/bin/python -m pytest tests/persistence`

Done when:

- persistence helpers support later shared-service work without changing frozen schemas

## DEV-105 — Shared controller/service lane

Owner type:

- worker

Depends on:

- `DEV-102`
- `DEV-103`
- `DEV-104`

Can run in parallel with:

- none

Read first:

- `spec.md`
- `proof.md`
- `../predev/backend/spec.md`

Allowed edit surface:

- `src/splitshot/ui/controller.py`
- `src/splitshot/ui/services/**` (new files may be created here if needed)
- `tests/browser/test_landing_backend_routes.py`
- `tests/browser/test_practiscore_session_api.py`
- `tests/browser/test_practiscore_sync_controller.py`
- `tests/browser/test_library_backend_contracts.py`

Forbidden edit surface:

- semantic changes to `workspace_*` methods
- semantic changes to Stage analysis/scoring methods
- `src/splitshot/browser/static/views/match-view.js`

Deliverables:

- shared non-Stage/non-Match responsibilities isolated behind clearer seams
- no hidden behavior changes to frozen workspace or Stage editor flows

Execute:

1. Isolate shared controller responsibilities such as landing, proxy, backup, and shared support behavior.
2. Keep frozen Match workspace and Stage editing methods behaviorally unchanged.
3. Use thin delegation if new shared-service modules are introduced.

Required validation:

- `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_practiscore_session_api.py tests/browser/test_practiscore_sync_controller.py tests/browser/test_library_backend_contracts.py`
- `uvx ruff check .`

Done when:

- shared services are clearer and protected frozen behaviors still test green

## DEV-106 — Landing UI backend-adoption lane

Owner type:

- worker

Depends on:

- `DEV-101`
- `DEV-102`
- `DEV-103`
- `DEV-105`

Can run in parallel with:

- none

Read first:

- `spec.md`
- `proof.md`
- `stage-reference.md`
- `match-reference.md`

Allowed edit surface:

- `src/splitshot/browser/static/app.js` (landing functions and landing event wiring only)
- `src/splitshot/ui/services/shared_backend.py` (landing recent payload shaping only)
- `src/splitshot/browser/static/index.html` (landing section only)
- `src/splitshot/browser/static/styles/landing.css`
- `tests/browser/test_landing_backend_routes.py`
- `tests/browser/test_browser_static_ui.py`

Forbidden edit surface:

- non-landing `app.js` orchestration
- `src/splitshot/browser/static/lib/shell-runtime.js`
- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/panes/**`

Deliverables:

- Landing recent activity is backend-driven
- local browser storage is no longer the authoritative landing truth
- `Recent Stages` remains truthful even when newer match or library recents exist

Execute:

1. Replace landing recent-activity truth sourced only from browser local storage.
2. Use the backend contract as the authoritative source.
3. Preserve stage entries in the landing payload before truncation so mixed recents cannot crowd them out.
4. Preserve current landing navigation and user-facing labels.

Required validation:

- `./.venv/bin/python -m pytest tests/browser/test_landing_backend_routes.py tests/browser/test_browser_static_ui.py`

Done when:

- Landing reflects backend truth and no frozen app behavior is touched

## DEV-107 — Root-shell registration and fallback-cleanup lane

Owner type:

- worker

Depends on:

- `DEV-101`
- `DEV-105`
- `DEV-106`

Can run in parallel with:

- none

Read first:

- `spec.md`
- `plan.md`
- `stage-reference.md`
- `match-reference.md`

Allowed edit surface:

- `src/splitshot/browser/static/app.js` (non-landing shell orchestration only)
- `src/splitshot/browser/static/lib/global-compat.js`
- `tests/browser/test_automation_ui_shell_contracts.py`
- `tests/browser/test_browser_static_ui.py`
- `tests/browser/test_browser_interactions.py`

Forbidden edit surface:

- `src/splitshot/browser/static/views/match-view.js`
- `src/splitshot/browser/static/panes/**`
- protected frozen route semantics

Deliverables:

- less fallback ownership in the root shell
- clearer app registration and shell-only responsibilities

Execute:

1. Remove or reduce legacy fallback ownership in the root shell where delegate-first behavior already exists.
2. Keep Stage and Match user-visible behavior unchanged.
3. Keep shared shell limited to landing/home/surface switch/global status/app registration.

Required validation:

- `./.venv/bin/python -m pytest tests/browser/test_automation_ui_shell_contracts.py tests/browser/test_browser_static_ui.py tests/browser/test_browser_interactions.py tests/browser/test_workspace_flows.py`

Done when:

- shell ownership is smaller and guardrail packs prove no frozen-baseline drift

## DEV-201 — Frozen-baseline proof-audit lane

Owner type:

- integrator only

Depends on:

- `DEV-106`
- `DEV-107`

Can run in parallel with:

- none

Read first:

- `spec.md`
- `proof.md`
- `stage-reference.md`
- `match-reference.md`
- `docs/project/browser-control-qa-matrix.md`

Allowed edit surface:

- `proof.md`
- `stage-reference.md`
- `match-reference.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md`
- `docs/project/browser-full-e2e-qa-plan.md`
- `tests/browser/test_browser_control_coverage_matrix.py`
- `tests/browser/test_browser_control_inventory_audit.py`

Forbidden edit surface:

- `src/**`
- `../predev/**` except by integrator after acceptance

Deliverables:

- truthful proof-class mapping for Stage and Match control families
- honest weakness ledger
- required update checklist synchronized with current ownership

Execute:

1. Classify Stage and Match control families using the proof taxonomy.
2. Update QA and coverage docs where ownership or claims shifted.
3. Call out current weaknesses honestly instead of masking them with optimistic wording.

Required validation:

- `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py`

Done when:

- frozen-baseline proof expectations are explicit enough that later proof work does not need to rediscover them

## DEV-301 — Integrator review, devil’s advocate, and handoff lane

Owner type:

- integrator only

Depends on:

- `DEV-201` and all prior worker lanes

Can run in parallel with:

- none

Read first:

- `progress.md`
- `proof.md`
- `outcome.md`
- all worker handoff packets
- touched source-lane ledgers

Allowed edit surface:

- `progress.md`
- `proof.md`
- `outcome.md`
- `artifacts.md`
- touched `../predev/backend/*` and `../predev/modularization/*` ledgers when status moved
- `orchestration.prompt.md` if execution rules changed during the wave

Forbidden edit surface:

- new implementation code unless fixing an integrator-only merge error

Deliverables:

- shared ledgers synchronized
- review-agent findings resolved or recorded
- explicit residual risks and next actions

Execute:

1. Merge worker handoff results into `progress.md`, `proof.md`, and `outcome.md`.
2. Run a review-agent pass, a devil’s-advocate pass, and a validation pass.
3. Resolve or record every material finding.
4. Update touched source-lane ledgers if task status actually moved.
5. Publish the next-wave or handoff state clearly.

Required validation:

- `./.venv/bin/splitshot --check`
- `./.venv/bin/python -m pytest tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_control_inventory_audit.py`
- `./.venv/bin/python scripts/testing/run_test_suite.py --mode all-together --format table` only when the integrator needs a fresh full-suite anchor

Done when:

- shared docs agree, review findings are resolved or logged, and the next execution state is explicit

# Development Proof Ledger

## Purpose

This file defines the proof model for the active `development/` bundle.

It does **not** replace the final acceptance and signoff work owned by `testing/`. Instead, it states what builders must preserve, what they must prove when they move ownership boundaries, and what evidence the integrator must assemble before handoff.

Stable cross-surface seam IDs and evidence lists live in `docs/project/browser-proof-seams.json`.

## Normative proof rule

A meaningful control or workflow does **not** count as complete merely because a button exists or a smoke interaction passes.

A meaningful control must do at least one of the following:

1. mutate persisted truth, or
2. produce or alter a user-consumable output or artifact.

If a control does neither, it may still exist, but it cannot close a meaningful implementation claim by itself.

## Proof taxonomy

| Class | Meaning | Qualifies for meaningful closure? | Examples |
| --- | --- | --- | --- |
| `PERSISTED_MODEL` | Mutates saved project, workspace, profile, library, settings, or other durable state. | Yes | `project.json`, `profiles.json`, workspace bundle, library record, saved settings |
| `OUTPUT_ARTIFACT` | Produces or changes rendered/exported/downloadable/servable output. | Yes | MP4 export, recap output, CSV/TXT metric export, export log download, media route output |
| `LOCAL_PERSISTED_UI` | Persists browser-local UI preferences only. | Yes, but only for local UI scope | `splitshot.match.*`, `splitshot.library.*` |
| `RUNTIME_EPHEMERAL` | Exists only in transient UI state and does not persist or produce output on its own. | No, by itself | temporary selection, queue checkbox before export, waveform zoom/pan, focus state |

## Builder update rule

Whenever a control owner, route, persistence target, or output path changes, the same change must update all applicable proof anchors:

- `stage-reference.md` and/or `match-reference.md`
- `docs/project/browser-control-qa-matrix.md`
- `docs/project/browser-control-coverage-plan.md` when coverage claims change
- `docs/project/browser-full-e2e-qa-plan.md` when end-to-end scope changes
- `tests/browser/test_browser_control_coverage_matrix.py`
- `tests/browser/test_browser_control_inventory_audit.py` when IDs/surfaces change
- relevant interaction/contract/persistence/export tests
- user-facing docs when user-visible workflow or naming changes

## Foundation-proof gates for active development work

| Task lane | Required proof class | Required evidence |
| --- | --- | --- |
| `DEV-101` API runtime boundary | `PERSISTED_MODEL` + contract proof | route-response ownership tests; no accidental full-state apply on structured responses |
| `DEV-102` server route dispatch modularization | `PERSISTED_MODEL` + route contract proof | route-family tests; landing route delegates correctly; no public route drift |
| `DEV-103` `/api/state` summary split | `PERSISTED_MODEL` + summary contract proof | summary-state tests; no heavy workflow payload regression |
| `DEV-104` persistence support helpers | `PERSISTED_MODEL` | persistence tests for recent-activity/library helper changes |
| `DEV-105` shared controller/service extraction | `PERSISTED_MODEL` | controller tests; no Stage/Match semantic drift in protected methods |
| `DEV-106` Landing UI backend adoption | `PERSISTED_MODEL` + UI proof | `DEV-106.landing_recent` — landing backend-route + static render contract + recent-row interaction proof for `/api/landing/recent` |
| `DEV-107` root shell cleanup | `PERSISTED_MODEL` family preservation + compat/static shell contract | `DEV-107.root_shell_compat` — compat/static shell contract plus workflow guardrails, retained host open-project callback, and direct Performance-library rerender/selected-record consumers |
| `DEV-201` frozen-baseline proof audit | documentation + proof integrity | updated references, QA matrix, control-proof mapping, honest weakness ledger |
| `DEV-301` integrator/handoff | aggregate proof integrity | review-agent findings resolved, progress/proof/outcome synchronized, residual risks recorded |

## Recorded foundation evidence

- `DEV-106.landing_recent` / `DEV-106` closure evidence: `tests/browser/test_landing_backend_routes.py` proves `/api/landing/recent` still delegates through the backend owner and preserves stage/single landing rows before truncation so mixed match/library recents cannot crowd them out; `tests/browser/test_browser_static_ui.py` proves landing recents are sourced from `/api/landing/recent`, the `Recent Stages` render path no longer treats `splitshot.recentActivity` as authoritative truth, and recent-row clicks remain surface-only rather than auto-opening a project; `tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open` proves the backend-rendered recent row really switches to the Stage surface without opening a project or workspace. This is backend-route + static-render-contract + interaction proof.
- `DEV-107.root_shell_compat` / `DEV-107` closure evidence: `tests/browser/test_automation_ui_shell_contracts.py`, `tests/browser/test_browser_static_ui.py`, `tests/browser/test_browser_interactions.py`, and `tests/browser/test_workspace_flows.py` prove the shared shell still exposes the three core surfaces, preserves Match stage-open/return and setup-once flows, and keeps the pinned lower-pane Match contract while root-shell global exposure moves through `installLegacyGlobalCompat(...)` instead of duplicate tail-end `window.*` assignments; `tests/browser/test_browser_interactions.py::test_shell_compat_host_on_open_project_callback_opens_saved_project` proves the retained host open-project callback; and `tests/browser/test_browser_interactions.py::test_performance_library_compat_selected_record_and_render_rerender_detail_truth` proves direct `renderAutomationSurface` / `selectedLibraryRecord` consumers keep Performance-library lower-detail truth and persistence working. This is a compat/static shell contract plus guarded interaction-consumer proof for the retained compatibility surface.
- `DEV-301` handoff evidence: the review/devil passes confirmed the aggregate `development/` ledgers and the touched `predev/backend/*` and `predev/modularization/*` ledgers now carry the same `DEV-106.landing_recent` and `DEV-107.root_shell_compat` seam records; `./.venv/bin/splitshot --check` passed the runtime-health gate; `tests/browser/test_browser_control_coverage_matrix.py` plus `tests/browser/test_browser_control_inventory_audit.py` now pass as a `5 passed` seam-registry-backed audit pair; and `./.venv/bin/python scripts/testing/run_test_suite.py --mode all-together --format raw --raw-output artifacts/all-together-raw.txt --json-output artifacts/all-together.json --pytest-arg=-x` reran the canonical all-together suite green with `691 passed in 1821.89s (0:30:21)`. This is Work Effort 1 handoff proof, not final screenshot or acceptance-signoff proof.

## Frozen Stage baseline proof ledger

Stage is frozen as a behavior baseline. Builders do not add new Stage features here; they preserve and re-prove the existing baseline when shared ownership changes.

Use `stage-reference.md` for the compact mixed-family proof-taxonomy summary when one Stage family contains both proof-bearing controls and lighter browser-only/runtime-only affordances.

| Stage family | Proof class | Primary truth or artifact | Primary proof anchors | Current expectation |
| --- | --- | --- | --- | --- |
| Project / import / PractiScore setup | `PERSISTED_MODEL` | `project.json`, staged `Input/`/`CSV/`, PractiScore state | `stage-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_project_lifecycle_contracts.py`, PractiScore browser + analysis tests | Must remain frozen; any contract drift forces explicit reopen. |
| ShotML settings and proposals | `PERSISTED_MODEL` | `AnalysisState` in `project.json` | `stage-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_browser_remaining_controls_e2e.py` | Preserve current behavior; prove settings/proposals still persist truthfully. |
| Splits / waveform shot and event editing | `PERSISTED_MODEL` + `RUNTIME_EPHEMERAL` | `AnalysisState.shots`, `AnalysisState.events`; transient waveform view state | `stage-reference.md`, `tests/browser/test_timing_waveform_contracts.py`, browser interactions | Shot/event edits are meaningful; waveform navigation alone is not. |
| Scoring | `PERSISTED_MODEL` | `ScoringState` in `project.json` | `stage-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_scoring_metrics_contracts.py` | Preserve scoring truth and row-edit behavior. |
| Compose / added media / sync | `PERSISTED_MODEL` + `OUTPUT_ARTIFACT` | merge settings in `project.json`; exported render outputs | `stage-reference.md`, `tests/browser/test_merge_export_contracts.py`, `tests/export/test_export.py`, full-app/browser interactions | Settings must persist; output-affecting changes must be proven through render/export artifacts. |
| Markers / Overlay / Review | `PERSISTED_MODEL` + `OUTPUT_ARTIFACT` | popup/overlay/review payloads in `project.json`; rendered output behavior | `stage-reference.md`, `tests/browser/test_overlay_review_contracts.py`, browser interactions | Preserve existing overlay/review ownership and output relevance. |
| Metrics | `OUTPUT_ARTIFACT` + `PERSISTED_MODEL` | derived metrics tables; CSV/TXT downloads; expansion state in UI state | `stage-reference.md`, `tests/browser/test_metrics_e2e.py`, browser interactions | Downloads count as output artifacts; browser-only expansion does not close the lane by itself. |
| Export / output profiles / hooks | `PERSISTED_MODEL` + `OUTPUT_ARTIFACT` | `project.json`, `profiles.json`, exported video, export log | `stage-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/export/test_export.py`, `tests/browser/test_merge_export_contracts.py` | Output-affecting controls must be tied to real artifact proof. |
| Settings defaults | `PERSISTED_MODEL` | app/folder defaults, project UI state | `stage-reference.md`, `tests/browser/test_settings_e2e.py`, settings truth-gate tests | Preserve saved defaults and isolation rules. |

## Frozen Match baseline proof ledger

Match is frozen as a behavior baseline. Builders preserve the workflow exactly as documented unless a protected reopen is declared.

Use `match-reference.md` for the compact mixed-family proof-taxonomy summary when a Match family mixes saved truth, export output, and runtime-only setup controls.

| Match family | Proof class | Primary truth or artifact | Primary proof anchors | Current expectation |
| --- | --- | --- | --- | --- |
| Workspace lifecycle and stage membership | `PERSISTED_MODEL` | workspace bundle, stage membership, open/return context | `match-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_workspace_flows.py` | Preserve open/save/add/remove/open-return semantics. |
| Shared defaults / overrides / apply-from-first | `PERSISTED_MODEL` | workspace defaults/override state, sibling stage updates, stage profiles/projects | `match-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_workspace_flows.py` | Preserve propagation semantics and conflict behavior. |
| Recap workflow | `OUTPUT_ARTIFACT` + `RUNTIME_EPHEMERAL` | runtime recap selection/order/options until render, then `recap.mp4` output | `match-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_workspace_export_and_recap.py` | Render output is the meaningful closure; pre-render checklist state alone is not. |
| Composite clips / angle / audio / cut overrides | `PERSISTED_MODEL` + `OUTPUT_ARTIFACT` | workspace clip state, `profiles.json`, composite export output | `match-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_workspace_flows.py`, composite/export tests | Clip state must persist; output-affecting workflows must reach export artifacts. |
| Batch export | `OUTPUT_ARTIFACT` | exported stage outputs/composites under workspace export paths | `match-reference.md`, `tests/browser/test_browser_interactions.py`, `tests/browser/test_workspace_export_and_recap.py` | Queue selection alone is not enough; exported files are the proof target. |
| Match local settings | `LOCAL_PERSISTED_UI` | `splitshot.match.settings`, section, rail state | `match-reference.md`, browser interactions | Local settings count only for local-scope proof, not domain-state closure. |
| Runtime-only workflow state | `RUNTIME_EPHEMERAL` | recap selection before render, queue checkboxes before export, current focus | `match-reference.md`, browser interactions | Must remain honest in docs; cannot close meaningful claims alone. |

## Known weaknesses to keep explicit

1. `test_browser_control_coverage_matrix.py` mainly proves doc-string coverage, not semantic per-control truth.
2. `test_browser_control_inventory_audit.py` catches missing controls and IDs, but not proof depth by itself.
3. `stage-reference.md` and `match-reference.md` are rich manual maps, but they are not auto-generated from code and can drift.
4. Some output proof today is controller-heavy rather than full browser-path-heavy.
5. The QA matrix currently admits that not every control has one-control-one-test coverage; builders must not over-claim otherwise.
6. Any change to Project-pane PractiScore behavior must follow the PractiScore repo instruction set in the same change.
7. Coverage-plan phases and inventory ownership describe browser test/document ownership, not proof class or meaningful closure by themselves.

## PractiScore-specific proof obligations

If a change touches Project-pane PractiScore workflow or any related UI/backend state, the same change must preserve and update:

- manual `Select PractiScore File` fallback
- local `Match type`, `Stage #`, `Competitor name`, and `Place` controls
- browser contract keys: `practiscore_session`, `practiscore_sync`, and `practiscore_options`
- owning browser tests and QA/docs where control IDs or coverage claims change

## Handoff boundary to `testing/`

`development/` owns proof-readiness and truthful proof mapping.

`testing/` still owns:

- final screenshot packages
- final proof bundles and artifact capture
- QA matrix closeout as an acceptance gate
- full-suite closeout
- final visual approval and signoff

## Completion rule

This proof ledger is satisfied only when:

1. active foundation lanes have explicit evidence requirements,
2. frozen Stage and Match behavior families are mapped to truthful proof classes,
3. known weaknesses remain visible instead of hidden by optimistic wording, and
4. builder agents have an unambiguous checklist of required doc/test updates whenever ownership or proof surfaces change.

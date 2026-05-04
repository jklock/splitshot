# SplitShot Modularization Program Plan

**Status:** active
**Program branch:** `modularization`
**Last audited:** 2026-05-02

## Mission

Refactor the browser frontend from a monolithic `app.js` implementation into a best-practice modular architecture **without changing the user experience at all**.

This program is an internal architecture change only. The following must remain identical unless a task document explicitly proves that a compatibility-preserving internal adjustment is required:

- visible UI structure and pane order
- user-facing control labels and control ids
- layout behavior and default sizing
- browser workflows and timing of interactions
- server API contracts and persisted project semantics
- browser test expectations and audit baselines

The output of this program must also leave the browser shell ready for the later PWA work described in `../PWA/pwa-after-modularization.md` and `../cloudflare/cloudflare-pages.md`, but this program does **not** ship manifest, service worker, or install UX changes as part of modularization.

## Audited baseline

The facts below were verified against the live repository on 2026-05-02.

| Area | Verified actual |
| --- | --- |
| Git branch | `modularization` |
| Browser shell HTML | `src/splitshot/browser/static/index.html` — 1,194 lines |
| Browser monolith JS | `src/splitshot/browser/static/app.js` — 14,376 lines |
| Browser stylesheet | `src/splitshot/browser/static/styles.css` — 4,587 lines |
| Browser server | `src/splitshot/browser/server.py` — 1,712 lines |
| Browser state builder | `src/splitshot/browser/state.py` — 227 lines |
| Browser test inventory | `tests/browser/` — 18 test files / 225 top-level test functions |
| Browser monolith structure | `app.js` has 0 `import` statements, 0 `export` statements, 0 classes, 91 top-level `let` globals, and 739 named `function` declarations |
| Monolith shell seams | `render()` lines 12,731–12,747; `wireEvents()` lines 13,763–14,376 |
| Static shell structure | still a classic `<script>` load, not module-based |
| Existing UI audit artifacts | `artifacts/browser-ui-surface-audit-latest.json`, `artifacts/browser-interaction-audit-latest.json` |
| Missing QA docs | `docs/project/browser-control-qa-matrix.md`, `docs/project/browser-control-coverage-plan.md`, `docs/project/browser-full-e2e-qa-plan.md` |

## Program artifacts

This directory is the operational control plane for modularization.

| File | Role |
| --- | --- |
| `plan.md` | master program definition, task map, constraints, and sign-off rules |
| `progress.md` | append-only execution ledger for task claims, completions, blockers, and proof links |
| `orchestration-prompt.md` | master orchestration prompt for the top-level chat that spawns and manages subagents end to end |
| `validation.md` | zero-UX-delta validation directions |
| `audit.md` | structural and architectural audit directions |
| `tasks/` | executable task packets with non-overlapping ownership |
| `proof/` | immutable proof records for each run |

## Non-negotiable constraints

1. **Zero UX delta.** This is an internal refactor. The UI must remain visually and behaviorally identical.
2. **No feature creep.** Do not add product features during modularization.
3. **No silent contract drift.** Browser ids, route payloads, and persistence expectations must remain compatible until a dedicated migration task says otherwise.
4. **Best-practice module boundaries.** Shared behavior belongs in the backbone, not as hidden cross-pane dependencies.
5. **Every run leaves evidence.** No task is considered complete without proof and progress updates.
6. **Parallel work is allowed only when ownership does not overlap.** Shared hotspot files require explicit single-owner control.

## Task catalog

The task packets in `tasks/` are the executable work units for subagents.

| ID | Title | Purpose | Depends on | Parallel lane |
| --- | --- | --- | --- | --- |
| `T00` | Foundation and governance | Create the modularization control plane and operating rules | none | no |
| `T01` | Baseline truth audit | Lock down current facts and produce ownership anchors for future extraction tasks | `T00` | no |
| `T02` | QA baseline doc restoration | Restore the missing QA matrix and coverage-plan docs required by browser validation | `T01` | no |
| `T03` | Bootstrap module shell | Prepare the browser shell for module loading with compatibility shims | `T01`, `T02` | no |
| `T04` | Backbone core | Extract zero-dependency backbone modules (`utils`, `event-bus`, `store`) | `T03` | no |
| `T05` | Backbone runtime | Extract runtime backbone modules (`api`, `layout`, `keys`, `processing`, `activity`) | `T04` | no |
| `T06` | Components shell | Extract status bar, video player, and shared shell components | `T05` | no |
| `T07` | Components waveform and overlay | Extract waveform and overlay canvas behavior with no UX change | `T06` | no |
| `T08` | Pilot scoring pane | Prove the pane extraction pattern with the scoring pane | `T07` | no |
| `T09A` | Settings and metrics panes | Extract low-coupling panes after the pilot succeeds | `T08` | yes |
| `T09B` | Project and merge panes | Extract project and merge panes while preserving PractiScore parity | `T08` | yes |
| `T09C` | Export and review panes | Extract export and review panes and their shared test ownership | `T08` | yes |
| `T09D` | ShotML and overlay panes | Extract shotml and overlay after review/overlay contracts are stable | `T09C` | limited |
| `T09E` | Markers and timing panes | Extract the highest-coupling panes last | `T09D` | no |
| `T10` | Monolith cleanup | Remove wrappers and retired monolithic scaffolding | `T09A`, `T09B`, `T09C`, `T09D`, `T09E` | no |
| `T11` | CSS split | Split `styles.css` while preserving the exact visual result | `T10` | no |
| `T12` | Final certification and PWA readiness | Prove modular completion, zero UX drift, and future PWA readiness | `T10`, `T11` | no |

## Execution order and concurrency

The program intentionally starts with governance and baseline truth before any code motion:

```text
T00 -> T01 -> T02 -> T03 -> T04 -> T05 -> T06 -> T07 -> T08
                                                ├-> T09A
                                                ├-> T09B
                                                └-> T09C -> T09D -> T09E
T09A/T09B/T09C/T09D/T09E -> T10 -> T11 -> T12
```

Parallelism is only allowed when the `touches-files` lists in the task packets do not intersect and when shared test ownership has already been partitioned.

## Shared hotspots

The following files require explicit single-owner control during any active task run:

| Hotspot | Default owner task |
| --- | --- |
| `src/splitshot/browser/static/index.html` | `T03` until `T10`; `T11` may only touch stylesheet link wiring after cleanup |
| `src/splitshot/browser/static/app.js` | `T03`–`T10`, but only one active task may edit owned anchor blocks at a time |
| `src/splitshot/browser/static/styles.css` | `T11` |
| `tests/browser/test_browser_static_ui.py` | `T02`, `T03`, `T11`, `T12` |
| `tests/browser/test_browser_interactions.py` | `T07`, `T09D`, `T09E`, `T12` |
| `tests/browser/test_merge_export_contracts.py` | merge assertions owned by `T09B`, export/review assertions owned by `T09C` |
| `tests/browser/test_overlay_review_contracts.py` | review assertions owned by `T09C`, overlay assertions owned by `T09D` |
| `tests/browser/test_browser_control_inventory_audit.py` | `T02`, then `T12` |
| `tests/browser/test_browser_control_coverage_matrix.py` | `T02`, then `T12` |
| `docs/project/browser-control-qa-matrix.md` | `T02`, then task-specific doc updates, then `T12` reconciliation |

`T01` must extend `audit.md` with exact ownership anchors or line-range notes before `T03` can start.

## Validation and proof policy

- Every task must follow `validation.md`.
- Every task must follow `audit.md`.
- Every task run must produce a new immutable proof record in `proof/`.
- `progress.md` is the source of truth for task status and active claims.
- No task may be marked `done` without a proof file and a validation summary.

## Done criteria for the entire program

The modularization program is complete only when all of the following are true:

1. `T00`–`T12` are marked `done` or explicitly waived with rationale.
2. The browser UI contract remains identical to the baseline.
3. The required browser suites and audits pass at a 100% pass rate for the final certification run.
4. `app.js` has been reduced from monolith to bootstrap-only responsibility.
5. Pane and component behavior live in dedicated modules with no prohibited cross-pane coupling.
6. The resulting static asset layout is suitable for later PWA work without redoing the architecture.

## Source documents

These files remain the human-facing source documents that describe the design intent and downstream future state:

- `../00-index.md`
- `../modular.md`
- `../PWA/pwa-after-modularization.md`
- `../cloudflare/cloudflare-pages.md`
- `../../docs/project/ARCHITECTURE.md`
- `../../src/splitshot/browser/static/README.md`
- `../../docs/project/DEVELOPING.md`

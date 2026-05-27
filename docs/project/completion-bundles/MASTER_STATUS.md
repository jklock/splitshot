# SplitShot Completion Program Master Status

This file is the authoritative cross-bundle status board for `docs/project/completion-bundles`.

Use this file to answer:

- what is actually done,
- what is only implemented but still waiting on proof,
- what has not had a dedicated execution pass yet,
- what must happen next,
- how the source bundles map into the two aggregate work efforts,
- which evidence counts as acceptance evidence versus historical reference.

Source-bundle files remain the source of detailed execution notes. The aggregate `development/` and `testing/` bundles are the execution overlays that let this program close in exactly two work efforts, while `predev/` now contains the detailed source bundles and parity-input reference material.

## Program snapshot

- Last updated: `2026-05-26`
- Program state: `Work Effort 1 complete / Work Effort 2 handoff pending`
- Work Effort 1 / Set 1: `development/`
- Work Effort 2 / Set 2: `testing/`
- Canonical repo-health proof anchor: `../../../artifacts/all-together.json`
- Canonical baseline result: `691 passed in 1821.89s (0:30:21)` on `2026-05-26`

Important distinction:

- `predev/tests/` is the source bundle for test modularization.
- `testing/` is the aggregate Work Effort 2 overlay.
- They are related, but they are **not** the same thing.

## Directory model

The working directory now has three execution-facing subdirectories:

- `development/` — aggregate Work Effort 1 / Set 1
- `testing/` — aggregate Work Effort 2 / Set 2
- `predev/` — container for all detailed source bundles and parity-input/reference material

### `predev/` = source-bundle container

These six source bundles remain intact inside `predev/` and remain the detailed truth for lane-local scope, task state, specs, outcomes, and artifacts:

- `predev/stage/`
- `predev/match/`
- `predev/performance/`
- `predev/backend/`
- `predev/modularization/`
- `predev/tests/`

### Aggregate bundles = the two work efforts

These two aggregate bundles are the execution overlays that let the program close in exactly two work efforts:

- `development/` — Work Effort 1 / Set 1 for all implementation and development work across the source bundles
- `testing/` — Work Effort 2 / Set 2 for all testing, proof packaging, artifact capture, QA/doc sync, final gates, and signoff across the source bundles

### Input brief

- `predev/newfeatures/from-shooting-cut.md` remains a parity-input source brief, not completion proof and not a source lane.

### Normalized status vocabulary

Use these status terms consistently across every bundle:

- `execution-ready / implementation pending`
  - The bundle contract, backlog, and proof rules have been reset into an executable state.
  - Active implementation work under that reset has not yet been executed or revalidated.
- `planning baseline`
  - The lane has a written contract, backlog, and evidence plan, but it has **not** had a dedicated execution pass yet.
  - Broad repo validation does **not** count as completing this lane.
- `implementation advanced / proof pending`
  - The lane was materially worked in the current pass and significant implementation or focused validation landed.
  - The lane is still **not done** because final proof packaging, screenshots, artifact recording, and/or visual approval remain open.
- `done`
  - The lane `outcome.md` final gate is fully closed, required evidence is linked, and approval is recorded.

## Aggregate work-effort scoreboard

| Aggregate bundle | Work effort | Status | Task-state summary | What is firmly done | What still blocks done |
| --- | --- | --- | --- | --- | --- |
| `development/` | `Work Effort 1 / Set 1` | `done` | `DEV-001` through `DEV-301` complete | execution contract reset, frozen-baseline guardrails, proof taxonomy, backend/state/persistence/controller/landing/shell implementation closure, seam-registry-backed audit sync, and the republished Work Effort 1 handoff are recorded | none inside Work Effort 1; remaining proof/signoff scope belongs to `testing/` |
| `testing/` | `Work Effort 2 / Set 2` | `implementation advanced / proof pending` | `STG-007` and `STG-008` complete; Match `MCH-002` through `MCH-007` complete; Performance proof/signoff package partial; Backend `BEK-007` / `BEK-008` future; Modularization `MOD-006` / `MOD-007` future; source `predev/tests/` bundle `TST-001` through `TST-009` future | Stage and Match docs/test/proof/signoff are complete; focused proof slices and the repo-health baseline already exist for Performance | Remaining Performance proof packaging, Backend and Modularization proof/signoff passes, all `TST-*` work, screenshots/artifacts/docs sync, final suite runs, and visual signoff |

Important clarification for aggregate status interpretation:

- The `development/` aggregate bundle was reset from a historical retrospective overlay into an active execution contract; that reset is now complete through `DEV-301`, including the reopened proof closure and fresh all-together anchor.
- Historical implementation notes remain preserved in the source bundles under `predev/` until the reset `DEV-*` lanes actually move those statuses again.
- For live execution of the reset bundle, use `development/progress.md`, `development/tasks.md`, and `development/outcome.md` as the immediate authority.
- Historical source-bundle completion notes did **not** authorize skipping reset `DEV-*` lanes in `development/`; that reset Work Effort 1 execution is now closed, and any later implementation issue must use an explicit reopen rather than informal caveat language.
- When a reset `DEV-*` lane materially moves a source lane, the integrator must update the touched aggregate and `predev/*` ledgers in the same integration pass.
- When a reset bundle status materially moves, the integrator must update `MASTER_STATUS.md` in that same integration pass.

## Source-bundle scoreboard

These six source bundles remain the detailed lane truth inside `predev/`.

| Source bundle | Status | Task-state summary | What is firmly done | What still blocks done |
| --- | --- | --- | --- | --- |
| `predev/stage/` | `done` | `STG-001` through `STG-008` complete | Contract reset, Project cleanup, shared-shell hardening, defaults/regression closure, Stage-owned parity closure, docs/test/proof sync, final gate confirmation, artifact recording cleanup, visual signoff | none |
| `predev/match/` | `done` | `MCH-001` through `MCH-007` complete | Contract reset, shared-shell convergence, lifecycle/auto-seed proof, lower-pane/right-inspector proof, recap/composite/export/parity closure, settings isolation/doc sync, screenshots/output artifacts, visual signoff | none |
| `predev/performance/` | `implementation advanced / proof pending` | `PRF-001`, `PRF-005` complete; `PRF-002`, `PRF-003`, `PRF-004`, `PRF-006` partial; `PRF-007` open | Contract reset, shared-shell implementation, reopen/settings isolation, notes/tags and analytics truth already partly proven, visible stale/error manual recovery restored | Lower-pane/right-inspector proof packaging, search/filter/detail proof depth, backup/export artifacts, screenshots, visual signoff |
| `predev/backend/` | `implementation advanced / proof pending` | `BEK-001` through `BEK-006` complete; `BEK-007` and `BEK-008` open | Route/state inventory, `/api/state` summary contract, status/error recovery, persistence/import/PractiScore support, and Match/Performance backend support are materially landed | Final proof package, route/state artifact packaging, residual-risk closeout, approval |
| `predev/modularization/` | `implementation advanced / proof pending` | `MOD-001` through `MOD-005` complete; `MOD-006` and `MOD-007` open | Ownership inventory, interface rules, Match/Performance delegation cleanup, and app-local settings isolation are materially landed | Final proof package, temporary-exception closeout, approval |
| `predev/tests/` | `planning baseline` | `TST-001` through `TST-009` still future work | Contract, backlog, and artifact expectations exist; repo-wide validation baseline exists | Dedicated test-modularization pass, ownership carve-out, fixture/artifact isolation, runner/doc/CI sync, approval |

## Two-work-effort source mapping

This is the required mapping between the source bundles and the two aggregate work efforts.

| Source bundle | `development/` = Work Effort 1 / Set 1 | `testing/` = Work Effort 2 / Set 2 |
| --- | --- | --- |
| `predev/stage/` | `STG-001` through `STG-006` | `STG-007` and `STG-008` |
| `predev/match/` | `MCH-001` plus implementation portions of `MCH-002` through `MCH-006` | proof/signoff work tied to `MCH-002`, `MCH-003`, `MCH-004`, `MCH-006`, all of `MCH-007`, plus any remaining Match artifact/signoff packaging needed to close the final gate |
| `predev/performance/` | `PRF-001` plus implementation portions of `PRF-002` through `PRF-005` | proof/signoff work tied to `PRF-002`, `PRF-003`, `PRF-004`, `PRF-006`, all of `PRF-007`, plus any remaining Performance artifact/signoff packaging needed to close the final gate |
| `predev/backend/` | `BEK-001` through `BEK-006` | `BEK-007` and `BEK-008` |
| `predev/modularization/` | `MOD-001` through `MOD-005` | `MOD-006` and `MOD-007` |
| `predev/tests/` | none | all of `TST-001` through `TST-009` |

Important clarification:

- The source `predev/tests/` bundle remains the detailed truth for test modularization.
- The aggregate `testing/` bundle includes that entire source `predev/tests/` bundle **plus** the proof/signoff closure from the other source bundles.
- Do not use `predev/tests/` and `testing/` interchangeably.

## Current done ledger

This ledger preserves historical source-lane completion context. It is not a release authorization to skip active reset tasks in `development/`.

### Completed enough to count as materially advanced

#### Stage

- `STG-001` — contract reset complete
- `STG-002` — Project automation cleanup complete
- `STG-003` — shared Stage shell hardening complete
- `STG-004` — import/home/output defaults complete
- `STG-005` — PiP/Review/marker/top-bar regression closure complete
- `STG-006` — Stage-owned parity closure complete
- `STG-007` — docs/test/proof sync complete

#### Match complete items

- `MCH-001` — contract reset complete
- `MCH-002` — shared-shell convergence proof complete
- `MCH-003` — lifecycle and auto-seed proof complete
- `MCH-004` — lower-pane/right-inspector workflow proof complete
- `MCH-005` — recap/composite/export/parity closure complete
- `MCH-006` — Match settings isolation and doc sync complete
- `MCH-007` — Match done gate complete

#### Performance complete items

- `PRF-001` — contract reset complete
- `PRF-005` — Performance settings isolation and naming alignment complete

#### Backend complete items

- `BEK-001` — route and state ownership inventory complete
- `BEK-002` — `/api/state` summary contract complete
- `BEK-003` — status, error, and activity normalization complete for Work Effort 1
- `BEK-004` — persistence and truth behavior closure complete for Work Effort 1
- `BEK-005` — import and PractiScore contract protection complete for Work Effort 1
- `BEK-006` — Match and Performance backend support closure complete

#### Modularization complete items

- `MOD-001` — shell/module ownership inventory complete
- `MOD-002` — stable module interface rules complete
- `MOD-003` — Stage isolation verification complete
- `MOD-004` — shared-shell constraint closure complete with documented temporary exceptions
- `MOD-005` — app-local persistence and settings isolation complete

### Implemented but still proof-pending

#### Performance proof-pending items

- `PRF-002` — shared-shell convergence implemented, but lower-pane/right-inspector proof remains open
- `PRF-003` — record/detail workflow rebuild implemented, but search/filter/detail proof depth remains open
- `PRF-004` — analytics and persistence truth partly proven, but backup/export proof remains open
- `PRF-006` — docs largely synchronized, but screenshot and remaining proof-package work remains open

### Explicitly not complete yet

- `PRF-007`
- `BEK-007`
- `BEK-008`
- `MOD-006`
- `MOD-007`
- `TST-001` through `TST-009`

## Evidence model

### Acceptance evidence

Evidence counts toward source-bundle completion only when it is recorded in the owning source `outcome.md` and `artifacts.md` and supports the current shell/ownership contract.

Evidence counts toward aggregate-bundle completion only when:

1. the mapped source-bundle work is accurately reflected,
2. the aggregate bundle’s active ledgers point at the same truth (`development/` may use `progress.md`, `proof.md`, and `outcome.md` while retaining `artifacts.md` only as a compatibility pointer),
3. the reserved work-effort boundaries are respected, and
4. final proof/signoff work is closed in `testing/` rather than being silently absorbed into `development/`.

A source bundle is not `done` until all of the following are true:

1. The owning final gate in `outcome.md` is fully checked.
2. The required proof artifacts for that lane are linked in `artifacts.md`.
3. The owning docs and QA/test references are updated.
4. Visual approval is recorded when the lane requires browser-visible signoff.

### Historical reference evidence

Historical artifact bundles and pre-reset proof remain useful reference material, but they do **not** count as acceptance evidence for the current contract unless the lane ledger explicitly says they still apply.

### Baseline repo-health evidence

`../../../artifacts/all-together.json` is the canonical repo-health anchor.

It proves that the repository reached a passing full-suite baseline after the current Stage/Match/Performance work, but it does **not** by itself close:

- `development/`
- `testing/`
- `predev/backend/`
- `predev/modularization/`
- `predev/tests/`

## Evidence completeness matrix

| Lane | Focused tests | Screenshots | Output / artifact packaging | Final gate |
| --- | --- | --- | --- | --- |
| `predev/stage/` | recorded | recorded | recorded | closed |
| `predev/match/` | recorded | recorded | recorded | closed |
| `predev/performance/` | partly recorded | pending | pending for backup/export and shell-proof packaging | open |
| `predev/backend/` | targeted validation recorded | n/a | final proof package pending | open |
| `predev/modularization/` | targeted validation recorded | n/a | final proof package pending | open |
| `predev/tests/` | baseline only | n/a | pending | open |

## Ordered work-effort plan

The completion program is now expressed as exactly two work efforts.

### 1. Work Effort 1 / Set 1 — `development/`

Preserve this order inside Work Effort 1 unless a newly discovered blocker forces a documented change:

1. Preserve the settled Stage implementation baseline (`STG-001` through `STG-006`) and reopen it only if a real implementation blocker is found.
2. Preserve the settled Match implementation baseline (`MCH-001` plus implementation sides of `MCH-002` through `MCH-006`) and do not silently shift Match proof/signoff work back into development.
3. Preserve the settled Performance implementation baseline (`PRF-001` plus implementation sides of `PRF-002` through `PRF-005`) and do not silently shift Performance proof/signoff work back into development.
4. Execute Backend implementation scope (`BEK-001` through `BEK-006`) in order:
   - route/state ownership inventory,
   - `/api/state` hardening,
   - status/error normalization,
   - persistence truth closure,
   - import/PractiScore protection,
   - Match/Performance backend support closure.
5. Execute Modularization implementation scope (`MOD-001` through `MOD-005`) in order:
   - ownership inventory,
   - stable interfaces,
   - Stage isolation,
   - shared-shell constraint closure,
   - app-local persistence/settings isolation.
6. Publish the Work Effort 1 handoff in the live `development/` ledgers named by the bundle spec (`development/outcome.md`, plus `development/progress.md` and `development/proof.md` when they own execution truth).

### 2. Work Effort 2 / Set 2 — `testing/`

Preserve this order inside Work Effort 2 unless a newly discovered blocker forces a documented change:

1. Preserve the closed Stage testing/signoff scope through `STG-007` and `STG-008`, reopening it only if a new first-order blocker appears.
2. Preserve the closed Match proof/signoff scope through `MCH-007`, reopening it only if a new first-order blocker appears.
3. Close the remaining Performance shell/detail/search-filter/backup-export package and `PRF-007`.
4. Close Backend and Modularization testing/signoff scope through `BEK-007`, `BEK-008`, `MOD-006`, and `MOD-007`.
5. Execute the entire source `predev/tests/` bundle scope (`TST-001` through `TST-009`).
6. Refresh screenshots, artifacts, QA docs, coverage docs, and user-facing docs where required.
7. Run focused proof slices, owned suites, the canonical full suite, and final visual signoff last.

## Cross-bundle dependencies

- `development/` aggregates implementation across the source bundles.
- `testing/` closes proof and signoff against that implementation handoff.
- `predev/stage/` owns the canonical shell grammar reused by `predev/match/` and `predev/performance/`.
- `predev/match/` depends on Stage handoff/return behavior plus shared-shell truth.
- `predev/performance/` depends on shared-shell truth and stable reopen/backend behavior.
- `predev/backend/` has now had its dedicated Work Effort 1 implementation pass; Work Effort 2 depends on keeping that shared route/state truth aligned while the final proof/signoff package closes.
- `predev/modularization/` depends on explicit backend and shell ownership rules and should not be credited from incidental refactors.
- the source `predev/tests/` bundle depends on the settled ownership model from the app, backend, and modularization bundles, but it executes inside aggregate Work Effort 2.

## Normalization decisions recorded here

- `README.md`, `RECOVERY_NEXT_STEPS.md`, the six source bundles under `predev/`, and the two aggregate bundles should defer to this file for cross-bundle summaries.
- the completion program is intended to close in exactly two work efforts: `development/` for Work Effort 1 / Set 1 and `testing/` for Work Effort 2 / Set 2.
- source bundles stay intact under `predev/`; aggregate bundles are overlays, not replacements.
- `predev/` is a source-bundle container, not a third work effort.
- the source `predev/tests/` bundle is not the same thing as the aggregate `testing/` bundle.
- `docs/project/completion-bundles/predev/newfeatures/from-shooting-cut.md` is a parity-input source brief, not completion proof.
- the unnumbered `orchestration.prompt.md` file in each bundle is the canonical prompt source.
- the new aggregate bundles do not use numbered duplicate prompt files.
- Stage should no longer be summarized as only `STG-001` through `STG-005` complete; the normalized state is `STG-001` through `STG-008` complete.
- Backend and Modularization have now received their dedicated Work Effort 1 implementation passes; only the source `predev/tests/` bundle should remain at `planning baseline` until its dedicated execution pass occurs.

## Per-bundle file mapping

Use the bundle-local files for detail in either a source or aggregate bundle:

- `plan.md` — scope, sequencing, boundaries, and acceptance framing
- `tasks.md` — actionable backlog and task state
- `spec.md` — normative requirements and non-regression contract
- `outcome.md` — lane-local ledger, final gate, waivers, and signoff record
- `artifacts.md` — evidence classes, artifact paths, and proof ledger, unless the bundle spec explicitly retains it as a compatibility pointer while live execution truth moves to other ledgers
- `orchestration.prompt.md` — canonical lane execution prompt

## Editorial verification checklist

Before considering this directory coherent, confirm all of the following:

- every source bundle under `predev/` still acts as the detailed lane truth,
- `development/` is described as Work Effort 1 / Set 1 everywhere,
- `testing/` is described as Work Effort 2 / Set 2 everywhere,
- `predev/tests/` and `testing/` are never treated as synonyms,
- no aggregate bundle claims proof/signoff work inside `development/`,
- no source bundle is deleted or replaced by an aggregate bundle,
- the aggregate bundles use only unnumbered canonical prompt files,
- every top-level summary points to the same three-directory, two-work-effort execution model.

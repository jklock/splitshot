# Stage Completion Plan

## Objective

Re-establish Stage as the canonical SplitShot editing shell and workflow. Stage defines the layout grammar that Match and Performance must reuse: preview-dominant main content, right-side inspector, and a lower detail/info pane arranged around the video workspace.

## Current execution status

- Normalized lane status: `done`
- Task status: `STG-001` through `STG-008` complete
- Cross-lane authority: `../../MASTER_STATUS.md`

## Scope

This bundle covers the Stage lane and the shared shell rules that Stage owns:

- Stage shell grammar in `#view-stage`
- Project setup/import flow as the entry into editing
- PractiScore file/session/sync interactions surfaced through Project and Stage
- Compose, splits, score, overlay, markers, review, export, timing, scoring, metrics, and ShotML Stage workflows
- redistribution of the current Project-pane automation controls into the actual editing flow
- Stage-owned docs, prompts, tests, screenshots, and proof artifacts that define the shared shell contract reused by Match and Performance

## Non-goals

This bundle does not by itself complete:

- Match recap/composite/export implementation details
- Performance analytics implementation details
- broad backend modernization outside the Stage-first workflow reset
- reintroducing a separate Project automation dashboard or any other placeholder/no-op control bucket

## Current-state summary

Stage is the canonical editing surface in the product again, and the lane is now through its final done gate.

Current facts that matter:

- Stage already contains the shell grammar the user wants reused everywhere.
- Project cleanup, shared-shell hardening, Stage defaults/regression closure, and Stage-owned parity implementation are all materially complete in this lane.
- The previously open Compose waveform/default/sync, imported-summary authoring, review layout, marker-style inheritance, and top-bar status placement issues are now implemented and covered by focused proof slices recorded in `outcome.md` and `artifacts.md`.
- Match and Performance are now treated as Stage-shell variants rather than separate shell families.
- Existing completion ledgers for Stage, Match, and Performance are only valid when read through the normalized status model in `../../MASTER_STATUS.md`.
- The Stage lane now records closed final-gate proof: runtime health, targeted browser verification, artifact existence checks, and visual approval.

## Architecture boundaries

### Stage owns

- the canonical shell grammar reused by Match and Performance
- the Stage editing workflow order: `Project -> Compose -> Splits/Score -> Overlay -> Markers -> Review -> Export`
- Stage-specific pane behavior and Stage-visible control semantics
- Project-pane setup/import behavior and PractiScore entry points surfaced for Stage work
- Stage-owned tests, docs, screenshots, and proof artifacts

### Match and Performance own

- their workflow-specific data and controls inside the shared Stage shell family
- Match tile, recap, composite, export, and workspace semantics
- Performance record, analytics, reopen, backup, export, and settings semantics

### Shared shell owns

- app switching
- landing navigation
- global status/notification plumbing
- truly global settings entry points

### Shared backend owns

- route transport
- controller mutations and persistence truth
- analysis, review, reopen, and export services

## Protected contracts

The Stage-first reset must preserve these invariants unless the same change updates the owning tests and docs:

- `practiscore_session`
- `practiscore_sync`
- `practiscore_options`
- manual `Select PractiScore File` fallback
- local `Match type`, `Stage #`, `Competitor name`, and `Place` controls
- footer order `Home` then `Settings`
- preview-dominant Stage workspace
- no top automation strip and no Project-pane automation dump

## Work phases

## Phase 1 — Contract reset

Reset the Stage bundle so it defines the product direction again:

- rewrite Stage docs/prompts around the shared Stage shell
- record the user-mandated workflow order
- mark the old Stage signoff as superseded by the redesign
- identify the tests/docs that must move with shell changes

Exit criteria:

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, and `artifacts.md` all describe the same Stage-first target
- Stage prompts instruct future work to preserve the workflow order and shared-shell ownership

## Phase 2 — Shell grammar hardening

Stabilize Stage as the shell source-of-truth before deeper feature work:

- extract or normalize the shell primitives Match and Performance will reuse
- keep the video workspace dominant in Stage
- preserve the lower pane and right inspector grammar
- remove stale assumptions that Match or Performance need their own shell families

Exit criteria:

- Stage shell primitives are explicit and reusable
- the shared shell no longer encourages separate Match/Performance layout families

## Phase 3 — Workflow redistribution

Move Stage-adjacent automation controls into the real editing flow:

- Project: setup/import/PractiScore only
- Compose: secondary media import, source roles, sync/alignment, waveform-secondary visibility
- Splits/Score/Overlay/Markers: keep or absorb controls that logically belong there
- Review: review source plus imported/custom summary authoring
- Export: output profiles, auto trim, title cards, watermark/logo, frame shape, render options

Exit criteria:

- Project is no longer a catch-all automation pane
- no control remains in Project unless it is logically part of setup or import

## Phase 4 — Regression closure

Close the Stage-visible regressions that block the new shell:

- project-home and import-copy behavior
- project output-folder defaults
- Compose waveform visibility and playback sync
- review defaults and imported-summary authoring
- review two-column layout
- marker-vs-overlay style separation
- top-bar/status-bar placement

Exit criteria:

- the Stage flow works from setup through export without known workflow blockers
- the major user-reported regressions are backed by owning tests or proof artifacts

## Phase 5 — Stage and Stage-owned parity closure

Close the features that must be represented and functional inside the Stage flow:

- Auto Trim
- Compose layout parity
- Match composite parity
- intro title cards
- custom watermark
- score-import expansion

Exit criteria:

- each Stage-owned or Stage-led feature is implemented or explicitly documented as deferred
- placeholder UI is not counted as feature completion

## Phase 6 — Docs, tests, and proof alignment

Synchronize the Stage lane with the shared shell reset:

- static UI/browser contract tests
- interaction tests and focused regression coverage
- QA matrix and coverage docs
- user-facing Stage and Project docs
- screenshot and artifact ledgers

Exit criteria:

- docs, tests, and artifact ledgers all agree on the new Stage-first contract

## Phase 7 — Final signoff

Stage is complete only when all of these are true:

- Stage-owned tests pass for the new shell/workflow contract
- Match and Performance shell reuse no longer depends on stale standalone-shell assumptions
- screenshot proof exists for empty and loaded Stage states plus the redistributed workflow panes
- residual risks and waivers are recorded in `outcome.md`
- visual review signs off on the new Stage shell

## Universal acceptance criteria

The Stage bundle must produce:

- loading states for async work
- recoverable error states
- visible keyboard focus and logical tab order
- responsive checks at 1280px and 900px
- destructive-action confirmation where data loss is possible
- no dead, placeholder, or misleading controls inside the active workflow

## Primary risks

- static browser tests assert literal source strings and DOM structure
- old completion proof can be mistaken for approval of the new shell direction
- Project-pane cleanup can regress protected PractiScore behavior if moved carelessly
- Stage fixes can look green in backend tests while still failing the browser interaction flow

## Required references

- `../newfeatures/from-shooting-cut.md`
- `../../ARCHITECTURE.md`
- `../../browser-control-qa-matrix.md`
- `../../browser-control-coverage-plan.md`
- `../../browser-full-e2e-qa-plan.md`
- `../../../../tests/TEST_SUITE_GUIDE.md`

## Plan result

This Stage bundle is the execution contract for resetting SplitShot around the Stage shell and the user-defined editing flow.

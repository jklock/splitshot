# Match Completion Plan

## Objective

Align Match to the Stage shell and make it the match-level workflow that sits inside that shared layout: tile-based stage browsing in the main area, selected-stage information in the lower pane, and workflow controls in the right-hand inspector.

## Scope

This bundle covers Match behavior inside the shared Stage shell family:

- Match shell reuse of the Stage layout grammar
- workspace lifecycle: create, open, save, reopen
- stage list, stage membership, and auto-seeded stage registration from Stage/project setup
- tile selection and selected-stage information behavior
- shared defaults and stage overrides
- setup-once and apply-from-first workflows
- recap, composite, and batch export flows
- Match-only settings and persistence
- Match docs, tests, screenshots, and proof

## Non-goals

This bundle does not by itself complete:

- Stage editor internals beyond the explicit handoff and return path
- Performance analytics workflows
- broad backend refactors outside Match-owned route and state needs
- any separate Match shell family distinct from Stage

## Current-state summary

Match currently exists as a dedicated surface in `#view-match`, but the contract is aimed at the wrong target.

Current facts that matter:

- Match routes, workspace persistence, defaults/overrides, recap, composite, and export behavior already exist.
- The existing bundle marks Match complete as a standalone app, which conflicts with the new product direction.
- The current Match shell grammar is separate from Stage even though the user wants the same design reused.
- Match also depends on a reliable Stage handoff and return path plus stage-registration behavior that should begin at project setup time.

## Architecture boundaries

### Match owns

- match-level workflow semantics inside the shared Stage shell
- tile selection and selected-stage info behavior
- workspace stage membership, defaults, overrides, recap, composite, and export semantics
- Match settings that affect Match only

### Stage owns

- the canonical shell grammar reused by Match
- the single-stage editing experience after Match opens a stage
- the stage/project setup entry that can auto-seed Match membership

### Shared shell owns

- app switching and landing navigation
- global status / notifications
- truly global settings entry points

### Shared backend owns

- workspace persistence and autosave
- workspace export and recap render behavior
- workspace open-stage / return-to-workspace contract
- controller truth for stage entries, defaults, overrides, clips, and exports

## Match work phases

## Phase 1 — Contract reset

Reset the Match bundle around the Stage-shell direction:

- remove the standalone-Match-app framing
- record Match as a Stage-shell variant
- define the tile + lower-info + right-inspector grammar
- mark prior Match signoff as historical rather than current approval

Exit criteria:

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, and `artifacts.md` describe the same Match target
- Match prompts no longer instruct future work to preserve a separate Match shell family

## Phase 2 — Shell convergence and tile workflow

Move Match onto the shared Stage shell:

- reuse the Stage shell primitives
- move Match stage browsing into a tile-based main area
- repurpose the lower pane as selected-stage information instead of a generic waveform space
- keep workflow controls in the right-hand inspector

Exit criteria:

- Match visibly shares the Stage shell family
- the main/lower/right arrangement is clear and stable

## Phase 3 — Lifecycle and auto-seed alignment

Close the project-to-match lifecycle seams:

- new/open/save workspace flow
- stage add/remove/select behavior
- auto-create or attach Match membership when a Stage folder/project is opened
- open Stage from Match and return to Match predictably

Exit criteria:

- Stage registration and Match lifecycle behavior are deterministic and user-visible

## Phase 4 — Recap, composite, export, and parity closure

Close Match output workflows and Shooting Cut parity gaps:

- setup-once and apply-from-first behavior
- recap render flow and recap merge gaps
- composite clip management and per-clip controls
- batch export flow
- Auto Trim, Split Sync/Stage Mix orchestration, intro/title/watermark parity, and score-import expansion where they belong in Match

Exit criteria:

- Match output workflows are implemented or explicitly documented as deferred
- placeholder UI is not counted as parity

## Phase 5 — Settings, docs, and proof alignment

Finalize Match isolation and proof:

- Match settings remain Match-only
- QA docs and browser plans accurately reflect shared-shell Match ownership
- screenshots and artifacts reflect the new tile/info shell

Exit criteria:

- docs/tests/artifacts all agree on current Match behavior

## Universal acceptance criteria

The Match bundle must provide:

- the same shell family as Stage
- a tile-based main area for stage selection
- a lower pane dedicated to the selected tile’s details and information
- a right-hand inspector for Match workflow controls
- footer order `Home` then `Settings`
- loading and recoverable error states
- confirmation on destructive actions such as stage removal
- proof that Stage handoff and return-to-workspace work predictably

## Primary risks

- old Match proof can be mistaken for approval of the wrong shell model
- stage auto-seed behavior can drift between Project, Stage, and Match if not owned clearly
- recap/composite/export behavior can remain route-true but UX-false if shell convergence lands incompletely
- Match-only settings can silently leak into shared shell behavior if not isolated

## Required references

- `../newfeatures/from-shooting-cut.md`
- `../../ARCHITECTURE.md`
- `../../browser-control-qa-matrix.md`
- `../../browser-control-coverage-plan.md`
- `../../browser-full-e2e-qa-plan.md`
- `../../../tests/TEST_SUITE_GUIDE.md`
- `../../../src/splitshot/browser/static/views/match-view.js`
- `../../../src/splitshot/browser/server.py`
- `../../../src/splitshot/ui/controller.py`

## Plan result

This Match bundle is the execution contract for delivering Match as a Stage-shell variant with tile-first workflow, Stage handoff, and proof-backed recap/export behavior.

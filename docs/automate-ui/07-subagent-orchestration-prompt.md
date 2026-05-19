# UI Implementation Agent Prompt

Use this prompt to assign the full `docs/automate-ui/` implementation to an execution agent.

## Prompt

You are implementing the full UI completion package for SplitShot automation work.

You must treat `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/` as the execution command center and `/Volumes/Storage/GitHub/splitshot/docs/automate/` as the backend contract that already defines the product/data/API foundation.

Your job is to finish the browser-shell and packaged-Electron UI so the shipped product truthfully exposes the automation backend that now exists.

Do not rewrite the plan. Execute it.

## Read Order

Read these files first, in this order:

1. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/spec.md`
2. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/execution-order.md`
3. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/todo.md`
4. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/outcomes.md`
5. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/agent-rules.md`
6. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/tracks/01-pip-performance-and-merge-editor.md`
7. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/tracks/02-shell-navigation-and-surface-model.md`
8. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/tracks/03-single-video-ui.md`
9. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/tracks/04-multi-video-ui.md`
10. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/tracks/05-performance-library-ui.md`
11. `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/tracks/06-proof-regression-release.md`
12. `/Volumes/Storage/GitHub/splitshot/docs/automate/00a-splitshot-naming-contract.md`
13. `/Volumes/Storage/GitHub/splitshot/docs/automate/00b-implementation-quality-contract.md`
14. `/Volumes/Storage/GitHub/splitshot/docs/automate/10-acceptance-and-proof.md`
15. `/Volumes/Storage/GitHub/splitshot/docs/automate/11-release-readiness.md`

After reading the docs, inspect the current code reality before changing anything:

- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/index.html`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/app.js`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/panes/merge-pane.js`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/components/video-player.js`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/server.py`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/state.py`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/ui/controller.py`

## Non-Negotiable Rules

1. Keep SplitShot-native naming everywhere.
2. Do not copy competitor labels into UI labels, route names, schema names, comments, tests, docs, or release notes.
3. Do not invent a different shell structure than the one defined in `docs/automate-ui/spec.md`.
4. Do not treat PiP as a cosmetic issue. Fix preview playback smoothness first.
5. Do not leave partial UI surfaces. A surface is not complete if it only has layout without route/state wiring.
6. Do not bloat `/api/state` with heavy clip or library payloads. Use dedicated fetches.
7. Do not claim completion without targeted proof, relevant suite proof, and updated docs/progress.
8. Do not regress existing visible stage-edit behavior while adding the new shell.

## Primary Outcome

Deliver a browser-shell and packaged-app UI that truthfully exposes:

- `Single Video`
- `Multi Video`
- `Performance Library`

and makes third-person / extra-video sync usable by fixing jumpy preview playback.

## Required Implementation Order

Execute in this order unless a documented blocker forces a narrower prerequisite:

1. PiP performance and merge editor stabilization
2. Shell navigation and surface model
3. Single Video UI completion
4. Multi Video UI completion
5. Performance Library UI completion
6. UI-enabling backend support pass
7. Proof, regression, and release closure

## Scope Boundaries

This is UI completion work. Do not turn it into a new backend architecture project.

Allowed backend support work is limited to what the UI package already calls out:

- persist stage clips and clip-local angle/audio/cut state
- add `POST /api/workspace/stage/clips/list`
- add `POST /api/angle/director/plan`
- keep existing route/state contracts coherent for the new UI

If more backend work appears necessary, verify it against the existing docs first and keep it tightly scoped to unblocking the UI.

## Phase Requirements

### Phase 1: PiP Performance And Merge Editor

You must treat this as blocker number one.

Current failure shape:

- preview drift is checked too aggressively
- small drift causes reseek churn
- preview playback looks jumpy
- third-person sync cannot be judged visually

Required outcome:

- continuous playback is the default preview behavior
- small drift uses bounded playback-rate correction only
- large drift uses one reseek, then returns to continuous playback
- hard seek is limited to attach, scrub, pause/play boundary, sync nudge, large drift breach, or source reset
- active drag suspends heavy sync churn
- pointermove does not commit route writes on every event

You must verify:

- no per-frame `fastSeek` or `currentTime` churn during steady playback
- no reseek loop on every RAF while the main video plays
- preview remains visually smooth enough to sync by eye
- merge adjustments still commit accurately after drag or nudge

### Phase 2: Shell Navigation And Surface Model

Replace the current flat legacy rail as the top-level product model.

Required outcome:

- top-level surface switcher for `Single Video`, `Multi Video`, and `Performance Library`
- context header with active project/workspace, active stage, return-to-workspace affordance, and output/proxy/render status
- mode-aware panes under the correct parent surface
- clear empty, loading, stale, unresolved-link, and error states

### Phase 3: Single Video UI

Required outcome:

- preserve current deep stage-edit panes
- add first-class output-profile manager
- expose create, duplicate, rename, delete, retained-review source selection, render-plan preview, and render-result state
- expose `Run Window`, `Metric Captions`, `Frame Profiles`, `Lead-In Card`, `Brand Mark`, and `Subject Track Crop` hooks
- show inherited/defaulted values when editing a stage from inside a workspace

### Phase 4: Multi Video UI

Required outcome:

- real workspace UI
- workspace create/open/save
- stage table with status, missing media, override, and review indicators
- stage open/return flow
- shared-default editor
- stage-override editor
- separate `Match Recap` and `Stage Composite` surfaces

`Stage Composite` must include:

- clip list
- clip add/update/remove
- angle role editing
- `Angle Align` controls
- audio mix lane controls
- cut override plan UI
- composite render action

`Match Recap` must include:

- stage inclusion/exclusion
- order visibility
- result-card controls
- match-scope output-profile render action

### Phase 5: Performance Library UI

Required outcome:

- dedicated library surface, not a small embedded widget
- summary tiles
- list/filter/search/sort UI
- selected-record details
- retained proxy status and actions
- open proxy / refresh proxy / open stage / open workspace actions

### Phase 6: UI Support Pass

Only after the UI structure is clear, add the narrow support deltas required by the package if they are still missing.

Required outcome:

- stage clip persistence is no longer only in-memory
- stage clip read route exists and is wired
- angle-director plan read route exists and is wired

### Phase 7: Proof, Regression, And Release

You must not stop after the UI appears to work.

Required outcome:

- targeted tests for changed behavior
- relevant browser/export suites
- browser audit if UI/routes/controller behavior changed in ways the audit covers
- packaged proof for critical flows
- docs/progress updates reflecting final implementation state
- SplitShot-native release wording if the work is being shipped now

## Files Most Likely To Change

Expect most UI work to center on:

- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/index.html`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/app.js`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/panes/merge-pane.js`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/static/components/video-player.js`

Expect narrow support changes in:

- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/server.py`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/browser/state.py`
- `/Volumes/Storage/GitHub/splitshot/src/splitshot/ui/controller.py`

Expect tests to land under:

- `/Volumes/Storage/GitHub/splitshot/tests/browser/`
- `/Volumes/Storage/GitHub/splitshot/tests/export/`

Update the UI package docs when implementation reality resolves or narrows anything important:

- `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/progress.md`
- `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/todo.md`
- `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/outcomes.md`
- `/Volumes/Storage/GitHub/splitshot/docs/automate-ui/artifacts/ui-proof-matrix.md`

## Required Proof Order

Use the narrowest useful checks first.

1. Targeted tests for PiP sync/performance and touched UI contracts
2. Relevant browser suites
3. Relevant export/library suites if touched
4. Browser audit where applicable
5. Canonical grouped runner before merge or release if requested

Do not rerun the same broad failing command without first isolating the smaller failing target.

## Minimum Scenarios That Must Pass

### PiP performance

- attach third-person or extra video
- play primary and preview sources together
- confirm smooth preview playback
- confirm visual sync can be adjusted without jumpy reseek behavior
- drag PiP during playback without route churn or unusable stutter

### Single Video

- open or create a stage
- edit stage truth
- create and manage multiple output profiles
- render `Run Window`
- render `Metric Captions`
- set retained proxy source

### Multi Video

- create or open workspace
- add stages
- apply shared defaults
- override one stage
- open stage and return
- render `Match Recap`

### Stage Composite

- add clips
- assign angle roles
- run `Angle Align`
- edit audio mix
- edit cut override plan
- render `Stage Composite`

### Performance Library

- confirm record creation after accepted save
- browse and filter records
- open retained proxy
- reopen stage or workspace from history

### Packaged app

- run at least one Single Video flow
- run at least one Multi Video or Stage Composite flow
- prove PiP preview smoothness in packaged mode too

## Definition Of Done

The work is only complete when all of the following are true:

1. The shell exposes `Single Video`, `Multi Video`, and `Performance Library` clearly.
2. PiP preview playback is smooth enough to sync visually.
3. `Match Recap` and `Stage Composite` are separate, usable surfaces.
4. Output profiles are first-class UI, not hidden behind the old export flow.
5. The UI does not depend on fake state or missing read endpoints.
6. Targeted tests exist for changed behavior.
7. Relevant suite proof passes.
8. Updated docs/progress reflect the implemented state.
9. No known regression remains against frozen visible contracts you touched.

## Final Reporting Requirements

When you finish, report in this structure:

Changed:
- implementation summary grouped by surface/feature area

Verified:
- exact commands run
- pass/fail
- failing test names only if any fail
- artifact paths for long outputs

Result:
- whether the UI package is now implemented end to end
- whether any narrow follow-up remains

Risks:
- only real unresolved risk, not generic caveats

Do not say the work is complete unless the proof is real.

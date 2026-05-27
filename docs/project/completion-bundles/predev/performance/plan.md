# Performance Completion Plan

## Objective

Align Performance to the Stage shell and present it as the history/analytics workflow inside that shared layout: graphs and data in the main area, selected-record information in the lower pane, and filters/settings/actions in the right-hand inspector.

## Current execution status

- Normalized lane status: `done`
- Task status: `PRF-001` through `PRF-007` complete
- Cross-lane authority: `../../MASTER_STATUS.md`

## Scope

This bundle covers Performance behavior inside the shared Stage shell family:

- Performance shell reuse of the Stage layout grammar
- overview tiles, record listing, search, sort, and filter behavior
- selected-record detail, reopen, notes, and tags behavior
- analytics and trend views
- backup/restore and CSV/JSON export workflows
- Performance-only settings and persistence
- Performance docs, tests, screenshots, and proof

## Naming note

The current implementation is still housed under `#view-library` and `createLibraryView(...)`. This bundle treats that surface as the user-facing Performance app. Internal `library` names may remain temporarily, but the shell and user-facing contract must align with Performance.

## Non-goals

This bundle does not by itself complete:

- Stage editing workflows except for reopen entry points
- Match workspace editing except for reopen entry points
- broad analytics-engine changes beyond what is required to keep current claims truthful
- any separate Performance shell family distinct from Stage

## Current-state summary

Performance already has meaningful backend and interaction proof, and the Work Effort 2 closeout pass has now closed the remaining focused proof packaging and signoff.

Current facts that matter:

- The backend exposes list/filter/open/export/analytics/backup/tag/note routes and much of that proof remains valuable.
- The bundle has been reset around Performance as a Stage-shell variant rather than a standalone shell family.
- The shared-shell layout, record/detail workflow, reopen behavior, settings isolation, and notes/tags or analytics truth are all now proven and recorded in the source ledger.
- The repo-owned screenshot package, backup/export artifacts, and visual approval are all now linked from `outcome.md` and `artifacts.md`, so the lane no longer carries an open final-gate item.

## Architecture boundaries

### Performance owns

- Performance workflow semantics inside the shared Stage shell
- record listing, selection, detail, analytics, backup, export, notes, tags, and settings behavior
- Performance-local persistence and proof artifacts

### Stage owns

- the canonical shell grammar reused by Performance
- the shared main/lower/right arrangement and visible shell conventions

### Shared shell owns

- landing navigation and app switching
- global status/notification behavior
- shared home and truly global settings entry points

### Shared backend owns

- library record loading and filtering
- analytics query routes
- record reopen targets for Stage and Match
- backup/create/restore and export endpoints
- tag and note persistence truth

## Performance work phases

## Phase 1 — Contract reset and naming alignment

Reset the Performance bundle around the shared-shell direction:

- remove the standalone-Performance-app framing
- record the current internal `library` naming seam and user-facing Performance requirement
- define the graph/data main area plus lower-record-info grammar
- mark prior signoff evidence as historical rather than current approval

Exit criteria:

- `plan.md`, `spec.md`, `tasks.md`, `outcome.md`, and `artifacts.md` describe the same Performance target
- Performance prompts no longer instruct future work to preserve a separate shell family

## Phase 2 — Shell convergence and record workflow

Move Performance onto the shared Stage shell:

- reuse the Stage shell primitives
- place graphs/data in the main area
- use the lower pane for selected-record information
- keep filters, notes/tags, reopen, backup/export, and settings actions in the right-hand inspector

Exit criteria:

- Performance visibly shares the Stage shell family
- the main/lower/right arrangement is clear and stable

## Phase 3 — Carry forward backend truth inside the new shell

Re-verify the behaviors that already have meaningful proof:

- loading, refresh, stale, and empty-state behavior
- record selection and detail rendering
- stage/workspace reopen behavior
- notes and tags persistence truth
- analytics truth and messaging
- backup/export behavior

Exit criteria:

- preserved behavior is re-proven against the new shell where required
- no stale shell assumptions remain in tests or docs

## Phase 4 — Settings, docs, and proof alignment

Finalize Performance isolation and proof:

- Performance settings remain isolated
- naming remains truthful even if internal `library` identifiers persist
- QA docs, user docs, and screenshot artifacts reflect the shared-shell Performance view

Exit criteria:

- docs/tests/artifacts all agree on current Performance behavior

## Universal acceptance criteria

The Performance bundle must provide:

- the same shell family as Stage
- graphs and data in the main content area
- a lower pane dedicated to the selected record’s detail/info
- a right-hand inspector for Performance filters, actions, and settings
- footer order `Home` then `Settings`
- empty, loading, stale, success, and error states where relevant
- truthful reopen, analytics, backup, and export flows

## Primary risks

- old non-visual proof can be misread as approval of the wrong shell model
- internal `library` naming can create documentation drift if not explicitly mapped
- Performance can still look complete in backend tests while visible browsing/detail behavior drifts in the new shell

## Required references

- `../newfeatures/from-shooting-cut.md`
- `../../ARCHITECTURE.md`
- `../../browser-control-qa-matrix.md`
- `../../browser-control-coverage-plan.md`
- `../../browser-full-e2e-qa-plan.md`
- `../../../../tests/TEST_SUITE_GUIDE.md`
- `../../../src/splitshot/browser/static/views/library-view.js`
- `../../../src/splitshot/browser/server.py`
- `../../../src/splitshot/ui/controller.py`

## Plan result

This Performance bundle is the execution contract for delivering Performance as a Stage-shell variant with truthful record browsing, analytics, reopen, and data-protection workflows.

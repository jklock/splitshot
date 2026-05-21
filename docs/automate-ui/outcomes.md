# Automate UI Outcomes

## Completion Definition

The UI overhaul is complete only when all of the following are true.

## Released Baseline Preservation

- the shipped `v1.0.5` Windows export-font path still holds
- packaged OCR proof for overlay readability still holds
- packaged/test workflows still consume `docs/Clip1.MP4`

## Product Surfaces

- `Single Video` is the deep stage editor
- `Multi Video` is the workspace-level editor
- `Performance Library` is the historical browse/reopen surface
- the shell exposes those three surfaces directly

## PiP Playback

- added third-person or extra preview video plays smoothly enough to sync visually
- small drift no longer causes constant reseek jumps
- PiP drag remains usable during playback
- sync nudges still land accurately

Current implementation note:

- browser preview sync now throttles large-drift reseeks, uses bounded rate correction for smaller drift, and skips heavy preview sync while PiP drag is active.

## Single Video

- output profiles are first-class UI
- profile CRUD exists
- retained-review source selection exists
- Run Window, Metric Captions, Frame Profiles, Lead-In Card, Brand Mark, and Subject Track Crop hooks are visible and usable

## Multi Video

- workspace lifecycle is visible and usable
- stage table reflects real workspace state
- shared defaults and per-stage overrides are visible and editable
- `Match Recap` and `Stage Composite` are separate flows in UI and proof

## Performance Library

- records can be browsed, filtered, selected, and reopened
- retained proxy actions are visible and truthful
- stage and workspace reopen flows are deterministic from the UI

## Proof

- targeted UI suites pass
- targeted baseline-preservation suites pass
- PiP performance contract passes
- browser E2E flows pass
- packaged UI proof passes for the shipped flows
- release wording remains SplitShot-native if shipping

Current proof note:

- targeted static shell, PiP contract, inventory audit, and coverage matrix proof passes
- browser test suite: 286 passed (covers all three automation surfaces, legacy tool panes, PiP contracts, workspace flows, export, and shell navigation)
- export test suite: 43 passed (covers export pipeline, overlay font policy, and Clip1.MP4 fixture)
- browser interaction audit (`scripts/audits/browser/run_browser_interaction_audit.py`) has a pre-existing primary-import timeout unrelated to UI shell changes
- packaged UI proof has not been run; this is the primary remaining deferred gate

## Current Readiness State

- All P0 baseline guardrails verified: Windows export-font, Clip1.MP4 fixture, browser preview font stacks
- All P0 UI blockers resolved: PiP playback smooth, three-surface shell model, legacy stage-edit behavior stable
- All P1 UI-enabling support complete: stage clip persistence, dedicated read routes, angle-director plan route
- All P1 shell/navigation items complete: surface switcher, context header, rehomed tool panes, empty/loading/error/stale states
- All P1 Single Video items complete: output-profile manager, profile CRUD, retained-review source selector, output hook editors, render-plan state
- All P1 Multi Video items complete: workspace lifecycle, stage grid, shared-defaults editor, stage-override editor, Match Recap, Stage Composite
- All P1 Performance Library items complete: summary tiles, filter/search/sort, record detail, proxy actions, reopen actions
- All P1 proof items complete: targeted UI suites, PiP performance contract, browser E2E test suite
- Remaining deferred: packaged automation proof and packaged PiP playback proof
- Changelog/release-note wording is SplitShot-native; re-check only needed when shipping

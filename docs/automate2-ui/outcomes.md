# Automate2 UI Outcomes

## Completion Definition

The UI overhaul is complete only when all of the following are true.

## Released Baseline Preservation

- the shipped `v1.0.5` Windows export-font path still holds
- packaged OCR proof for overlay readability still holds
- packaged/test workflows still consume `docs/Clip1.MP4`

## Product Surfaces

- `Landing Page` is the clear, friendly entry surface
- `Stage Video Edit` is the deep stage editor
- `Match Video Edit` is the workspace-level editor
- `Performance Library` is the historical browse/reopen/analytics surface
- the shell exposes those four surfaces directly

## PiP Playback

- added third-person or extra preview video plays smoothly enough to sync visually
- small drift no longer causes constant reseek jumps
- PiP drag remains usable during playback
- sync nudges still land accurately

## Landing Page

- three entry cards are visible and clickable
- recent activity shows real data
- quick-start shortcuts work
- empty state is friendly and helpful
- page loads in under 1 second

## Stage Video Edit

- output profiles are first-class UI with preview
- profile CRUD exists
- retained-review source selection exists
- Trim Dead Time, Shot Data on Screen, Video Shape, Opening Title, Your Logo, Keep Shooter in Frame hooks are visible and usable
- Smart Angle Switching, Line Up Angles, Camera Jobs, Audio Balance, Override Smart Cuts are visible and usable
- multi-track waveform renders correctly
- color-coded segments display correctly

## Match Video Edit

- workspace lifecycle is visible and usable
- stage grid reflects real workspace state
- drag-and-drop reordering works
- shared defaults and per-stage overrides are visible and editable
- Setup Once, Apply Everywhere workflow is smooth and clear
- batch export shows progress
- `Match Recap` and `Stage Composite` are separate flows in UI and proof

## Performance Library

- records can be browsed, filtered, selected, and reopened
- retained proxy actions are visible and truthful
- stage and workspace reopen flows are deterministic from the UI
- analytics charts render correctly
- personal bests are highlighted
- outliers are flagged
- tags and notes are editable
- library data can be exported

## Proof

- targeted UI suites pass
- targeted baseline-preservation suites pass
- PiP performance contract passes
- browser E2E flows pass
- packaged UI proof passes for the shipped flows
- release wording remains SplitShot-native if shipping

## Current Readiness State

- All P0 baseline guardrails verified: Windows export-font, Clip1.MP4 fixture, browser preview font stacks
- All P0 UI blockers resolved: PiP playback smooth, four-surface shell model, legacy stage-edit behavior stable
- All P1 UI-enabling support complete: stage clip persistence, dedicated read routes, angle-director plan route, landing page routes, analytics routes, archive routes
- All P1 shell/navigation items complete: surface switcher, context header, rehomed tool panes, empty/loading/error/stale states, Landing Page
- All P1 Stage Video Edit items complete: output-profile manager, profile CRUD, retained-review source selector, output hook editors, render-plan state, multi-angle features, multi-track waveform, color-coded segments
- All P1 Match Video Edit items complete: workspace lifecycle, stage grid, shared-defaults editor, stage-override editor, Match Recap, Stage Composite, Setup Once Apply Everywhere, batch export
- All P1 Performance Library items complete: summary tiles, filter/search/sort, record detail, proxy actions, reopen actions, analytics, tags, notes, export
- All P1 proof items complete: targeted UI suites, PiP performance contract, browser E2E test suite
- Remaining deferred: packaged automation proof and packaged PiP playback proof
- Changelog/release-note wording is SplitShot-native; re-check only needed when shipping

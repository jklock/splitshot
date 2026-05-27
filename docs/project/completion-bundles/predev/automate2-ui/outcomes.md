> **Note:** Historical ledger; invalidated by later audit. Do not execute this package. Migrate still-valid requirements into Automate3 only.


# Automate2 UI Outcomes

## Completion Definition

> **Superseded.** The following were targets, not proven achievements. Current status is in `docs/automate3/14-truth-audit-matrix.md`.

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

> **Superseded.** These were planned targets, not proven achievements. All "complete" claims are unproven. Current status is in `docs/automate3/14-truth-audit-matrix.md`.

- P0 baseline guardrails: historical claim, must be re-verified
- P0 UI blockers: historical claim, must be re-verified
- P1 UI-enabling support: historical claim, must be re-verified
- P1 shell/navigation: historical claim, must be re-verified
- P1 Stage Video Edit: historical claim, must be re-verified
- P1 Match Video Edit: historical claim, must be re-verified
- P1 Performance Library: historical claim, must be re-verified
- P1 proof items: historical claim, must be re-verified
- Deferred: packaged automation proof and packaged PiP playback proof

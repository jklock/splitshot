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

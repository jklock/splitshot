# Track 01: PiP Performance And Merge Editor

## Goal

Make PiP preview smooth enough to sync visually and keep merge adjustments usable during playback.

## Current Problem

The browser shell currently reseeks preview media too aggressively during live playback:

- drift is checked continuously
- a small threshold breach triggers hard seek
- this affects classic secondary preview and merge-preview items
- playback appears jumpy instead of continuous

This makes third-person sync work visually unreliable.

## Required Changes

### Sync strategy

- small drift:
  - bounded playback-rate correction only
- large drift:
  - one hard seek, then resume normal playback

Hard seek allowed only for:

- initial attach
- scrub
- play/pause boundary
- explicit sync nudge
- large drift breach
- source reset

### Drag strategy

- cache preview geometry on drag start
- use lightweight visual movement during drag
- suspend heavy preview reseek/sync during drag
- do not recompute full overlay/video sync on every pointermove
- route commit only on pointerup or debounced settle

### Merge editor UI additions

- explicit sync state visibility
- active correction mode messaging
- clear “visual sync” controls vs “saved offset” controls
- stable feedback for angle-aligned sources

## Proof

- targeted PiP performance test
- merge interaction browser test
- packaged PiP playback proof

## Acceptance

- preview plays smoothly enough to sync by eye
- drag no longer feels unusable during playback
- no per-frame reseek churn during steady playback
